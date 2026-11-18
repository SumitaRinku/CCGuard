"""Update check and in-app install for CCGuard; contacts only GitHub, never Claude or Anthropic.

Check: one request to https://api.github.com/repos/SumitaRinku/CCGuard/releases, on the user's click
or, when the user turned it on, at most once a day. Without a login GitHub allows 60 API requests an
hour per IP, and a proxy exit IP is shared by many people, so when the API refuses (rate limit or any
other error) the check falls back to plain github.com pages that are not API-limited: the
/releases/latest redirect names the newest tag, and that tag's bundled release-notes.json (read from
raw.githubusercontent.com) gives the notes. Install (installed app only, on the user's
click): download the release's installer and its SHA256SUMS file from this repository's release,
verify the hash, then run the installer silently after CCGuard has exited; it relaunches CCGuard.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.request

from version import __version__

REPO = 'SumitaRinku/CCGuard'
RELEASES_API = 'https://api.github.com/repos/%s/releases?per_page=20' % REPO
RELEASES_PAGE = 'https://github.com/%s/releases' % REPO
LATEST_PAGE = RELEASES_PAGE + '/latest'
NOTES_RAW = 'https://raw.githubusercontent.com/%s/v%%s/assets/monitor/release-notes.json' % REPO
TIMEOUT = 10
DOWNLOAD_TIMEOUT = 120
MAX_INSTALLER = 200 * 1024 * 1024
AUTO_INTERVAL = 24 * 3600
NOTES_LIMIT = 4000


class UpdateError(Exception):
    pass


def parse_version(text):
    """'v0.6.0' / '0.6.0' -> (0, 6, 0); None when it is not a plain X.Y.Z."""
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', str(text or '').strip())
    return tuple(int(part) for part in match.groups()) if match else None


def allowed_url(url):
    """Only this repository's release pages and assets may be opened from the panel."""
    return isinstance(url, str) and (url == RELEASES_PAGE or url.startswith(RELEASES_PAGE + '/'))


def plain_notes(markdown):
    """Release body as short plain lines for the panel (shown as text, never as HTML)."""
    lines, size = [], 0
    for raw in str(markdown or '').splitlines():
        line = raw.strip()
        if not line or line.startswith('|') or set(line) <= set('-|: '):
            continue
        line = re.sub(r'^#+\s*', '', line)
        line = re.sub(r'^[-*]\s+', '', line)
        line = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
        line = re.sub(r'`([^`]*)`', r'\1', line)
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        size += len(line)
        if size > NOTES_LIMIT:
            lines.append('…')
            break
        lines.append(line)
    return lines


def http_get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'CCGuard/' + __version__,
                                                  'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, response.read(4 * 1024 * 1024)


def http_final_url(url):
    """Where a github.com URL redirects to (HEAD request, redirects followed)."""
    request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'CCGuard/' + __version__})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.geturl()


def _api_reason(error):
    """Readable reason for an API failure; GitHub's unauthenticated limit gets a plain explanation."""
    code = getattr(error, 'code', None)
    if code in (403, 429):
        return 'GitHub 接口限流（未登录时同一 IP 每小时 60 次，代理出口 IP 常被多人共用）'
    return str(getattr(error, 'reason', None) or error)


def _from_api(get, mine, note):
    note('请求 ' + RELEASES_API + '，读取已发布的版本')
    status, body = get(RELEASES_API)
    if status != 200:
        raise UpdateError('GitHub 返回 HTTP %s' % status)
    try:
        items = json.loads(body.decode('utf-8'))
    except ValueError:
        raise UpdateError('GitHub 返回的不是 JSON') from None
    if not isinstance(items, list):
        raise UpdateError('GitHub 返回格式不对')
    newer = []
    for item in items:
        if not isinstance(item, dict) or item.get('draft') or item.get('prerelease'):
            continue
        number = parse_version(item.get('tag_name'))
        if number is None or number <= mine:
            continue
        assets = [asset for asset in item.get('assets') or [] if isinstance(asset, dict)]
        installer = next((asset.get('browser_download_url') for asset in assets
                          if str(asset.get('name', '')).startswith('CCGuard-Setup-')
                          and str(asset.get('name', '')).endswith('.exe')), None)
        sums = next((asset.get('browser_download_url') for asset in assets
                     if str(asset.get('name', '')).startswith('SHA256SUMS-installer-')), None)
        page = item.get('html_url')
        newer.append({'number': number, 'version': '.'.join(map(str, number)),
                      'name': str(item.get('name') or item.get('tag_name')),
                      'date': str(item.get('published_at') or '')[:10],
                      'page_url': page if allowed_url(page) else RELEASES_PAGE,
                      'installer_url': installer if allowed_url(installer) else None,
                      'sums_url': sums if allowed_url(sums) else None,
                      'notes': plain_notes(item.get('body'))})
    return newer


