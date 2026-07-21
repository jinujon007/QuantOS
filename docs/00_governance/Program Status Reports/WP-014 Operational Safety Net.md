---
type: report
work_package: WP-014
date: 2026-07-21
status: complete
adr: ADR-039
---

# WP-014 — Operational Safety Net (alert + backup + watchdog)

## What was built

Three `tools/` leaf scripts (stdlib PowerShell, zero Python deps), wired
into `daily_run.ps1` per ADR-039:

- `send_alert.ps1` — one webhook POST per non-clean daily run (any
  FAILED/HALTED step, incl. a DEGRADED `paper_trader.py`). Endpoint:
  `QUANTOS_ALERT_URL` user env var (ntfy topic / any raw-POST webhook).
  Unset → logged `SKIPPED`, never a failure. Status-only messages, no
  holdings/account data.
- `backup_state.ps1` — after every run, copies the non-git-protected
  state (`paper_state.json`, `paper_trades.csv`, `universe_pit.db`,
  `risk.db`, `daily_run.log`, `journal.md`, results CSVs, `shadow/`) to
  `QUANTOS_BACKUP_DIR` (default `D:\QuantOS_Backups`), dated folders,
  newest 30 kept. Backup failure = FAILED step → DEGRADED tile + alert.
- `daily_watchdog.ps1` + `register_watchdog_task.ps1` — second
  scheduled task ("QuantOS Daily Watchdog", weekdays 16:30,
  StartWhenAvailable, **registered on this machine 2026-07-21**) alerts
  when today has no "daily run start" log entry — the failure class the
  runner cannot self-report. 3-minute recheck guards the boot race
  (both tasks firing together after an off-all-day power-up).

`daily_run.ps1` additions: `PsStep` helper (exit-code contract identical
to `RunStep`), problem accumulation across steps, backup step after the
console rebuild, conditional alert dispatch last.

## Verification evidence

- Live double-run of `backup_state.ps1`: 9 items to
  `D:\QuantOS_Backups\2026-07-21`, idempotent (nested-`shadow\shadow`
  Copy-Item bug caught in self-review, fixed, re-verified).
- `send_alert.ps1` unconfigured path: exit 3, `SKIPPED` logging.
- `daily_watchdog.ps1` with today's run present: exit 0, silent.
- Full `daily_run.ps1` end-to-end (idempotent day): all steps OK, log
  parser (`api/collectors.py::collect_daily_run`) semantics preserved —
  new lines either end in " OK"/" FAILED (...)" (counted correctly) or
  are neutral (`SKIPPED`, watchdog note).
- Gates: 233 pytest passed / ruff clean / `ruff format --check` clean /
  `mypy --strict -p quantos_core` clean. No Python touched.

## Freeze compliance

Operational-reliability tooling only (permitted class per CONTEXT.md's
Prospective Validation rule): reads state/logs, writes nothing any
signal path consumes. Validation clock unaffected.

## Register impact

- R-005 → Low (state now backed up daily; residual = same-disk default).
- R-006 → Low-Medium (missed runs detected ≤ ~50 min; residual =
  logged-out-at-trigger still needs stored credentials).
- TD-017 (10th-buy sizing, audit E-2) and TD-018 (legacy `_fetch_close`
  fail-open, audit E-1) recorded in the Technical Debt Register.

## Operator actions (one-time, recommended)

1. Pick a private topic: `https://ntfy.sh/quantos-<long-random-suffix>`;
   set it: `[Environment]::SetEnvironmentVariable("QUANTOS_ALERT_URL",
   "<url>", "User")`; subscribe in the ntfy app. Until then, alerts log
   SKIPPED and everything else still works.
2. Optionally point `QUANTOS_BACKUP_DIR` at a synced/second-disk folder
   to cover disk death (default covers git-accident/corruption only).
