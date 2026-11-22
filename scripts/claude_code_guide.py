"""Claude Code stability checklist, based on https://ip.net.coffee/claude/claudecode.html.

Thirteen items, written in our own words. Where the panel can check an item locally it does: from the
10 monitor checks, the last exit score (including time-zone consistency), and a few top-level keys
and the rule order of the proxy core's Clash/Mihomo config. Nothing here touches the network; rule
targets, group and node names are never returned, only whether a Claude rule exists, where it sits,
whether required domains are covered, and whether any rule routes DIRECT or REJECT.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SOURCE_URL = 'https://ip.net.coffee/claude/claudecode.html'
ASIA = {'JP', 'SG', 'KR', 'TW', 'HK', 'MO', 'MY', 'TH', 'PH', 'VN', 'ID', 'IN'}
NEAR = {'US', 'CA'}
BROAD_RULES = ('GEOSITE', 'GEOIP', 'MATCH', 'FINAL', 'RULE-SET')
DOMAIN_RULES = ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-REGEX')
CLAUDE = re.compile(r'anthropic|claude', re.I)
REQUIRED_CLAUDE_DOMAINS = ('anthropic.com', 'claude.ai', 'claude.com')
REJECT_TARGETS = ('REJECT', 'REJECT-DROP')
_AUTO = object()

# Fallback for frozen Windows builds that do not ship tzdata: (std_minutes, dst_rule).
_FALLBACK_ZONES = {
    'utc': 0, 'etc/utc': 0, 'etc/gmt': 0, 'gmt': 0,
    'asia/tokyo': 540, 'asia/seoul': 540, 'asia/pyongyang': 540,
    'asia/shanghai': 480, 'asia/chongqing': 480, 'asia/harbin': 480, 'asia/urumqi': 480,
    'asia/hong_kong': 480, 'asia/macau': 480, 'asia/taipei': 480, 'asia/singapore': 480,
    'asia/kuala_lumpur': 480, 'asia/manila': 480, 'asia/makassar': 480,
    'asia/bangkok': 420, 'asia/ho_chi_minh': 420, 'asia/saigon': 420, 'asia/jakarta': 420,
    'asia/phnom_penh': 420, 'asia/vientiane': 420,
    'asia/dhaka': 360, 'asia/yangon': 390, 'asia/kathmandu': 345,
    'asia/kolkata': 330, 'asia/calcutta': 330, 'asia/colombo': 330,
    'asia/almaty': 300, 'asia/tashkent': 300, 'asia/karachi': 300,
    'asia/dubai': 240, 'asia/muscat': 240,
    'asia/riyadh': 180, 'asia/kuwait': 180, 'europe/moscow': 180, 'europe/istanbul': 180,
    'america/phoenix': -420, 'pacific/honolulu': -600,
    'america/sao_paulo': -180, 'america/argentina/buenos_aires': -180,
    'america/new_york': (-300, 'us'), 'america/toronto': (-300, 'us'), 'america/detroit': (-300, 'us'),
    'america/chicago': (-360, 'us'), 'america/winnipeg': (-360, 'us'),
    'america/denver': (-420, 'us'), 'america/edmonton': (-420, 'us'),
    'america/los_angeles': (-480, 'us'), 'america/vancouver': (-480, 'us'),
    'america/anchorage': (-540, 'us'), 'america/st_johns': (-210, 'us'),
    'europe/london': (0, 'eu'), 'europe/dublin': (0, 'eu'), 'europe/lisbon': (0, 'eu'),
    'europe/paris': (60, 'eu'), 'europe/berlin': (60, 'eu'), 'europe/amsterdam': (60, 'eu'),
    'europe/brussels': (60, 'eu'), 'europe/madrid': (60, 'eu'), 'europe/rome': (60, 'eu'),
    'europe/zurich': (60, 'eu'), 'europe/vienna': (60, 'eu'), 'europe/stockholm': (60, 'eu'),
    'europe/oslo': (60, 'eu'), 'europe/warsaw': (60, 'eu'), 'europe/prague': (60, 'eu'),
    'europe/helsinki': (120, 'eu'), 'europe/athens': (120, 'eu'), 'europe/bucharest': (120, 'eu'),
    'europe/sofia': (120, 'eu'), 'europe/kiev': (120, 'eu'), 'europe/kyiv': (120, 'eu'),
    'australia/brisbane': 600, 'australia/perth': 480,
    'australia/sydney': (600, 'au'), 'australia/melbourne': (600, 'au'), 'australia/adelaide': (570, 'au'),
    'pacific/auckland': (720, 'nz'),
}

ITEMS = [
    ('exit_ip', '出口 IP 用住宅或 ISP 地址',
     '风控首先看出口 IP 的类型和信誉。家宽、ISP 地址最好，原生 VPS 次之，云厂商机房段和多人共用的代理 IP 风险最高。',
     '在“出口”页检测当前出口；类型是机房或带 VPN／代理标记时，换住宅或 ISP 出口。'),
    ('ip_stability', '出口要稳定',
     '家宽 IP 偶尔变化是正常现象；机房 IP 频繁切换会触发异常检测、限速和响应抖动。',
     '用机房 IP 时固定一个出口长期使用，不要在多个节点间来回切换；关掉客户端的自动测速选节点。'),
    ('timezone_match', '本机时区与出口一致',
     '网页和客户端环境能直接读取本机时区（IANA 时区与 UTC 偏移），服务端会拿它与出口 IP 所在时区比对，不一致时容易触发风控。',
     '将系统时区设为与固定出口一致，或改用与本机同一时区的代理出口。'),
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
     'Claude 除了 claude.ai 和 anthropic.com，开发者平台与登录还会访问 claude.com 及风控子域 s-cdn.anthropic.com，都要走同一个代理出口，且不能被去广告规则拦截。',
     '为 anthropic.com、claude.ai、claude.com 写专门的分流规则并指向同一个固定出口，不要指向 DIRECT，也不要拦截 s-cdn.anthropic.com。'),
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
    ('device_env', '固定客户端与浏览器环境',
     '网页风控采集显卡、Canvas、音频、CPU 核数等 70 余项软硬件特征，清 Cookie、开无痕或换浏览器资料夹都不会改变指纹；桌面版和 CLI 也会保存固定设备 ID。同一设备登录多个账号或使用篡改指纹、自动化工具会触发高危标记。',
     '固定在同一个正常浏览器或 Claude 桌面版使用同一账号；不要在同一设备上切换多个账号，不装伪造 UA／Canvas 指纹的扩展，不用自动化工具驱动浏览器。'),
]


def _nth_sunday(year, month, n):
    """Return UTC midnight of the nth (1-based) or last (-1) Sunday of the given month."""
    if n > 0:
        first = datetime(year, month, 1, tzinfo=timezone.utc)
        return first + timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))
    next_month = datetime(year + (month == 12), (month % 12) + 1, 1, tzinfo=timezone.utc)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - 6) % 7)


def _dst_active(utc_dt, std_minutes, rule):
    year = utc_dt.year
    shift = timedelta(minutes=std_minutes)
    if rule == 'us':
        start = _nth_sunday(year, 3, 2) + timedelta(hours=2) - shift
        end = _nth_sunday(year, 11, 1) + timedelta(hours=1) - shift
        return start <= utc_dt < end
    if rule == 'eu':
        start = _nth_sunday(year, 3, -1) + timedelta(hours=1)
        end = _nth_sunday(year, 10, -1) + timedelta(hours=1)
        return start <= utc_dt < end
    if rule == 'au':
        end = _nth_sunday(year, 4, 1) + timedelta(hours=2) - shift
        start = _nth_sunday(year, 10, 1) + timedelta(hours=2) - shift
        return utc_dt < end or utc_dt >= start
    if rule == 'nz':
        end = _nth_sunday(year, 4, 1) + timedelta(hours=2) - shift
        start = _nth_sunday(year, 9, -1) + timedelta(hours=2) - shift
        return utc_dt < end or utc_dt >= start
    return False


def _utc_text(minutes):
    sign = '-' if minutes < 0 else '+'
    hours, mins = divmod(abs(int(minutes)), 60)
    return 'UTC%s%d%s' % (sign, hours, ':%02d' % mins if mins else '')


def tz_offset_minutes(zone_name, now=None):
    """Minutes east of UTC for an IANA zone at `now`, or None when unknown."""
    zone = str(zone_name or '').strip()
    if not zone or zone == '未知':
        return None
    if now is None:
        now_utc = datetime.now(timezone.utc)
    else:
        now_utc = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    try:
        offset = now_utc.astimezone(ZoneInfo(zone)).utcoffset()
        if offset is not None:
            return int(round(offset.total_seconds() / 60))
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        pass
    entry = _FALLBACK_ZONES.get(zone.lower())
    if entry is None:
        return None
    if isinstance(entry, tuple):
        std_minutes, rule = entry
        return std_minutes + (60 if _dst_active(now_utc, std_minutes, rule) else 0)
    return entry


def local_offset_minutes(now=None):
    """Current machine's minutes east of UTC, or None if unavailable."""
    dt = now if now is not None else datetime.now().astimezone()
    if dt.tzinfo is None:
        dt = dt.astimezone()
    offset = dt.utcoffset()
    return int(round(offset.total_seconds() / 60)) if offset is not None else None


