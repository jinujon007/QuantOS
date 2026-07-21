---
type: adr
number: 039
date: 2026-07-21
status: accepted
supersedes: none
---

# ADR-039 — Shell-Level Operational Safety Net Ahead of Phase 7 (WP-014)

## Decision

Three `tools/` leaf scripts, wired into the unattended daily runner:

1. **Alert dispatch** (`send_alert.ps1`): one webhook POST per non-clean
   daily run (any FAILED/HALTED step, including a DEGRADED
   `paper_trader.py` exit). Endpoint comes from the `QUANTOS_ALERT_URL`
   user environment variable (ntfy.sh topic or any raw-POST webhook);
   unset = logged as SKIPPED, never a failure. Messages carry run status
   only — no holdings, orders, or account data.
2. **State backup** (`backup_state.ps1`): after every daily run, copy the
   non-regenerable state — `paper_state.json`, `paper_trades.csv`,
   `universe_pit.db`, `risk.db`, `daily_run.log`, `journal.md`, pinned
   results CSVs, `data/shadow/` — to `QUANTOS_BACKUP_DIR` (default
   `D:\QuantOS_Backups`; never C:, which is full), dated folders, newest
   30 kept. `data/cache/` excluded (regenerable).
3. **Missed-run watchdog** (`daily_watchdog.ps1` + one-time
   `register_watchdog_task.ps1`): a second scheduled task (weekdays
   16:30, StartWhenAvailable) that alerts when `daily_run.log` has no
   "daily run start" entry for today — the failure class the runner
   cannot report on itself (task never fired: machine off, logged out,
   scheduler broken — R-006's residual risk).

## Context

The console tile (WP-011) closed the "runner logs FAILED but nothing
surfaces it" gap — pull-only. A silent dead scheduler already cost one
month of validation data once (PRD §2). Meanwhile the validation
record's evidence files are single-copy on one disk: `paper_trades.csv`
untracked, `risk.db`/`daily_run.log`/`data/shadow/` gitignored,
`paper_state.json` history = one working-tree copy (TD-016). R-005's
push habit protects source, not state.

## Why shell scripts and not the AlertSink port / monitoring module

The Constitution's alerting design (`AlertSink`, `monitoring`) is domain
alerting for Phase 7. This safety net must fire precisely when Python,
the venv, or the domain code is what broke — so it lives in the
imperative shell (`tools/`, dependency leaf per ADR-029), stdlib
PowerShell only. Phase 7 builds the real AlertSink on top; these scripts
then become its transport or get retired by it. Same
slice-ahead-of-phase justification as ADR-034.

Config via user environment variables rather than `AppConfig` because
the layered config system is WP-006 (reserved, unbuilt), and these
values are per-machine operator concerns, not domain configuration.

## Freeze compliance

Zero effect on signals or state: alerting/backup/watchdog read state
and logs, never write trading state. Explicitly the "operational
reliability fixes" class permitted by the Prospective Validation rule
(CONTEXT.md).

## Alternatives Considered

- **Telegram bot as the transport.** Rejected for now: needs a bot
  token (a secret, with nowhere proper to live until the secret-store
  loader exists). ntfy topic URLs are shareable-secret-lite and the
  script accepts any raw-POST webhook, Telegram included, later.
- **Windows toast notifications.** Rejected: invisible from a
  non-interactive scheduled task, and useless when the operator is away
  — which is exactly the scenario that matters.
- **Committing state daily instead of file backups.** Deferred to the
  TD-016 decision (ADR-040): git history as backup couples unattended
  pushes to credentials and pollutes source history with state churn.

## Consequences

- `daily_run.ps1` gains two steps (backup, conditional alert); a backup
  failure marks the day DEGRADED on the console tile.
- Operator setup (one-time, optional but strongly recommended): set
  `QUANTOS_ALERT_URL`, subscribe to the topic, run
  `tools/register_watchdog_task.ps1`. Unconfigured, backups still run
  with the D:\ default; alerts log SKIPPED.
- R-006 downgraded (missed runs now detected within ~50 minutes);
  R-005's state-loss component mitigated same-disk by default,
  off-machine when the operator points `QUANTOS_BACKUP_DIR` at a synced
  folder.
