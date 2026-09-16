# Crelabel 第二阶段执行任务（历史归档）

> 本文件对应旧版 0.6.4，已经失效。Grok、Codex 或其他代理现在接手时，请先阅读 `AGENTS.md` 和 `HANDOFF.md`，不要按本文件的版本号、功能范围或发布步骤继续工作。

你在 `C:\Users\Administrator\Documents\prime hand\label_bridge` 工作。请直接检查并在必要时修复代码，然后运行验证。不要重构无关文件，不要删除旧 release，不要安装或捆绑任何未知来源的 Zebra 驱动。

## 产品边界

- 软件名必须是 `Crelabel`，当前版本 `0.6.4`。
- 默认且主要支持 `Zebra ZD888TA 300 dpi ZPL`。
- 默认标签纸为 40 × 30 mm，允许修改宽高和使用 50×30、60×40 预设。
- UI 要能切换：
  - 热转印（碳带）：打印 ZPL 必须含 `^MTT`。
  - 热敏（无碳带）：打印 ZPL 必须含 `^MTD`。
- UI 支持日期：不打印、使用今天、指定日期。
- 支持飞书多维表格链接、Excel、CSV；最多选 5 列；每条飞书记录链接生成二维码。
- 飞书连接默认使用 24 小时本地缓存，刷新按钮强制在线读取。
- Zebra 官方驱动 EULA 需要用户确认，因此 Crelabel 只检测打印队列、启动官方安装流程，或使用部署方自行放入 `drivers/ZebraDriverSetup.exe` 的获批内部副本。

## 你需要执行

1. 检查 `crelabel.py`、`label_core.py`、`feishu_client.py`、`Crelabel.iss`、`build.ps1` 是否满足上述边界。
2. 只修复明确缺陷；保持现有现代双栏界面结构。
3. 运行并记录以下自动验证：
   - `python -m py_compile crelabel.py label_core.py feishu_client.py`
   - 生成 40×30 mm / 300 dpi 标签，使用 `zxingcpp` 同时解码 Code 128 和二维码。
   - 断言热转印 ZPL 含 `^MTT`，热敏 ZPL 含 `^MTD`。
   - Qt 使用 `QT_QPA_PLATFORM=offscreen` 启动窗口，加载 `sample.csv`，确认纸张 40×30、300 dpi、两种打印方式选项和三种日期模式存在。
   - 不要调用真实打印机，不要修改飞书在线数据。
4. 不要构建最终安装包；主代理会在检查差异后构建和验收。
5. 最终只报告：改了什么、验证结果、仍需人工/实机验证的项目。
