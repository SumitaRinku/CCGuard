"""Claude Code checklist: routing read from a synthetic config, and each item's status."""
from datetime import datetime, timezone
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
guide = importlib.import_module('claude_code_guide')

CONFIG = '''mixed-port: 7890
mode: rule
ipv6: false
global-client-fingerprint: chrome
disable-keep-alive: false
proxies:
  - {name: secret-node-tokyo, type: vless, server: 203.0.113.9, uuid: do-not-leak, client-fingerprint: chrome}
proxy-groups:
  - {name: MyPrivateGroup, type: select, proxies: [secret-node-tokyo]}
rules:
  - DOMAIN-SUFFIX,anthropic.com,MyPrivateGroup
  - DOMAIN-SUFFIX,claude.ai,MyPrivateGroup
  - GEOSITE,cn,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,MyPrivateGroup
'''


class Routing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'config.yaml'

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, text, fmt='auto'):
        self.path.write_text(text, encoding='utf-8')
        return guide.read_routing(self.path, fmt)

    def test_reads_keys_and_rule_order(self):
        r = self.read(CONFIG)
        self.assertTrue(r['readable'])
        self.assertEqual((r['mode'], r['global_fingerprint'], r['disable_keep_alive']), ('rule', 'chrome', False))
        self.assertEqual((r['rules'], r['claude_rule'], r['broad_rule'], r['claude_direct']), (5, 0, 2, False))
        self.assertEqual(r['node_fingerprints'], 1)
        self.assertFalse(r['claude_reject'])
        self.assertEqual(r['missing_domains'], ['claude.com'])

    def test_all_required_domains_covered_by_suffix_keyword_or_ruleset(self):
        full = CONFIG.replace('  - DOMAIN-SUFFIX,claude.ai,MyPrivateGroup\n',
                              '  - DOMAIN-SUFFIX,claude.ai,MyPrivateGroup\n  - DOMAIN-SUFFIX,claude.com,MyPrivateGroup\n')
        self.assertEqual(self.read(full)['missing_domains'], [])

        keyword = 'mode: rule\nrules:\n  - DOMAIN-KEYWORD,claude,MyPrivateGroup\n  - DOMAIN-SUFFIX,anthropic.com,MyPrivateGroup\n  - MATCH,MyPrivateGroup\n'
        self.assertEqual(self.read(keyword)['missing_domains'], [])

        ruleset = 'mode: rule\nrules:\n  - RULE-SET,claude-domains,MyPrivateGroup\n  - MATCH,MyPrivateGroup\n'
        self.assertEqual(self.read(ruleset)['missing_domains'], [])

    def test_reject_rules_are_flagged_and_skipped_for_proxy_order(self):
        text = ('mode: rule\nrules:\n'
                '  - DOMAIN,s-cdn.anthropic.com,REJECT\n'
                '  - DOMAIN-SUFFIX,anthropic.com,MyPrivateGroup\n'
                '  - DOMAIN-SUFFIX,claude.ai,MyPrivateGroup\n'
                '  - DOMAIN-SUFFIX,claude.com,MyPrivateGroup\n'
                '  - MATCH,MyPrivateGroup\n')
        r = self.read(text)
        self.assertTrue(r['claude_reject'])
        self.assertEqual(r['claude_rule'], 1)
        self.assertEqual(r['missing_domains'], [])

        drop = 'mode: rule\nrules:\n  - DOMAIN-SUFFIX,anthropic.com,REJECT-DROP\n  - MATCH,MyPrivateGroup\n'
        r_drop = self.read(drop)
        self.assertTrue(r_drop['claude_reject'])
        self.assertEqual(r_drop['claude_rule'], 0)

    def test_never_returns_names_addresses_or_secrets(self):
        body = json.dumps(self.read(CONFIG))
        for secret in ('secret-node', 'MyPrivateGroup', '203.0.113', 'do-not-leak', 'vless'):
            self.assertNotIn(secret, body)

    def test_claude_after_broad_rules_and_direct(self):
        text = CONFIG.replace('  - DOMAIN-SUFFIX,anthropic.com,MyPrivateGroup\n  - DOMAIN-SUFFIX,claude.ai,MyPrivateGroup\n', '')
        text += '  - DOMAIN-SUFFIX,claude.ai,DIRECT\n'
        r = self.read(text)
        self.assertEqual((r['claude_rule'], r['broad_rule'], r['claude_direct']), (3, 0, True))

    def test_empty_fingerprint_and_missing_keys(self):
        r = self.read('mode: "rule"\nglobal-client-fingerprint: ""\nrules:\n  - MATCH,X\n')
        self.assertIsNone(r['global_fingerprint'])
        self.assertIsNone(r['disable_keep_alive'])
        self.assertIsNone(r['claude_rule'])
        self.assertFalse(r['claude_reject'])
        self.assertEqual(r['missing_domains'], [])

    def test_non_clash_or_missing_is_unreadable(self):
        self.assertFalse(self.read('{"route": {"rules": []}}')['readable'])
        self.assertFalse(self.read(CONFIG, 'sing-box')['readable'])
        self.assertFalse(guide.read_routing('', 'auto')['readable'])
        self.assertFalse(guide.read_routing(Path(self.tmp.name) / 'missing.yaml')['readable'])


CHECKS_OK = [{'id': name, 'state': 'ok'} for name in ('dns_hijack', 'dns_servers', 'core_ipv6', 'os_ipv6')]
RESIDENTIAL = {'ok': True, 'score': 100,
               'facts': {'kind': '住宅', 'flags': [], 'country_code': 'JP', 'location': 'Japan Tokyo', 'timezone': 'Asia/Tokyo'}}
