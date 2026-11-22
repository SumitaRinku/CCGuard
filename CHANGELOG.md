# 更新记录

每个版本给出主要变化与验证方式；逐次提交的细节见 git 历史。面向用户的简短更新日志在 `assets/monitor/release-notes.json`，面板“关于”页显示。

## 0.8.0（2026-11-22）

- 导航与标题（提交 `3ed80a7`）：侧栏 `Claude` 改名为 `防漏与清单`，顶部主标题随页面切换更新。
- 状态页防漏联动：整体状态为 `fail` 且 Claude 仍在运行时，状态页顶部显示高危提醒横幅与“立即关闭 Claude”按钮。
- 设置页可视化代理配置：可直接设置代理客户端预设、配置格式与运行配置路径（支持“自动查找”与“浏览…”选择文件），并与通知设置一起原子校验保存。
- 检查清单增强：13 项检查清单顶部显示状态汇总统计；未检测出口时显示“去检测出口”快捷按钮，存在 `需调整` 项时支持一键展开/收起。
- 关于页与诊断摘要：关于页显示作者（`SumitaRinku`）、开源许可（`GPL-3.0-only`）以及 GitHub 仓库／问题反馈／发布页入口；日志页和关于页支持一键复制脱敏诊断摘要（不含 IP、路径或节点名）。
- 验证：本机 Windows 11（Python 3.12.9）通过 339 项单元测试（跳过 1 项自备字体测试）、Node 页面逻辑测试、`compileall`，并实机打开 Edge WebView2 面板截取状态、防漏与清单、设置、关于四页核对排版；推送 CI（Linux 3.12 / 3.10、Windows 3.12）与 `Windows installer` 构建验证均通过。

## 0.7.6（2026-11-22）

- 发布：本仓库 `v0.7.6`（提交 `d2113b9`）。`CCGuard-Setup-0.7.6.exe` SHA-256 `fda996f37542883b51895dc3c799026fd46f1b68b46bf35687802c3d056c2e5d`，另附 `SHA256SUMS-installer-0.7.6.txt`；下载回的资产哈希一致。发布构建通过打包自检 26 项、静默安装、安装后自检、静默卸载；推送 CI 通过。
- Claude Code 检查清单由 11 项扩展为 13 项（提交 `fd5c0b2`）。
- 新增“本机时区与出口一致”自动检查（`timezone_match`）：出口评分后对比出口 IP 的 IANA 时区与本机 UTC 偏移；优先使用标准库 `zoneinfo`，无 `tzdata` 的冻结构建回退到内置夏令时感知偏移表。
- 新增“固定客户端与浏览器环境”自查项（`device_env`）：提醒固定单一客户端与账号，避免同设备多号切换、指纹伪装或自动化驱动。
- 细化 Clash／Mihomo 分流规则检测：要求同时覆盖 `anthropic.com`、`claude.ai` 与 `claude.com`（支持 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`DOMAIN-REGEX`、`RULE-SET`），并检测含 `REJECT`／`REJECT-DROP` 的拦截规则（不回传任何节点名、分组名或地址）。
- 验证：本机 Windows 11（Python 3.12.9）通过 335 项单元测试（跳过 1 项自备字体测试）、Node 页面逻辑检查、`compileall`；推送 CI（Linux 3.12 / 3.10、Windows 3.12）与 `Windows installer` 打包验证均通过。

## 0.7.5（2026-11-21）

