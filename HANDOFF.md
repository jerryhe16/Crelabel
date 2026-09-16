# Crelabel 当前接管说明

更新日期：2026-09-16  
当前源码版本：0.8.12  
当前负责人：无  
发布状态：本地安装包已存在；是否被用户实机确认、是否应上传飞书，需要重新确认。

Git 状态：本地仓库，默认分支 `main`，源码基线提交 `ccd4e9a`；未配置远程仓库。

## 当前结论

当前源码可以继续维护，核心回归和整机 UI 验证可运行，但历史说明存在版本漂移。后续只以本文件、`AGENTS.md` 和当前源码为准；`GROK_QA_TASK.md`、`grok-qa-transcript.md` 与 v0.8.2/v0.8.3 验证目录属于历史证据，不代表当前发布状态。

## 当前功能基线

- 两种业务入口：物料标签、整机标签。
- 飞书多维表格直连、扫码授权、本机缓存、Excel/CSV 导入。
- 物料标签：最多 5 个文字字段、自定义文字、Code128、记录二维码、日期。
- 整机标签：样机编号、L/R、记录二维码，可显示 Prime Hand Logo；编号和 L/R 可独立拖动缩放。
- Zebra ZD888TA：300 dpi RAW ZPL、热转印/热敏、间隙/黑标/连续纸、校准、队列检查修复。
- 精臣 B1 Pro：Windows 驱动打印，一项文字加可选条形码或二维码，小尺寸自动排版。
- 预览支持直接选择、拖动、缩放和按标签类型保存默认布局。

## 2026-09-16 接管核验

已执行：

```powershell
python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools\verify_crelabel.py tools\verify_machine_ui.py
python tools\verify_crelabel.py
python tools\verify_machine_ui.py
Start-Process release\Crelabel_v0.8.12\Crelabel.exe --self-test -Wait -PassThru
```

结果：

- 语法检查通过。
- 核心回归通过：40×30/300 dpi、Code128、二维码、飞书授权流程、热转印/热敏、介质识别和校准指令。
- 整机 UI 验证通过：5 个完整样机编号、30×20/40×30、二维码解码、L/R、空选择和忙碌状态保护、两种窗口尺寸。
- 打包程序自检退出码为 0。
- `verify_crelabel.py` 的飞书缓存附加检查被跳过，原因是缓存内容与脚本中固定的 115 条断言不一致；核心测试没有因此失败，但该断言需要改为基于当前数据或独立 fixture。
- `verify_machine_ui.py` 会覆盖 `outputs/v0.8.3-validation/results.json`，且旧《验证报告》仍写“通用映射 0/5”，当前结果已变成 5/5；该历史报告不能作为当前结论。

当前本地安装包：

- `release/Crelabel-Setup-v0.8.12.exe`
- 大小：66,898,158 bytes
- SHA256：`5A28AE97744E02295E37B07E7B199EA046565C97F47E41F4C76AB0CF05458F81`

## 当前未验证和下一步

1. **实机打印未在本次接管中执行。** 需要斑马实际出纸、白色树脂碳带清晰度、位置、手机扫码和飞书权限检查。
2. 用户当前反馈 ZD888TA 300 dpi 的最低速度是 76 mm/s，驱动界面曾显示“热感”；使用碳带时应为热转印。建议下一项开发是在 Crelabel 中加入 Zebra 打印速度和浓度，并直接输出 `^PR` / `~SD`，避免 RAW ZPL 与驱动首选项不一致。
3. 在实现速度/浓度前，应先确定该机型允许值、默认值、配置是否随任务保存，并增加 ZPL 单元测试；不要先构建或上传。
4. README、`同事使用说明-Crelabel.txt`、`飞书直连环境说明.txt` 仍含旧版本描述，发布下一版前应统一更新，但不要把历史文件当作当前功能规范。
5. 项目已建立本地 Git 仓库，`main` 保存稳定基线；目前没有配置远程仓库。后续功能使用 `codex/*` 或 `grok/*` 分支，并按 `AGENTS.md` 交接和审查。

## 最近交接记录

### 2026-09-16 / Codex / 并发改动保护

- 目标：Git 基线提交后发现 `crelabel.py` 出现一组不属于仓库初始化任务的并发源码改动，避免覆盖或丢失。
- 分支：`codex/preserve-concurrent-layout`。
- 内容：命名布局模板、条码/二维码显示开关及相关界面逻辑；来源待确认，暂不合并到 `main`。
- 验证：`py_compile` 通过；`verify_machine_ui.py` 通过；`verify_crelabel.py` 失败，报错为 `column_combos[4]` 越界，因此当前状态仅为 WIP，不是可发布版本。
- 下一步：由接手者核对这组改动是否为 Grok 正在开发的功能，并修复/更新核心回归后再申请合并。
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
- 验证：见上方“2026-09-16 接管核验”。
- 发布：未构建新版本，未上传飞书，未修改飞书简介。
- 下一步：先由用户确认是否开发“Zebra 速度/浓度”控制；接手代理须先登记当前工作。
