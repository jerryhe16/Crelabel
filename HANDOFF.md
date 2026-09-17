# Crelabel 当前接管说明

更新日期：2026-09-17
当前源码版本：0.8.15
当前负责人：Codex
发布状态：`计划中`。正在为飞书与 GitHub 公开发布移除不可再分发字体、整理开源文档并重建安装包；尚未发布。

当前工作：Codex，分支 `codex/open-source-release`。目标是生成可分发的 0.8.15、更新飞书文档并建立公开 GitHub 仓库；预计修改构建配置、版本文件、README、许可与协作文档。

Git 状态：本地仓库，默认分支 `main` @ `22c443f` 及本条文档提交。未配置远程仓库。

## 当前结论

- **主线是 `main` 上的 0.8.14。** 用户已要求合并换行/统一字号/对齐修复并打安装包。
- `9f9dd93`（布局模板 / 条码与二维码勾选 / 四字段）是 Grok 当时的并发改动；`500c49d` 已带上修复后的 `verify_crelabel.py`（不再访问 `column_combos[4]`）。`codex/preserve-concurrent-layout` 现已与 `main` 同指向 `ec622cd`，**不要再合并一次**。
- 「质检留样」是用户本机配置里的自定义内容，不是产品默认文案。用户已明确不用改。
- 后续 Codex 与 Grok 必须按 `AGENTS.md` 分分支、必要时用 worktree，禁止直接在 `main` 上开功能。
- 用户计划以后把仓库上传 GitHub，再交给其他代理维护。在用户给出远程地址并明确允许推送之前，**不添加 remote、不 push、不改 GitHub 简介**。
- 权威入口只有 `AGENTS.md`、本文件和当前源码。`GROK_QA_TASK.md`、`grok-qa-transcript.md` 与 v0.8.2/v0.8.3 验证目录是历史证据。

## 当前功能基线（0.8.14）

- 两种业务入口：物料标签、整机标签。
- 飞书多维表格直连、扫码授权、本机缓存、Excel/CSV 导入。
- 物料标签：左侧 4 个文字字段 + 日期（不打印 / 今天 / 指定日期）；可勾选打印 Logo / 条形码 / 二维码；自定义文字；Code128；飞书记录二维码。
- 整机标签：样机编号、L/R、记录二维码，默认可显示 Prime Hand Logo；缺完整编号、左右手或记录链接时禁止打印。
- 版式：文字大小统一调整；过长文字按当前字号换行，自定义内容可用 `\n` 手动换行；左/中/右对齐会立刻重排文字。预览可拖动缩放；可保存多个命名模板并切换；「恢复出厂」回到当前纸张的出厂排版。30×20 使用更紧的出厂默认值。
- Zebra ZD888TA：300 dpi RAW ZPL、热转印 `^MTT` / 热敏 `^MTD`、间隙/黑标/连续纸、校准、队列检查修复。
- 精臣 B1 Pro：Windows 驱动打印，一项文字加可选条形码或二维码，小尺寸自动排版。

## 2026-09-16 用户确认主线

用户决定：当前已验证版本可以成为主线；「质检留样」保持现状；后续只要 Codex 与 Grok 能共同开发即可。GitHub 上传由用户稍后安排，不在本次执行。

当前本地安装包（构建产物，不入库）：

- `release/Crelabel-Setup-v0.8.14.exe`
- 大小：66,913,356 bytes
- SHA256：`5E0BBC89DAF359616A99C3F7DE7291909ABDB012596469C0E9A32D1DE2202FD2`
- 便携目录：`release/Crelabel_v0.8.14/Crelabel.exe`（`--self-test` 退出码 0）

历史安装包 `release/Crelabel-Setup-v0.8.13.exe` 仍可留在本地，不再作为开发基线。

## 2026-09-16 接管核验（历史，Codex 当时针对 0.8.12 源码/包）

已执行：

```powershell
python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools\verify_crelabel.py tools\verify_machine_ui.py
python tools\verify_crelabel.py
python tools\verify_machine_ui.py
```

当时结果：语法检查通过；核心回归通过；整机 UI 验证通过；飞书缓存固定 115 条附加断言被跳过。该核验不能替代用户对 0.8.13 的确认。

## 当前未完成和下一步

1. GitHub 远程尚未配置。用户准备好仓库地址后，再由用户或被明确授权的代理添加 remote 并推送 `main`。不要抢先创建 GitHub 仓库。
2. 未上传飞书，未替换飞书附件或简介。
3. README 正文仍是早期历史说明；同事使用以 `Crelabel-Quick-Guide.txt` 为准。发布到 GitHub 前可再整理 README，但不要把历史说明当成当前规范。
4. Zebra 打印速度/浓度（`^PR` / `~SD`）仍是可选后续功能，需先定允许值与测试，且须用户点名后再做。
5. `verify_crelabel.py` 末尾飞书缓存「115 条」断言仍可能被跳过，不影响核心回归。

下一位代理最先应该做：读 `AGENTS.md` 和本文件；确认「当前工作」为空；从 `main` 拉 `codex/<task>` 或 `grok/<task>` 分支；若与另一代理同时改代码，使用独立 worktree。

## 最近交接记录

### 2026-09-16 / Grok / 发布 0.8.14 安装包