- 发布：本仓库 `v0.7.5`（提交 `df50371`），同时包含上面“常驻探测进程”的修复。`CCGuard-Setup-0.7.5.exe` SHA-256 `884e0066986d7c7c15dc4d53275cbcd94ef71e8812346eb5a17c833795bd9f01`，另附 `SHA256SUMS-installer-0.7.5.txt`；下载回的资产哈希一致。发布构建通过打包自检 26 项、静默安装、安装后自检、静默卸载；推送 CI 通过。
- 通知：任一检查变为失效立即通知，不受冷却限制（原先恢复后 120 秒内再次失效、或从降级升级为失效会被冷却吞掉）；降级仍按冷却。只在从失效或降级恢复时提示“回到正常”，从未知恢复不再逐项提示。连续 30 秒全部未知时提醒“无法判断防护状态”。监测进程意外退出时托盘先提示“CCGuard 已停止”再退出（原先静默退出）。托盘改为每 2 秒读取状态。通知规则移到 `tray-alerts.ps1`，Windows 上用真实规则跑状态序列测试；托盘新增仅供测试的 `-NoticeLog` 参数。
- 验证：实机启动托盘、用假状态驱动：失效到通知约 1.0 秒，恢复后冷却期内再次失效照样通知，结束监测进程后 2 秒内提示并在 14 秒后退出。
- 修复：监测有时提示“监测已停止更新”。在实际机器上，每轮采集都新开一个 PowerShell，重新加载网络和防火墙模块，一轮要 14～15 秒，偶尔超过 20 秒超时（整轮记为“未知”）；托盘的停止判定是 3 个采集间隔（默认 15 秒），采集时间正好卡在这条线上。改为常驻、无窗口的 PowerShell 进程，每轮只发一个请求；放行规则列表（约 4 秒）每 60 秒刷新一次。本机实测每轮从约 14.6 秒降到约 1.2 秒，10 项结果不变。托盘停止判定改为 3 个间隔且至少 60 秒。
- 卡住的一轮会结束该进程、下一轮换新的；CCGuard 退出时常驻进程读到输入结束后自行退出。
- 验证：新增测试覆盖进程复用、超时换新、进程退出后换新、输出异常、托盘阈值；Windows 上实际启动常驻进程连续采集两次并确认随输入关闭退出。

## 0.7.4（2026-11-18）

- 发布：本仓库 `v0.7.4`（提交 `dfbb630`）。`CCGuard-Setup-0.7.4.exe` SHA-256 `9843d23affa15b365502b125b6f52e67fc6d2e8350d8b4a32233bb81b8cf399b`，另附 `SHA256SUMS-installer-0.7.4.txt`；下载回的资产哈希一致。发布构建通过打包自检、静默安装、安装后自检、静默卸载；推送 CI 通过。
- Claude 页写明建议使用 Claude 桌面版（Desktop），不建议使用命令行版 Claude Code（CLI）。
- 开机自启列表不再列出 `CoworkVMService`（按用户决定不管它的开机启动）；关闭 Claude 时仍会停止该服务。
- 出口页信息更详细：地区核对、运营商类型与名称、逐项风险标记、滥用评分、反向解析域名、RPKI、出口时区与本机时区对比、Cloudflare 节点与 TLS／HTTP 版本。反向解析去掉含 IP 的主机名，网段不显示；测试检查结果里不含 IP。
- 修复：检查更新显示 “rate limit exceeded”。GitHub 接口未登录时同一 IP 每小时 60 次，代理出口 IP 多人共用时很快用完。接口失败时改为读取 `releases/latest` 的跳转确定最新版本，从该标签的 `release-notes.json` 读更新日志，安装程序与校验文件按固定文件名下载并照常校验；限流时提示原因。
- 验证：单元测试覆盖限流回退、无更新日志、已是最新、跳转地址异常；真实网络下强制接口失败，回退找到 0.7.3、读到更新日志，并按回退给出的地址下载安装程序且通过 SHA-256 校验。

## 0.7.3（2026-11-18）

- 侧栏左上角 CCGuard 标题上移，下方显示当前版本号（读 `scripts/version.py`）。用于从 0.7.2 实测软件内更新。
- 发布：本仓库 `v0.7.3`（提交 `e84b897`）。`CCGuard-Setup-0.7.3.exe` SHA-256 `abff77e102ff601afe62ff162f4d168b9f4f24b7cbf6e676851839ed377efc3f`，另附 `SHA256SUMS-installer-0.7.3.txt`；下载回的资产哈希一致。发布构建通过打包自检、静默安装、安装后自检、静默卸载；推送 CI 通过。

## 0.7.2（2026-11-18）

- 修复：“关于”页“下载并安装”后 CCGuard 退出，但新版本没有安装、也没有重新打开。安装程序已下载并通过校验，原因在启动等待进程的方式：`DETACHED_PROCESS` 让 Windows PowerShell 拿不到控制台，脚本一行未执行就退出，安装程序从未启动。改为只用 `CREATE_NO_WINDOW`，等待进程仍在 CCGuard 退出后继续运行。
- 新增 Windows 回归测试：子进程按 CCGuard 的方式启动等待进程后退出，断言安装程序（用记录参数的替身）在其退出后以 `/SILENT /SUPPRESSMSGBOXES /NORESTART /RELAUNCH` 启动；旧代码下该测试失败。
- 0.7.0、0.7.1 里的这段代码有问题，从这两个版本需手动安装一次 0.7.2。
- 发布：本仓库 `v0.7.2`（提交 `4deb29c`）。`CCGuard-Setup-0.7.2.exe` 由 `Windows installer` 工作流在发布时构建并附上，SHA-256 `83b085da472e2d4acbfefc180f4c75223129ed3490078dcb2076d963f6346370`，另附 `SHA256SUMS-installer-0.7.2.txt`；下载回的资产哈希一致。发布构建通过打包自检、静默安装、安装后自检、静默卸载；推送 CI 在 Linux、Windows（3.12）与 Linux 3.10 通过，Windows 上实际运行了新回归测试。

