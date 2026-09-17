# Crelabel 当前接管说明

更新日期：2026-09-17
当前源码版本：0.8.15
当前负责人：无
状态：源码和飞书便携包已发布；自动验证通过；本次未做实机打印。

## 当前权威位置

- GitHub：`https://github.com/zerodemary/Crelabel`
- 默认分支：`main`
- 飞书发布文档：`https://ncn5zs910x3g.feishu.cn/wiki/R8oYwCCP0iRENSkmnmMcqGPGngh`
- 飞书文档版本：revision 386
- 飞书附件：`Crelabel_v0.8.15_portable_publish.zip`
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
