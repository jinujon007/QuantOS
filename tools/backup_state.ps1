# QuantOS state backup (WP-014, ADR-039).
#
# Copies every non-regenerable operational artifact -- the validation
# record and safety state -- to a dated folder outside the repository,
# because git protects source but NOT this state: paper_trades.csv is
# untracked, risk.db / daily_run.log / data\shadow are gitignored, and
# paper_state.json's history is exactly one working-tree copy (TD-016).
# A single-disk failure (or one careless `git checkout -- data/`) is
# currently the loss of the 13-week prospective-validation evidence.
#
# Destination: QUANTOS_BACKUP_DIR user env var if set, else
# D:\QuantOS_Backups (never C: -- that drive is full, CONTEXT.md).
# Same-disk default still covers the git-accident/corruption class;
# point QUANTOS_BACKUP_DIR at a synced folder (OneDrive/GDrive) or a
# second physical drive to cover disk death too.
#
# Retention: newest 30 dated folders (~6 weeks of weekday runs).
# Same-day re-runs overwrite the same dated folder (last state wins).
#
# Exit codes: 0 backed up | 1 any copy/rotation failure (caller surfaces
# it as a FAILED step -> DEGRADED console tile + alert).

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$backupRoot = $env:QUANTOS_BACKUP_DIR
if ([string]::IsNullOrWhiteSpace($backupRoot)) { $backupRoot = "D:\QuantOS_Backups" }

$stamp = Get-Date -Format "yyyy-MM-dd"
$dest = Join-Path $backupRoot $stamp

# Everything here is state or evidence, not regenerable source. data\cache
# (459 price CSVs) is deliberately excluded: regenerable via download_data.py.
$files = @(
    "data\paper_state.json",
    "data\paper_trades.csv",
    "data\universe_pit.db",
    "data\risk.db",
    "data\daily_run.log",
    "data\journal.md",
    "data\results\equity_curve.csv",
    "data\results\equity_comparison.csv"
)

$failed = $false
try {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
} catch {
    Write-Output "backup failed: cannot create $dest -- $($_.Exception.Message)"
    exit 1
}

$copied = 0
foreach ($rel in $files) {
    $src = Join-Path $projectDir $rel
    if (Test-Path $src) {
        try {
            Copy-Item -Path $src -Destination $dest -Force
            $copied++
        } catch {
            Write-Output "backup failed on ${rel}: $($_.Exception.Message)"
            $failed = $true
        }
    }
    # A missing source is not a failure: paper_trades.csv does not exist
    # until the first fill, shadow state until the first shadow run, etc.
}

$shadowSrc = Join-Path $projectDir "data\shadow"
if (Test-Path $shadowSrc) {
    try {
        # Copy CONTENTS into a pre-created folder: Copy-Item on the dir
        # itself would nest data\shadow INSIDE an existing destination
        # folder on a same-day re-run (shadow\shadow\...).
        $shadowDest = Join-Path $dest "shadow"
        New-Item -ItemType Directory -Force -Path $shadowDest | Out-Null
        Copy-Item -Path (Join-Path $shadowSrc "*") -Destination $shadowDest -Recurse -Force
        $copied++
    } catch {
        Write-Output "backup failed on data\shadow: $($_.Exception.Message)"
        $failed = $true
    }
}

# Rotate: keep the newest 30 dated folders. Only touch children of the
# backup root whose names look like dates -- never anything else.
try {
    $dated = Get-ChildItem -Path $backupRoot -Directory |
        Where-Object { $_.Name -match "^\d{4}-\d{2}-\d{2}$" } |
        Sort-Object Name -Descending
    if ($dated.Count -gt 30) {
        $dated | Select-Object -Skip 30 | ForEach-Object {
            Remove-Item -Path $_.FullName -Recurse -Force -Confirm:$false
        }
    }
} catch {
    Write-Output "backup rotation failed: $($_.Exception.Message)"
    $failed = $true
}

if ($failed) { exit 1 }
Write-Output "backed up $copied item(s) to $dest"
exit 0
