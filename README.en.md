<div align="center">

<img src="assets/monitor/logo-ok.png" width="96" height="96" alt="CCGuard shield">

# CCGuard

**Lower the risk of Claude risk control: CCGuard watches proxy, TUN, routing, firewall, DNS and IPv6 and alerts you the moment protection breaks.**

<p>
  <img alt="Windows 10/11" src="https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square">
  <img alt="GPL-3.0-only" src="https://img.shields.io/badge/License-GPL--3.0--only-2E7D32?style=flat-square">
  <a href="https://github.com/SumitaRinku/CCGuard/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/SumitaRinku/CCGuard?style=flat-square"></a>
</p>

[中文](README.md) ｜ **English**

</div>

---

## What CCGuard is

Claude applies risk control based on where traffic comes from. An exit IP that changes mid-session, a real IP or DNS lookup leaking around the proxy, or web traffic going out over IPv6 past the proxy all make an account look like it is in several places at once, and are common triggers.

CCGuard watches the settings on a Windows machine that keep all traffic on one proxy exit: the proxy core, TUN, default route, default-block firewall, DNS and IPv6. When any of them breaks, the tray icon changes colour and a notification appears; open the card to see why and how to fix it. The exit score tells you whether the exit IP itself is clean.

CCGuard never contacts Claude and does not change system settings: the 10 checks only read the local machine, so it can stay running.

## What it does