def _release_entry(number, date='', notes=()):
    version = '.'.join(map(str, number))
    base = '%s/download/v%s/' % (RELEASES_PAGE, version)
    return {'number': number, 'version': version, 'name': 'CCGuard v' + version, 'date': date,
            'page_url': '%s/tag/v%s' % (RELEASES_PAGE, version),
            'installer_url': base + 'CCGuard-Setup-%s.exe' % version,
            'sums_url': base + 'SHA256SUMS-installer-%s.txt' % version,
            'notes': [str(item) for item in notes][:20]}


def _from_pages(get, resolve, mine, note):
    """Fallback without the API: newest tag from the /releases/latest redirect, notes from that tag."""
    note('改为读取 ' + LATEST_PAGE + ' 的跳转，确定最新版本')
    final = resolve(LATEST_PAGE)
    match = re.fullmatch(re.escape(RELEASES_PAGE) + r'/tag/(v\d+\.\d+\.\d+)', str(final or ''))
    latest = parse_version(match.group(1)) if match else None
    if latest is None:
        raise UpdateError('发布页没有给出最新版本')
    if latest <= mine:
        return []
    entries = {latest: _release_entry(latest)}
    url = NOTES_RAW % '.'.join(map(str, latest))
    note('读取该版本附带的更新日志 ' + url)
    try:
        status, body = get(url)
        data = json.loads(body.decode('utf-8')) if status == 200 else []
    except (urllib.error.URLError, OSError, ValueError):
        data = []
        note('更新日志没有读到，只显示版本号')
    for entry in data if isinstance(data, list) else []:
        number = parse_version(entry.get('version')) if isinstance(entry, dict) else None
        if number and mine < number <= latest and isinstance(entry.get('items'), list):
            entries[number] = _release_entry(number, str(entry.get('date') or '')[:10], entry['items'])
    return list(entries.values())


def check(get=http_get, current=__version__, clock=time.time, resolve=http_final_url):
    """Newer published releases than `current`, newest first; never raises."""
    log = []

    def note(text, ok=None):
        log.append({'time': time.strftime('%H:%M:%S', time.localtime(clock())), 'text': text, 'ok': ok})

    result = {'ok': False, 'current': current, 'update': False, 'releases': [], 'page_url': RELEASES_PAGE,
              'checked_at': int(clock()), 'log': log}
    try:
        mine = parse_version(current)
        if mine is None:
            raise UpdateError('当前版本号无法识别：%s' % current)
        try:
            newer = _from_api(get, mine, note)
        except (UpdateError, urllib.error.URLError, OSError, ValueError) as error:
            note('GitHub 接口没有返回：%s' % _api_reason(error), False)
            newer = _from_pages(get, resolve, mine, note)
        newer.sort(key=lambda entry: entry['number'], reverse=True)
        for entry in newer:
            entry.pop('number')
        result.update(ok=True, update=bool(newer), releases=newer,
                      latest=newer[0]['version'] if newer else current)
        note('发现新版本 %s' % newer[0]['version'] if newer else '已是最新版本 %s' % current, True if not newer else None)
    except (UpdateError, urllib.error.URLError, OSError, ValueError) as error:
        result['error'] = _api_reason(error)
        note('检查失败：%s' % result['error'], False)
    return result


