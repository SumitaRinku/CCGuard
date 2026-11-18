"""Claude Code stability checklist, based on https://ip.net.coffee/claude/claudecode.html.

Eleven items, written in our own words. Where the panel can check an item locally it does: from the
10 monitor checks, the last exit score, and a few top-level keys and the rule order of the proxy
core's Clash/Mihomo config. Nothing here touches the network; rule targets, group and node names are
never returned, only whether a Claude rule exists, where it sits, and whether it routes DIRECT.
"""
from pathlib import Path
import re

SOURCE_URL = 'https://ip.net.coffee/claude/claudecode.html'
ASIA = {'JP', 'SG', 'KR', 'TW', 'HK', 'MO', 'MY', 'TH', 'PH', 'VN', 'ID', 'IN'}
NEAR = {'US', 'CA'}
BROAD_RULES = ('GEOSITE', 'GEOIP', 'MATCH', 'FINAL', 'RULE-SET')
DOMAIN_RULES = ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-REGEX')
CLAUDE = re.compile(r'anthropic|claude', re.I)

ITEMS = [
    ('exit_ip', '出口 IP 用住宅或 ISP 地址',
     '风控首先看出口 IP 的类型和信誉。家宽、ISP 地址最好，原生 VPS 次之，云厂商机房段和多人共用的代理 IP 风险最高。',
     '在“出口”页检测当前出口；类型是机房或带 VPN／代理标记时，换住宅或 ISP 出口。'),
    ('ip_stability', '出口要稳定',
     '家宽 IP 偶尔变化是正常现象；机房 IP 频繁切换会触发异常检测、限速和响应抖动。',
     '用机房 IP 时固定一个出口长期使用，不要在多个节点间来回切换；关掉客户端的自动测速选节点。'),
    ('tcp_only', '只走 TCP，不让 UDP 漏出',
     'Claude Code 的请求是 HTTPS（TCP）。放开 UDP／QUIC 时，丢包更敏感，UDP 还可能绕过代理暴露真实 IP。',
     '在代理配置里把 Claude 相关出站限制为 TCP；浏览器里用 WebRTC 泄露检测确认没有真实 IP。'),
    ('tls_fingerprint', 'TLS 指纹模拟浏览器',
     '代理客户端默认的 TLS 握手和真实浏览器不同，可以据此识别出代理流量。',
     'Clash／Mihomo 设置 global-client-fingerprint: chrome，或给节点设置 client-fingerprint: chrome。'),
    ('dns_proxy', 'DNS 走代理',
     '连接来自海外出口、DNS 查询却发给本地运营商，这种地域不一致是常见的风控原因。',
     '开启代理核心的 DNS 接管，使用代理内的加密 DNS（DoH），物理网卡 DNS 指向代理。'),
    ('ipv6_off', '关闭 IPv6',
     '代理环境下 IPv6 会让分流失效、DNS 泄露，或者多出第二个出口地址。',
     '代理核心设置 ipv6: false，同时在物理网卡上关闭 IPv6。'),
    ('claude_rules', 'Claude 单独分流',
     'Claude Code 除了 claude.ai 和 api.anthropic.com，还会访问认证、CDN 等域名，都要走同一个出口。',
     '为 anthropic.com、claude.ai 写专门的分流规则，指向固定的代理出口，不要指向 DIRECT。完整域名列表见来源页面。'),
    ('rule_priority', 'Claude 规则排在通用规则前面',
     'GEOSITE、GEOIP 一类通配规则会把 Claude 的请求分到不同出口，甚至命中直连。',
     '把 Claude 的规则放在所有通用规则之前。'),
    ('keep_alive', '保持连接复用',
     '每次请求都重新建立 TCP + TLS 连接，延迟高，大量短连接也更像机器行为。',
     '不要关闭代理客户端的 keep-alive（Mihomo 的 disable-keep-alive 保持 false），也不要频繁断开重连代理。'),
    ('concurrency', '控制并发',
     '多个 Claude Code 任务共用一个出口 IP，短时间内高并发会触发限速。',
     '同一个出口 IP 上同时运行的任务控制在 5 个以内；需要更多时分散到多个出口。'),
    ('network_path', '网络路径短',
     '出口到 Anthropic 服务器的路径越短越稳定：亚洲出口到亚洲最好，到北美西海岸可以接受，绕经欧洲最差。',
     '优先选择亚洲或北美西海岸的出口节点。'),
]