def _rule_target(parts):
    if len(parts) <= 2:
        return ''
    return parts[2].split('#', 1)[0].strip().upper()


def _covered_domains(kind, pattern):
    """Subset of REQUIRED_CLAUDE_DOMAINS covered by one non-REJECT rule (whitelist constants only)."""
    text = pattern.split('#', 1)[0].strip().lower()
    if kind == 'RULE-SET':
        return set(REQUIRED_CLAUDE_DOMAINS) if CLAUDE.search(text) else set()
    if kind == 'DOMAIN':
        return {domain for domain in REQUIRED_CLAUDE_DOMAINS if text == domain}
    if kind == 'DOMAIN-SUFFIX':
        domain = text.lstrip('.')
        return {req for req in REQUIRED_CLAUDE_DOMAINS if domain == req or req.endswith('.' + domain)}
    if kind == 'DOMAIN-KEYWORD':
        return {req for req in REQUIRED_CLAUDE_DOMAINS if text in req}
    if kind == 'DOMAIN-REGEX':
        try:
            regex = re.compile(text, re.I)
        except re.error:
            return set()
        return {req for req in REQUIRED_CLAUDE_DOMAINS if regex.search(req)}
    return set()


def read_routing(path, config_format='auto'):
    """Clash/Mihomo only: the keys and rule positions the checklist needs, nothing else."""
    result = {'readable': False, 'mode': None, 'global_fingerprint': None, 'node_fingerprints': 0,
              'disable_keep_alive': None, 'rules': 0, 'claude_rule': None, 'claude_direct': False,
              'claude_reject': False, 'missing_domains': [], 'broad_rule': None}
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
    first_match = first_proxy_match = None
    covered = set()
    for index, rule in enumerate(rules):
        parts = [part.strip() for part in rule.split(',')]
        kind = parts[0].upper() if parts else ''
        is_claude = ((kind in DOMAIN_RULES and len(parts) > 1 and CLAUDE.search(parts[1]))
                     or (kind == 'RULE-SET' and len(parts) > 1 and CLAUDE.search(parts[1])))
        if is_claude:
            if first_match is None:
                first_match = index
            target = _rule_target(parts)
            if target in REJECT_TARGETS:
                result['claude_reject'] = True
            else:
                if first_proxy_match is None:
                    first_proxy_match = index
                if target == 'DIRECT':
                    result['claude_direct'] = True
                covered |= _covered_domains(kind, parts[1])
        if result['broad_rule'] is None and kind in BROAD_RULES and not (kind == 'RULE-SET' and len(parts) > 1 and CLAUDE.search(parts[1])):
            result['broad_rule'] = index
    result['claude_rule'] = first_proxy_match if first_proxy_match is not None else first_match
    if first_proxy_match is not None:
        result['missing_domains'] = [domain for domain in REQUIRED_CLAUDE_DOMAINS if domain not in covered]
    return result


