# Crelabel 当前接管说明

更新日期：2026-09-17
当前源码版本：0.8.15
当前负责人：无
当前工作：2026-09-21，用户指定的 jerryhe16/Crelabel fork，分支 codex/flexible-import-stable-layout；通用飞书链接连接与拖动布局修复。状态：自动验证通过；未发布、未实机打印。
状态：源码和飞书便携包已发布；自动验证通过；本次未做实机打印。

## 当前权威位置

- GitHub：`https://github.com/zerodemary/Crelabel`
- 默认分支：`main`
- 飞书发布文档：`https://ncn5zs910x3g.feishu.cn/wiki/R8oYwCCP0iRENSkmnmMcqGPGngh`
- 飞书文档版本：revision 390
- 飞书附件：`Crelabel_v0.8.15_portable.zip`
- 附件大小：66,933,467 bytes
- SHA256：`06386822652401B6134BE99ECB0C980BD03D42B0C48486558907D87C3278185A`

## 0.8.15 发布说明

- 基于 Grok 0.8.14 主线：保留长文字自动换行、统一字号、文字对齐、命名模板和现有打印功能。
- 移除 `LED Board-7` 字体。该文件自带许可仅允许个人使用，不再进入源码、Git 历史或发布包；程序改用 Windows 系统字体。
- GitHub 只发布源码，不包含安装包、飞书 CLI 二进制、打印机驱动、本机缓存、授权信息或用户数据。
- 飞书发布免安装便携 ZIP，包含 Crelabel、官方飞书 CLI 运行时、Logo、使用说明和第三方声明；不包含精臣或 Zebra 驱动。
- 本机 Inno Setup 显示 `Non-commercial use only`，因此本次生成的 Setup EXE 仅作为本地构建产物，未上传、未发布。若以后需要公开安装版，先确认商业许可。

## 当前验证

- `py_compile`：通过。
- `tools/verify_crelabel.py`：通过；本机缓存固定 115 条的附加检查仍可能跳过，不影响核心回归。
- `tools/verify_machine_ui.py`：通过；使用维护者本机未提交的测试数据。
- 便携版 `Crelabel.exe --self-test`：退出码 0。
- GitHub Actions：Windows 核心测试通过。
- 飞书回读：功能说明、GitHub 链接和 v0.8.15 附件均已确认存在，旧 v0.8.1 附件已删除。
- 未验证：Zebra/精臣真实出纸、白色碳带清晰度、物理位置和手机扫码。

## 开发和发布规则

1. 开始前完整阅读 `AGENTS.md` 和本文件。
2. 从最新 `main` 创建 `codex/<task>` 或 `grok/<task>` 分支；不要直接开发在 `main`。
3. 在本文件登记负责人、目标、分支和预计修改文件。
4. 修改后运行 `AGENTS.md` 中的检查并提交 Pull Request。
5. Codex 或维护者审查差异与验证证据后再合并。
6. 未经用户明确确认，不构建正式发布版、不替换飞书附件、不修改飞书简介。
7. GitHub 不提交第三方二进制、来源不明字体、驱动、缓存、令牌或业务数据。

## 下一项建议

- 邀请同事使用个人 GitHub 账号协作，优先采用分支或 Fork + Pull Request，不共享同一个账号令牌。
- 将具体需求写成 GitHub Issue；让同事的 Codex 在独立分支完成，并在 PR 中附测试结果和未验证项。
- 下一次功能发布时先做真实标签打印和扫码验收，再生成新的飞书附件。

## 2026-09-21 通用飞书链接与拖动修复交接

- 负责人：Codex；目标：用户指定的 fork 支持有权限的任意 Base/Wiki 原始链接、选择表/字段/行，修复拖动导致其他元素尤其二维码尺寸变化。
- 修改：`crelabel.py`、`feishu_client.py`、`label_core.py`、`tools/verify_crelabel.py`、新增 `tools/verify_source_layout.py`、`.github/workflows/ci.yml`、`README.md`、本文件。
- 界面：新增可见链接输入和连接按钮、多表选择；保留原链接视图范围，切表移除旧视图/记录过滤；记住每种标签类型成功连接的链接。链接字段也可选为打印文字，默认不打印链接文字。连接失败或切换数据表时清除旧记录，防止误打旧表。
- 渲染：自动流尺寸测量与手动坐标分离，保留整机编号/LR 的自然分组；换行文字以整个边界框定位，防止多次拖动漂移。预览、ZPL 和 Windows 图形打印仍使用同一渲染入口。
- 飞书：按本机官方 CLI 1.0.96 帮助修复 `--record-ids` 为 `--record-id`；补全 resolver 返回的表/视图坐标处理，拒绝重复或不完整分页。保持 user 身份，不回写在线字段/记录。
- 验证环境：项目 `.venv`，Python 3.12.14，requirements.txt 固定依赖及 zxing-cpp 3.1.1。
- 通过：`python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools/verify_crelabel.py tools/verify_machine_ui.py tools/verify_source_layout.py`；`python tools/verify_crelabel.py`（可选私有缓存缺失，明确跳过）；`python tools/verify_source_layout.py`（13 项离线测试）；`git diff --check`。
- 未通过/未执行完整实表测试：已尝试 `python tools/verify_machine_ui.py`，因仓库未提供 `outputs/machine-live.json` 而退出；该脚本还依赖维护者旧版本基线。新增测试覆盖合成整机布局、二维码独立解码和两个窗口尺寸，不能代替真实数据验证。
- 本地产物：忽略目录 `outputs/source-layout-validation/` 下 1440×900 与 1120×720 界面截图；未构建安装包、未更新版本、未发送打印任务、未上传飞书。
- 限制：共享视图链接仍需换用原始链接；权限不足须本人授权。此次没有用户提供的目标表，未进行真实飞书端到端连接；Zebra/精臣出纸和实物扫码未验证。
- 下一步：审查本分支，在真实目标表连接、选择非连续行、拖动元素后试打一张并扫码。源码 PR 只提交 jerryhe16/Crelabel，不改上游 zerodemary/Crelabel。
- 远端交付：用户于 2026-09-21 明确回复“推送吧”后，功能提交 `db72daf` 已推送至 `jerryhe16/Crelabel` 的 `codex/flexible-import-stable-layout` 分支；已创建 PR https://github.com/jerryhe16/Crelabel/pull/1 ，等待审查，未合并。
