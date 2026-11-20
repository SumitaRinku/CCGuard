param(
    [Parameter(Mandatory=$true)][string]$StatePath,
    [string]$Url = '',
    [string]$ShowFile = '',
    [Parameter(Mandatory=$true)][string]$IconDir,
    [int]$IntervalSeconds = 5,
    [int]$CooldownSeconds = 120,
    [int]$OwnerPid = 0,
    [string]$QuitFile = '',
    [string]$NoticeLog = ''
)
$ErrorActionPreference = 'SilentlyContinue'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
# DPI awareness before any window exists: otherwise Windows bitmap-stretches the tray menu on
# high-DPI screens and its text looks blurry. AllowSetForegroundWindow lets the panel come to the
# front when the user opens it from the tray (the click gives this process the foreground right).
Add-Type -Namespace CCGuard -Name Native -MemberDefinition @'
[DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(System.IntPtr value);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
[DllImport("user32.dll")] public static extern bool AllowSetForegroundWindow(int processId);
'@
try {
    if (-not [CCGuard.Native]::SetProcessDpiAwarenessContext([System.IntPtr](-4))) { [void][CCGuard.Native]::SetProcessDPIAware() }
} catch {
    try { [void][CCGuard.Native]::SetProcessDPIAware() } catch {}
}
[System.Windows.Forms.Application]::EnableVisualStyles()

$labels = @{
    proxy_core = '代理核心'; tun_adapter = 'TUN 网卡'; default_route = '默认路由';
    firewall_block = '防火墙默认阻止'; guardian_rules = '放行规则'; core_ipv6 = '核心 IPv6';
    strict_route = '严格路由'; dns_hijack = 'DNS 接管'; dns_servers = '网卡 DNS'; os_ipv6 = '系统 IPv6'
}
$stateText = @{ ok = '正常'; degraded = '降级'; fail = '失效'; unknown = '未知' }
$AppName = 'CCGuard'
$AppId = 'CCGuard.Monitor'

. (Join-Path $PSScriptRoot 'tray-alerts.ps1')
$script:memory = New-AlertMemory
$script:ownerGoneAt = $null
$script:paused = $false
$script:staleNotified = $false
$script:currentState = ''

$tray = New-Object System.Windows.Forms.NotifyIcon
$tray.Visible = $true

$menu = New-Object System.Windows.Forms.ContextMenuStrip
$menu.Font = New-Object System.Drawing.Font('Microsoft YaHei UI', 9)
$openItem = $menu.Items.Add('打开面板')
$pauseItem = $menu.Items.Add('暂停提醒')
$pauseItem.CheckOnClick = $true
$exitItem = $menu.Items.Add('退出')
function Open-Panel {
    try { [void][CCGuard.Native]::AllowSetForegroundWindow(-1) } catch {}
    if ($Url) { Start-Process $Url; return }
    if ($ShowFile) { New-Item -ItemType File -Path $ShowFile -Force | Out-Null }
}

function Confirm-Quit {
    $owner = New-Object System.Windows.Forms.Form
    $owner.TopMost = $true
    $owner.ShowInTaskbar = $false
    $owner.StartPosition = 'Manual'
    $owner.Location = New-Object System.Drawing.Point(-32000, -32000)
    $owner.Size = New-Object System.Drawing.Size(1, 1)
    $owner.Show()
    $owner.Activate()
    try {
        $answer = [System.Windows.Forms.MessageBox]::Show($owner, '退出后监测和提醒都会停止。', ('退出 ' + $AppName + '？'),
            [System.Windows.Forms.MessageBoxButtons]::OKCancel, [System.Windows.Forms.MessageBoxIcon]::Question,
            [System.Windows.Forms.MessageBoxDefaultButton]::Button2)
    } finally {
        $owner.Dispose()
    }
    return $answer -eq [System.Windows.Forms.DialogResult]::OK
}

function Exit-App {
    if (-not (Confirm-Quit)) { return }
    # Tell the panel this is a deliberate quit, so it exits too instead of reappearing.
    if ($QuitFile) { try { New-Item -ItemType File -Path $QuitFile -Force | Out-Null } catch {} }
    $timer.Stop()
    $tray.Visible = $false
    $tray.Dispose()
    [System.Windows.Forms.Application]::Exit()
}

if ($Url -or $ShowFile) {
    $openItem.add_Click({ Open-Panel })
    $tray.add_DoubleClick({ Open-Panel })
} else {
    $openItem.Enabled = $false
    $openItem.Text = '打开面板（不可用）'
}
$pauseItem.add_Click({ $script:paused = $pauseItem.Checked })
$exitItem.add_Click({ Exit-App })
$tray.ContextMenuStrip = $menu

function Get-StateIcon([string]$state) {
    $candidate = Join-Path $IconDir ('icon-' + $state + '.ico')
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    return (Join-Path $IconDir 'icon-unknown.ico')
}

function Set-TrayState([string]$state) {
    if ($script:currentState -eq $state) { return }
    $iconPath = Get-StateIcon $state
    if (-not (Test-Path -LiteralPath $iconPath)) { return }
    # Ask for the tray's own size (16 px at 100 %, larger at higher DPI) so Windows does not rescale.
    $newIcon = New-Object System.Drawing.Icon($iconPath, [System.Windows.Forms.SystemInformation]::SmallIconSize)
    $oldIcon = $tray.Icon
    $tray.Icon = $newIcon
    if ($oldIcon) { $oldIcon.Dispose() }
    $label = $stateText[$state]
    if (-not $label) { $label = '未知' }
    $tray.Text = $AppName + ' · ' + $label
    $script:currentState = $state
}

# Windows names a notification after the sending program ("Windows PowerShell"). An unpackaged
# program gets its own name only through a Start menu shortcut carrying its app id; a registry-only
# identity is silently dropped (Windows 11 26300). monitor.py register-notifier creates that
# shortcut. With it: toasts as CCGuard. Without it, or WinRT unavailable: balloon as before.
$script:notifier = $null
$shortcut = Join-Path $env:APPDATA ('Microsoft\Windows\Start Menu\Programs\' + $AppName + '.lnk')
if ($env:APPDATA -and (Test-Path -LiteralPath $shortcut -PathType Leaf)) {
    try {
        $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $null = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
        $script:notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($AppId)
    } catch {
        $script:notifier = $null
    }
}

function New-ToastXml([string]$title, [string]$body) {
    $t = [Security.SecurityElement]::Escape($title)
    $b = [Security.SecurityElement]::Escape($body)
    return '<toast><visual><binding template="ToastGeneric"><text>' + $t + '</text><text>' + $b + '</text></binding></visual></toast>'
}

function Show-Notice($title, $body, $kind) {
    # Test seam: with -NoticeLog the notice is appended to that file instead of being shown.
    if ($NoticeLog) {
        Add-Content -LiteralPath $NoticeLog -Encoding UTF8 -Value ('{0}|{1}|{2}|{3}' -f [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(), $kind, $title, $body)
        return
    }
    # Before the first toast Windows reports an empty setting, so only an explicit "Disabled..."
    # (user, policy or manifest) sends us back to the balloon. The Start menu shortcut is what
    # makes Windows accept the identity at all.
    $setting = ''
    if ($script:notifier) { try { $setting = [string]$script:notifier.Setting } catch { $setting = 'Unknown' } }
    if ($script:notifier -and $setting -notmatch '^Disabled|^Unknown$') {
        try {
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml((New-ToastXml $title $body))
            $script:notifier.Show((New-Object Windows.UI.Notifications.ToastNotification $xml))
            return
        } catch {
            $script:notifier = $null
        }
    }
    $tray.ShowBalloonTip(8000, $title, $body, $kind)
}

function Read-State {
    for ($i = 0; $i -lt 3; $i++) {
        try {
            $raw = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8
            if ($raw) { return $raw | ConvertFrom-Json }
        } catch {
            Start-Sleep -Milliseconds 120
        }
    }
    return $null
}

Set-TrayState 'unknown'

$alertIcons = @{ error = [System.Windows.Forms.ToolTipIcon]::Error; warning = [System.Windows.Forms.ToolTipIcon]::Warning;
                 info = [System.Windows.Forms.ToolTipIcon]::Info }
$timer = New-Object System.Windows.Forms.Timer
# Read the state every 2 s whatever the collection interval, so a failure is shown as soon as the
# monitor has written it.
$timer.Interval = 2000
$timer.add_Tick({
    # The monitoring process is gone. A normal exit closes the tray first, so getting here means it
    # crashed or was killed: say so (protection is no longer watched), keep the icon 10 s so the
    # notice can show, then leave.
    if ($OwnerPid -gt 0 -and -not (Get-Process -Id $OwnerPid -ErrorAction SilentlyContinue)) {
        if ($null -eq $script:ownerGoneAt) {
            $script:ownerGoneAt = [DateTime]::UtcNow
            Set-TrayState 'unknown'
            if (-not $script:paused) {
                Show-Notice 'CCGuard 已停止' '监测进程意外退出，之后防护失效不会再提醒，请重新打开 CCGuard。' ([System.Windows.Forms.ToolTipIcon]::Error)
            }
            return
        }
        if (([DateTime]::UtcNow - $script:ownerGoneAt).TotalSeconds -lt 10) { return }
        $timer.Stop()
        $tray.Visible = $false
        $tray.Dispose()
        [System.Windows.Forms.Application]::Exit()
        return
    }
    $state = Read-State
    if (-not $state) { return }
    # The panel can change interval/cooldown at runtime; state.json carries the current values.
    $interval = $IntervalSeconds
    if ([int]$state.interval_seconds -ge 2) { $interval = [int]$state.interval_seconds }
    $cooldown = $CooldownSeconds
    if ($null -ne $state.cooldown_seconds -and [int]$state.cooldown_seconds -ge 0) { $cooldown = [int]$state.cooldown_seconds }
    $age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [int64]$state.checked_at
    # "Stopped" only after three missed rounds and at least a minute: one slow round (a cold start,
    # a busy machine, the rule list refresh) is not a stopped monitor.
    if ($age -gt [Math]::Max($interval * 3, 60)) {
        Set-TrayState 'unknown'
        if (-not $script:staleNotified) {
            if (-not $script:paused) { Show-Notice $AppName '监测已停止更新，请检查监测进程。' ([System.Windows.Forms.ToolTipIcon]::Warning) }
            $script:staleNotified = $true
        }
        return
    }
    $script:staleNotified = $false

    $overall = [string]$state.overall
    if (-not $overall) { $overall = 'unknown' }
    Set-TrayState $overall

    $notifyStates = @('fail', 'degraded')
    if ($state.notify_states) { $notifyStates = @($state.notify_states) }
    $paused = $script:paused -or [bool]$state.paused
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

    foreach ($alert in (Get-Alerts $script:memory $state $now $cooldown $notifyStates $labels $stateText)) {
        if (-not $paused) { Show-Notice $alert.title $alert.body $alertIcons[[string]$alert.kind] }
    }
})
$timer.Start()
[System.Windows.Forms.Application]::Run()
