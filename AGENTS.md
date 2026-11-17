# CCGuard 协作规范

本文件是仓库唯一的协作规则，供编码 Agent 和人工维护者使用；CLAUDE.md 只引用本文件。

## 项目

CCGuard 是 Windows 本机只读监测面板：检查代理核心、TUN、默认路由、防火墙、DNS 与 IPv6，失效时用托盘和系统通知提醒。只支持 Windows 10/11。功能与边界以 [docs/monitor.md](docs/monitor.md) 为准，设计取舍记在 [docs/decisions.md](docs/decisions.md)，变更记在 [CHANGELOG.md](CHANGELOG.md)。

## Git 与交付

- 相关测试通过后直接提交并推送 main，不创建 PR，不必逐批询问（用户常设授权）。使用普通、非强制提交；不强推，不改写共享历史；推送前核实远端 HEAD，有并发更新先整合。
- 推送后核实远端提交，并跟踪 CI 到最终结果。CI 跑 Linux 与 Windows（Python 3.12），另跑 Linux Python 3.10；涉及程序、打包或安装程序时，`Windows installer` 工作流还要构建并做静默安装、自检、卸载验证。没运行的不算通过。
- 发布 GitHub Release（稳定版本）必须先得到用户确认。
- 提交说明写清改了什么、为什么、测试命令与结果；结尾附协作者署名。

## 实现与验证

- 每次改动补齐单元测试；修缺陷必须加能复现旧问题的回归测试。不靠删测试、放松断言、吞掉异常来让测试变绿。
- 推送前跑：`python -m unittest discover -s tests`、`node tests/monitor-panel.cjs`、`node tests/monitor-interaction.cjs`、`python -m compileall -q scripts packaging tools`。改到打包时用 `python tools/build_windows.py` 本地构建并看自检结果。
- 改界面时实际打开面板截图核对；写清在什么环境验证过，没验证的标 not_run，不把局部结果说成全部完成。
- 改动保持小范围、可审查、可回退；不覆盖与任务无关的文件。

## 运行边界

- **只读**：不修改防火墙、路由、代理配置或系统设置，不重启代理核心，不需要管理员。
- **监测不联网**：10 项检查只读本机。联网功能只在用户点击时运行，只联系固定地址：出口评分请求 `1.1.1.1/cdn-cgi/trace` 和 `ip.net.coffee/api/iprisk`，检查更新请求 GitHub 本仓库的发布列表。不访问 claude.ai、anthropic.com；ip.net.coffee 的完整检测页只能由用户在自己的浏览器里打开。
- **隐私**：状态文件、检测日志、历史记录和通知不写 IP 地址和文件路径；界面只显示 IP 前两段。不向仓库、日志、测试夹具或 Issue 写入密码、令牌、订阅链接、真实代理地址或个人机器记录。
- 新增依赖、付费服务、自动下载或自动更新，先说明取舍并得到用户确认。构建依赖固定版本（`requirements-build.txt`），打包的第三方文件固定来源并校验哈希。

## 版本

- 版本号只写在 `scripts/version.py`。发版时同时改 `version.py`、在 `assets/monitor/release-notes.json` 最前面加这个版本的更新日志、写 CHANGELOG；测试会检查前两者一致，发布标签与 `version.py` 不一致时安装程序构建会失败。
- 发布后下载资产核对哈希，把发布记录写进 CHANGELOG。

## 表达

- 不用“所有者”这一称谓。直接写规则与结论，保留日期、决定和验证结果。
- 界面文字简洁：不滥用中圆点，不常驻摆放说明、免责或统计文字。
