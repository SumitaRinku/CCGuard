"""Claude desktop app on this machine: running state, close, and login autostart.

The Windows app is an MSIX package (Claude_<publisher id>) whose processes keep running in the
background after its window is closed, so traffic can keep flowing while the user thinks Claude is
gone. The package also installs a Windows service (CoworkVMService, shown as "Claude") that runs as
LocalSystem and starts at boot. Everything here is local: process list, window list, service status
and per-user registry. Nothing contacts Claude. Closing Claude and turning off its autostart only
happen on the user's click.
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
# Services the Claude package installs. Only these names are touched, and only when the service
# binary sits inside the Claude package (checked against DESKTOP_MARKERS).
SERVICE_NAMES = ('CoworkVMService',)
SERVICE_STATES = {1: 'stopped', 2: 'starting', 3: 'stopping', 4: 'running', 5: 'continuing', 6: 'pausing', 7: 'paused'}
START_TYPES = {0: 'boot', 1: 'system', 2: 'auto', 3: 'demand', 4: 'disabled'}
PACKAGE_FAMILY = re.compile(r'^(claude|anthropic)_', re.I)
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


def _package_family(pid):
    """Package family name of a process ('' for unpackaged or inaccessible processes)."""
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ''
    try:
        size = wintypes.UINT(256)
        buffer = ctypes.create_unicode_buffer(size.value)
        return buffer.value if kernel32.GetPackageFamilyName(handle, ctypes.byref(size), buffer) == 0 else ''
    finally:
        kernel32.CloseHandle(handle)


def packaged_pids(processes, family=_package_family):
    """Processes running with the Claude package identity, e.g. its RuntimeBroker."""
    return sorted(pid for pid, _ppid, _path in processes if pid > 4 and PACKAGE_FAMILY.match(family(pid) or ''))


def _windows_services(names=SERVICE_NAMES):
    """[{'name','state','start','path'}] for the named services that exist."""
    from ctypes import wintypes
    advapi = ctypes.windll.advapi32
    advapi.OpenSCManagerW.restype = wintypes.HANDLE
    advapi.OpenSCManagerW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    advapi.OpenServiceW.restype = wintypes.HANDLE
    advapi.OpenServiceW.argtypes = (wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD)
    advapi.QueryServiceStatus.argtypes = (wintypes.HANDLE, ctypes.c_void_p)
    advapi.QueryServiceConfigW.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                           ctypes.POINTER(wintypes.DWORD))
    advapi.CloseServiceHandle.argtypes = (wintypes.HANDLE,)

    class SERVICE_STATUS(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in ('type', 'state', 'controls', 'exit', 'service_exit',
                                                         'checkpoint', 'wait')]

    class QUERY_SERVICE_CONFIGW(ctypes.Structure):
        _fields_ = [('type', wintypes.DWORD), ('start', wintypes.DWORD), ('error', wintypes.DWORD),
                    ('path', wintypes.LPWSTR), ('group', wintypes.LPWSTR), ('tag', wintypes.DWORD),
                    ('dependencies', wintypes.LPWSTR), ('account', wintypes.LPWSTR), ('display', wintypes.LPWSTR)]

    manager = advapi.OpenSCManagerW(None, None, 0x0001)  # SC_MANAGER_CONNECT
    if not manager:
        raise ClaudeAppError('无法读取服务列表')
    found = []
    try:
        for name in names:
            service = advapi.OpenServiceW(manager, name, 0x0005)  # QUERY_CONFIG | QUERY_STATUS
            if not service:
                continue
            try:
                current = SERVICE_STATUS()
                state = (SERVICE_STATES.get(current.state, 'unknown')
                         if advapi.QueryServiceStatus(service, ctypes.byref(current)) else 'unknown')
                needed = wintypes.DWORD(0)
                advapi.QueryServiceConfigW(service, None, 0, ctypes.byref(needed))
                buffer = ctypes.create_string_buffer(max(needed.value, ctypes.sizeof(QUERY_SERVICE_CONFIGW)))
                start, path = None, ''
                if advapi.QueryServiceConfigW(service, buffer, len(buffer), ctypes.byref(needed)):
                    config = ctypes.cast(buffer, ctypes.POINTER(QUERY_SERVICE_CONFIGW)).contents
                    start, path = START_TYPES.get(config.start), config.path or ''
                found.append({'name': name, 'state': state, 'start': start, 'path': path})
            finally:
                advapi.CloseServiceHandle(service)
    finally:
        advapi.CloseServiceHandle(manager)
    return found


def claude_services(services=None):
    """Claude's own services: listed names whose binary is inside the Claude package; never raises."""
    if services is None:
        if platform.system() != 'Windows':
            return []
        try:
            services = _windows_services()
        except (ClaudeAppError, OSError, AttributeError):
            return []
    return [service for service in services if service.get('name') in SERVICE_NAMES
            and any(marker in str(service.get('path', '')).lower() for marker in DESKTOP_MARKERS)]


def _active(service):
    return service.get('state') in ('running', 'starting', 'continuing', 'pausing', 'paused')


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


