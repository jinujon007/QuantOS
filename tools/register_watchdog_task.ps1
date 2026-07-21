# Registers the "QuantOS Daily Watchdog" scheduled task (WP-014, ADR-039).
#
# Weekdays 16:30 local, StartWhenAvailable (a late logon still triggers a
# catch-up check, same setting the main 15:40 task uses). Idempotent:
# re-running replaces the existing definition. Remove with:
#   Unregister-ScheduledTask -TaskName "QuantOS Daily Watchdog" -Confirm:$false

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$script = Join-Path $projectDir "tools\daily_watchdog.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday -At 16:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName "QuantOS Daily Watchdog" `
    -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Output "Registered 'QuantOS Daily Watchdog' (weekdays 16:30, StartWhenAvailable)."
