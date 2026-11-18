"""Claude desktop detection, close and autostart; fakes only, the real Claude is never touched."""
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
claude = importlib.import_module('claude_app')

APP = r'C:\Program Files\WindowsApps\Claude_5.1_x64__pzs8sxrjxfjjc\app\Claude.exe'
CODE = r'C:\Users\u\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\claude-code\2.1\x\claude.exe'
PROCESSES = [(1, 0, 'explorer.exe'), (100, 1, APP), (101, 100, APP), (102, 100, APP), (103, 100, CODE),
             (200, 1, r'C:\Users\u\.local\bin\claude.exe')]


class Detection(unittest.TestCase):
    def test_classify_finds_the_app_its_root_and_hosted_code_sessions(self):
        found = claude.classify(PROCESSES)
        self.assertEqual(found['desktop'], [100, 101, 102])
        self.assertEqual(found['roots'], [100])
        self.assertEqual(found['code'], [103])
        self.assertEqual(found['kind'], 'msix')

    def test_standalone_claude_code_is_not_the_desktop_app(self):
        self.assertEqual(claude.classify([(200, 1, r'C:\Users\u\.local\bin\claude.exe')])['desktop'], [])

    def test_classic_install_is_recognised(self):
        path = r'C:\Users\u\AppData\Local\AnthropicClaude\app-1.0\claude.exe'
        self.assertEqual(claude.classify([(5, 1, path)])['kind'], 'classic')

    def test_background_when_no_window(self):
        state = claude.status(PROCESSES, window_pids=set())
        self.assertEqual((state['running'], state['window'], state['background']), (True, False, True))
        self.assertEqual((state['processes'], state['code_sessions']), (3, 1))

    def test_window_visible(self):
        state = claude.status(PROCESSES, window_pids={100})
        self.assertEqual((state['window'], state['background']), (True, False))

    def test_not_running(self):
        state = claude.status([(1, 0, 'explorer.exe')], window_pids=set())
        self.assertEqual((state['running'], state['background'], state['processes']), (False, False, 0))


class Close(unittest.TestCase):
    def test_ends_each_root_process_tree(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0)
        self.assertEqual(claude.close(PROCESSES, run=run), {'closed': 1})
        self.assertEqual(calls, [['taskkill', '/PID', '100', '/T', '/F']])

    def test_nothing_running_does_nothing(self):
        self.assertEqual(claude.close([(1, 0, 'explorer.exe')], run=lambda *a, **k: self.fail()), {'closed': 0})

    def test_failure_is_reported(self):
        with self.assertRaises(claude.ClaudeAppError):
            claude.close(PROCESSES, run=lambda argv, **k: subprocess.CompletedProcess(argv, 1))


class FakeRegistry:
    def __init__(self, tree):
        self.tree = tree          # {path: {'keys': [...], 'values': {...}}}
        self.writes = []

    def subkeys(self, path):
        return list(self.tree.get(path, {}).get('keys', []))

    def values(self, path):
        return dict(self.tree.get(path, {}).get('values', {}))

    def set_dword(self, path, name, value):
        self.writes.append(('dword', path, name, value))

    def set_binary(self, path, name, value):
        self.writes.append(('binary', path, name, bytes(value)))


def registry(state=2, run=None, approved=None):
    pkg = claude.PACKAGE_KEY
    return FakeRegistry({
        pkg: {'keys': ['Claude_pzs8sxrjxfjjc', 'Microsoft.Other_123']},
        pkg + '\\Claude_pzs8sxrjxfjjc': {'keys': ['ClaudeStartup', 'Schemas']},
        pkg + '\\Claude_pzs8sxrjxfjjc\\ClaudeStartup': {'values': {'State': state}},
        pkg + '\\Claude_pzs8sxrjxfjjc\\Schemas': {'values': {}},
        pkg + '\\Microsoft.Other_123': {'keys': ['Task']},
        pkg + '\\Microsoft.Other_123\\Task': {'values': {'State': 2}},
        claude.RUN_KEY: {'values': run or {}},
        claude.APPROVED_KEY + '\\Run': {'values': approved or {}},
    })


class Autostart(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_msix_startup_task_states(self):
        for state, enabled, locked in ((0, False, False), (1, False, False), (2, True, False), (3, False, True), (4, True, True)):
            entries = claude.autostart(registry(state), startup_folder=self.folder)
            self.assertEqual(len(entries), 1, entries)
            self.assertEqual((entries[0]['enabled'], entries[0]['locked']), (enabled, locked), state)
            self.assertEqual(entries[0]['id'], 'task:Claude_pzs8sxrjxfjjc:ClaudeStartup')

    def test_run_values_and_startup_shortcuts(self):
        reg = registry(0, run={'Claude': r'C:\AnthropicClaude\claude.exe', 'CCGuard': 'x', 'Other': 'y'},
                       approved={'Claude': b'\x03' + bytes(11)})
        (self.folder / 'Claude.lnk').write_bytes(b'')
        (self.folder / 'CCGuard.lnk').write_bytes(b'')
        entries = {entry['id']: entry for entry in claude.autostart(reg, startup_folder=self.folder)}
        self.assertEqual(set(entries), {'task:Claude_pzs8sxrjxfjjc:ClaudeStartup', 'run:Claude', 'folder:Claude.lnk'})
        self.assertFalse(entries['run:Claude']['enabled'])
        self.assertTrue(entries['folder:Claude.lnk']['enabled'])

    def test_disable_task_writes_disabled_by_user(self):
        reg = registry(2)
        claude.disable_autostart('task:Claude_pzs8sxrjxfjjc:ClaudeStartup', reg)
        self.assertEqual(reg.writes, [('dword', claude.PACKAGE_KEY + '\\Claude_pzs8sxrjxfjjc\\ClaudeStartup', 'State', 1)])

    def test_policy_controlled_task_is_refused(self):
        with self.assertRaises(claude.ClaudeAppError):
            claude.disable_autostart('task:Claude_pzs8sxrjxfjjc:ClaudeStartup', registry(4))

    def test_disable_run_and_folder_entries_like_task_manager(self):
        reg = registry(0)
        claude.disable_autostart('run:Claude', reg)
        claude.disable_autostart('folder:Claude.lnk', reg)
        self.assertEqual(reg.writes, [('binary', claude.APPROVED_KEY + '\\Run', 'Claude', b'\x03' + bytes(11)),
                                      ('binary', claude.APPROVED_KEY + '\\StartupFolder', 'Claude.lnk', b'\x03' + bytes(11))])

    def test_only_claude_entries_can_be_touched(self):
        for entry_id in ('task:Microsoft.Other_123:Task', 'run:CCGuard', 'folder:Other.lnk', 'other:Claude', 'task:Claude_x:'):
            with self.assertRaises(claude.ClaudeAppError, msg=entry_id):
                claude.disable_autostart(entry_id, registry(2))

    def test_missing_task_is_reported(self):
        with self.assertRaises(claude.ClaudeAppError):
            claude.disable_autostart('task:Claude_pzs8sxrjxfjjc:Nope', registry(2))

    def test_approved_flag(self):
        self.assertTrue(claude._approved_enabled(None))
        self.assertTrue(claude._approved_enabled(b'\x02' + bytes(11)))
        self.assertFalse(claude._approved_enabled(b'\x03' + bytes(11)))


if __name__ == '__main__':
    unittest.main()
