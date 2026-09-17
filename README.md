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

## 开发环境

要求 Windows 10/11、Python 3.11+。安装依赖后运行：

```powershell
python -m pip install -r requirements.txt
python crelabel.py
```

运行核心检查：

```powershell
python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools\verify_crelabel.py
python tools\verify_crelabel.py
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
