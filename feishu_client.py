from __future__ import annotations

import json
import os
import shutil
import subprocess
import hashlib
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


EXCLUDED_FIELD_TYPES = {"attachment", "link"}
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Crelabel" / "cache"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60
CRELABEL_CLI_CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Crelabel" / "lark-cli"
CONFIG_URL_PROGRESS = "__CRELABEL_CONFIG_URL__="
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
REQUIRED_SCOPES = (
    "base:field:read",
    "base:record:read",
    "base:table:read",
    "base:view:read",
    "wiki:node:retrieve",
)


class FeishuError(RuntimeError):
    pass


SHARED_VIEW_MESSAGE = (
    "你粘贴的是飞书“共享视图”链接（/share/base/view/），该链接只能用于浏览，"
    "不包含 Crelabel 读取数据所需的多维表格、数据表和视图 ID。\n\n"
    "请在飞书中打开原始多维表格，然后复制浏览器地址栏里的内部链接。"
    "正确链接通常包含 /wiki/ 或 /base/，并带有 table= 和 view= 参数。\n\n"
    "如果你只能打开共享页面，请让表格管理员为你开通原始多维表格访问权限。"
)


def validate_feishu_url(url: str) -> None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FeishuError("请输入完整的飞书多维表格链接。")
    if "/share/base/view/" in parsed.path.lower():
        raise FeishuError(SHARED_VIEW_MESSAGE)
    if not re.search(r"/(base|wiki|share/base/record)/[^/]+", parsed.path):
        raise FeishuError("请粘贴飞书多维表格的 /base/ 或 /wiki/ 原始链接，或记录分享链接。")


def table_url(url: str, table_id: str) -> str:
    """Switch tables without carrying another table's view/record filters."""
    parsed = urlparse(url.strip())
    query = parse_qs(parsed.query)
    for key in ("view", "record", "record_id"):
        query.pop(key, None)
    query["table"] = [table_id]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def discover_feishu_source(url: str, progress: Callable[[str], None] | None = None) -> dict:
    validate_feishu_url(url)
    notify = progress or (lambda _message: None)
    notify("正在解析链接并读取数据表列表…")
    resolved = run_cli("base", "+url-resolve", "--url", url.strip(), "--as", "user", "--format", "json")
    base_token = resolved.get("base_token")
    if not base_token:
        raise FeishuError("该链接未指向多维表格，请复制原始多维表格链接。")
    tables = run_cli("base", "+table-list", "--base-token", base_token,
                     "--as", "user", "--format", "json").get("tables", [])
    tables = [{"id": item.get("id") or item.get("table_id"),
               "name": item.get("name") or item.get("title") or item.get("id") or item.get("table_id")}
              for item in tables if item.get("id") or item.get("table_id")]
    if not tables:
        raise FeishuError("该多维表格没有可访问的数据表。")
    query = parse_qs(urlparse(url).query)
    selected = (query.get("table") or [resolved.get("table_id", "")])[0]
    if selected and selected not in {item["id"] for item in tables}:
        raise FeishuError("链接指定的数据表不存在或没有访问权限，请检查链接。")
    # A root link with several tables must wait for the user's choice.
    if not selected and len(tables) == 1:
        selected = tables[0]["id"]
    return {"source_url": url.strip(), "base_token": base_token, "tables": tables,
            "table_id": selected, "title": resolved.get("title", "飞书多维表格")}


def _extract_json(raw: str) -> dict:
    """Accept lark-cli progress text followed by a JSON payload."""
    decoder = json.JSONDecoder()
    candidates: list[dict] = []
    for index, character in enumerate(raw):
        if character != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            candidates.append(payload)
    if candidates:
        envelopes = [item for item in candidates if "ok" in item]
        if envelopes:
            return envelopes[-1]
        command_payloads = [item for item in candidates if any(key in item for key in ("data", "error"))]
        return (command_payloads or candidates)[-1]
    raise json.JSONDecodeError("No JSON object found", raw, 0)


