# Crelabel

Crelabel 是面向 Prime Hand 小批量研发和生产现场的 Windows 标签打印工具。它可以读取飞书多维表格、Excel 或 CSV，将物料和整机记录生成可预览、可调整、可扫码追溯的标签。

当前版本：**0.8.15**

## 主要能力

- 物料标签：最多 4 个文字字段加日期，可选 Code128、飞书记录二维码和自定义文字。
- 整机标签：样机编号、L/R、详情二维码和可选 Logo；缺少关键数据时阻止打印。
- 飞书直连：使用同事本人扫码授权读取 Base/Wiki，不回写在线表格。
- Zebra ZD888TA：300 dpi RAW ZPL，支持热转印/热敏、间隙/黑标/连续纸、走纸校准和队列修复。
- 精臣 B1 Pro：通过 Windows 驱动打印，一项文字加可选条形码或二维码，小尺寸自动排版。
- 标签设计：实时预览、拖动缩放、统一字号、自动换行、文字对齐和命名模板。

## 连接自己的飞书多维表格

1. 首次使用点击“飞书扫码授权”，使用本人有表格访问权限的账号完成授权。
2. 在“标签类型”下方粘贴多维表格的 `/base/` 或 `/wiki/` 原始链接，点击“连接链接”。支持不同团队、不同多维表格，不再限制为内置预设。
3. 带 `table=` 的链接直接读取对应数据表；只粘贴多维表格首页链接时，如果有多张表，先从下拉框选择数据表。带 `view=` 的链接保留该视图的筛选和排序；切换数据表后读取新表全部记录，不沿用旧表视图。
4. 在“标签内容”下拉框选择要打印的字段（也可选择链接字段、不打印或自定义文字）。保留现有每张标签最多 4 个字段加日期的布局限制；精臣小标签仍限制为一个文字字段。
5. 点击选择记录，按 Ctrl 多选、Shift 连选，也可全选或清除选择。核对预览和已选张数后，点击“打印选中”。

软件记住每种标签类型最后成功连接的链接。整机标签仍检查样机编号、左右手和记录链接；普通表格使用物料标签模式。读取和生成记录二维码链接均使用本人权限，不回写表格。

共享视图 `/share/base/view/` 无法通过当前飞书 CLI 解析为完整的数据表坐标，会提示改用原始链接；没有访问权限的表格须先取得权限。程序不会通过公开分享页面绕过权限。

拖动元素现在只改变位置：二维码和条码尺寸使用独立于拖动坐标的自动布局测量，其他元素保持原来的位置和尺寸；换行文字不再因重复拖动发生横向漂移。预览与打印使用同一渲染函数。

## 开发与验证

要求 Windows 10/11、Python 3.11+。安装依赖后运行：

```powershell
python -m pip install -r requirements.txt
python crelabel.py
```

运行核心检查：

```powershell
python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools\verify_crelabel.py
python tools\verify_crelabel.py
python tools\verify_source_layout.py
```

`tools/verify_machine_ui.py` 使用未提交的本机飞书测试数据，只适合维护者在配置完成的机器上运行。

## 构建说明

`build.ps1` 会调用 PyInstaller 和 Inno Setup。由于第三方授权限制，仓库不包含以下二进制文件：

- `vendor/lark-cli/lark-cli.exe`：从飞书/Lark 官方渠道获取后放入该目录。
- `drivers/NiimbotPrinterDriverInstaller-3.0.2.1.exe`：可选，仅在确认允许内部再分发后放入 `drivers/`。
- `drivers/ZebraDriverSetup.exe`：可选；必须自行确认 Zebra EULA，正常情况下由软件打开官方安装页面。

应用文字默认使用 Windows 系统字体，仓库不捆绑来源或商用权限不明确的字体文件。

## 协作方式

开发者和代码代理开始工作前必须完整阅读 [AGENTS.md](AGENTS.md) 与 [HANDOFF.md](HANDOFF.md)。

1. 从最新 `main` 创建 `codex/<task>` 或 `grok/<task>` 分支。
2. 在 `HANDOFF.md` 登记负责人、目标和预计修改文件。
3. 修改源码并补充验证。
4. 提交 Pull Request，不直接向 `main` 推送功能提交。
5. 安装包与飞书发布仍需用户实机确认。

更多细节见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 开源许可

代码以 [MIT License](LICENSE) 发布。Prime Hand、Crelabel 名称、Logo、图标及其他品牌资产不包含在 MIT 商标授权中，详见 [NOTICE.md](NOTICE.md)。第三方组件继续适用各自许可证，见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
