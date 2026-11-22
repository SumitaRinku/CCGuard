"""Version number, bundled update log and the manual update check; offline with fake HTTP."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

update = importlib.import_module('app_update')
version = importlib.import_module('version')
monitor = importlib.import_module('monitor')

PAGE = 'https://github.com/SumitaRinku/CCGuard/releases'


def release(tag, **extra):
    item = {'tag_name': tag, 'name': 'CCGuard ' + tag, 'published_at': '2026-12-01T00:00:00Z',
            'html_url': PAGE + '/tag/' + tag, 'body': '## 本次更新\n\n- **新功能** `x`\n- 修复 [问题](http://example)\n',
            'assets': [{'name': 'CCGuard-Setup-%s.exe' % tag.lstrip('v'),
                        'browser_download_url': PAGE + '/download/%s/CCGuard-Setup-%s.exe' % (tag, tag.lstrip('v'))},
                       {'name': 'ccguard.zip', 'browser_download_url': PAGE + '/download/x.zip'}]}
    item.update(extra)
    return item


def fake(items, status=200):
    calls = []

    def get(url):
        calls.append(url)
        if isinstance(items, Exception):
            raise items
        return status, json.dumps(items).encode() if not isinstance(items, bytes) else items
    get.calls = calls
    return get


class Version(unittest.TestCase):
    def test_single_source(self):
        self.assertIsNotNone(update.parse_version(version.__version__))
        self.assertEqual(update.__version__, version.__version__)

    def test_cli_prints_it(self):
        with self.assertRaises(SystemExit) as raised, patch('sys.stdout') as out:
            monitor.main(['--version'])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(version.__version__, ''.join(call.args[0] for call in out.write.call_args_list))

    def test_bundled_update_log_starts_with_this_version(self):
        notes = update.release_notes()
        self.assertEqual(notes[0]['version'], version.__version__)
        self.assertTrue(all(entry['items'] and all(isinstance(i, str) and i for i in entry['items']) for entry in notes))
        numbers = [update.parse_version(entry['version']) for entry in notes]
        self.assertEqual(numbers, sorted(numbers, reverse=True))
        self.assertEqual(len(numbers), len(set(numbers)))

    def test_update_log_is_shipped(self):
        # The exe bundles the whole assets/monitor folder and names the lazily imported modules.
        spec = (ROOT / 'packaging/ccguard.spec').read_text(encoding='utf-8')
        self.assertIn("(str(ASSETS), 'ccguard/assets/monitor')", spec)
        self.assertTrue((ROOT / 'assets/monitor/release-notes.json').is_file())
        for name in ("'app_update'", "'version'"):
            self.assertIn(name, spec)

    def test_unreadable_log_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / 'notes.json'
            broken.write_text('not json', encoding='utf-8')
            self.assertEqual(update.release_notes(broken), [])
            self.assertEqual(update.release_notes(Path(folder) / 'missing.json'), [])


class Check(unittest.TestCase):
    def test_newer_releases_newest_first_with_notes_and_installer(self):
        items = [release('v0.6.0'), release('v0.7.0'), release('v0.8.0', draft=True),
                 release('v0.9.0', prerelease=True), release('v0.6.1'), release('nightly'), 'junk']
        get = fake(items)
        result = update.check(get=get, current='0.6.0', clock=lambda: 0)
        self.assertEqual(get.calls, [update.RELEASES_API])
        self.assertTrue(result['ok'] and result['update'])
        self.assertEqual([r['version'] for r in result['releases']], ['0.7.0', '0.6.1'])
        self.assertEqual(result['latest'], '0.7.0')
        top = result['releases'][0]
        self.assertEqual(top['installer_url'], PAGE + '/download/v0.7.0/CCGuard-Setup-0.7.0.exe')
        self.assertEqual(top['notes'], ['本次更新', '新功能 x', '修复 问题'])
        json.dumps(result, ensure_ascii=False)

    def test_up_to_date(self):
        result = update.check(get=fake([release('v0.5.1'), release('v0.6.0')]), current='0.6.0')
        self.assertTrue(result['ok'])
        self.assertFalse(result['update'])
        self.assertEqual(result['releases'], [])
        self.assertEqual(result['log'][-1]['text'], '已是最新版本 0.6.0')

    def test_links_outside_this_repository_are_dropped(self):
        evil = release('v0.7.0', html_url='https://evil.example/x')
        evil['assets'][0]['browser_download_url'] = 'https://evil.example/CCGuard-Setup-0.7.0.exe'
        top = update.check(get=fake([evil]), current='0.6.0')['releases'][0]
        self.assertEqual(top['page_url'], PAGE)
        self.assertIsNone(top['installer_url'])

    def test_failures_are_reported_not_raised(self):
        def offline(url):
            raise urllib.error.URLError('offline')
        for get in (fake(urllib.error.URLError('offline')), fake(TimeoutError('slow')), fake([], status=403),
                    fake(b'<html>'), fake({'message': 'rate limited'})):
            result = update.check(get=get, current='0.6.0', resolve=offline)
            self.assertFalse(result['ok'])
            self.assertTrue(result['error'])
            self.assertTrue(result['log'][-1]['text'].startswith('检查失败'))
        self.assertFalse(update.check(get=fake([]), current='dev')['ok'])

    def test_rate_limited_api_falls_back_to_release_pages(self):
        notes = json.dumps([{'version': '0.9.0', 'date': '2026-12-01', 'items': ['新功能']},
                            {'version': '0.8.0', 'date': '2026-11-30', 'items': ['修复']},
                            {'version': '0.6.0', 'date': '2026-11-17', 'items': ['旧']}]).encode()
        asked = []

        def get(url):
            asked.append(url)
            if url == update.RELEASES_API:
                raise urllib.error.HTTPError(url, 403, 'rate limit exceeded', {}, None)
            return 200, notes
        result = update.check(get=get, current='0.6.0', clock=lambda: 0,
                              resolve=lambda url: asked.append(url) or PAGE + '/tag/v0.9.0')
        self.assertTrue(result['ok'])
        self.assertEqual(asked, [update.RELEASES_API, update.LATEST_PAGE,
                                 'https://raw.githubusercontent.com/SumitaRinku/CCGuard/v0.9.0/assets/monitor/release-notes.json'])
        self.assertEqual([r['version'] for r in result['releases']], ['0.9.0', '0.8.0'])
        top = result['releases'][0]
        self.assertEqual(top['installer_url'], PAGE + '/download/v0.9.0/CCGuard-Setup-0.9.0.exe')
        self.assertEqual(top['sums_url'], PAGE + '/download/v0.9.0/SHA256SUMS-installer-0.9.0.txt')
        self.assertEqual((top['page_url'], top['notes'], top['date']), (PAGE + '/tag/v0.9.0', ['新功能'], '2026-12-01'))
        self.assertTrue(all(update.allowed_url(top[key]) for key in ('installer_url', 'sums_url', 'page_url')))
        self.assertIn('每小时 60 次', ' '.join(row['text'] for row in result['log']))

    def test_fallback_without_notes_and_when_up_to_date(self):
        def get(url):
            raise urllib.error.HTTPError(url, 429, 'too many', {}, None)
        result = update.check(get=get, current='0.6.0', resolve=lambda url: PAGE + '/tag/v0.9.0')
        self.assertEqual([(r['version'], r['notes']) for r in result['releases']], [('0.9.0', [])])
        same = update.check(get=get, current='0.9.0', resolve=lambda url: PAGE + '/tag/v0.9.0')
        self.assertEqual((same['ok'], same['update']), (True, False))
        odd = update.check(get=get, current='0.6.0', resolve=lambda url: 'https://evil.example/tag/v9.9.9')
        self.assertFalse(odd['ok'])
        self.assertIn('60 次', odd['error'] + ' '.join(row['text'] for row in odd['log']))

    def test_only_github_is_contacted(self):
        self.assertTrue(update.RELEASES_API.startswith('https://api.github.com/repos/SumitaRinku/CCGuard/'))
        source = (SCRIPTS / 'app_update.py').read_text(encoding='utf-8')
        self.assertNotIn('claude.ai', source)
        self.assertNotIn('anthropic.com', source)

    def test_notes_are_plain_and_bounded(self):
        lines = update.plain_notes('| a | b |\n|---|---|\n# H\n' + '- x' * 1 + '\n' + ('长' * 300 + '\n') * 30)
        self.assertEqual(lines[:2], ['H', 'x'])
        self.assertEqual(lines[-1], '…')
        self.assertLessEqual(sum(len(line) for line in lines), update.NOTES_LIMIT + 1)
        self.assertNotIn('·', ''.join(update.plain_notes('- a\n- b')))

    def test_allowed_url(self):
        self.assertTrue(update.allowed_url(PAGE))
        self.assertTrue(update.allowed_url(PAGE + '/tag/v1.0.0'))
        for bad in ('https://github.com/SumitaRinku/CCGuard', 'https://github.com/SumitaRinku/CCGuard/releasesX',
                    'https://evil.example/' + PAGE, None, 5):
            self.assertFalse(update.allowed_url(bad), bad)
        self.assertTrue(update.allowed_repo_url(update.REPO_URL))
        self.assertTrue(update.allowed_repo_url(update.ISSUES_URL))
        self.assertTrue(update.allowed_repo_url(PAGE))
        for bad in ('https://github.com/SumitaRinku/CCGuard/settings', 'https://evil.example/x', None):
            self.assertFalse(update.allowed_repo_url(bad), bad)


class Install(unittest.TestCase):
    NAME = 'CCGuard-Setup-0.9.0.exe'
    DATA = b'installer bytes'

    def release(self, **extra):
        base = PAGE + '/download/v0.9.0/'
        entry = {'version': '0.9.0', 'installer_url': base + self.NAME, 'sums_url': base + 'SHA256SUMS-installer-0.9.0.txt'}
        entry.update(extra)
        return entry

    def fake(self, data=None, sums=None):
        import hashlib
        digest = hashlib.sha256(self.DATA).hexdigest()
        sums = sums if sums is not None else ('%s  %s\n' % (digest, self.NAME)).encode()
        calls = []

        def download(url, limit=None):
            calls.append(url)
            return sums if url.endswith('.txt') else (data if data is not None else self.DATA)
        download.calls = calls
        return download

    def test_check_lists_the_checksum_file(self):
        item = release('v0.9.0')
        item['assets'].append({'name': 'SHA256SUMS-installer-0.9.0.txt', 'browser_download_url': PAGE + '/download/v0.9.0/SHA256SUMS-installer-0.9.0.txt'})
        top = update.check(get=fake([item]), current='0.6.0')['releases'][0]
        self.assertEqual(top['sums_url'], PAGE + '/download/v0.9.0/SHA256SUMS-installer-0.9.0.txt')

    def test_verified_download(self):
        with tempfile.TemporaryDirectory() as folder:
            download = self.fake()
            path = update.download_installer(self.release(), folder, download=download)
            self.assertEqual(path.read_bytes(), self.DATA)
            self.assertEqual(path.name, self.NAME)
            self.assertEqual(len(download.calls), 2)

    def test_hash_mismatch_is_refused_and_nothing_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(update.UpdateError):
                update.download_installer(self.release(), folder, download=self.fake(data=b'tampered'))
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_only_this_repositorys_installer(self):
        for bad in (self.release(installer_url='https://evil.example/CCGuard-Setup-0.9.0.exe'),
                    self.release(sums_url=None),
                    self.release(installer_url=PAGE + '/download/v0.9.0/other.exe')):
            with tempfile.TemporaryDirectory() as folder, self.assertRaises(update.UpdateError):
                update.download_installer(bad, folder, download=self.fake())

    def test_sums_must_name_the_file(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(update.UpdateError):
            update.download_installer(self.release(), folder, download=self.fake(sums=b'abc  other.exe\n'))

    def test_installer_waits_for_ccguard_then_runs_silently_and_relaunches(self):
        command = update.install_command(r"C:\Users\o'brien\CCGuard-Setup-0.9.0.exe", 4242)
        self.assertEqual(command[0], 'powershell.exe')
        script = command[-1]
        self.assertTrue(script.startswith('Wait-Process -Id 4242'))
        self.assertIn("'C:\\Users\\o''brien\\CCGuard-Setup-0.9.0.exe'", script)
        for flag in ("'/SILENT'", "'/SUPPRESSMSGBOXES'", "'/NORESTART'", "'/RELAUNCH'"):
            self.assertIn(flag, script)


CHILD = """
import sys, time
sys.path.insert(0, sys.argv[1])
import app_update
app_update.start_install(sys.argv[2])
time.sleep(1.5)
"""


class InstallLaunch(unittest.TestCase):
    def test_waiter_is_hidden_but_not_detached(self):
        seen = {}
        update.start_install('setup.exe', wait_pid=7, popen=lambda argv, **kw: seen.update(kw, argv=argv))
        self.assertEqual(seen['creationflags'] & 0x00000008, 0)      # DETACHED_PROCESS kills PowerShell 5.1
        if sys.platform == 'win32':
            self.assertEqual(seen['creationflags'], 0x08000000)       # CREATE_NO_WINDOW
        self.assertIn('Wait-Process -Id 7', seen['argv'][-1])

    @unittest.skipUnless(sys.platform == 'win32', 'Windows PowerShell')
    def test_installer_starts_after_ccguard_has_exited(self):
        """Regression for v0.7.0: CCGuard exited, the update never installed."""
        import subprocess
        import time
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            fake = folder / "CCGuard-Setup-9.9.9 o'k.cmd"
            fake.write_bytes(b'@echo %* > "%~dp0ran.txt"\r\n')
            child = subprocess.run([sys.executable, '-c', CHILD, str(ROOT / 'scripts'), str(fake)], timeout=60)
            exited = time.time()
            self.assertEqual(child.returncode, 0)
            marker = folder / 'ran.txt'
            deadline = time.time() + 30
            while not marker.exists() and time.time() < deadline:
                time.sleep(0.2)
            self.assertTrue(marker.exists(), 'installer was never started')
            time.sleep(0.3)
            self.assertEqual(marker.read_text().split(), ['/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/RELAUNCH'])
            self.assertGreaterEqual(marker.stat().st_mtime, exited - 1)


class Prefs(unittest.TestCase):
    def test_defaults_save_and_due(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'prefs.json'
            self.assertEqual(update.load_prefs(path), {'auto_update_check': False, 'last_update_check': 0})
            update.save_prefs(path, {'auto_update_check': True, 'last_update_check': 100})
            prefs = update.load_prefs(path)
            self.assertEqual(prefs, {'auto_update_check': True, 'last_update_check': 100})
            self.assertFalse(update.auto_check_due(prefs, 100 + update.AUTO_INTERVAL - 1))
            self.assertTrue(update.auto_check_due(prefs, 100 + update.AUTO_INTERVAL))
            self.assertFalse(update.auto_check_due(dict(prefs, auto_update_check=False), 10 ** 10))
            path.write_text('[1, 2]', encoding='utf-8')
            self.assertFalse(update.load_prefs(path)['auto_update_check'])
            path.write_text('{"auto_update_check": "yes"}', encoding='utf-8')
            self.assertFalse(update.load_prefs(path)['auto_update_check'])

    def test_prefs_live_next_to_the_config(self):
        self.assertEqual(update.prefs_path(Path('x') / 'monitor.json').name, 'prefs.json')


class Cli(unittest.TestCase):
    def test_update_check_exit_code_follows_result(self):
        with patch.object(update, 'check', return_value={'ok': True}), patch('sys.stdout'):
            self.assertEqual(monitor.main(['update-check']), 0)
        with patch.object(update, 'check', return_value={'ok': False}), patch('sys.stdout'):
            self.assertEqual(monitor.main(['update-check']), 1)


if __name__ == '__main__':
    unittest.main()
