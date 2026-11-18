"""Claude Code checklist: routing read from a synthetic config, and each item's status."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

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

    def test_non_clash_or_missing_is_unreadable(self):
        self.assertFalse(self.read('{"route": {"rules": []}}')['readable'])
        self.assertFalse(self.read(CONFIG, 'sing-box')['readable'])
        self.assertFalse(guide.read_routing('', 'auto')['readable'])
        self.assertFalse(guide.read_routing(Path(self.tmp.name) / 'missing.yaml')['readable'])


CHECKS_OK = [{'id': name, 'state': 'ok'} for name in ('dns_hijack', 'dns_servers', 'core_ipv6', 'os_ipv6')]
RESIDENTIAL = {'ok': True, 'score': 100, 'facts': {'kind': '住宅', 'flags': [], 'country_code': 'JP', 'location': 'Japan Tokyo'}}
GOOD = {'readable': True, 'mode': 'rule', 'global_fingerprint': 'chrome', 'node_fingerprints': 0,
        'disable_keep_alive': False, 'rules': 5, 'claude_rule': 0, 'claude_direct': False, 'broad_rule': 2}


def statuses(checks=CHECKS_OK, exit_result=RESIDENTIAL, routing=GOOD):
    return {item['id']: item['status'] for item in guide.evaluate(checks, exit_result, routing)}


class Evaluate(unittest.TestCase):
    def test_eleven_items_with_guidance(self):
        items = guide.evaluate(CHECKS_OK, RESIDENTIAL, GOOD)
        self.assertEqual(len(items), 11)
        for item in items:
            self.assertTrue(item['title'] and item['why'] and item['how'] and item['note'])

    def test_good_setup(self):
        s = statuses()
        for item_id in ('exit_ip', 'tls_fingerprint', 'dns_proxy', 'ipv6_off', 'claude_rules', 'rule_priority',
                        'keep_alive', 'network_path'):
            self.assertEqual(s[item_id], 'ok', item_id)
        for item_id in ('ip_stability', 'tcp_only', 'concurrency'):
            self.assertEqual(s[item_id], 'manual', item_id)

    def test_problems_are_flagged(self):
        datacenter = {'ok': True, 'score': 40, 'facts': {'kind': '机房', 'flags': ['VPN'], 'country_code': 'DE', 'location': 'Germany'}}
        routing = dict(GOOD, global_fingerprint=None, claude_rule=4, broad_rule=2, disable_keep_alive=True)
        checks = [{'id': 'dns_hijack', 'state': 'degraded'}, {'id': 'os_ipv6', 'state': 'degraded'}]
        s = statuses(checks, datacenter, routing)
        for item_id in ('exit_ip', 'ip_stability', 'tls_fingerprint', 'dns_proxy', 'ipv6_off', 'rule_priority',
                        'keep_alive', 'network_path'):
            self.assertEqual(s[item_id], 'warn', item_id)

    def test_direct_and_missing_rules(self):
        self.assertEqual(statuses(routing=dict(GOOD, claude_direct=True))['claude_rules'], 'warn')
        missing = statuses(routing=dict(GOOD, claude_rule=None))
        self.assertEqual((missing['claude_rules'], missing['rule_priority']), ('warn', 'warn'))

    def test_global_and_direct_modes(self):
        self.assertEqual(statuses(routing=dict(GOOD, mode='global', claude_rule=None))['claude_rules'], 'ok')
        self.assertEqual(statuses(routing=dict(GOOD, mode='direct'))['rule_priority'], 'warn')

    def test_unknown_without_data(self):
        s = statuses([], None, {'readable': False})
        for item_id in ('exit_ip', 'tls_fingerprint', 'dns_proxy', 'ipv6_off', 'claude_rules', 'network_path'):
            self.assertEqual(s[item_id], 'unknown', item_id)

    def test_node_fingerprints_count(self):
        self.assertEqual(statuses(routing=dict(GOOD, global_fingerprint=None, node_fingerprints=3))['tls_fingerprint'], 'ok')

    def test_source_is_credited(self):
        self.assertEqual(guide.SOURCE_URL, 'https://ip.net.coffee/claude/claudecode.html')


if __name__ == '__main__':
    unittest.main()
