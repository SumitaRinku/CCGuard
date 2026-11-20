# Which notifications the tray raises for a new state. Pure functions (no window, no tray), so the
# tests can feed state sequences through them. Dot-sourced by tray.ps1.
#
# Rules:
#   - fail: always notified at once, cooldown or not (a protection failure, including a repeat
#     after recovery or an escalation from degraded, must never be swallowed);
#   - other states in notify_states (degraded by default): at most once per check per cooldown;
#   - back to ok from a state that is notified (fail, degraded): a recovery notice; unknown -> ok
#     (a slow first round, for example) is not news;
#   - every check unknown for 30 s (nothing can be read): one warning, and a notice when it clears.

$script:BlindAfterMs = 30000

function New-AlertMemory {
    return @{ previous = @{}; lastSent = @{}; blindSince = $null; blindNotified = $false }
}

function New-Alert($title, $body, $kind) {
    return [pscustomobject]@{ title = $title; body = $body; kind = $kind }
}

function Get-Alerts($memory, $state, [int64]$nowMs, [int]$cooldown, $notifyStates, $labels, $stateText) {
    $alerts = New-Object System.Collections.ArrayList
    $checks = @($state.checks)
    foreach ($check in $checks) {
        $id = [string]$check.id
        $after = [string]$check.state
        $before = $memory.previous[$id]
        if ($before -eq $after) { continue }
        $label = $labels[$id]
        if (-not $label) { $label = $id }
        if ($notifyStates -contains $after) {
            $due = -not $memory.lastSent.ContainsKey($id) -or ($nowMs - [int64]$memory.lastSent[$id]) -ge ($cooldown * 1000)
            if ($after -eq 'fail' -or $due) {
                if ($after -eq 'fail') {
                    [void]$alerts.Add((New-Alert '防护告警' ($label + '：失效') 'error'))
                } else {
                    [void]$alerts.Add((New-Alert '防护告警' ($label + '：' + $stateText[$after]) 'warning'))
                }
                $memory.lastSent[$id] = $nowMs
            }
        } elseif ($after -eq 'ok' -and $notifyStates -contains $before) {
            [void]$alerts.Add((New-Alert '已恢复' ($label + ' 回到正常') 'info'))
        }
        $memory.previous[$id] = $after
    }
    $blind = $checks.Count -gt 0 -and -not ($checks | Where-Object { [string]$_.state -ne 'unknown' })
    if ($blind) {
        if ($null -eq $memory.blindSince) {
            $memory.blindSince = $nowMs
        } elseif (-not $memory.blindNotified -and ($nowMs - [int64]$memory.blindSince) -ge $script:BlindAfterMs) {
            [void]$alerts.Add((New-Alert '无法判断防护状态' '连续 30 秒读不到本机状态，防护失效可能无法及时提醒。' 'warning'))
            $memory.blindNotified = $true
        }
    } else {
        if ($memory.blindNotified) {
            [void]$alerts.Add((New-Alert '已恢复' '重新读到本机状态' 'info'))
        }
        $memory.blindSince = $null
        $memory.blindNotified = $false
    }
    return $alerts.ToArray()
}