def release_notes(path=None):
    """The bundled update log: [{version, date, items}], newest first; [] if unreadable."""
    if path is None:
        import monitor  # resolves the asset folder for both the script and the frozen exe
        path = monitor.ICON_DIR / 'release-notes.json'
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    notes = [entry for entry in data if isinstance(entry, dict) and parse_version(entry.get('version'))
             and isinstance(entry.get('items'), list)]
    return sorted(notes, key=lambda entry: parse_version(entry['version']), reverse=True)


# ---------------------------------------------------------------------------------------------
# In-app install (installed app only)

def http_download(url, limit=MAX_INSTALLER):
    request = urllib.request.Request(url, headers={'User-Agent': 'CCGuard/' + __version__})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
        if response.status != 200:
            raise UpdateError('下载返回 HTTP %s' % response.status)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError('下载的文件过大')
    return data


def expected_hash(sums_text, name):
    """SHA-256 for `name` from a SHA256SUMS file ("<hash>  <name>" per line)."""
    for line in sums_text.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip('*') == name and re.fullmatch(r'[0-9a-fA-F]{64}', parts[0]):
            return parts[0].lower()
    raise UpdateError('校验文件里没有 %s' % name)


def download_installer(release, folder, download=http_download):
    """Download the release's installer into folder after verifying its SHA-256; returns the path."""
    url, sums_url = release.get('installer_url'), release.get('sums_url')
    if not (allowed_url(url) and allowed_url(sums_url)):
        raise UpdateError('这个版本没有可校验的安装程序，请在发布页手动下载')
    name = url.rsplit('/', 1)[-1]
    if not re.fullmatch(r'CCGuard-Setup-\d+\.\d+\.\d+\.exe', name):
        raise UpdateError('安装程序文件名不对：%s' % name)
    digest = expected_hash(download(sums_url, 64 * 1024).decode('utf-8', 'replace'), name)
    data = download(url)
    if hashlib.sha256(data).hexdigest() != digest:
        raise UpdateError('安装程序校验失败，已丢弃')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    tmp = target.with_suffix('.part')
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return target


def install_command(installer, wait_pid):
    """Hidden PowerShell that waits for CCGuard (pid) to exit, then runs the installer silently.

    The installer refuses to start while CCGuard holds its mutex, so it must not run before we exit;
    /RELAUNCH makes the installer start CCGuard again when it finishes.
    """
    path = str(installer).replace("'", "''")
    script = ("Wait-Process -Id %d -Timeout 60 -ErrorAction SilentlyContinue; "
              "Start-Process -FilePath '%s' -ArgumentList '/SILENT','/SUPPRESSMSGBOXES','/NORESTART','/RELAUNCH'"
              % (int(wait_pid), path))
    return ['powershell.exe', '-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-Command', script]


def start_install(installer, wait_pid=None, popen=subprocess.Popen):
    # CREATE_NO_WINDOW only. With DETACHED_PROCESS, Windows PowerShell gets no console at all and
    # quits at once without running the script, so the installer never started (v0.7.0/0.7.1 bug).
    # A no-window child still outlives CCGuard: Windows does not end children when the parent exits.
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    return popen(install_command(installer, os.getpid() if wait_pid is None else wait_pid), creationflags=flags,
                 close_fds=True)


# ---------------------------------------------------------------------------------------------
# Preferences (prefs.json next to the config; the config schema itself stays unchanged)

def prefs_path(config_path):
    return Path(config_path).resolve().parent / 'prefs.json'


def load_prefs(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {'auto_update_check': data.get('auto_update_check') is True,
            'last_update_check': int(data.get('last_update_check') or 0)
            if isinstance(data.get('last_update_check'), (int, float)) else 0}


def save_prefs(path, prefs):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'auto_update_check': bool(prefs.get('auto_update_check')),
                               'last_update_check': int(prefs.get('last_update_check') or 0)}), encoding='utf-8')
    os.replace(tmp, path)


def auto_check_due(prefs, now):
    return bool(prefs.get('auto_update_check')) and now - int(prefs.get('last_update_check') or 0) >= AUTO_INTERVAL
