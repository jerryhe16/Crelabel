from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feishu_client import load_feishu_data


def export_package(url: str) -> dict:
    data = load_feishu_data(url)
    return {
        "format": "prime-hand-feishu-print-package",
        "version": 1,
        "source_url": url,
        "base_title": data.get("title", ""),
        "table_id": data["table_id"],
        "view_id": data["view_id"],
        "fields": data["fields"],
        "records": data["records"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出飞书多维表格记录和逐行分享链接")
    parser.add_argument("url", help="包含 table 和 view 参数的飞书多维表格完整链接")
    parser.add_argument("output", help="输出 JSON 数据包路径")
    args = parser.parse_args()
    package = export_package(args.url)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output.resolve()),
        "records": len(package["records"]),
        "fields": len(package["fields"]),
        "share_links": sum(bool(item["record_share_link"]) for item in package["records"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
