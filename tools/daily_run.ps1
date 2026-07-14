# QuantOS — unattended daily runner (WP interview decision, 2026-07-14).
# Registered in Windows Task Scheduler as "QuantOS Daily Paper Run"
# (weekdays 15:40 IST). Manual run: .\tools\daily_run.ps1
#
# Mon–Thu: paper_trader (regime + stop-loss monitoring) + console rebuild.
# Friday:  + PIT universe snapshot seed (accumulates real point-in-time
#          history) before the rebuild.
# Everything is appended to data\daily_run.log — the validation clock's
# evidence that the run actually happened each day.

$ErrorActionPreference = "Continue"
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectDir
$python = Join-Path $projectDir "venv\Scripts\python.exe"
$log = Join-Path $projectDir "data\daily_run.log"
$env:PYTHONIOENCODING = "utf-8"

function Log([string]$message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $log -Value "[$stamp] $message" -Encoding UTF8
}

function RunStep([string]$label, [string[]]$cmdArgs) {
    # Pipe through PowerShell strings so the log stays one encoding
    # (PS 5.1's native *>> writes interleaved UTF-16 — unreadable).
    & $python @cmdArgs 2>&1 | ForEach-Object { "$_" } | Add-Content -Path $log -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { Log "$label FAILED (exit $LASTEXITCODE)" } else { Log "$label OK" }
}

Log "=== daily run start ==="
RunStep "paper_trader.py" @("paper_trader.py")

if ((Get-Date).DayOfWeek -eq "Friday") {
    $today = Get-Date -Format "yyyy-MM-dd"
    RunStep "universe snapshot ($today)" @("tools\seed_universe_snapshot.py", $today)
    Log "FRIDAY: log this week's signals in data\journal.md (validation clock evidence)"
}

RunStep "console rebuild" @("tools\build_dashboard.py")
Log "=== daily run end ==="
