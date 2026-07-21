# Current Task

**Latest session 2026-07-21 — due-diligence audit + WP-014/015/016/017:
complete.** Full log: `docs/00_governance/(AI) Program Log - 2026-07-21.md`.
All on branch `docs/institutional-dd-2026-07-21` (PR #1, awaiting
operator merge).

- **WP-017 (ADR-042)**: daily paper-equity history — every completed
  run appends `date,total_value,cash,positions,degraded` to
  `data/paper_equity_history.csv` (true append; readers keep last row
  per date on `--force` reruns); `tools/paper_metrics.py` reports
  total return, annualized Sharpe, max drawdown (exit 1 = insufficient
  history). Sept-9 "paper Sharpe > 1.0" now computable. Freeze-safe
  (logging only, clock intact). 10 new tests → 259 total.

- **Audit** (`docs/01_audits/(AI) QuantOS Institutional Due Diligence -
  2026-07-21.md`): 5.5/10 institutional readiness (concurs with DRS
  61/100); first real rebalance verified (Fri 07-17 signal → Mon 07-20
  T+1 fills, 9 positions, SYRMA dropped = TD-017); shadow books MATCH
  daily; SEBI ≤10 orders/sec carve-out simplifies R-001 (Zerodha
  rewrite needed); ADR-022/023 verified stale (revisit before
  Phase 5); yfinance quarantine + bhavcopy-primary recommended.
- **WP-014 (ADR-039)**: alert (`QUANTOS_ALERT_URL`) + daily state
  backup (`QUANTOS_BACKUP_DIR`, default `D:\QuantOS_Backups`) +
  "QuantOS Daily Watchdog" task (registered, weekdays 16:30).
- **WP-015 (ADR-040)**: TD-016 closed — `paper_state.json` untracked;
  backups are the history; tree clean; 07-17 PIT snapshot committed.
- **WP-016 (ADR-041)**: `PositionLimitGate` (≤15% NAV/name, SELLs
  exempt, fail-closed) + `CompositeGate` behind the WP-008 seam; demo
  drills oversized order → BLOCKED; paper cycle deliberately un-gated
  until Phase 6 cutover.

**Gates at close:** 249 tests / ruff / format / mypy --strict /
determinism 3× / boundaries — all green. Registers + STATUS +
PROJECT_STATE synchronized.

## Next work package (recommended)

**WP-017 done. TD-015 closed** (venv rebuilt from lockfile, 56 pkgs,
all gates re-verified). **ADR-043 filed** — amends stale ADR-022/023
(metrics = ported cited formulas, not empyrical dep; MLflow rejected,
native run-manifest at Phase 5); DD "revisit before Phase 5" closed.
**TD-012 closed** (per-file inventory classification, Platform Code
bucket). **ADR-044 PROPOSED** — bhavcopy-primary data architecture,
yfinance quarantine, XNSE calendar (DD M-6): needs operator approval
before the Phase 2 fetch-adapter WP can start. Remaining open debt is
phase-gated (TD-013 Phase 6, TD-014/017 Momentum v1.1 boundary,
TD-018 supersession at cutover).

## Operator queue (code cannot do these)

1. SEBI/Zerodha checklist — personal Kite key, static IP, Strategy-ID
   + simulation confirmation, ≤10 orders/sec bucket in writing.
2. Set `QUANTOS_ALERT_URL` + subscribe (alerts currently log SKIPPED).
3. Point `QUANTOS_BACKUP_DIR` off-machine (optional, recommended).
4. Cutover decision after Fri 2026-07-25 shadow match (2nd clean
   weekly candidate).
5. Review + merge PR #1.

## Compressed history

WP-000..005 Phase 1 closed (typing, config, storage, logging, import
matrix) · WP-007 Phase 2 opened (PIT store, fail-closed prices) ·
WP-008 execution slice + 3 broker adapters + kill switch (ADR-034) ·
WP-009 Momentum v1.0 behind Strategy port, byte-parity (Phase 3) ·
WP-010 console + kill-switch CLI (ADR-035) · WP-011 desktop app
(ADR-036) · WP-012 portfolio accounting + CostModel (ADR-037) ·
WP-013 paper.run_cycle + shadow cutover harness (ADR-038) · daily
task "QuantOS Daily Paper Run" weekdays 15:40 since 2026-07-15.

## Out of scope for this document

Phase specifications — see `AI_CONTEXT.md` + Constitution. Frozen
strategy list — see CONTEXT.md Prospective Validation rule (0 touched
this session; clock intact, ~1/13 weeks).
