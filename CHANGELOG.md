# 更新记录

每个版本给出主要变化与验证方式；逐次提交的细节见 git 历史。面向用户的简短更新日志在 `assets/monitor/release-notes.json`，面板“关于”页显示。

## 0.7.1（2026-11-18）

- 修复：用 CCGuard 关闭 Claude 后，任务管理器的 Claude 分组里仍剩 `cowork-svc.exe` 和 `Runtime Broker`。前者是 Claude 安装包注册的 Windows 服务 `CoworkVMService`（显示名 Claude，LocalSystem，开机自动启动），后者是带 Claude 包标识的 RuntimeBroker。现在关闭时先结束进程树，再按包标识结束剩下的附属进程，最后 `sc stop` 停止服务；该服务的访问控制允许已登录用户停止，不需要管理员。
- 运行状态把运行中的 Claude 服务算作“后台运行”。开机自启列出该服务，开机自动启动时可改为手动（`sc config ... start= demand`，经 Windows 管理员确认）；只处理二进制在 Claude 安装包内的同名服务。
- 面板默认窗口加宽到 1000、最低高度 760（CSS 像素，按屏幕限制），其他页面显示更多内容。
- 验证：完整单元测试与页面 Node 测试通过；本机只读核对识别出 CoworkVMService（运行、自动启动）与 Claude 的 RuntimeBroker；提权命令用不提权的 `sc query` 替身核对退出码传递。真实的关闭和改启动类型未在本机执行（会话运行在 Claude 中）。

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