GOOD = {'readable': True, 'mode': 'rule', 'global_fingerprint': 'chrome', 'node_fingerprints': 0,
        'disable_keep_alive': False, 'rules': 6, 'claude_rule': 0, 'claude_direct': False,
        'claude_reject': False, 'missing_domains': [], 'broad_rule': 3}


def statuses(checks=CHECKS_OK, exit_result=RESIDENTIAL, routing=GOOD, local_offset=540):
    return {item['id']: item['status'] for item in guide.evaluate(checks, exit_result, routing, local_offset=local_offset)}


class Evaluate(unittest.TestCase):
    def test_thirteen_items_with_guidance(self):
        items = guide.evaluate(CHECKS_OK, RESIDENTIAL, GOOD, local_offset=540)
        self.assertEqual(len(items), 13)
        for item in items:
            self.assertTrue(item['title'] and item['why'] and item['how'] and item['note'])

    def test_good_setup(self):
        s = statuses()
        for item_id in ('exit_ip', 'timezone_match', 'tls_fingerprint', 'dns_proxy', 'ipv6_off',
                        'claude_rules', 'rule_priority', 'keep_alive', 'network_path'):
            self.assertEqual(s[item_id], 'ok', item_id)
        for item_id in ('ip_stability', 'tcp_only', 'concurrency', 'device_env'):
            self.assertEqual(s[item_id], 'manual', item_id)

    def test_problems_are_flagged(self):
        datacenter = {'ok': True, 'score': 40,
                      'facts': {'kind': '机房', 'flags': ['VPN'], 'country_code': 'DE', 'location': 'Germany', 'timezone': 'Europe/Berlin'}}
        routing = dict(GOOD, global_fingerprint=None, claude_rule=4, broad_rule=2, disable_keep_alive=True)
        checks = [{'id': 'dns_hijack', 'state': 'degraded'}, {'id': 'os_ipv6', 'state': 'degraded'}]
        s = statuses(checks, datacenter, routing, local_offset=540)
        for item_id in ('exit_ip', 'ip_stability', 'timezone_match', 'tls_fingerprint', 'dns_proxy', 'ipv6_off',
                        'rule_priority', 'keep_alive', 'network_path'):
            self.assertEqual(s[item_id], 'warn', item_id)

    def test_direct_reject_missing_domains_and_missing_rules(self):
        self.assertEqual(statuses(routing=dict(GOOD, claude_direct=True))['claude_rules'], 'warn')
        self.assertEqual(statuses(routing=dict(GOOD, claude_reject=True))['claude_rules'], 'warn')
        partial = guide.evaluate(CHECKS_OK, RESIDENTIAL, dict(GOOD, missing_domains=['claude.com']), local_offset=540)
        partial_rule = next(item for item in partial if item['id'] == 'claude_rules')
        self.assertEqual(partial_rule['status'], 'warn')
        self.assertIn('claude.com', partial_rule['note'])
        missing = statuses(routing=dict(GOOD, claude_rule=None))
        self.assertEqual((missing['claude_rules'], missing['rule_priority']), ('warn', 'warn'))

    def test_timezone_match_and_fallback(self):
        self.assertEqual(statuses(local_offset=480)['timezone_match'], 'warn')
        self.assertEqual(statuses(exit_result={'ok': True, 'score': 90, 'facts': {'kind': '住宅', 'flags': [], 'timezone': '未知'}})['timezone_match'], 'unknown')
        self.assertEqual(statuses(local_offset=None)['timezone_match'], 'unknown')

        winter = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
        summer = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        cases = [('Asia/Tokyo', winter, 540), ('Asia/Kolkata', winter, 330),
                 ('America/Los_Angeles', winter, -480), ('America/Los_Angeles', summer, -420),
                 ('Europe/London', winter, 0), ('Europe/London', summer, 60),
                 ('Australia/Sydney', winter, 660), ('Australia/Sydney', summer, 600)]
        for zone, dt, expected in cases:
            self.assertEqual(guide.tz_offset_minutes(zone, dt), expected, (zone, dt))
        with patch.object(guide, 'ZoneInfo', side_effect=guide.ZoneInfoNotFoundError('missing')):
            for zone, dt, expected in cases:
                self.assertEqual(guide.tz_offset_minutes(zone, dt), expected, ('fallback', zone, dt))
            self.assertIsNone(guide.tz_offset_minutes('Invalid/Zone', winter))

    def test_global_and_direct_modes(self):
        self.assertEqual(statuses(routing=dict(GOOD, mode='global', claude_rule=None))['claude_rules'], 'ok')
        self.assertEqual(statuses(routing=dict(GOOD, mode='direct'))['rule_priority'], 'warn')

    def test_unknown_without_data(self):
        s = statuses([], None, {'readable': False})
        for item_id in ('exit_ip', 'timezone_match', 'tls_fingerprint', 'dns_proxy', 'ipv6_off', 'claude_rules', 'network_path'):
            self.assertEqual(s[item_id], 'unknown', item_id)

    def test_node_fingerprints_count(self):
        self.assertEqual(statuses(routing=dict(GOOD, global_fingerprint=None, node_fingerprints=3))['tls_fingerprint'], 'ok')

    def test_source_is_credited(self):
        self.assertEqual(guide.SOURCE_URL, 'https://ip.net.coffee/claude/claudecode.html')


if __name__ == '__main__':
    unittest.main()