def read_routing(path, config_format='auto'):
    """Clash/Mihomo only: the keys and rule positions the checklist needs, nothing else."""
    result = {'readable': False, 'mode': None, 'global_fingerprint': None, 'node_fingerprints': 0,
              'disable_keep_alive': None, 'rules': 0, 'claude_rule': None, 'claude_direct': False, 'broad_rule': None}
    if not path or config_format not in ('auto', 'clash'):
        return result
    try:
        text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
    except OSError:
        return result
    if config_format == 'auto' and not re.search(r'(?m)^(rules|proxies|proxy-groups|mode)\s*:', text):
        return result
    result['readable'] = True

    def scalar(key):
        match = re.search(r'(?m)^%s\s*:\s*["\']?([^"\'#\s]+)' % re.escape(key), text)
        return match.group(1).strip().lower() if match else None

    result['mode'] = scalar('mode')
    result['global_fingerprint'] = scalar('global-client-fingerprint')
    keep = scalar('disable-keep-alive')
    result['disable_keep_alive'] = None if keep is None else keep in ('true', 'yes')
    result['node_fingerprints'] = len(re.findall(r'(?<!global-)client-fingerprint\s*:\s*["\']?chrome', text))
    rules, in_rules = [], False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line[0].isspace():
            in_rules = line.startswith('rules:')
            continue
        item = line.strip()
        if in_rules and item.startswith('- '):
            rules.append(item[2:].strip().strip('"\''))
    result['rules'] = len(rules)
    for index, rule in enumerate(rules):
        parts = [part.strip() for part in rule.split(',')]
        kind = parts[0].upper() if parts else ''
        if result['claude_rule'] is None and (
                (kind in DOMAIN_RULES and len(parts) > 1 and CLAUDE.search(parts[1]))
                or (kind == 'RULE-SET' and len(parts) > 1 and CLAUDE.search(parts[1]))):
            result['claude_rule'] = index
            result['claude_direct'] = len(parts) > 2 and parts[2].upper() == 'DIRECT'
        if result['broad_rule'] is None and kind in BROAD_RULES and not (kind == 'RULE-SET' and len(parts) > 1 and CLAUDE.search(parts[1])):
            result['broad_rule'] = index
    return result


def _states(checks):
    return {check.get('id'): check.get('state') for check in checks or []}