## 0.7.1（2026-11-18）

- 修复：用 CCGuard 关闭 Claude 后，任务管理器的 Claude 分组里仍剩 `cowork-svc.exe` 和 `Runtime Broker`。前者是 Claude 安装包注册的 Windows 服务 `CoworkVMService`（显示名 Claude，LocalSystem，开机自动启动），后者是带 Claude 包标识的 RuntimeBroker。现在关闭时先结束进程树，再按包标识结束剩下的附属进程，最后 `sc stop` 停止服务；该服务的访问控制允许已登录用户停止，不需要管理员。
- 运行状态把运行中的 Claude 服务算作“后台运行”。开机自启列出该服务，开机自动启动时可改为手动（`sc config ... start= demand`，经 Windows 管理员确认）；只处理二进制在 Claude 安装包内的同名服务。
- 面板默认窗口加宽到 1000、最低高度 760（CSS 像素，按屏幕限制），其他页面显示更多内容。
- 验证：完整单元测试与页面 Node 测试通过；本机只读核对识别出 CoworkVMService（运行、自动启动）与 Claude 的 RuntimeBroker；提权命令用不提权的 `sc query` 替身核对退出码传递。真实的关闭和改启动类型未在本机执行（会话运行在 Claude 中）。
- 发布：本仓库 `v0.7.1`（提交 `af514c5`）。`CCGuard-Setup-0.7.1.exe` 由 `Windows installer` 工作流在发布时构建并附上，SHA-256 `0490ee6aad42b1f3e65851e117b738653e5e2672b7b7364d3f5032cce78d02d5`，另附 `SHA256SUMS-installer-0.7.1.txt`；下载回的资产哈希一致。发布构建通过打包自检 25 项、静默安装、安装后自检、静默卸载；推送 CI 通过。

## 0.7.0（2026-11-18）

- Claude 页：显示 Claude 桌面版（MSIX）是否在后台运行、有无窗口、托管几个 Claude Code 会话，面板顶部常驻提示；确认后用 `taskkill /T /F` 结束整棵进程树。
- Claude 开机自启：检查 MSIX 启动任务、注册表 Run 与启动文件夹，可直接关闭（写系统的“已禁用”标记，不删条目；策略控制的不改）。
- Claude Code 检查清单：参考 ip.net.coffee 的指南整理 11 项，结合本机检查、出口评分和 Clash／Mihomo 配置（只取模式、计数和规则序号）自动判断，其余标“自查”。
- 更新：可选每天自动检查；安装版可在面板里下载安装程序，按同一 Release 的 SHA-256 清单校验后静默安装并重新打开（Inno `/RELAUNCH`）。设置存 `prefs.json`。
- 托盘：退出前确认，确认后面板随之退出、不再自动恢复；托盘进程按每显示器 DPI 感知运行，菜单在高分屏下清晰；“打开面板”把窗口带到最前面。
- 验证：完整单元测试与页面 Node 测试通过；真实窗口验证退出请求使面板退出、显示请求把面板带到最前；托盘菜单 DPI 前后截图对比；Claude 检测只读核对本机（未执行关闭）。
- 发布：本仓库 `v0.7.0`（提交 `513b14c`）。`CCGuard-Setup-0.7.0.exe` 由 `Windows installer` 工作流在发布时构建并附上，SHA-256 `50aa70335564198ad850506779477b40e3d051a3e63944fc49e6f30bba59fc4f`，另附 `SHA256SUMS-installer-0.7.0.txt`；下载回的资产哈希一致。发布构建通过打包自检 25 项、静默安装、安装后自检、静默卸载；推送 CI 在 Linux、Windows（3.12）与 Linux 3.10 通过。

## 独立仓库（2026-11-17）

