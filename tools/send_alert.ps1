# QuantOS operator alert dispatch (WP-014, ADR-039).
#
# POSTs a plain-text message to the webhook named by the QUANTOS_ALERT_URL
# user environment variable (ntfy.sh topic URL, or any endpoint accepting a
# raw-body POST). Deliberately shell-level, not an AlertSink adapter: this
# must fire even when the venv or Python itself is the thing that broke.
# The AlertSink port remains Phase 7 (Constitution Part II, Event Design).
#
# One-time operator setup (pick a private, unguessable topic name):
#   [Environment]::SetEnvironmentVariable("QUANTOS_ALERT_URL",
#       "https://ntfy.sh/quantos-<long-random-suffix>", "User")
#   then subscribe to that topic in the ntfy mobile/desktop app.
#
# Messages carry run status only -- never holdings, order, or account data.
#
# Exit codes: 0 sent | 1 send failed | 3 not configured (caller decides
# whether that is worth logging; it is never a run failure by itself).

param(
    [Parameter(Mandatory = $true)][string]$Message,
    [string]$Title = "QuantOS"
)

$url = $env:QUANTOS_ALERT_URL
if ([string]::IsNullOrWhiteSpace($url)) {
    Write-Output "alert not configured (QUANTOS_ALERT_URL unset)"
    exit 3
}

try {
    # ntfy reads the title from a header; other webhook receivers ignore it.
    Invoke-RestMethod -Uri $url -Method Post -Body $Message `
        -Headers @{ "Title" = $Title } -TimeoutSec 10 | Out-Null
    Write-Output "alert sent"
    exit 0
} catch {
    Write-Output "alert send failed: $($_.Exception.Message)"
    exit 1
}
