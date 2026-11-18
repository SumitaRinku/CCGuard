<div align="center">

<img src="assets/monitor/logo-ok.png" width="96" height="96" alt="CCGuard shield">

# CCGuard

**降低 Claude 风控风险：盯住代理、TUN、路由、防火墙、DNS 与 IPv6，防护一失效就提醒。**

<p>
  <img alt="Windows 10/11" src="https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square">
  <img alt="GPL-3.0-only" src="https://img.shields.io/badge/License-GPL--3.0--only-2E7D32?style=flat-square">
  <a href="https://github.com/SumitaRinku/CCGuard/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/SumitaRinku/CCGuard?style=flat-square"></a>
</p>

**中文** ｜ [English](README.en.md)

</div>

---

## CCGuard 是什么

Claude 会根据访问来源做风控。出口 IP 中途变化、真实 IP 或 DNS 从代理旁边漏出去、网页走 IPv6 绕过代理，都会让账号看起来同时来自不同地方，是触发风控的常见原因。

CCGuard 盯住 Windows 上让流量始终走同一个代理出口的那些设置：代理核心、TUN、默认路由、防火墙默认阻止、DNS 和 IPv6。任何一项失效，托盘图标变色并弹出通知，点开就能看到原因和修复步骤。出口评分则告诉你当前出口 IP 本身是否干净。

CCGuard 自己不连接 Claude，也不改系统设置：10 项检查只读本机，可以一直开着。

## 主要能力

