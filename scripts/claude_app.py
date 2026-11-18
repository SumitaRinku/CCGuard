"""Claude desktop app on this machine: running state, close, and login autostart.

The Windows app is an MSIX package (Claude_<publisher id>) whose processes keep running in the
background after its window is closed, so traffic can keep flowing while the user thinks Claude is
gone. Everything here is local: process list, window list and per-user registry. Nothing contacts
Claude. Closing Claude and turning off its autostart only happen on the user's click.
"""
import ctypes
import os
from pathlib import Path
import platform
import re
import subprocess

# Path markers of the desktop app: the MSIX install and the older per-user (Squirrel) install.
DESKTOP_MARKERS = ('\\windowsapps\\claude_', '\\anthropicclaude\\')
# Claude Code started by the desktop app lives under %LOCALAPPDATA%\Claude-Data\...\claude-code\.
CODE_MARKER = '\\claude-code\\'
PACKAGE_KEY = r'Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\SystemAppData'
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
APPROVED_KEY = r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved'
NAME_PATTERN = re.compile(r'claude|anthropic', re.I)
# Windows.ApplicationModel.StartupTaskState
TASK_STATES = {0: 'disabled', 1: 'disabled_by_user', 2: 'enabled', 3: 'disabled_by_policy', 4: 'enabled_by_policy'}


class ClaudeAppError(Exception):
    pass


# ---------------------------------------------------------------------------------------------
# Processes and windows (ctypes, no PowerShell: cheap enough to poll)

def _windows_processes():
    """[(pid, ppid, exe path or name)] for every process this user can query."""
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', ctypes.c_wchar * 260)]

    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.OpenProcess.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        raise ClaudeAppError('无法读取进程列表')
    rows = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            name = entry.szExeFile
            path = name
            if name.lower().startswith('claude'):
                handle = kernel32.OpenProcess(0x1000, False, entry.th32ProcessID)
                if handle:
                    buffer = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(len(buffer))
                    if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                        path = buffer.value
                    kernel32.CloseHandle(handle)
            rows.append((entry.th32ProcessID, entry.th32ParentProcessID, path))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return rows


def _windows_visible_window_pids():
    """Process ids that own a visible, titled top-level window."""
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    pids = set()
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pids.add(pid.value)
        return True

    user32.EnumWindows(proc(callback), 0)
    return pids


def classify(processes):
    """Desktop-app processes, their root (main) processes and the Claude Code sessions they host."""
    desktop = {pid: (ppid, path) for pid, ppid, path in processes
               if any(marker in str(path).lower() for marker in DESKTOP_MARKERS)}
    roots = sorted(pid for pid, (ppid, _path) in desktop.items() if ppid not in desktop)
    code = sorted(pid for pid, ppid, path in processes
                  if CODE_MARKER in str(path).lower() and ppid in desktop)
    kind = None
    if desktop:
        kind = 'msix' if any('\\windowsapps\\' in str(path).lower() for _ppid, path in desktop.values()) else 'classic'
    return {'desktop': sorted(desktop), 'roots': roots, 'code': code, 'kind': kind}


def status(processes=None, window_pids=None):
    """{'running', 'window', 'background', 'processes', 'code_sessions', 'kind'}; never raises."""
    if processes is None and platform.system() != 'Windows':
        return {'running': False, 'window': False, 'background': False, 'processes': 0, 'code_sessions': 0,
                'kind': None, 'supported': False}
    try:
        processes = _windows_processes() if processes is None else processes
        found = classify(processes)
        windows = _windows_visible_window_pids() if window_pids is None and found['desktop'] else (window_pids or set())
    except (ClaudeAppError, OSError, AttributeError) as error:
        return {'running': False, 'window': False, 'background': False, 'processes': 0, 'code_sessions': 0,
                'kind': None, 'supported': True, 'error': str(error)}
    running = bool(found['desktop'])
    window = any(pid in windows for pid in found['desktop'])
    return {'running': running, 'window': window, 'background': running and not window,
            'processes': len(found['desktop']), 'code_sessions': len(found['code']), 'kind': found['kind'],
            'supported': True, '_roots': found['roots']}


def close(processes=None, run=subprocess.run):
    """End the Claude desktop app and everything it started (taskkill /T on each root process)."""
    processes = _windows_processes() if processes is None else processes
    roots = classify(processes)['roots']
    if not roots:
        return {'closed': 0}
    failed = []
    for pid in roots:
        result = run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True,
                     timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode not in (0, 128):  # 128: already gone
            failed.append(pid)
    if failed:
        raise ClaudeAppError('有 %d 个 Claude 进程没能结束，可能需要在任务管理器里结束' % len(failed))
    return {'closed': len(roots)}


