# Crelabel 协作约定

本文件是 Codex、Grok 和其他开发代理的唯一协作入口。开始工作前必须完整阅读本文件和 `HANDOFF.md`。

## 1. 当前原则

- 一次只允许一个代理修改同一批文件。接手前先在 `HANDOFF.md` 的“当前工作”中写明负责人、目标和预计修改文件；完成或暂停时清除负责人并留下结果。
- 只做任务要求内的最小改动，不顺手重构无关代码，不删除历史 `release/`、验证图片或用户数据。
- 不把聊天记录当作唯一依据。任何影响后续接管的决定、限制、验证结果和未完成项，都要同步到 `HANDOFF.md`。
- 禁止写入或提交飞书 App Secret、访问令牌、个人授权信息。飞书数据默认只读，不修改或删除在线记录。

## 2. 文件职责

- `crelabel.py`：PySide6 界面、交互、配置、打印流程编排。
- `label_core.py`：字段映射、标签渲染、条码/二维码、ZPL、Windows 打印队列。
- `feishu_client.py`：内置 lark-cli、授权、缓存、多维表格读取。
- `compact_label.py` / `windows_print.py`：精臣 B1 Pro 的紧凑布局与 Windows 图形打印。
- `tools/verify_crelabel.py`：核心回归测试。
- `tools/verify_machine_ui.py`：整机标签、真实缓存数据和 UI 几何验证；不会向打印机发送任务。
- `build.ps1` / `Crelabel.iss`：便携目录和安装包构建。
- `Crelabel-Quick-Guide.txt`：同事实际使用说明。
- `HANDOFF.md`：当前真实状态和最近交接记录。

## 3. 不可破坏的产品边界

- Zebra 主路径为 `ZD888TA 300 dpi ZPL`，以 RAW ZPL 打印；热转印必须含 `^MTT`，热敏必须含 `^MTD`。
- 物料标签保留 Code128 与飞书记录二维码，最多选择 5 个文字字段；同一字段不能重复。
- 整机标签以样机编号、L/R 和详情二维码为核心；缺少完整编号、左右手或记录链接时必须阻止打印，不能猜测。
- 精臣 B1 Pro 走 Windows 驱动，不发送 Zebra ZPL；小标签必须限制内容数量并在放不下时明确报错。
- 预览调整必须同步到实际打印；尺寸、二维码和条码不得靠模糊缩放破坏可扫描性。
- 飞书授权使用同事本人身份，二维码仍遵守原表权限；不得回写或新增“分享链接”列。
- “自动验证通过”不等于“实机验证通过”。真实出纸、手机扫码、碳带/介质匹配必须单独记录。

## 4. 修改流程

1. 阅读 `HANDOFF.md`，确认当前版本、已知问题和是否有人正在修改。
2. 在 `HANDOFF.md` 登记当前工作；若已有负责人修改同一文件，先停止并协调。
3. 修改源码时同步补充或更新测试，不只改界面截图。
4. 至少执行：

   ```powershell
   python -m py_compile crelabel.py label_core.py feishu_client.py compact_label.py windows_print.py tools\verify_crelabel.py tools\verify_machine_ui.py
   python tools\verify_crelabel.py
   python tools\verify_machine_ui.py
   ```

5. 将执行命令、通过/失败结果、生成文件和未验证项写入 `HANDOFF.md`。
6. 只有用户明确要求并确认版本后，才更新版本号、构建安装包或发布。

## 5. Git 协作流程

- `main` 只保存已经检查过的稳定基线。初始化之后，Codex 和 Grok 不直接在 `main` 上开发功能。
- Codex 分支命名为 `codex/<task-slug>`，Grok 分支命名为 `grok/<task-slug>`；一个任务使用一个分支。
- 两个代理需要同时工作时，使用独立 worktree，避免共享工作目录互相覆盖：

  ```powershell
  git worktree add ..\label_bridge-codex-<task> -b codex/<task>
  git worktree add ..\label_bridge-grok-<task> -b grok/<task>
  ```

- 开始前确认 `git status` 干净，并在 `HANDOFF.md` 登记负责人、目标、分支和预计修改文件。
- 提交只包含本任务相关的源码、测试和文档；不得提交安装包、构建目录、验证输出、本机缓存、令牌或用户数据。
- 交接时提供分支名、提交号、差异范围、验证结果和未验证项。未经审查不得合并、变基或删除对方分支。
- 公开远程仓库为 `https://github.com/zerodemary/Crelabel`。其他代理仍以本文件和 `HANDOFF.md` 为唯一入口：先读这两份文件，再从最新 `main` 开自己的 `codex/<task>` 或 `grok/<task>` 分支。不要假设聊天记录仍可用。
- 禁止 force-push `main`、改写已共享历史、在未登记时修改同一批文件、提交 `release/`、`dist/`、`build/`、第三方驱动、字体、授权信息或用户数据。
- 功能开发通过 Pull Request 交由 Codex 或维护者审查；不得自行合并、发布安装包或更新飞书附件。

## 6. 版本和发布门禁

- 普通开发阶段不改版本号，不覆盖安装包。
- 确认发布时，必须同步修改 `APP_VERSION`、`build.ps1`、`Crelabel.iss`、`Crelabel-Quick-Guide.txt` 和 release 目录名。
- 构建后用以下方式检查 GUI 程序退出码：

  ```powershell
  $p = Start-Process -FilePath .\release\Crelabel_vX.Y.Z\Crelabel.exe -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
  $p.ExitCode
  ```

- 交付前核对完整路径、文件名、大小和 SHA256；不要手写或猜测下载链接。
- GitHub 只发布源码。飞书默认发布免安装便携 ZIP；只有确认 Inno Setup 商业使用许可、驱动再分发许可和其他第三方许可后，才可对外发布安装版。
- **未经用户明确确认，不上传飞书、不改飞书简介、不替换线上附件。**
- Codex 默认负责最终差异审查、版本同步、安装包验收和发布；Grok 可以实现与测试，但不得自行发布，除非用户当次明确授权。

## 7. 交接报告格式

每次完成或暂停时，在 `HANDOFF.md` 追加一条：

- 负责人和日期
- 目标
- 实际修改文件
- 已执行验证及结果
- 当前产物（如有）
- 实机/权限/外部系统未验证项
- 下一位代理最先应该做什么

状态词只使用：`计划中`、`实现完成`、`自动验证通过`、`安装包已构建`、`实机验证通过`、`已发布`。不得把前一状态冒充后一状态。