def _states(checks):
    return {check.get('id'): check.get('state') for check in checks or []}


def evaluate(checks=None, exit_result=None, routing=None, local_offset=_AUTO):
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

    resolved_local = local_offset_minutes() if local_offset is _AUTO else local_offset
    zone = str(facts.get('timezone') or '').strip()
    exit_offset = tz_offset_minutes(zone) if scored else None
    if not scored or exit_offset is None or resolved_local is None:
        out['timezone_match'] = ('unknown', '检测出口后对比本机与出口时区')
    elif exit_offset == resolved_local:
        out['timezone_match'] = ('ok', '本机与出口同为 %s（%s）' % (_utc_text(resolved_local), zone))
    else:
        out['timezone_match'] = ('warn', '出口为 %s（%s），本机为 %s' % (zone, _utc_text(exit_offset), _utc_text(resolved_local)))

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
        out['claude_rules'] = ('warn', '没有找到 anthropic.com／claude.ai／claude.com 的分流规则')
        out['rule_priority'] = ('warn', '没有 Claude 专用规则，请求由通用规则决定')
    else:
        if routing.get('claude_reject'):
            out['claude_rules'] = ('warn', 'Claude 相关域名含 REJECT 拦截规则，会导致风控信标或请求异常')
        elif routing.get('claude_direct'):
            out['claude_rules'] = ('warn', 'Claude 规则指向 DIRECT，请求不经过代理')
        elif routing.get('missing_domains'):
            out['claude_rules'] = ('warn', '已有 Claude 规则，但缺少 %s，部分页面可能走其他出口' % '、'.join(routing['missing_domains']))
        else:
            out['claude_rules'] = ('ok', '找到 Claude 分流规则（第 %d 条）' % (routing['claude_rule'] + 1))
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

    out['device_env'] = ('manual', '固定单一客户端与账号，不用指纹伪装或自动化驱动')

    return [{'id': item_id, 'title': title, 'status': out[item_id][0], 'note': out[item_id][1], 'why': why, 'how': how}
            for item_id, title, why, how in ITEMS]