| 能力 | 说明 |
| --- | --- |
| **10 项实时检查** | 代理核心、TUN、默认路由、防火墙、放行规则、核心 IPv6 / 严格路由 / DNS 接管、物理网卡 DNS / IPv6 |
| **安装程序** | 双击安装，不需要 Python 和管理员；首次打开自动生成配置；再次打开不会开第二个窗口 |
| **一条命令启动** | `quickstart` 自动识别主机、客户端和 TUN，生成配置并打开面板；已有配置不覆盖 |
| **状态色盾牌** | 绿 ✓ 正常、橙 ! 降级、红 ✕ 失效、灰 — 未知；窗口、托盘与网页标题同步 |
| **新界面** | WebView（pywebview + Edge WebView2）桌面面板：状态横幅、侧栏异常计数、彩色日志、跟随系统深色模式，窗口按内容自动定尺寸；没装 pywebview 时自动回退 tkinter 面板 |
| **状态历史** | 每项检查最近 24 小时／7 天的状态时间线，未运行监测的时段单独标出；记录存在配置旁的 `history.jsonl`，只含检查项和状态，保留 7 天 |
| **处理指引** | 点开任一检查卡片，查看它检查什么、当前结果对应的处理步骤、这一项最近 24 小时的变化和结果代码 |
| **检测日志** | 每项检查都记下读了哪条系统查询、看到了什么、为什么判成这个状态，在卡片详情的“检测过程”里逐条列出；不含 IP 和文件路径。原理见 [检测原理](docs/monitor.md#principles) |
| **出口评分** | “出口”页一键查看当前出口 IP 的信任分、类型（住宅／机房）、地区、运营商和 VPN／代理／滥用标记，数据来自 [ip.net.coffee](https://ip.net.coffee/claude/)；可在浏览器打开完整检测页。检测过程不连接 Claude，见 [出口评分](docs/monitor.md#exit-score) |
| **Claude 后台提醒** | Claude 桌面版（MSIX）关掉窗口后仍在后台运行并联网；面板顶部和“Claude”页显示它是否在运行、有没有窗口、带着几个 Claude Code 会话，可一键结束全部进程并停止它的后台服务 CoworkVMService。只看进程和服务状态，不连接 Claude |
| **Claude 开机自启** | 查出 Claude 的应用启动任务（StartupTask）、注册表 Run 项、启动文件夹快捷方式和开机自动启动的 CoworkVMService 服务，开着的可在面板里直接关闭（服务改为手动启动，需管理员确认一次） |
| **Claude Code 检查清单** | 按 [ip.net.coffee 的 Claude Code 稳定使用指南](https://ip.net.coffee/claude/claudecode.html) 整理 11 项：出口 IP、TLS 指纹、DNS、IPv6、分流规则顺序、长连接等。能从本机检查、出口评分和代理配置判断的项直接给出结果，其余给出自查方法 |
| **窗口 + 托盘 + 网页** | WebView 面板（默认）／tkinter 面板（回退）、托盘通知、`127.0.0.1` 本地网页备选 |
| **系统通知** | 状态跃迁时提醒，带冷却与恢复提示；可暂停 |
| **可选开机自启** | 当前用户 Startup 快捷方式，登录后隐藏到托盘；默认关闭，可随时撤销 |
| **多客户端预设** | FlClash、Clash Verge Rev、Clash Nyanpasu、Clash for Windows、Mihomo / Clash.Meta、sing-box、Hiddify、v2rayN、NekoRay / NekoBox |
| **TUN 自动识别** | 按网卡名称 / 描述片段识别，客户端升级后通常不用改配置 |
| **多配置格式** | Clash/Mihomo YAML、sing-box JSON（含 1.11+ `address`）、Xray JSON；读不出记 `unknown` |
| **候选识别** | `monitor.py detect` 无配置列出候选核心、TUN 网卡和可能的客户端预设 |

## 每项检查防的是什么

| 检查 | 失效时的风险 |
| --- | --- |
| 代理核心 | 代理停了，流量直接用本地网络和真实 IP 出去 |
| TUN 网卡 | 不经系统代理的程序直接用真实 IP 连接 |
| 默认路由 | 默认路由没走 TUN，流量绕过代理 |
| 防火墙默认阻止 | 代理断开或重连的那一刻，流量直接出网 |
| 放行规则 | 防火墙挡住代理核心自己，网络断掉 |
| 核心 IPv6 | 代理开了 IPv6，可能出现第二个出口地址 |
| 严格路由 | 其他网卡或 VPN 抢走流量 |
| DNS 接管 | DNS 查询不经代理，暴露本地运营商 |
| 网卡 DNS | 网卡 DNS 被改回运营商 DNS |
| 系统 IPv6 | 网页走 IPv6 直连，绕过只代理 IPv4 的出口 |

出口评分补上最后一环：出口 IP 是机房 IP、被标记为 VPN／代理，或位于 Claude 不提供服务的地区时，即使本机设置全部正常，风控风险也更高。

**CCGuard 本身**：只读本机，不改防火墙、路由和代理配置，不需要管理员；监测不联网，出口评分和检查更新只在你点击（或开启每日自动检查更新）时联网，都不连接 Claude；状态、日志和通知不含 IP 地址与文件路径；默认不开机自启。

## 快速开始

### 1. 准备

- Windows 10 / 11
- 代理客户端已经在运行，TUN 和防火墙已按你的方案部署

### 2. 安装

**安装程序（推荐）**：下载 [`CCGuard-Setup-0.7.2.exe`](https://github.com/SumitaRinku/CCGuard/releases/download/v0.7.2/CCGuard-Setup-0.7.2.exe)，双击安装。不需要 Python，也不需要管理员：程序装到当前用户的 `%LOCALAPPDATA%\Programs\CCGuard`，带开始菜单和桌面图标，可在“设置 → 应用 → 已安装的应用”里卸载。卸载会删掉程序、快捷方式和开机自启项，保留你的 `monitor.json` 与 `history.jsonl`。

安装程序由 GitHub Actions 从源码构建，安装、自检、卸载验证通过后才附到 Release，同目录的 `SHA256SUMS-installer-0.7.2.txt` 可核对哈希。安装程序没有代码签名，首次运行时 Windows SmartScreen 可能提示“Windows 已保护你的电脑”，点“更多信息 → 仍要运行”即可。

**源码运行**：需要 Python 3.10+（官方安装包通常自带 tkinter）。下载 Release 页的 “Source code (zip)” 或克隆仓库：

```powershell
git clone https://github.com/SumitaRinku/CCGuard.git
```

然后双击根目录的 `CCGuard.pyw`（无控制台）或 `CCGuard.cmd`（找不到 `pythonw` / `pyw` 时回退到 `python` / `py`，会短暂闪一下控制台）。想要 WebView 新界面，先执行 `python -m pip install -r requirements-desktop.txt` 安装 pywebview（Windows 10/11 自带 Edge WebView2）；不装也能用，会自动用 tkinter 面板。

### 3. 首次启动

从开始菜单、桌面或 `CCGuard.pyw` 打开。首次运行会自动识别主机名、代理客户端和 TUN 网卡，生成 `%LOCALAPPDATA%\CCGuard\monitor.json` 并打开面板，不需要命令行。再次打开不会开第二个窗口；已在运行时会提示从托盘打开。

### 4. 命令行启动（等价）

```bat
:: 仓库内
python scripts\monitor.py quickstart
```

`quickstart` 会读取本机主机名，识别正在运行的已知客户端与 TUN，在 `%LOCALAPPDATA%\CCGuard\monitor.json` 生成配置（已有配置不覆盖），然后打开面板 + 托盘。关掉窗口后托盘继续提醒。

常用选项：

```bat
:: 指定客户端预设
python ...\monitor.py quickstart --client flclash

:: 指定客户端实际加载的运行配置（绝对路径）
python ...\monitor.py quickstart --runtime-config "C:\Users\YOU\AppData\Roaming\com.follow\clash\config.yaml"

:: 只生成配置，不打开面板
python ...\monitor.py quickstart --no-launch

:: 同时开启开机自启（登录后隐藏到托盘）
python ...\monitor.py quickstart --autostart
```

快速配置默认不校验放行规则数量和 DNS 期望值；需要时在面板设置页或 JSON 里补。`runtime_config` 留空时，会在 FlClash、Clash Verge Rev 的默认位置自动查找运行配置；其他客户端或找不到时，三项配置检查显示 `unknown`，需要手动填写。

### 5. 手动配置（可选）

想自己填写时，先运行 `detect` 看候选核心和 TUN：

```bat
python ...\monitor.py detect
```

然后把 `assets\monitor\config.example.json` 复制到仓库外（例如 `%USERPROFILE%\.ccguard\monitor.json`），至少确认：

- `target`：`python -c "import platform; print(platform.node())"` 的精确输出
- `proxy.client`：下表中的客户端预设
- `proxy.tun_adapter`：保持 `auto`；识别不到时再填精确网卡名
- `proxy.runtime_config`：客户端实际加载的配置绝对路径；留空时自动查找 FlClash、Clash Verge Rev 的默认位置
- `firewall.allow_rule_prefix`、`network.expect_dns_servers`：按你的部署填写


### 6. 启动、自启与关闭

```bat
:: 打开面板 + 托盘
python ...\monitor.py gui --config "%LOCALAPPDATA%\CCGuard\monitor.json" --tray

:: 开启 / 关闭 / 查看开机自启
python ...\monitor.py autostart-enable --config "%LOCALAPPDATA%\CCGuard\monitor.json"
python ...\monitor.py autostart-disable
python ...\monitor.py autostart-status
```

面板左侧栏也有「开机自启」复选框，效果与命令相同。默认关闭；开启后登录 Windows 会自动打开面板并隐藏到托盘，不会弹出窗口。

其他入口：

```bat
:: 单次采集，输出 JSON（每项含 source 与 evidence 检测过程）
python ...\monitor.py check --config <private>\monitor.json

:: 出口评分（联网：Cloudflare trace + ip.net.coffee，不访问 Claude；不需要配置）
python ...\monitor.py ip-score

:: 本地网页（只监听 127.0.0.1，带随机会话令牌）
python ...\monitor.py serve --config <private>\monitor.json

:: 生成桌面 / 开始菜单入口（不写自启）
python ...\monitor.py desktop --config <private>\monitor.json --output <new-dir>

:: 让通知以 CCGuard 署名（当前用户开始菜单建一个入口）
python ...\monitor.py register-notifier --config <private>\monitor.json
```

## 支持的代理客户端

`proxy.client` 可选内置预设，预设自动填入进程名、TUN 名称片段和配置格式；`process_names`、`tun_adapter`、`config_format` 仍可覆盖。

| `client` | 默认进程名（节选） | TUN 名称片段（节选） | 配置格式 |
| --- | --- | --- | --- |
| `flclash` | `FlClashCore`、`FlClash` | `flclash`、`meta tunnel` | Clash YAML |
| `clash-verge-rev` | `verge-mihomo`、`clash-verge` | `clash`、`mihomo`、`meta` | Clash YAML |
| `clash-nyanpasu` | `clash-nyanpasu`、`mihomo` | `nyanpasu`、`mihomo` | Clash YAML |
| `clash-for-windows` | `Clash for Windows`、`clash-win64` | `clash` | Clash YAML |
| `mihomo` | `mihomo`、`clash-meta` | `mihomo`、`meta tunnel` | Clash YAML |
| `sing-box` | `sing-box` | `sing-box`、`sing-tun` | sing-box JSON |
| `hiddify` | `Hiddify`、`HiddifyCli`、`sing-box` | `hiddify`、`sing-tun` | sing-box JSON |
| `v2rayn` | `v2rayN`、`xray`、`v2ray` | `v2rayn`、`tun2socks` | Xray JSON |
| `nekoray` | `nekoray`、`nekobox`、`sing-box`、`xray` | `nekoray`、`nekobox` | 自动 |

- **TUN 自动识别**：`tun_adapter` 默认 `auto`，按网卡名称和描述里的片段匹配；完全对不上时用 `tun_match` 加片段。
- **进程名**：`process_names` 不填时用预设；显式填写优先；`client` 与 `process_names` 都不填时，任一已知代理核心在运行就算通过。
- **配置格式**：`config_format` 默认 `auto`。`.yaml`/`.yml` 按 Clash/Mihomo 解析；`.json` 按顶层键区分 sing-box 与 Xray；也可以强制指定。

## 检查项

| ID | 检查 | 失败时 |
| --- | --- | --- |
| `proxy_core` | 配置的进程名、客户端预设或已知代理核心是否在运行 | `fail` |
| `tun_adapter` | TUN 网卡存在且 Up | `fail` |
| `default_route` | `0.0.0.0/0` 最低度量路由是否走 TUN | `fail` |
| `firewall_block` | 三档防火墙启用且默认出站为 Block | `fail` |
| `guardian_rules` | 启用的放行规则数量是否达到配置下限 | `degraded` |
| `core_ipv6` | 运行配置是否关闭 IPv6 | `degraded` |
| `strict_route` | 运行配置是否开严格路由 | `degraded` |
| `dns_hijack` | 运行配置是否接管 53 端口 DNS | `degraded` |
| `dns_servers` | 物理网卡 DNS 等于期望值 | `degraded` |
| `os_ipv6` | 物理网卡 IPv6 绑定已禁用 | `degraded` |

`overall`：任一 `fail` → `fail`；否则任一 `degraded` → `degraded`；全部 `ok` → `ok`；其余 → `unknown`。

`core_ipv6`、`strict_route`、`dns_hijack` 是尽力而为的映射：格式不支持、键名版本不同或配置留空时记 `unknown`，需人工核对。

## 配置

最小示例（FlClash）：

```json
{
  "version": 1,
  "target": "YOUR-HOSTNAME",
  "proxy": {
    "client": "flclash",
    "process_names": ["FlClashCore"],
    "tun_adapter": "auto",
    "tun_match": [],
    "config_format": "auto",
    "runtime_config": "C:\\Users\\YOU\\AppData\\Roaming\\com.follow\\clash\\config.yaml"
  },
  "firewall": {
    "expect_default_block": true,
    "allow_rule_prefix": "guardian-",
    "min_allow_rules": 1
  },
  "network": {
    "expect_dns_servers": ["198.18.0.2"],
    "expect_ipv6_disabled": true
  },
  "alerts": {
    "cooldown_seconds": 120,
    "notify_states": ["fail", "degraded"],
    "interval_seconds": 5
  }
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `version` | 是 | 固定 `1` |
| `target` | 是 | 主机名，必须与 `platform.node()` 完全一致 |
| `proxy.client` | 否 | 上表预设；`custom` 或省略表示自定义 |
| `proxy.process_names` | 否 | 覆盖预设；`[]` 表示任一已知核心 |
| `proxy.tun_adapter` | 否 | 精确网卡名或 `auto`（默认） |
| `proxy.tun_match` | 否 | 额外 TUN 名称片段，最多 8 个 |
| `proxy.config_format` | 否 | `auto`、`clash`、`sing-box`、`xray` |
| `proxy.runtime_config` | 否 | 绝对路径；`""` 时自动查找 FlClash、Clash Verge Rev 的默认位置，找不到则三项配置检查为 `unknown` |
| `firewall.expect_default_block` | 是 | 是否要求默认出站 Block |
| `firewall.allow_rule_prefix` | 是 | 放行规则名前缀 |
| `firewall.min_allow_rules` | 是 | 放行规则数量下限，0–1000 |
| `network.expect_dns_servers` | 是 | 期望的物理网卡 DNS，最多 8 个 IPv4 |
| `network.expect_ipv6_disabled` | 是 | 是否要求物理网卡关闭 IPv6 |
| `alerts.cooldown_seconds` | 是 | 通知冷却，0–86400 秒 |
| `alerts.notify_states` | 是 | `fail`、`degraded`、`unknown` 的组合 |
| `alerts.interval_seconds` | 是 | 采集间隔，2–3600 秒 |
| `alerts.paused` | 否 | 暂停提醒 |

运行配置路径因客户端和版本而异，必须指向客户端实际加载的那一份；常见位置与各格式可读字段见 [monitor.md](docs/monitor.md)。

## 界面与通知

- **独立窗口**：左侧栏导航（状态 / 日志 / 设置）+ 状态卡片 + ttk 设置控件；设置页可调采集间隔、通知冷却、通知项和暂停提醒，并可「打开配置」直接编辑 JSON。
- **开机自启**：左侧栏「开机自启」复选框，登录后自动打开面板并隐藏到托盘；默认关闭，可随时取消。
- **字体**：安装版自带思源黑体（Noto Sans SC，SIL OFL 1.1），界面在所有电脑上一致，不依赖系统装了什么字体。Python 版不带字体文件，按已安装字体选：`Noto Sans SC` → `MiSans` → `HarmonyOS Sans SC` → 思源黑体 → `Microsoft YaHei UI`（Windows 自带）。英文字标用 Anthropic Serif（自备时）或 Georgia，检查码用 Anthropic Mono／`Cascadia Mono`／`Consolas`。
- **界面实现**：`gui --ui auto`（默认）优先 WebView，失败回退 tkinter；`--ui web` 只用 WebView（不可用时报错），`--ui tk` 只用 tkinter。
- **关闭窗口**：有托盘时可隐藏到托盘、直接关闭或取消；没有托盘时只提供关闭或取消。
- **托盘退出**：右键托盘图标选“退出”会先确认，确认后监测、托盘和面板一起退出，不会再自动弹回。“打开面板”会把窗口带到最前面。
- **托盘**：菜单按系统缩放清晰显示；盾牌图标随整体状态换色，悬停显示状态；状态跃迁时按冷却发系统通知，恢复也提示。
- **网页备选**：`serve` 只监听 `127.0.0.1` 的随机端口，路径带随机会话令牌，并校验 `Host`、`Origin`、`Sec-Fetch-Site`，带严格 CSP。
- **通知署名**：托盘运行在 PowerShell 中，默认显示「Windows PowerShell」。执行一次 `register-notifier` 后，通知以 CCGuard 署名；撤销用 `unregister-notifier`。
- 专注助手或系统通知设置可能吞掉气泡；以面板显示为准。

## 常见问题

| 现象 | 先做什么 |
| --- | --- |
| 双击没反应 | 先装 Python 3.10+；改双击 `CCGuard.cmd` 看提示；确认 `.pyw` 已关联到 `pythonw` |
| `quickstart` 没识别到客户端 | 先启动代理客户端，或用 `--client <预设>` 指定；也可先跑 `detect` 看候选 |
| `proxy_core` 失效 | 运行 `detect` 看核心进程名；用 `process_names` 显式填写 |
| `tun_adapter` 失效 | 确认客户端 TUN 已开启；用 `detect` 看网卡名；必要时加 `tun_match` |
| `default_route` 失效 | 确认默认路由走 TUN；检查是否有更高优先级的路由或 VPN |
| `core_ipv6` / `strict_route` / `dns_hijack` 未知 | 点开卡片看“检测过程”：没找到运行配置时，在配置里填 `runtime_config` 为客户端实际加载的文件；必要时指定 `config_format` |
| `dns_servers` / `os_ipv6` 降级 | 订阅更新或客户端升级可能改回 DNS 覆写或 IPv6；恢复后重新核对 |
| 开机自启没生效 | 确认程序目录和配置路径没有移动；重新勾选或用 `autostart-enable`；检查当前用户 Startup 目录里的 `CCGuard.lnk` |
| 字体仍不好看 | 用安装版（自带思源黑体）；Python 版可安装 Noto Sans SC 或 MiSans 到系统，最低回退为 `Microsoft YaHei UI` |
| 面板还是旧样式 | 没装 pywebview 或缺 WebView2，已回退 tkinter；执行 `python -m pip install -r requirements-desktop.txt`；新界面左侧有“历史”页 |
| 收不到通知 | 检查 Windows 通知设置与专注助手；面板显示才是准的 |
| 提示「监测已停止更新」 | 监测进程已退出或采集间隔过长；重新启动面板 |
| 窗口打不开 | 缺少 tkinter；改用 `serve` 网页版 |

## 项目结构

```text
CCGuard.pyw / CCGuard.cmd   源码运行的双击入口
scripts/
  monitor.py                监测引擎与命令行（quickstart、check、detect、gui、serve、ip-score、update-check…）
  monitor_webview.py        WebView 面板（pywebview 桥接，默认）
  monitor_gui.py            tkinter 面板（回退）
  monitor_history.py        状态历史（history.jsonl）与时间线
  monitor_guide.py          各检查项的说明与处理步骤
  ip_score.py               手动出口评分
  app_update.py             检查更新、下载校验与安装、更新日志
  claude_app.py             Claude 桌面版运行状态、关闭与开机自启
  claude_code_guide.py      Claude Code 稳定使用检查清单
  version.py                版本号（唯一来源）
assets/monitor/             面板页面、图标、托盘脚本、更新日志
packaging/                  CCGuard.exe 入口、PyInstaller 配置、Inno Setup 安装脚本与中文向导
tools/build_windows.py      构建 exe 与安装程序（CI 同一脚本）
tests/                      单元与回归测试、页面逻辑 Node 测试
docs/                       使用说明与设计决策
```

## 版本与更新

- **查看版本**：面板“关于”页显示当前版本；命令行 `monitor.py --version`；安装版也写在 `CCGuard.exe` 的文件属性里。
- **检查更新**：“关于”页点“检查更新”，向 GitHub 读取本仓库已发布的版本（不含草稿和预发布），列出比当前新的版本和它们的发布说明。只访问 GitHub。命令行：`monitor.py update-check`。
- **自动检查（可选）**：“关于”页勾选“自动检查更新”后，每天最多检查一次，有新版本时在面板顶部提示；默认关闭，设置存在配置旁的 `prefs.json`。
- **软件内安装**：安装版点“下载并安装”，确认后从本仓库 Release 下载安装程序，用同一发布里的 `SHA256SUMS-installer-*.txt` 校验哈希，校验通过才关闭 CCGuard、静默安装并自动重新打开；哈希不符时不安装。源码运行时改为在浏览器打开发布页。
- **手动升级**：运行新版本的安装程序即可覆盖安装，会先关闭正在运行的 CCGuard，保留 `monitor.json` 与 `history.jsonl`。
- **更新日志**：“关于”页列出每个版本的主要变化（随程序打包，离线可看）；完整开发记录见 [CHANGELOG.md](CHANGELOG.md)。
- **版本号规则**：`主版本.次版本.修订号`。只修问题升修订号，加功能升次版本号。版本号只写在 `scripts/version.py` 一处，界面、命令行、exe 属性和安装程序都读它。

**发布新版本的步骤**（维护者）：

1. 改 `version.py` 的 `__version__`，并在 `assets/monitor/release-notes.json` 最前面加这个版本的更新日志（测试会检查两者一致）。
2. 写 CHANGELOG，跑完整测试，推送到 main，等推送 CI 和安装程序构建都通过。
3. 用户确认后，发布 GitHub Release，标签 `vX.Y.Z`。`Windows installer` 工作流发现标签与 `version.py` 不一致会直接失败，一致才构建、验证并附上安装程序。
4. 下载发布的资产核对哈希，把发布记录写进 CHANGELOG。

## 开发与验证

```bash
python -m unittest discover -s tests -v
node tests/monitor-panel.cjs
node tests/monitor-interaction.cjs
python -m compileall -q scripts packaging tools
python -m pip install -r requirements-build.txt && python tools/build_windows.py   # 构建 exe（Windows）
```

- CI 在 Linux 与 Windows（Python 3.12）以及 Linux Python 3.10 上运行测试；改到程序或打包时，`Windows installer` 工作流还会构建安装程序并做静默安装、自检、卸载验证。
- 完整记录见 [CHANGELOG.md](CHANGELOG.md)，设计取舍见 [docs/decisions.md](docs/decisions.md)，协作规则见 [AGENTS.md](AGENTS.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [监测说明](docs/monitor.md) | 配置、客户端预设、检查项、通知与边界 |
| [检测原理](docs/monitor.md#principles) | 每项检查的数据来源、判定规则与检测日志；出口评分的请求与隐私 |
| [设计决策](docs/decisions.md) | 主要实现取舍 |
| [更新记录](CHANGELOG.md) | 每个版本改了什么、怎么验证 |
| [Releases](https://github.com/SumitaRinku/CCGuard/releases) | 安装程序与校验和 |

## 反馈

欢迎通过 [Issues](https://github.com/SumitaRinku/CCGuard/issues) 反馈问题。请说明 Windows 版本、代理客户端与版本、复现步骤和预期结果；账号、凭据、订阅链接和完整配置不要贴出来。

## 数据来源与致谢

- **出口评分**的信任分、IP 类型、地区、运营商与风险标记来自 [ip.net.coffee](https://ip.net.coffee/claude/) 的公开接口，评分分段和受限地区规则与其 Claude IP 检测页一致；完整检测页（含 Claude 出口 IP、DNS 与 WebRTC 泄露）请在浏览器里打开该网站查看。
- **Claude Code 检查清单**的条目和原理参考 [ip.net.coffee 的 Claude Code 稳定使用指南](https://ip.net.coffee/claude/claudecode.html)，用自己的话整理，面板里可一键打开原文。
- **出口 IP** 由 Cloudflare 的 `1.1.1.1/cdn-cgi/trace` 返回。
- 安装版界面字体为思源黑体（[Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC)，Adobe 与 Google 发布，SIL Open Font License 1.1），构建时从 [google/fonts](https://github.com/google/fonts/tree/main/ofl/notosanssc) 的固定提交下载并校验哈希，许可文本随程序附带（安装目录 `_internal\ccguard\assets\monitor\fonts\OFL.txt`）。
- 安装向导的简体中文翻译来自 Inno Setup 官方仓库收录的社区翻译（[jrsoftware/issrc](https://github.com/jrsoftware/issrc) 的 `Files/Languages/Unofficial/ChineseSimplified.isl`，维护者 Kira），原样保留其署名。

## 许可

GPL-3.0-only，见 [LICENSE](LICENSE)。第三方文件（字体、安装向导翻译）保留各自的许可与署名。
