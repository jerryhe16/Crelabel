## User

# Crelabel 第二阶段执行任务（由 Grok CLI 执行）

你在 `C:\Users\Administrator\Documents\prime hand\label_bridge` 工作。请直接检查并在必要时修复代码，然后运行验证。不要重构无关文件，不要删除旧 release，不要安装或捆绑任何未知来源的 Zebra 驱动。

## 产品边界

- 软件名必须是 `Crelabel`，当前版本 `0.5.0`。
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

## Assistant

先核对产品边界和核心文件，再只修明确缺陷并跑验证。

## Tools

- ListDir: .

## Assistant

正在读取核心源码和相关任务说明。

## Tools

- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\label_core.py
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\feishu_client.py
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\GROK_QA_TASK.md
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\Crelabel.iss
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\build.ps1
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\crelabel.py (1-400)
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\drivers\README.txt
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\sample.csv
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\requirements.txt
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\crelabel.py (401-834)

## Assistant

对照产品边界后，接着核对安装脚本、驱动检测，以及标签解码相关实现。

## Tools

- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\Crelabel.spec
- Search: ZebraDriverSetup|FeishuLabelPrinter|0\.4\.|0\.5\.|glob\(
- Read: C:\Users\Administrator\Documents\prime hand\label_bridge\Crelabel-Quick-Guide.txt
- Execute: python -c "import zxingcpp, sys; print('zxingcpp', getattr(zxingcpp, '__version__', 'ok')); import PySide6; print('PySide6', PySide6.__version__)" (Check zxingcpp and PySide6 availability)