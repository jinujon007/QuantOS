---
type: register
date: 2026-07-14
status: active
updated_by: Program audit 2026-07-14
---

# Risk Register

Living document, updated at the end of every work package. Distinct from
the Technical Debt Register: this tracks risks to the *program* (capital,
compliance, delivery), not code-quality items.

| ID | Risk | Likelihood | Impact | Mitigation / status | Owner |
|---|---|---|---|---|---|
| R-001 | SEBI Algo-ID/static-IP/2FA compliance checklist is 0/7, enforcement deadline (1 Apr 2026) already passed | Certain (already true) | Blocks any live-order placement outright — not an engineering risk, a legal one | Pure verification task, zero engineering dependency, explicitly sequenced to run in parallel with every phase (Blueprint §12) — not started this work package, unchanged | Operator (Jinu) — requires Angel One portal action, not code |
| R-002 | Prospective Validation freeze integrity depends on 13 *clean* weekly rebalances, and 3 scheduler gaps (missing log day, truncated run, late trigger) were found in the first 5 weeks | Medium | If the observation count includes a silently-broken week, the 2026-09-09 go-live decision would rest on a false premise | Root-cause not yet done (Blueprint Phase 0 item, separate from this repo's engineering Phase 0) — still open | Unassigned |
| R-003 | `My_terminal/trading_backtests/` (16-strategy suite, 2 of them live-tournament strategies: Quality Factor, Factor Timing) has zero characterization-test/golden-file protection | High if that codebase is ever touched | A future change there could silently alter live-tournament strategy behavior with nothing to catch it — same failure mode Phase 0 exists to prevent, just not yet applied to that repo | Not mitigated — TD-004 tracks the fix (its own Phase 0 pass), not scheduled | Unassigned |
| R-004 | Repository reorganization (this work package) touched only documentation and empty scaffolding — but any reorg carries a nonzero chance of an overlooked cross-reference breaking | Low | A broken doc link is a discoverability problem, not a trading-correctness one | Mitigated: grepped for hardcoded relative-path references before every `git mv`; none of the moved files were referenced by exact path anywhere (only by name, which Obsidian resolves vault-wide) | This work package |
| R-005 | ~~No GitHub remote~~ **Partially mitigated 2026-07-14** (private remote, push-per-WP habit); **state-loss component mitigated 2026-07-21 (WP-014):** source history is on origin, and the non-git-protected state (`paper_trades.csv` untracked; `risk.db`/`daily_run.log`/`shadow/` gitignored; `paper_state.json` single-copy) is now backed up daily to `QUANTOS_BACKUP_DIR` (default `D:\QuantOS_Backups`, 30-day rotation, ADR-039) | ~~Medium~~ Low (residual: default backup dir is same-disk; operator pointing it at a synced folder closes disk-death) | Loss of validation evidence on disk failure or git-restore accident | WP-014 backup step runs after every daily run; backup failure surfaces as DEGRADED + alert | Operator (point `QUANTOS_BACKUP_DIR` off-machine) |
| R-006 | Scheduled task "QuantOS Daily Paper Run" runs with Logon Mode: Interactive only — if the operator is not logged in at 15:40 the daily paper run silently skips, and a skipped Friday is a missed rebalance | ~~Medium~~ Low-Medium | Directly corrupts the 13-week prospective-validation record (R-002's failure mode, new cause) | StartWhenAvailable (2026-07-14) + **WP-014 (2026-07-21): "QuantOS Daily Watchdog" task (weekdays 16:30, boot-race-guarded) alerts on a day with no run start; non-clean runs push one webhook alert (`QUANTOS_ALERT_URL`)**. Residual: run-whether-logged-on-or-not still needs stored credentials; alert channel needs one-time operator setup | Operator (set `QUANTOS_ALERT_URL`, subscribe) |

## Likelihood / Impact scale

Likelihood: **Certain** (already true) / **High** / **Medium** / **Low**.
Impact: rated against capital risk, compliance risk, and safety-net
integrity — not code-quality alone (that's the Technical Debt Register).