- 目标：用户要求合并 `grok/unified-text-wrap-align` 并发布安装包。
- 修改：版本号同步为 0.8.14（`crelabel.py`、`build.ps1`、`Crelabel.iss`、`Crelabel-Quick-Guide.txt`、`README.md`、`HANDOFF.md`）。`main` 已快进包含 `3d8760b` 与 `22c443f`。
- 验证：`py_compile` 通过；`verify_crelabel.py` 核心回归通过（飞书缓存 115 条附加断言仍 skipped）；`verify_machine_ui.py` 通过；打包程序 `--self-test` 退出码 0。
- 产物：`release/Crelabel-Setup-v0.8.14.exe`（66,913,356 bytes，SHA256 `5E0BBC89DAF359616A99C3F7DE7291909ABDB012596469C0E9A32D1DE2202FD2`）。
- 发布：仅本地安装包；未上传飞书、未推送 GitHub。安装前请先关闭正在运行的 `C:\Program Files\Crelabel\Crelabel.exe`。

### 2026-09-16 / Grok / 统一字号、换行与对齐

- 目标：规格描述过长不再缩小字号，改为换行；文字大小统一调整；修复文字对齐点击无效。
- 分支：`grok/unified-text-wrap-align`。
- 修改：`label_core.py`、`crelabel.py`、`tools/verify_crelabel.py`、`HANDOFF.md`。
- 行为：按当前统一字号自动换行；自定义内容可用 `\n` 手动换行；版式里只保留一个「文字大小」；改对齐会清掉文字的拖动钉住位置并立即重排。
- 验证：`py_compile` 通过；`verify_crelabel.py` 核心回归通过（飞书缓存 115 条附加断言仍 skipped）；`verify_machine_ui.py` 通过。
- 未做：不改版本号、不构建安装包、未合并 `main`、未实机打印长规格描述。
- 下一步：用户或 Codex 审查后合并；实机看 30×20 / 40×30 换行和对齐。

### 2026-09-16 / Grok / 记录已验证主线

- 目标：按用户确认，把 0.8.13 记为后续共同开发主线；不改「质检留样」；不上传 GitHub。
- 分支：`grok/record-verified-mainline`。
- 修改：`HANDOFF.md`、`AGENTS.md`、`README.md` 入口提示、`tools/verify_crelabel.py`（测试改为不读取本机配置）。未改产品源码，未改版本号，未构建新安装包，未改「质检留样」。
- 验证：`py_compile` 通过；`verify_crelabel.py` 核心回归通过（飞书缓存「115 条」附加断言仍 skipped）；`verify_machine_ui.py` 通过。测试曾因读取本机配置里关闭的条码/二维码勾选而失败，已改为空配置隔离。
- 发布：未推送远程，未上传飞书。
- 下一步：Codex 或其他代理可从 `main` 开新功能分支。GitHub 等用户给出地址。

### 2026-09-16 / Grok 最新版确认为基线

- 用户决定：以 Grok 当前最新版为后续开发基准。
- 当前源码：0.8.13；涉及 `crelabel.py`、`tools/verify_crelabel.py`、`build.ps1`、`Crelabel.iss` 和 `Crelabel-Quick-Guide.txt`。
- 自动验证：语法检查、`verify_crelabel.py`、`verify_machine_ui.py` 均通过；飞书缓存固定 115 条附加断言仍被跳过。
- Git：这套源码进入 `main` 后即为权威开发基线；此前“来源待确认”的说明被本条结论取代。
- 发布：当时文档仍写尚未构建 0.8.13；其后已构建安装包，并由用户确认为主线（见上条）。

### 2026-09-16 / Codex / 并发改动保护（已由后续结论取代）

- 目标：Git 基线提交后发现 `crelabel.py` 出现一组不属于仓库初始化任务的并发源码改动，避免覆盖或丢失。
- 分支：`codex/preserve-concurrent-layout`。
- 内容：命名布局模板、条码/二维码显示开关及相关界面逻辑；当时来源待确认，后续用户已确认这是 Grok 最新版，并已进入 `main`。
- 验证：当时 `verify_crelabel.py` 因 `column_combos[4]` 越界失败；`500c49d` 已修复，不必再合并该 WIP 提交。
- 发布：未构建安装包，未上传飞书，未修改飞书简介。

### 2026-09-16 / Codex / Git 基线

- 目标：建立 Codex 与 Grok 可审查、可回滚的本地 Git 协作基线。
- 修改：新增 `.gitignore`、`.gitattributes`，并在 `AGENTS.md` 增加分支与 worktree 规则。
- 基线：`main` 的源码基线提交为 `ccd4e9a`（`chore: establish Crelabel source baseline`）。
- 排除项：构建目录、安装包、第三方可执行文件、验证输出、本机缓存、数据库和可能包含授权信息的本地文件。
- 远程：未配置；未经用户指定平台和目标，不推送代码。
- 发布：未改软件功能，未构建新版本，未上传飞书，未修改飞书简介。

### 2026-09-16 / Codex

- 目标：审核 Grok 留下的接管描述并建立双方可持续协作方式。
- 修改：新增 `AGENTS.md` 与 `HANDOFF.md`；将旧 Grok 任务和 README 标记为历史入口。
- 验证：见上方历史接管核验。
- 发布：未构建新版本，未上传飞书，未修改飞书简介。