| Capability | What it does |
| --- | --- |
| **10 live checks** | Proxy core, TUN, default route, firewall, allow rules, core IPv6 / strict route / DNS hijack, physical-adapter DNS / IPv6 |
| **Installer** | Install by double-click, with no Python or admin rights; the first start writes a config; opening it again does not start a second window |
| **One-command start** | `quickstart` detects the host, client and TUN, writes a config and opens the panel; an existing config is never overwritten |
| **State-coloured shield** | Green ✓ ok, orange ! degraded, red ✕ fail, grey — unknown; window, tray and page title stay in sync |
| **New UI** | WebView desktop panel (pywebview + Edge WebView2): status banner, sidebar problem count, coloured log, follows system dark mode, window sized to its content; falls back to the tkinter panel when pywebview is missing |
| **State history** | 24-hour / 7-day timeline per check, with unmonitored time shown separately; stored in `history.jsonl` next to the config, check ids and states only, kept for 7 days |
| **Fix guidance** | Click any check card to see what it checks, the steps for the current result, its last 24 hours and the result code |
| **Detection log** | Every check records which system query it read, what it saw and why it reached its state; listed under "检测过程" in the card detail, without IP addresses or file paths. See [how checks work](docs/monitor.md#principles) |
| **Exit score** | On the \"出口\" page, see the current exit IP's trust score, type (residential / datacenter), location and a region cross-check, network and provider, each risk flag, abuse score, reverse DNS, RPKI, exit vs local time zone, and the Cloudflare edge, from [ip.net.coffee](https://ip.net.coffee/claude/); open the full check page in your browser. The check never contacts Claude; see [exit score](docs/monitor.md#exit-score) |
| **Claude background warning** | The Claude desktop app (MSIX) keeps running and online after its window is closed. The panel header and the "Claude" page show whether it is running, whether it has a window and how many Claude Code sessions it hosts, and can end all of its processes and stop its background service CoworkVMService. Reads process and service status only; never contacts Claude. Use the desktop app rather than the Claude Code CLI |
| **Claude autostart** | Finds Claude's app startup task (StartupTask), registry Run values and Startup-folder shortcuts; enabled ones can be turned off from the panel, the same as \"Disable\" in Task Manager |
| **Claude Code checklist** | 11 items based on [ip.net.coffee's guide to using Claude Code reliably](https://ip.net.coffee/claude/claudecode.html): exit IP, TLS fingerprint, DNS, IPv6, rule order, keep-alive and more. Items that local checks, the exit score and the proxy config can answer are judged automatically; the rest come with how to check them yourself |
| **Window + tray + web** | WebView panel (default) / tkinter panel (fallback), tray notifications, local `127.0.0.1` web page as an alternative |
| **System notifications** | Alerts on state transitions with cooldown and recovery notices; can be paused |
| **Optional autostart** | A per-user Startup shortcut opens the panel hidden in the tray at login; off by default |
| **Client presets** | FlClash, Clash Verge Rev, Clash Nyanpasu, Clash for Windows, Mihomo / Clash.Meta, sing-box, Hiddify, v2rayN, NekoRay / NekoBox |
| **TUN auto-detection** | Matches adapter name / description fragments, so client upgrades usually need no config change |
| **Multiple config formats** | Clash/Mihomo YAML, sing-box JSON (including 1.11+ `address`), Xray JSON; unreadable fields stay `unknown` |
| **Candidate detection** | `monitor.py detect` lists candidate cores, TUN adapters and client presets without a config |

## What each check protects against

| Check | Risk when it fails |
| --- | --- |
| Proxy core | The proxy stopped; traffic goes out on the local network with the real IP |
| TUN adapter | Programs that ignore the system proxy connect with the real IP |
| Default route | The default route bypasses TUN, so traffic skips the proxy |
| Firewall default block | While the proxy disconnects or reconnects, traffic goes straight out |
| Allow rules | The firewall blocks the proxy core itself and the network drops |
| Core IPv6 | The proxy uses IPv6 and a second exit address can appear |
| Strict route | Another adapter or VPN takes over traffic |
| DNS hijack | DNS lookups skip the proxy and reveal the local ISP |
| Adapter DNS | The adapter DNS has been reset to the ISP's servers |
| System IPv6 | Web traffic goes out over IPv6 directly, past an IPv4-only exit |

The exit score covers the last piece: a datacenter IP, an IP flagged as VPN / proxy, or one in a region Claude does not serve carries more risk even when every local setting is correct.

**CCGuard itself**: reads the local machine only, never changes firewall, routes or proxy config, needs no admin rights; monitoring stays offline, and the exit score and update check go online only when you click them (or turn on the daily update check), never contacting Claude; state, logs and notifications contain no IP addresses or file paths; autostart is off by default.

## Quick start

### 1. Requirements

- Windows 10 / 11
- The proxy client is running, with TUN and the firewall set up the way you deployed them

### 2. Install

**Installer (recommended)**: download [`CCGuard-Setup-0.7.3.exe`](https://github.com/SumitaRinku/CCGuard/releases/download/v0.7.3/CCGuard-Setup-0.7.3.exe) and run it. It needs neither Python nor administrator rights: it installs for the current user into `%LOCALAPPDATA%\Programs\CCGuard` with Start menu and desktop shortcuts, and can be removed from Settings > Apps. Uninstalling removes the program, its shortcuts and the autostart entry, and keeps your `monitor.json` and `history.jsonl`.

The installer is built from source on GitHub Actions and attached to the release only after a silent install, self-test and uninstall pass; `SHA256SUMS-installer-0.7.3.txt` holds its hash. It is not code-signed, so SmartScreen may show "Windows protected your PC" on first run: choose "More info > Run anyway".

**From source**: needs Python 3.10+ (the official installer normally includes tkinter). Download "Source code (zip)" from the release page or clone the repository:

```powershell
git clone https://github.com/SumitaRinku/CCGuard.git
```

Then double-click `CCGuard.pyw` (no console) or `CCGuard.cmd` (falls back to `python` / `py` when `pythonw` / `pyw` are missing, briefly showing a console). For the WebView UI run `python -m pip install -r requirements-desktop.txt` first to install pywebview (Windows 10/11 ship Edge WebView2); without it CCGuard uses the tkinter panel.

### 3. First start

Open it from the Start menu, the desktop or `CCGuard.pyw`. The first run detects the host name, proxy client and TUN adapter, writes `%LOCALAPPDATA%\CCGuard\monitor.json` and opens the panel, with no command line. Opening it again does not start a second window; it points you to the tray instead.

### 4. Command-line start (equivalent)

```bat
:: repository
python scripts\monitor.py quickstart
```

`quickstart` reads the host name, detects running known clients and TUN adapters, writes `%LOCALAPPDATA%\CCGuard\monitor.json` (an existing config is never overwritten), and opens the panel + tray. The tray keeps alerting after the window closes.

Common options:

```bat
:: pick a client preset
python ...\monitor.py quickstart --client flclash

:: point at the config the client actually loads (absolute path)
python ...\monitor.py quickstart --runtime-config "C:\Users\YOU\AppData\Roaming\com.follow\clash\config.yaml"

:: write the config without opening the panel
python ...\monitor.py quickstart --no-launch

:: also enable autostart (starts hidden in the tray at login)
python ...\monitor.py quickstart --autostart
```

The quick config does not check the allow-rule count or expected DNS servers by default; add them in Settings or the JSON. With an empty `runtime_config`, CCGuard looks for the runtime config in the default places of FlClash and Clash Verge Rev; for other clients, or when nothing is found, the three config checks stay `unknown` and the path has to be filled in.

### 5. Manual configuration (optional)

To fill it in yourself, run `detect` first to see candidate cores and TUN adapters:

```bat
python ...\monitor.py detect
```

Then copy `assets\monitor\config.example.json` to a private directory outside the repository (for example `%USERPROFILE%\.ccguard\monitor.json`) and confirm at least:

- `target`: the exact output of `python -c "import platform; print(platform.node())"`
- `proxy.client`: a preset from the table below
- `proxy.tun_adapter`: keep `auto`; fill the exact adapter name only when detection fails
- `proxy.runtime_config`: the absolute path of the config the client actually loads; when empty, the default places of FlClash and Clash Verge Rev are searched
- `firewall.allow_rule_prefix`, `network.expect_dns_servers`: match your deployment


### 6. Start, autostart and close

```bat
:: open the panel + tray
python ...\monitor.py gui --config "%LOCALAPPDATA%\CCGuard\monitor.json" --tray

:: enable / disable / check autostart
python ...\monitor.py autostart-enable --config "%LOCALAPPDATA%\CCGuard\monitor.json"
python ...\monitor.py autostart-disable
python ...\monitor.py autostart-status
```

The left sidebar also has an "autostart" checkbox with the same effect. It is off by default; when enabled, login opens the panel hidden in the tray, without a window popping up.

Other entries:

```bat
:: one collection, JSON output (each check carries its source and evidence)
python ...\monitor.py check --config <private>\monitor.json

:: exit score (online: Cloudflare trace + ip.net.coffee, never Claude; no config needed)
python ...\monitor.py ip-score

:: local web page (listens on 127.0.0.1 only, random session token)
python ...\monitor.py serve --config <private>\monitor.json

:: desktop / Start menu entry (does not add autostart)
python ...\monitor.py desktop --config <private>\monitor.json --output <new-dir>

:: name notifications CCGuard (creates one per-user Start menu entry)
python ...\monitor.py register-notifier --config <private>\monitor.json
```

## Supported proxy clients

`proxy.client` selects a built-in preset that fills process names, TUN hints and the config format; `process_names`, `tun_adapter` and `config_format` can still override it.

| `client` | Default process names (sample) | TUN hints (sample) | Config format |
| --- | --- | --- | --- |
| `flclash` | `FlClashCore`, `FlClash` | `flclash`, `meta tunnel` | Clash YAML |
| `clash-verge-rev` | `verge-mihomo`, `clash-verge` | `clash`, `mihomo`, `meta` | Clash YAML |
| `clash-nyanpasu` | `clash-nyanpasu`, `mihomo` | `nyanpasu`, `mihomo` | Clash YAML |
| `clash-for-windows` | `Clash for Windows`, `clash-win64` | `clash` | Clash YAML |
| `mihomo` | `mihomo`, `clash-meta` | `mihomo`, `meta tunnel` | Clash YAML |
| `sing-box` | `sing-box` | `sing-box`, `sing-tun` | sing-box JSON |
| `hiddify` | `Hiddify`, `HiddifyCli`, `sing-box` | `hiddify`, `sing-tun` | sing-box JSON |
| `v2rayn` | `v2rayN`, `xray`, `v2ray` | `v2rayn`, `tun2socks` | Xray JSON |
| `nekoray` | `nekoray`, `nekobox`, `sing-box`, `xray` | `nekoray`, `nekobox` | auto |

- **TUN auto-detection**: `tun_adapter` defaults to `auto` and matches name/description fragments; add a `tun_match` fragment when it cannot find the adapter.
- **Process names**: an omitted `process_names` uses the preset; an explicit list wins; with neither `client` nor `process_names`, any known proxy core counts.
- **Config format**: `config_format` defaults to `auto`. `.yaml`/`.yml` is parsed as Clash/Mihomo; `.json` is distinguished by top-level keys; it can also be forced.

## Checks

| ID | Check | Failure |
| --- | --- | --- |
| `proxy_core` | Configured process name, client preset or a known proxy core is running | `fail` |
| `tun_adapter` | TUN adapter exists and is Up | `fail` |
| `default_route` | The lowest-metric `0.0.0.0/0` route goes through TUN | `fail` |
| `firewall_block` | All three firewall profiles are enabled with default outbound Block | `fail` |
| `guardian_rules` | Enabled allow rules meet the configured minimum | `degraded` |
| `core_ipv6` | The runtime config disables IPv6 | `degraded` |
| `strict_route` | The runtime config enables strict route | `degraded` |
| `dns_hijack` | The runtime config hijacks DNS on port 53 | `degraded` |
| `dns_servers` | Physical-adapter DNS equals the expected value | `degraded` |
| `os_ipv6` | IPv6 binding is disabled on physical adapters | `degraded` |

`overall`: any `fail` → `fail`; otherwise any `degraded` → `degraded`; all `ok` → `ok`; anything else → `unknown`.

`core_ipv6`, `strict_route` and `dns_hijack` are best-effort mappings: an unsupported format, a version-specific key name or an empty config stays `unknown` and needs a manual check.

## Configuration

Minimal example (FlClash):

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

| Field | Required | Meaning |
| --- | --- | --- |
| `version` | yes | fixed `1` |
| `target` | yes | host name; must match `platform.node()` exactly |
| `proxy.client` | no | a preset above; `custom` or omitted means custom |
| `proxy.process_names` | no | overrides the preset; `[]` means any known core |
| `proxy.tun_adapter` | no | exact adapter name or `auto` (default) |
| `proxy.tun_match` | no | extra TUN name fragments, at most 8 |
| `proxy.config_format` | no | `auto`, `clash`, `sing-box` or `xray` |
| `proxy.runtime_config` | no | absolute path; `""` searches the default places of FlClash and Clash Verge Rev, otherwise the three config checks are `unknown` |
| `firewall.expect_default_block` | yes | require default outbound Block |
| `firewall.allow_rule_prefix` | yes | allow-rule name prefix |
| `firewall.min_allow_rules` | yes | minimum allow rules, 0–1000 |
| `network.expect_dns_servers` | yes | expected physical-adapter DNS, up to 8 IPv4 addresses |
| `network.expect_ipv6_disabled` | yes | require IPv6 disabled on physical adapters |
| `alerts.cooldown_seconds` | yes | notification cooldown, 0–86400 seconds |
| `alerts.notify_states` | yes | a combination of `fail`, `degraded`, `unknown` |
| `alerts.interval_seconds` | yes | collection interval, 2–3600 seconds |
| `alerts.paused` | no | pause notifications |

Runtime config paths differ by client and version; always point to the file the client actually loads. See [monitor.md](docs/monitor.md) for common locations and the fields each format can express.

## UI and notifications

- **Native window**: dark sidebar navigation (Status / Log / Settings) + status cards + ttk settings controls; Settings adjusts the interval, cooldown, notification states and pause, and can open the JSON config directly.
- **Autostart**: a sidebar checkbox opens the panel hidden in the tray at login; off by default and removable at any time.
- **Fonts**: the installed app bundles Noto Sans SC (SIL OFL 1.1), so the UI looks the same on every machine regardless of installed fonts. The Python package ships no font files and picks from installed fonts: `Noto Sans SC` → `MiSans` → `HarmonyOS Sans SC` → Source Han Sans → `Microsoft YaHei UI` (ships with Windows). The Latin wordmark uses Anthropic Serif (if supplied) or Georgia, check codes Anthropic Mono / `Cascadia Mono` / `Consolas`.
- **UI implementation**: `gui --ui auto` (default) prefers WebView and falls back to tkinter; `--ui web` is WebView only (error if unavailable), `--ui tk` is tkinter only.
- **Closing the window**: with a tray, hide to tray, close, or cancel; without a tray, only close or cancel.
- **Quitting from the tray**: "退出" in the tray menu asks first; once confirmed, monitoring, tray and panel all exit and the panel does not come back. "打开面板" brings the window to the front.
- **Tray**: the menu renders sharply at any display scaling; the shield changes colour with the overall state and shows the state on hover; transitions raise notifications with cooldown, and recovery is announced.
- **Web fallback**: `serve` listens on a random `127.0.0.1` port with a random session token, validates `Host`, `Origin` and `Sec-Fetch-Site`, and sends a strict CSP.
- **Notification name**: the tray runs in PowerShell and shows "Windows PowerShell" by default. Run `register-notifier` once to have notifications signed as CCGuard; `unregister-notifier` removes it.
- Focus Assist or Windows notification settings may suppress balloons; trust the panel.

## Troubleshooting

| Symptom | First step |
| --- | --- |
| Double-click does nothing | Install Python 3.10+ first; double-click `CCGuard.cmd` to see the fallback message; make sure `.pyw` is associated with `pythonw` |
| `quickstart` finds no client | Start the proxy client first, or pass `--client <preset>`; run `detect` to see candidates |
| `proxy_core` fails | Run `detect`; set the core process name explicitly with `process_names` |
| `tun_adapter` fails | Confirm the client TUN is on; run `detect`; add a `tun_match` fragment if needed |
| `default_route` fails | Confirm the default route goes through TUN; check for a higher-priority route or VPN |
| `core_ipv6` / `strict_route` / `dns_hijack` unknown | Open the card's "检测过程": if no runtime config was found, set `runtime_config` to the file the client actually loads; set `config_format` if needed |
| `dns_servers` / `os_ipv6` degraded | A subscription update or client upgrade may have restored DNS override or IPv6; recheck |
| Autostart does not work | Confirm the program directory and config path have not moved; toggle it again or run `autostart-enable`; check `CCGuard.lnk` in the current user's Startup folder |
| Fonts still look poor | Use the installer build (bundles Noto Sans SC); for the Python package install Noto Sans SC or MiSans system-wide; the last fallback is `Microsoft YaHei UI` |
| The panel still looks old | pywebview or WebView2 is missing, so it fell back to tkinter; run `python -m pip install -r requirements-desktop.txt`; the new UI has a "历史" (history) page in the sidebar |
| No notifications | Check Windows notification settings and Focus Assist; the panel is the source of truth |
| "monitor stopped updating" | The monitor process exited or the interval is too long; restart the panel |
| The window will not open | tkinter is missing; use the `serve` web page |

## Project layout

```text
CCGuard.pyw / CCGuard.cmd   double-click entries for running from source
scripts/
  monitor.py                monitor engine and CLI (quickstart, check, detect, gui, serve, ip-score, update-check…)
  monitor_webview.py        WebView panel (pywebview bridge, default)
  monitor_gui.py            tkinter panel (fallback)
  monitor_history.py        state history (history.jsonl) and timelines
  monitor_guide.py          what each check looks at and how to fix it
  ip_score.py               manual exit score
  app_update.py             update check, verified download and install, update log
  claude_app.py             Claude desktop app status, close and autostart
  claude_code_guide.py      Claude Code checklist
  version.py                version number (single source)
assets/monitor/             panel pages, icons, tray script, update log
packaging/                  CCGuard.exe entry, PyInstaller spec, Inno Setup script and Chinese wizard
tools/build_windows.py      builds the exe and installer (same script as CI)
tests/                      unit and regression tests, Node page-logic tests
docs/                       usage reference and design decisions
```

## Versions and updates

- **Current version**: shown on the panel's "关于" (About) page, by `monitor.py --version`, and in `CCGuard.exe`'s file properties.
- **Update check**: on the About page click "检查更新"; it reads this repository's published releases from GitHub (no drafts or pre-releases) and lists newer versions with their notes. It contacts only GitHub. CLI: `monitor.py update-check`.
- **Automatic check (optional)**: tick "自动检查更新" on the About page to check at most once a day and show a notice in the panel when a new version is out. Off by default; stored in `prefs.json` next to the config.
- **In-app install**: in the installed app, "下载并安装" asks first, downloads the installer from this repository's release, checks it against `SHA256SUMS-installer-*.txt` from the same release, and only then closes CCGuard, installs silently and reopens it. A hash mismatch stops the install. When run from source it opens the release page instead.
- **Manual upgrade**: run the newer installer; it closes a running CCGuard first and keeps `monitor.json` and `history.jsonl`.
- **Update log**: the About page lists each version's main changes (bundled, works offline); the full development record is [CHANGELOG.md](CHANGELOG.md).
- **Numbering**: `major.minor.patch`; fixes bump the patch number, features bump the minor number. The version lives only in `scripts/version.py`, which the UI, CLI, exe properties and installer all read.

**Releasing** (maintainers):

1. Bump `__version__` in `version.py` and add the version's entry at the top of `assets/monitor/release-notes.json` (a test checks they match).
2. Update CHANGELOG, run the full suite, push to main, and wait for the push CI and the installer build.
3. After the user confirms, publish a GitHub Release tagged `vX.Y.Z`. The `Windows installer` workflow fails if the tag differs from `version.py`; otherwise it builds, verifies and attaches the installer.
4. Download the published assets, check their hashes, and record the release in CHANGELOG.

## Development and verification

```bash
python -m unittest discover -s tests -v
node tests/monitor-panel.cjs
node tests/monitor-interaction.cjs
python -m compileall -q scripts packaging tools
python -m pip install -r requirements-build.txt && python tools/build_windows.py   # build the exe (Windows)
```

- CI runs the tests on Linux and Windows (Python 3.12) and on Linux Python 3.10; when the app or packaging changes, the `Windows installer` workflow also builds the installer and verifies a silent install, self-test and uninstall.
- See [CHANGELOG.md](CHANGELOG.md) for the full record, [docs/decisions.md](docs/decisions.md) for design trade-offs and [AGENTS.md](AGENTS.md) for contribution rules.

## Documentation

| Document | Contents |
| --- | --- |
| [Monitor reference](docs/monitor.md) (Chinese) | Configuration, client presets, checks, notifications and boundaries |
| [How checks work](docs/monitor.md#principles) | Data source, rule and detection log for every check; requests and privacy of the exit score |
| [Design decisions](docs/decisions.md) | Main implementation trade-offs |
| [Changelog](CHANGELOG.md) | What changed in each version and how it was verified |
| [Releases](https://github.com/SumitaRinku/CCGuard/releases) | Installer and checksums |

## Feedback

Report problems through [Issues](https://github.com/SumitaRinku/CCGuard/issues). Include the Windows version, proxy client and version, reproduction steps and expected result; keep accounts, credentials, subscription links and full configs out of it.

## Data sources and credits

- The **exit score**'s trust score, IP type, location, network and risk flags come from the public API of [ip.net.coffee](https://ip.net.coffee/claude/); the score bands and restricted-region rule follow its Claude IP check page. Open that site in your browser for the full check (Claude exit IP, DNS and WebRTC leaks).
- The **Claude Code checklist** items and their reasoning follow [ip.net.coffee's guide to using Claude Code reliably](https://ip.net.coffee/claude/claudecode.html), rewritten in our own words; the panel links to the original.
- The **exit IP** comes from Cloudflare's `1.1.1.1/cdn-cgi/trace`.
- The installed app's UI font is [Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC) (Adobe and Google, SIL Open Font License 1.1), downloaded at build time from a fixed commit of [google/fonts](https://github.com/google/fonts/tree/main/ofl/notosanssc) with its hash checked; the license text ships with the app (`_internal\ccguard\assets\monitor\fonts\OFL.txt` in the install folder).
- The installer wizard's Simplified Chinese translation is the community translation carried in the official Inno Setup repository ([jrsoftware/issrc](https://github.com/jrsoftware/issrc), `Files/Languages/Unofficial/ChineseSimplified.isl`, maintained by Kira), kept with its credits.

## License

GPL-3.0-only, see [LICENSE](LICENSE). Third-party files (font, wizard translation) keep their own licenses and credits.
