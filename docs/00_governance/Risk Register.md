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
| R-005 | ~~No GitHub remote~~ **Partially mitigated 2026-07-14:** private remote exists (`github.com/jinujon007/QuantOS`) — but `main` sits 12 commits ahead of `origin/main` (only WP-000..002-era history is off-machine), so the single-point-of-failure window is still open for everything since | Medium | Loss of WP-003→WP-011 history (storage, logging, data platform, execution slice, strategy port, console, desktop app) on one disk failure | Push `main` + tags to origin; then make push part of the per-WP done-definition (TD-007 tracks the CI-on-real-runner angle) | Operator (Jinu) |
| R-006 | Scheduled task "QuantOS Daily Paper Run" runs with Logon Mode: Interactive only — if the operator is not logged in at 15:40 the daily paper run silently skips, and a skipped Friday is a missed rebalance | Medium | Directly corrupts the 13-week prospective-validation record (R-002's failure mode, new cause) | StartWhenAvailable enabled 2026-07-14 (missed trigger fires at next logon); full fix = run-whether-logged-on-or-not (needs stored credentials) or an explicit missed-run alert in the console freshness pills | Operator (Jinu) |

## Likelihood / Impact scale

Likelihood: **Certain** (already true) / **High** / **Medium** / **Low**.
Impact: rated against capital risk, compliance risk, and safety-net
integrity — not code-quality alone (that's the Technical Debt Register).