def cli_runtime() -> str:
    app_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    appdata = Path(os.environ.get("APPDATA", ""))
    candidates = [
        app_root / "runtime/lark-cli.exe",
        app_root / "vendor/lark-cli/lark-cli.exe",
        appdata / "npm/node_modules/@larksuite/cli/bin/lark-cli.exe",
    ]
    system_cli = shutil.which("lark-cli.exe") or shutil.which("lark-cli")
    if system_cli:
        candidates.append(Path(system_cli))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FeishuError("Crelabel 内置飞书运行环境缺失。请重新安装完整版本。")


def cli_config_dir() -> Path:
    # Crelabel deliberately owns an isolated profile. Reusing ~/.lark-cli made
    # the app inherit stale app permissions from unrelated CLI installations.
    explicit = os.environ.get("CRELABEL_LARK_CONFIG_DIR", "").strip()
    if explicit:
        return Path(explicit)
    return CRELABEL_CLI_CONFIG_DIR


def migrate_existing_app_config() -> bool:
    """Seed Crelabel with an existing CLI app config without reusing its profile.

    Only the app configuration is copied. User authorization is intentionally
    performed again with Crelabel's exact scopes.
    """
    target = cli_config_dir() / "config.json"
    if target.exists():
        return False
    source = Path.home() / ".lark-cli" / "config.json"
    if not source.exists() or source.resolve() == target.resolve():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def cli_env() -> dict[str, str]:
    config_dir = cli_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LARKSUITE_CLI_CONFIG_DIR"] = str(config_dir)
    env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
    env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
    return env