# ---------------------------------------------------------------------------------------------
# Autostart: MSIX StartupTask, HKCU Run values, Startup folder shortcuts

class Registry:
    """The few HKCU operations needed, behind a small interface so tests use a fake."""

    def __init__(self):
        import winreg
        self.winreg = winreg

    def subkeys(self, path):
        try:
            with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, path) as key:
                names, index = [], 0
                while True:
                    try:
                        names.append(self.winreg.EnumKey(key, index))
                    except OSError:
                        return names
                    index += 1
        except OSError:
            return []

    def values(self, path):
        try:
            with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, path) as key:
                out, index = {}, 0
                while True:
                    try:
                        name, data, _kind = self.winreg.EnumValue(key, index)
                    except OSError:
                        return out
                    out[name] = data
                    index += 1
        except OSError:
            return {}

    def set_dword(self, path, name, value):
        with self.winreg.OpenKey(self.winreg.HKEY_CURRENT_USER, path, 0, self.winreg.KEY_SET_VALUE) as key:
            self.winreg.SetValueEx(key, name, 0, self.winreg.REG_DWORD, int(value))

    def set_binary(self, path, name, value):
        with self.winreg.CreateKey(self.winreg.HKEY_CURRENT_USER, path) as key:
            self.winreg.SetValueEx(key, name, 0, self.winreg.REG_BINARY, bytes(value))


def _startup_folder():
    appdata = os.environ.get('APPDATA')
    return Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup' if appdata else None


def _approved_enabled(data):
    """StartupApproved data: missing or even first byte = enabled; odd first byte = disabled."""
    return not (isinstance(data, (bytes, bytearray)) and data and data[0] & 1)


def autostart(registry=None, startup_folder=None):
    """[{'id','kind','name','enabled'}] Claude entries that start at login; [] when there are none."""
    if registry is None and platform.system() != 'Windows':
        return []
    registry = registry or Registry()
    entries = []
    for package in registry.subkeys(PACKAGE_KEY):
        if not re.match(r'^(claude|anthropic)', package, re.I):
            continue
        for task in registry.subkeys(PACKAGE_KEY + '\\' + package):
            values = registry.values(PACKAGE_KEY + '\\' + package + '\\' + task)
            if 'State' not in values:
                continue
            state = int(values['State'])
            entries.append({'id': 'task:%s:%s' % (package, task), 'kind': 'msix', 'name': '%s（应用启动任务）' % task,
                            'enabled': state in (2, 4), 'state': TASK_STATES.get(state, str(state)),
                            'locked': state in (3, 4)})
    approved_run = registry.values(APPROVED_KEY + '\\Run')
    for name, command in registry.values(RUN_KEY).items():
        if NAME_PATTERN.search(name) or NAME_PATTERN.search(str(command)):
            entries.append({'id': 'run:' + name, 'kind': 'run', 'name': name + '（注册表启动项）',
                            'enabled': _approved_enabled(approved_run.get(name)), 'locked': False})
    folder = startup_folder if startup_folder is not None else _startup_folder()
    approved_folder = registry.values(APPROVED_KEY + '\\StartupFolder')
    if folder and folder.is_dir():
        for item in sorted(folder.iterdir()):
            if NAME_PATTERN.search(item.name):
                entries.append({'id': 'folder:' + item.name, 'kind': 'folder', 'name': item.name + '（启动文件夹）',
                                'enabled': _approved_enabled(approved_folder.get(item.name)), 'locked': False})
    return entries


def disable_autostart(entry_id, registry=None):
    """Turn one entry off the way Windows Settings does; reversible from Settings > Apps > Startup."""
    registry = registry or Registry()
    kind, _, rest = entry_id.partition(':')
    if kind == 'task':
        package, _, task = rest.partition(':')
        if not re.match(r'^(claude|anthropic)', package, re.I) or not task:
            raise ClaudeAppError('不是 Claude 的启动任务')
        path = PACKAGE_KEY + '\\' + package + '\\' + task
        state = registry.values(path).get('State')
        if state is None:
            raise ClaudeAppError('找不到这个启动任务')
        if int(state) in (3, 4):
            raise ClaudeAppError('这个启动任务由组织策略控制，不能在本机关闭')
        registry.set_dword(path, 'State', 1)  # DisabledByUser: the app can no longer re-enable itself
    elif kind in ('run', 'folder'):
        if not NAME_PATTERN.search(rest):
            raise ClaudeAppError('不是 Claude 的启动项')
        # 0x03 + zeros: "disabled" as Task Manager and Settings write it; the entry itself stays.
        registry.set_binary(APPROVED_KEY + ('\\Run' if kind == 'run' else '\\StartupFolder'), rest, b'\x03' + bytes(11))
    else:
        raise ClaudeAppError('未知的启动项')
    return {'ok': True, 'id': entry_id}