- CCGuard 从原先所在的 Skill 仓库中独立出来，成为本仓库。保留了 CCGuard 文件的全部提交历史，目录改为 `scripts/`、`assets/monitor/`、`docs/`；打包后的资源目录由 `claude-guardian/` 改为 `ccguard/`；检查更新改查本仓库的发布列表。
- 去掉对原 Skill 的依赖：`monitor.py desktop` 只支持 Windows（不再借用断网保护开关的图标生成 macOS／Linux 入口）；处理指引里“用断网保护开关重新开启”改为通用说法；托盘与网页通知署名改为 CCGuard。
- 新的协作规则（AGENTS.md）只保留与 CCGuard 相关的部分；CI 只跑 Linux 与 Windows。
- 源码运行改为直接双击仓库根目录的 `CCGuard.pyw`；Release 只附安装程序，源码用 GitHub 自动附带的源码包。

## 0.6.1（2026-11-17）

- 安装版自带思源黑体 Noto Sans SC（SIL OFL 1.1），各机界面字体一致。构建时从 google/fonts 固定提交 `a85815a4` 下载并校验大小与 SHA-256，字体不进 git；WebView 面板以 `@font-face` 首选加载，tkinter 面板优先 `Noto Sans SC`。
- 验证：完整单元测试通过；本机构建 exe 自检 23 项（含字体与许可文件）通过，实际面板加载了打包字体；CI 构建安装程序并通过静默安装、自检、卸载。
- 发布：本仓库 `v0.6.1`（提交 `463ef26`）。`CCGuard-Setup-0.6.1.exe` 由 `Windows installer` 工作流在发布时构建并附上，SHA-256 `c7842fc8f8fcef2694cb4a0154bbf98ee99d5827b74267190bafb1b706ea2e10`，另附 `SHA256SUMS-installer-0.6.1.txt`；下载回的资产哈希一致。发布构建下载并校验字体，通过打包自检 23 项、静默安装、安装后自检、静默卸载；推送 CI 在 Linux、Windows（3.12）与 Linux 3.10 通过。原仓库已改名为 Claude-Guardian 并归档为只读，README 开头注明本仓库地址

## 0.6.0（2026-11-17）

- 修复：安装版首次运行时核心 IPv6、DNS 接管、严格路由显示“未知”。`runtime_config` 留空时在 FlClash、Clash Verge Rev 的默认位置自动查找运行配置。
- 版本号唯一来源 `scripts/version.py`；面板“关于”页、`monitor.py --version`、exe 属性和安装程序都读它，发布标签不一致时安装程序构建失败。
- “关于”页手动检查更新（只在点击时请求 GitHub 发布列表，不下载、不安装）与随程序打包的更新日志。
- 验证：用安装版生成的真实配置复现并确认修复；CI 构建安装程序通过自检 21 项、静默安装、卸载。

## 0.5.1（2026-11-17）

- 安装向导改为简体中文：使用 Inno Setup 官方仓库收录的社区翻译，原样保留译者署名，按 Windows 界面语言自动选择。

## 0.5.0（2026-11-17）

- Windows 安装程序：PyInstaller 打包 Python 与 pywebview，Inno Setup 生成按当前用户安装、不需要管理员的安装程序；开始菜单入口带 `CCGuard.Monitor` 应用标识；升级前关闭正在运行的面板；卸载保留配置与历史。由 GitHub Actions 从源码构建，附到 Release 前做静默安装、自检、卸载验证。
- 出口页写明数据来源（Cloudflare 1.1.1.1、ip.net.coffee）。

## 0.4.0（2026-11-17）

- WebView 面板（pywebview + Edge WebView2）为默认界面，不可用时回退 tkinter；中文优先字体；跟随系统深色模式；窗口按内容定尺寸。
- 出口评分（手动联网，不访问 Claude）、每项检查的检测日志、处理指引、状态历史（`history.jsonl`，保留 7 天）。
- 修复：点关闭按钮时面板卡死（pywebview 在界面线程同步执行关闭回调，回调里又等待同一线程）；监测进程退出后托盘自行退出。
- 界面精简：去掉常驻说明、免责和统计文字。

## 0.3.0（2026-11-16）

- 双击启动（`CCGuard.pyw`／`CCGuard.cmd`）与单实例；`quickstart` 一键生成配置；可选开机自启（当前用户 Startup 快捷方式）。

## 0.2.0（2026-11-16）

- 支持 FlClash、Clash Verge Rev、Clash Nyanpasu、Clash for Windows、Mihomo、sing-box、Hiddify、v2rayN、NekoRay 等客户端预设，以及 Clash YAML、sing-box JSON、Xray JSON 运行配置；TUN 网卡自动识别；`detect` 候选识别。

## 0.1（2026-11-15）

- 只读 Windows 监测：10 项检查、盾牌状态图标、托盘与系统通知、本地网页备选。