def run_cli(*args: str) -> dict:
    executable = cli_runtime()
    result = subprocess.run(
        [executable, *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    raw = result.stdout.strip() or result.stderr.strip()
    try:
        payload = _extract_json(raw)
    except json.JSONDecodeError as exc:
        raise FeishuError(f"飞书命令返回了无法识别的内容：{raw[:500]}") from exc
    if result.returncode != 0 or payload.get("ok") is False:
        error = payload.get("error", {})
        hint = error.get("hint")
        message = error.get("message") or raw[:500]
        lowered = message.lower()
        if "base view share url" in lowered or "does not support resolving base view share urls" in lowered:
            raise FeishuError(SHARED_VIEW_MESSAGE)
        if "device code is invalid" in lowered or "restart the device authorization flow" in lowered:
            raise FeishuError("飞书授权二维码已失效，需要重新生成授权二维码。")
        if "need_user_authorization" in lowered:
            raise FeishuError("当前飞书授权已失效或权限不足，请重新扫码授权后再连接。")
        raise FeishuError(f"{message}{'\n' + hint if hint else ''}")
    return payload.get("data", payload)


def is_cli_configured() -> bool:
    result = subprocess.run(
        [cli_runtime(), "config", "show"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=cli_env(),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0


def configure_and_begin_auth(progress: Callable[[str], None] | None = None) -> dict:
    notify = progress or (lambda _message: None)
    if migrate_existing_app_config():
        notify("已自动导入现有飞书应用配置，正在生成授权二维码…")
    if not is_cli_configured():
        notify("首次使用：正在生成飞书应用配置二维码…")
        process = subprocess.Popen(
            [cli_runtime(), "config", "init", "--new", "--lang", "zh_cn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=cli_env(),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output: list[str] = []
        config_url_sent = False
        if process.stdout:
            for line in process.stdout:
                cleaned = ANSI_ESCAPE.sub("", line).strip()
                if cleaned:
                    output.append(cleaned)
                match = re.search(r"https?://\S+", cleaned)
                if match and not config_url_sent:
                    notify(CONFIG_URL_PROGRESS + match.group(0))
                    config_url_sent = True
        return_code = process.wait()
        if return_code != 0:
            details = "\n".join(output[-8:])
            raise FeishuError(f"飞书应用配置未完成。请重新扫码再试。{f'\n{details}' if details else ''}")
        if not is_cli_configured():
            raise FeishuError("飞书应用配置没有保存成功，请重新扫码再试。")
        notify("应用配置完成，正在生成用户授权二维码…")
    return begin_user_auth()


def environment_status() -> dict:
    executable = cli_runtime()
    configured = is_cli_configured()
    result: dict = {
        "runtime_ok": True,
        "runtime_path": executable,
        "config_path": str(cli_config_dir()),
        "reused_existing_config": False,
        "configured": configured,
        "authorized": False,
        "required_scopes": list(REQUIRED_SCOPES),
        "missing_scopes": list(REQUIRED_SCOPES),
        "scope_ready": False,
    }
    if not configured:
        return result
    try:
        auth = run_cli("auth", "status", "--json", "--verify")
        result["authorized"] = bool(auth.get("verified") or auth.get("userOpenId") or auth.get("identity") == "user")
        result["auth"] = auth
        if result["authorized"]:
            scope_check = run_cli("auth", "check", "--scope", " ".join(REQUIRED_SCOPES), "--json")
            result["missing_scopes"] = scope_check.get("missing") or []
            result["scope_ready"] = not result["missing_scopes"]
    except FeishuError as exc:
        result["auth_error"] = str(exc)
    return result


def begin_user_auth() -> dict:
    # Explicit scopes keep the authorization stable across lark-cli releases
    # and include wiki resolution for /wiki/ Base links.
    return run_cli(
        "auth", "login", "--scope", " ".join(REQUIRED_SCOPES),
        "--no-wait", "--json",
    )


def complete_user_auth(device_code: str) -> dict:
    result = run_cli("auth", "login", "--device-code", device_code, "--json")
    scope_check = run_cli("auth", "check", "--scope", " ".join(REQUIRED_SCOPES), "--json")
    missing = scope_check.get("missing") or []
    if missing:
        raise FeishuError("飞书仍有必要权限未授权，请重新扫码授权。缺少：" + "、".join(missing))
    return result


def chunks(items: list[str], size: int):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _cache_file(url: str) -> Path:
    digest = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _read_cache(url: str, max_age_seconds: int) -> dict | None:
    path = _cache_file(url)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 2 or not payload.get("data", {}).get("records"):
            return None
        if time.time() - float(payload.get("cached_at_epoch", 0)) > max_age_seconds:
            return None
        data = payload["data"]
        data["cache_hit"] = True
        data["cached_at"] = payload.get("cached_at", "")
        return data
    except Exception:
        return None


def _read_stale_cache(url: str) -> dict | None:
    """Read an older snapshot for connection metadata and stable share links."""
    path = _cache_file(url)
    try:
        return json.loads(path.read_text(encoding="utf-8"))["data"]
    except Exception:
        return None


def _write_cache(url: str, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 2,
        "cached_at_epoch": time.time(),
        "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data,
    }
    _cache_file(url).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_feishu_data(
    url: str,
    progress: Callable[[str], None] | None = None,
    force_refresh: bool = False,
    cache_max_age_seconds: int = CACHE_MAX_AGE_SECONDS,
) -> dict:
    notify = progress or (lambda _message: None)
    normalized_url = url.strip()
    validate_feishu_url(normalized_url)
    if not force_refresh:
        cached = _read_cache(normalized_url, cache_max_age_seconds)
        if cached:
            notify("已从本机缓存快速打开；需要最新数据时点击“刷新”")
            return cached
    parsed = urlparse(normalized_url)
    query = parse_qs(parsed.query)
    table_id = (query.get("table") or [""])[0]
    view_id = (query.get("view") or [""])[0]
    previous = _read_stale_cache(normalized_url) or {}

    cached_base_token = previous.get("base_token", "")
    if cached_base_token:
        notify("正在复用已验证的飞书连接…")
        resolved = {"base_token": cached_base_token, "title": previous.get("title", "飞书多维表格"),
                    "table_id": previous.get("table_id", ""), "view_id": previous.get("view_id", "")}
    else:
        notify("首次连接：正在解析飞书链接…")
        resolved = run_cli("base", "+url-resolve", "--url", normalized_url, "--as", "user", "--format", "json")
    base_token = resolved.get("base_token")
    if not base_token:
        raise FeishuError("该链接未指向多维表格，请复制原始多维表格链接。")
    table_id = table_id or resolved.get("table_id", "")
    # An explicit table without a view means all its records, especially after
    # switching away from a wiki/record link's original table.
    if "table" not in query:
        view_id = view_id or resolved.get("view_id", "")

    if not table_id:
        if previous.get("table_id"):
            table_id = previous["table_id"]
        else:
            tables = run_cli(
                "base", "+table-list", "--base-token", base_token,
                "--as", "user", "--format", "json",
            ).get("tables", [])
            if len(tables) == 1:
                table_id = tables[0].get("id") or tables[0].get("table_id", "")
            else:
                raise FeishuError("链接没有定位到具体数据表。请打开目标表格/视图后，复制带 table 参数的完整链接。")

    cached_fields = previous.get("fields", []) if not force_refresh and previous.get("table_id") == table_id else []
    if cached_fields:
        printable_fields = cached_fields
        notify("已复用字段配置，正在读取最新记录…")
    else:
        notify("正在读取可打印字段…")
        field_info = run_cli(
            "base", "+field-list", "--base-token", base_token,
            "--table-id", table_id, "--as", "user", "--format", "json",
        )
        printable_fields = [
            item["name"] for item in field_info.get("fields", [])
            if item.get("type") not in EXCLUDED_FIELD_TYPES
        ]
    if not printable_fields:
        raise FeishuError("目标数据表没有可打印字段。")

    records: list[dict] = []
    seen_record_ids: set[str] = set()
    offset = 0
    while True:
        notify(f"正在读取记录… 已读取 {len(records)} 条")
        args = [
            "base", "+record-list", "--base-token", base_token,
            "--table-id", table_id, "--limit", "200", "--offset", str(offset),
            "--as", "user", "--format", "json",
        ]
        if view_id:
            args.extend(["--view-id", view_id])
        for field_name in printable_fields:
            args.extend(["--field-id", field_name])
        page = run_cli(*args)
        fields = page.get("fields", printable_fields)
        record_ids = page.get("record_id_list", [])
        rows = page.get("data", [])
        if len(record_ids) != len(rows):
            raise FeishuError("飞书记录和记录ID数量不一致，请刷新重试。")
        for record_id, row in zip(record_ids, rows):
            if not record_id or record_id in seen_record_ids or len(row) != len(fields):
                raise FeishuError("飞书返回了重复或不完整的记录，已停止读取，请刷新重试。")
            seen_record_ids.add(record_id)
            records.append({
                "record_id": record_id,
                "fields": dict(zip(fields, row)),
                "record_share_link": "",
            })
        if not page.get("has_more"):
            break
        if not rows:
            raise FeishuError("飞书返回了不完整分页，已停止读取。")
        offset += len(rows)

    cached_links = {
        item.get("record_id", ""): item.get("record_share_link", "")
        for item in previous.get("records", [])
        if item.get("record_id") and item.get("record_share_link")
    }
    links: dict[str, str] = dict(cached_links)
    record_ids = [item["record_id"] for item in records]
    missing_record_ids = [record_id for record_id in record_ids if record_id not in links]
    batches = list(chunks(missing_record_ids, 100))

    def fetch_links(batch: list[str]) -> dict[str, str]:
        share_data = run_cli(
            "base", "+record-share-link-create", "--base-token", base_token,
            "--table-id", table_id, "--record-id", ",".join(batch),
            "--as", "user", "--format", "json",
        )
        return share_data.get("record_share_links", {})

    if batches:
        notify(f"正在为 {len(missing_record_ids)} 条新增记录生成二维码链接…")
        with ThreadPoolExecutor(max_workers=min(3, len(batches))) as executor:
            futures = {executor.submit(fetch_links, batch): index for index, batch in enumerate(batches, start=1)}
            for completed, future in enumerate(as_completed(futures), start=1):
                links.update(future.result())
                notify(f"正在生成分享链接… {completed}/{len(batches)} 批")
    elif record_ids:
        notify("已复用逐行二维码链接")
    for item in records:
        item["record_share_link"] = links.get(item["record_id"], "")

    notify("飞书数据读取完成")
    result = {
        "source_url": normalized_url,
        "title": resolved.get("title", "飞书多维表格"),
        "base_token": base_token,
        "table_id": table_id,
        "view_id": view_id,
        "fields": printable_fields,
        "records": records,
        "cache_hit": False,
    }
    _write_cache(normalized_url, result)
    return result