def evaluate(checks=None, exit_result=None, routing=None):
    """[{'id','title','status','note','why','how'}]: status ok / warn / unknown / manual."""
    states = _states(checks)
    routing = routing or {}
    facts = (exit_result or {}).get('facts') or {}
    scored = bool(exit_result and exit_result.get('ok'))
    out = {}

    if not scored:
        out['exit_ip'] = ('unknown', '还没有检测出口，去“出口”页点“检测”')
    elif facts.get('kind') == '机房' or facts.get('flags'):
        out['exit_ip'] = ('warn', '当前出口是%s%s' % (facts.get('kind', '未知类型'),
                                                  '，带' + '、'.join(facts['flags']) + '标记' if facts.get('flags') else ''))
    elif facts.get('kind') in ('住宅', '运营商', '移动网络'):
        out['exit_ip'] = ('ok', '当前出口是%s，信任分 %s' % (facts['kind'], exit_result.get('score')))
    else:
        out['exit_ip'] = ('unknown', '出口类型未知（%s）' % facts.get('kind', '未知'))

    out['ip_stability'] = ('warn', '当前是机房出口：固定这个出口，不要频繁切换') if scored and facts.get('kind') == '机房' \
        else ('manual', '家宽出口偶尔变化没关系；机房出口要固定')
    out['tcp_only'] = ('manual', '在代理配置和浏览器里自查')

    if not routing.get('readable'):
        out['tls_fingerprint'] = ('unknown', '读不到 Clash／Mihomo 运行配置')
    elif routing.get('global_fingerprint') == 'chrome':
        out['tls_fingerprint'] = ('ok', '全局 TLS 指纹为 chrome')
    elif routing.get('node_fingerprints'):
        out['tls_fingerprint'] = ('ok', '%d 个节点设置了 chrome 指纹' % routing['node_fingerprints'])
    else:
        out['tls_fingerprint'] = ('warn', '没有设置 chrome 指纹（当前全局指纹：%s）' % (routing.get('global_fingerprint') or '未设置'))

    dns = [states.get('dns_hijack'), states.get('dns_servers')]
    out['dns_proxy'] = ('ok', 'DNS 接管与网卡 DNS 都正常') if all(s == 'ok' for s in dns) \
        else ('warn', '见状态页的 DNS 接管、网卡 DNS') if any(s in ('fail', 'degraded') for s in dns) \
        else ('unknown', '状态页的 DNS 检查还没有结果')
    v6 = [states.get('core_ipv6'), states.get('os_ipv6')]
    out['ipv6_off'] = ('ok', '代理核心和系统 IPv6 都已关闭') if all(s == 'ok' for s in v6) \
        else ('warn', '见状态页的核心 IPv6、系统 IPv6') if any(s in ('fail', 'degraded') for s in v6) \
        else ('unknown', '状态页的 IPv6 检查还没有结果')

    mode = routing.get('mode')
    if not routing.get('readable'):
        out['claude_rules'] = out['rule_priority'] = ('unknown', '读不到 Clash／Mihomo 运行配置')
    elif mode == 'global':
        out['claude_rules'] = out['rule_priority'] = ('ok', '全局模式：所有流量走同一个出口')
    elif mode == 'direct':
        out['claude_rules'] = out['rule_priority'] = ('warn', '直连模式：流量不经过代理')
    elif routing.get('claude_rule') is None:
        out['claude_rules'] = ('warn', '没有找到 anthropic.com／claude.ai 的分流规则')
        out['rule_priority'] = ('warn', '没有 Claude 专用规则，请求由通用规则决定')
    else:
        out['claude_rules'] = ('warn', 'Claude 规则指向 DIRECT，请求不经过代理') if routing.get('claude_direct') \
            else ('ok', '找到 Claude 分流规则（第 %d 条）' % (routing['claude_rule'] + 1))
        broad = routing.get('broad_rule')
        out['rule_priority'] = ('ok', 'Claude 规则在第 %d 条，通用规则从第 %d 条开始' % (routing['claude_rule'] + 1, broad + 1)) \
            if broad is None or routing['claude_rule'] < broad \
            else ('warn', 'Claude 规则排在通用规则（第 %d 条）之后' % (broad + 1))

    if not routing.get('readable') or routing.get('disable_keep_alive') is None:
        out['keep_alive'] = ('manual', '确认代理客户端没有关闭 keep-alive') if not routing.get('readable') \
            else ('ok', '配置没有关闭 keep-alive')
    else:
        out['keep_alive'] = ('warn', '配置里 disable-keep-alive 为 true') if routing['disable_keep_alive'] \
            else ('ok', 'keep-alive 保持开启')
    out['concurrency'] = ('manual', '同一出口上同时运行的任务不超过 5 个')

    code = str(facts.get('country_code') or '').upper()
    if not scored or not code:
        out['network_path'] = ('unknown', '检测出口后显示出口所在地区')
    elif code in ASIA:
        out['network_path'] = ('ok', '出口在亚洲（%s）' % facts.get('location', code))
    elif code in NEAR:
        out['network_path'] = ('ok', '出口在北美（%s）' % facts.get('location', code))
    else:
        out['network_path'] = ('warn', '出口在 %s，路径可能绕远' % facts.get('location', code))

    return [{'id': item_id, 'title': title, 'status': out[item_id][0], 'note': out[item_id][1], 'why': why, 'how': how}
            for item_id, title, why, how in ITEMS]
