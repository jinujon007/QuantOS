# QuantOS missed-run watchdog (WP-014, ADR-039).
#
# Closes R-006's blind spot from the outside: the daily runner can only
# report failures for runs that START. If the 15:40 task never fires
# (machine off, operator logged out, scheduler broken), nothing anywhere
# says so -- the console tile just goes quietly stale. This script runs
# as its own scheduled task ("QuantOS Daily Watchdog", weekdays 16:30,
# registered by tools\register_watchdog_task.ps1) and alerts when
# data\daily_run.log has no "daily run start" entry stamped today.
#
# Weekends/holidays: the task is registered weekdays-only, matching the
# main task. An NSE holiday still runs paper_trader (which no-ops safely)
# so the start marker exists and the watchdog stays silent -- correct.
#
# Exit codes: 0 run found (or nothing to do) | 1 missed run detected.

$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$log = Join-Path $projectDir "data\daily_run.log"
$today = Get-Date -Format "yyyy-MM-dd"

function Test-RunStarted {
    if (-not (Test-Path $log)) { return $false }
    return [bool](Select-String -Path $log -Pattern "^\[$today .*daily run start" -Quiet)
}

if (Test-RunStarted) { exit 0 }

# Boot-race guard: after an off-all-day machine powers up, BOTH tasks
# fire via StartWhenAvailable at nearly the same moment — this check can
# land before the main run writes its start line. Give it three minutes,
# then decide.
Start-Sleep -Seconds 180
if (Test-RunStarted) { exit 0 }

# Missed run. Say so where the operator will see it: the alert channel,
# and the log itself (neutral wording -- the parser in api/collectors.py
# must not read this as a failed step of the PREVIOUS day's block).
$message = "Daily paper run never started today ($today) - machine off or task blocked. Validation record is missing a day; run tools\daily_run.ps1 manually (weekend catch-up logic recovers a missed Friday)."
$stampNow = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $log -Value "[$stampNow] watchdog: no daily run start entry for $today - alert dispatched" -Encoding UTF8

& (Join-Path $projectDir "tools\send_alert.ps1") -Message $message -Title "QuantOS watchdog"
exit 1
