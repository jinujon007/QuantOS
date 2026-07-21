# QuantOS — unattended daily runner (WP interview decision, 2026-07-14).
# Registered in Windows Task Scheduler as "QuantOS Daily Paper Run"
# (weekdays 15:40 IST). Manual run: .\tools\daily_run.ps1
#
# Mon–Thu: paper_trader (regime + stop-loss monitoring) + console rebuild.
# Fri–Sun: + PIT universe snapshot for the week's Friday (Sat/Sun runs are
#          StartWhenAvailable catch-ups after a missed Friday; the seed is
#          idempotent via --skip-if-exists, so a normal week logs no error).
# Everything is appended to data\daily_run.log — the validation clock's
# evidence that the run actually happened each day.

$ErrorActionPreference = "Continue"
# PS 5.1 decodes native stdout with the OEM codepage by default, turning the
# UTF-8 rupee/dash output into mojibake in the evidence log.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $projectDir
$python = Join-Path $projectDir "venv\Scripts\python.exe"
$log = Join-Path $projectDir "data\daily_run.log"
$env:PYTHONIOENCODING = "utf-8"

function Log([string]$message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $log -Value "[$stamp] $message" -Encoding UTF8
}

if (-not (Test-Path $python)) {
    Log "=== daily run ABORTED: venv python not found at $python ==="
    exit 1
}

# Non-OK steps collected here feed the end-of-run alert (WP-014, ADR-039).
$script:problems = @()

function RunStep([string]$label, [string[]]$cmdArgs) {
    # Pipe through PowerShell strings so the log stays one encoding
    # (PS 5.1's native *>> writes interleaved UTF-16 — unreadable).
    & $python @cmdArgs 2>&1 | ForEach-Object { "$_" } | Add-Content -Path $log -Encoding UTF8
    if ($LASTEXITCODE -eq 2) { Log "$label HALTED (kill switch engaged)"; $script:problems += "$label HALTED" }
    elseif ($LASTEXITCODE -ne 0) { Log "$label FAILED (exit $LASTEXITCODE)"; $script:problems += "$label FAILED (exit $LASTEXITCODE)" }
    else { Log "$label OK" }
}

function PsStep([string]$label, [string]$scriptPath) {
    # Same contract as RunStep, for PowerShell tool scripts (they signal
    # via exit codes just like the Python steps).
    & $scriptPath 2>&1 | ForEach-Object { "$_" } | Add-Content -Path $log -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { Log "$label FAILED (exit $LASTEXITCODE)"; $script:problems += "$label FAILED" }
    else { Log "$label OK" }
}

Log "=== daily run start ==="
RunStep "paper_trader.py" @("paper_trader.py")

# Shadow cycle (ADR-038): quantos_core's run_cycle beside the legacy
# loop, own state in data\shadow\, read-only w.r.t. the record. A
# divergence exits 1 -> FAILED here -> DEGRADED on the console tile.
RunStep "shadow cycle" @("tools\run_paper_cycle.py")

# Friday's PIT snapshot, with weekend catch-up: a missed Friday run fires
# Sat/Sun via StartWhenAvailable and must still record Friday's membership.
$dow = (Get-Date).DayOfWeek
if ($dow -in @("Friday", "Saturday", "Sunday")) {
    $friday = Get-Date
    while ($friday.DayOfWeek -ne "Friday") { $friday = $friday.AddDays(-1) }
    $fridayStr = $friday.ToString("yyyy-MM-dd")
    RunStep "universe snapshot ($fridayStr)" @("tools\seed_universe_snapshot.py", $fridayStr, "--skip-if-exists")
    Log "FRIDAY: log this week's signals in data\journal.md (validation clock evidence)"
}

# End marker BEFORE the console rebuild: the rebuild parses this log for
# the last-run tile, and a block that hasn't ended yet would always render
# as INCOMPLETE during its own run. A rebuild failure lands after the
# marker and still surfaces (DEGRADED) on the next rebuild.
Log "=== daily run end ==="
RunStep "console rebuild" @("tools\build_dashboard.py")

# State backup after everything else, so it captures today's post-run
# state (WP-014, ADR-039). A backup failure marks the day DEGRADED on
# the console tile and joins the alert below.
PsStep "state backup" (Join-Path $projectDir "tools\backup_state.ps1")

# One alert per non-clean run — push, not pull: a silent broken day cost
# a month once (PRD §2); the console tile only helps if someone opens it.
if ($script:problems.Count -gt 0) {
    $summary = "Daily run $((Get-Date -Format 'yyyy-MM-dd')) needs attention: " + ($script:problems -join "; ") + ". See data\daily_run.log."
    $alertOutput = & (Join-Path $projectDir "tools\send_alert.ps1") -Message $summary -Title "QuantOS daily run"
    "$alertOutput" | Add-Content -Path $log -Encoding UTF8
    if ($LASTEXITCODE -eq 3) { Log "alert dispatch SKIPPED (QUANTOS_ALERT_URL unset)" }
    elseif ($LASTEXITCODE -ne 0) { Log "alert dispatch FAILED (exit $LASTEXITCODE)" }
    else { Log "alert dispatch OK" }
}