def status(processes=None, window_pids=None, services=None):
    """{'running', 'window', 'background', 'processes', 'code_sessions', 'services', 'kind'}; never raises.

    Real services are queried only together with the real process list (fakes stay fakes).
    """
    if processes is None and platform.system() != 'Windows':
        return {'running': False, 'window': False, 'background': False, 'processes': 0, 'code_sessions': 0,
                'services': 0, 'kind': None, 'supported': False}
    if services is None and processes is not None:
        services = []
    active = [service for service in claude_services(services) if _active(service)]
    try:
        processes = _windows_processes() if processes is None else processes
        found = classify(processes)
        windows = _windows_visible_window_pids() if window_pids is None and found['desktop'] else (window_pids or set())
    except (ClaudeAppError, OSError, AttributeError) as error:
        return {'running': bool(active), 'window': False, 'background': bool(active), 'processes': 0,
                'code_sessions': 0, 'services': len(active), 'kind': None, 'supported': True, 'error': str(error)}
    running = bool(found['desktop']) or bool(active)
    window = any(pid in windows for pid in found['desktop'])
    return {'running': running, 'window': window, 'background': running and not window,
            'processes': len(found['desktop']), 'code_sessions': len(found['code']), 'services': len(active),
            'kind': found['kind'] or ('msix' if active else None), 'supported': True, '_roots': found['roots']}


def _run(run, argv, timeout=30):
    return run(argv, capture_output=True, text=True, timeout=timeout,
               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def close(processes=None, run=subprocess.run, packaged=None, services=None):
    """End the Claude app, its helpers and its services.

    1. taskkill /T on each root process: the windows, background processes and hosted Claude Code.
    2. Leftover processes with the Claude package identity (its RuntimeBroker and the like).
    3. Stop Claude's services (CoworkVMService). Its access list lets any signed-in user stop it,
       so no administrator rights are needed.
    Real helpers and services are looked up only together with the real process list.
    """
    real = processes is None
    processes = _windows_processes() if real else processes
    found = classify(processes)
    if packaged is None:
        packaged = packaged_pids(processes) if real else []
    if services is None and not real:
        services = []
    helpers = [pid for pid in packaged if pid not in found['desktop'] and pid not in found['code']]
    active = [service['name'] for service in claude_services(services) if _active(service)]
    failed, failed_services = [], []
    for pid in found['roots'] + helpers:
        if _run(run, ['taskkill', '/PID', str(pid), '/T', '/F']).returncode not in (0, 128):  # 128: already gone
            failed.append(pid)
    for name in active:
        if _run(run, ['sc.exe', 'stop', name]).returncode not in (0, 1062):  # 1062: not started
            failed_services.append(name)
    if failed:
        raise ClaudeAppError('有 %d 个 Claude 进程没能结束，可能需要在任务管理器里结束' % len(failed))
    if failed_services:
        raise ClaudeAppError('Claude 的后台服务 %s 没能停止，可在“服务”里手动停止' % '、'.join(failed_services))
    return {'closed': len(found['roots']), 'helpers': len(helpers), 'services': len(active)}


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


def autostart(registry=None, startup_folder=None, services=None):
    """[{'id','kind','name','enabled'}] Claude entries that start at login or boot; [] when there are none.

    Real services are queried only together with the real registry (fakes stay fakes).
    """
    if registry is None and platform.system() != 'Windows':
        return []
    if services is None and registry is not None:
        services = []
    registry = registry or Registry()
    entries = []
    for service in claude_services(services):
        auto = service.get('start') == 'auto'
        entries.append({'id': 'service:' + service['name'], 'kind': 'service',
                        'name': '%s（系统服务%s）' % (service['name'], '，开机启动' if auto else ''),
                        'enabled': auto, 'locked': False, 'admin': True})
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


def manual_start_command(name):
    """Elevated `sc config <name> start= demand`: Windows shows its own administrator prompt."""
    return ['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command',
            "$p = Start-Process -FilePath sc.exe -ArgumentList 'config','%s','start=','demand' "
            "-Verb RunAs -WindowStyle Hidden -PassThru -Wait; exit $p.ExitCode" % name]


def disable_autostart(entry_id, registry=None, run=subprocess.run, services=None):
    """Turn one entry off the way Windows Settings does; reversible from Settings > Apps > Startup.

    A Claude service is switched from automatic to manual start (one administrator prompt); Claude
    can still start it when it needs it, and the Services console can switch it back.
    """
    kind, _, rest = entry_id.partition(':')
    if kind == 'service':
        if services is None and registry is not None:
            services = []
        if rest not in SERVICE_NAMES or not any(s['name'] == rest for s in claude_services(services)):
            raise ClaudeAppError('不是 Claude 的服务')
        if _run(run, manual_start_command(rest), timeout=180).returncode != 0:
            raise ClaudeAppError('没有改成手动启动：需要在 Windows 弹出的管理员提示里选“是”')
        return {'ok': True, 'id': entry_id}
    registry = registry or Registry()
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
