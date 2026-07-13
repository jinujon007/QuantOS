# AlgoTrader — Daily Runner
# Run this every day after 3:30 PM IST.
# On Fridays: full rebalance. Mon-Thu: regime check + stop loss monitoring.
#
# Usage: Right-click → Run with PowerShell
#        OR in terminal: .\run_today.ps1

$ErrorActionPreference = "Stop"
$projectDir = "d:\Brain\JINU JOSHI\02 Self\Projects\AlgoTrader"

Set-Location $projectDir
& ".\venv\Scripts\Activate.ps1"

$day = (Get-Date).DayOfWeek
$isFriday = ($day -eq "Friday")

if ($isFriday) {
    Write-Host ""
    Write-Host "  FRIDAY — REBALANCE DAY" -ForegroundColor Yellow
    Write-Host "  After this runs, open data\journal.md and log the top 10 signals." -ForegroundColor Yellow
    Write-Host ""
}

python paper_trader.py

if ($isFriday) {
    Write-Host ""
    Write-Host "  Done. Now open data\journal.md and log today's signals." -ForegroundColor Green
    Write-Host "  Journal: $projectDir\data\journal.md" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Trade log: $projectDir\data\paper_trades.csv" -ForegroundColor Cyan
Write-Host "  State:     $projectDir\data\paper_state.json" -ForegroundColor Cyan
