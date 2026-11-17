# 更新记录

每个版本给出主要变化与验证方式；逐次提交的细节见 git 历史。面向用户的简短更新日志在 `assets/monitor/release-notes.json`，面板“关于”页显示。

## 独立仓库（2026-11-17）

- CCGuard 从原先所在的 Skill 仓库中独立出来，成为本仓库。保留了 CCGuard 文件的全部提交历史，目录改为 `scripts/`、`assets/monitor/`、`docs/`；打包后的资源目录由 `claude-guardian/` 改为 `ccguard/`；检查更新改查本仓库的发布列表。
- 去掉对原 Skill 的依赖：`monitor.py desktop` 只支持 Windows（不再借用断网保护开关的图标生成 macOS／Linux 入口）；处理指引里“用断网保护开关重新开启”改为通用说法；托盘与网页通知署名改为 CCGuard。
- 新的协作规则（AGENTS.md）只保留与 CCGuard 相关的部分；CI 只跑 Linux 与 Windows。
- 源码运行改为直接双击仓库根目录的 `CCGuard.pyw`；Release 只附安装程序，源码用 GitHub 自动附带的源码包。

## 0.6.1（2026-11-17）

- 安装版自带思源黑体 Noto Sans SC（SIL OFL 1.1），各机界面字体一致。构建时从 google/fonts 固定提交 `a85815a4` 下载并校验大小与 SHA-256，字体不进 git；WebView 面板以 `@font-face` 首选加载，tkinter 面板优先 `Noto Sans SC`。
- 验证：完整单元测试通过；本机构建 exe 自检 23 项（含字体与许可文件）通过，实际面板加载了打包字体；CI 构建安装程序并通过静默安装、自检、卸载。

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
