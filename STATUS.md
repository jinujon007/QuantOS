# Status

**Engineering phase:** Phase 1 closed (WP-005) · Phase 2 open (WP-007, partial) · Phase 3 open (WP-009) · Phase 5/6 slices open (WP-012/013) · Phase 7 safety-net slice (WP-014)
**Last work package:** WP-014 — operational safety net: alert + state backup + missed-run watchdog (2026-07-21, ADR-039)
**Business phase (EXECUTION_PLAN.md vocabulary):** Prospective Validation — paper trading, 0/13 weekly rebalances logged

## What's done

- Phase 0: characterization tests, golden files, determinism proof, dependency
  lock, CI, repo standards — zero behavioral change to the six original
  scripts (`momentum_backtest.py`, `paper_trader.py`, `transaction_costs.py`,
  `fetch_universe.py`, `download_data.py`, `factor_attribution.py`).
- WP-000: `docs/` hierarchy reorganized, `quantos_core/` package skeleton,
  Technical Debt Register and Risk Register stood up.
- WP-001–005 (Phase 1, closed): strict typing gate, typed immutable AppConfig,
  `Repository[T]` + transactional SQLite, JSON-lines structured logging,
  enforced import-boundary matrix (ADR-032).
- WP-007 (Phase 2, opened): DataProvider ports, PIT universe store,
  fail-closed CSV price provider (ADR-033).
- WP-008 + review hardening: broker ports, Paper/Zerodha/Angel adapters,
  persisted kill switch, gated ExecutionEngine + order journal (ADR-034);
  UNKNOWN-state error taxonomy, fail-closed price paths.
- WP-009 (Phase 3, opened): Momentum v1.0 behind the Strategy port,
  byte-equal parity with the frozen script, params in
  `strategies_registry/momentum_v1.yaml` (ADR-015).
- WP-010: static read-only operator console + kill-switch CLI (ADR-035).
- Ops: unattended daily runner + Windows scheduled task, weekdays 15:40
  (`tools/daily_run.ps1`).
- WP-011: QuantOS Desktop — local FastAPI on 127.0.0.1:8742 + Edge app
  window; broker connect flows, dashboard, kill-switch UI (ADR-036).

- WP-012 (2026-07-15, ADR-037): portfolio accounting core — immutable
  `PortfolioState`, pure T+1 fill/queue transitions with the audit
  invariants as spec, shared CostModel port (rates bit-identical to the
  frozen cost script).
- WP-013 (2026-07-15, ADR-038): `paper.run_cycle(as_of) -> CycleReport`
  over injected snapshots + the shadow harness
  (`tools/run_paper_cycle.py`, daily via `daily_run.ps1`) comparing the
  new cycle's books to `data/paper_state.json` every day.
- WP-014 (2026-07-21, ADR-039): operational safety net — webhook alert
  on any non-clean daily run (`QUANTOS_ALERT_URL`), dated daily state
  backups with 30-day rotation (`QUANTOS_BACKUP_DIR`, default
  `D:\QuantOS_Backups`), and a "QuantOS Daily Watchdog" scheduled task
  (weekdays 16:30) that alerts when the daily run never started.
  Institutional due-diligence report filed
  (`docs/01_audits/`, 2026-07-21); TD-017/TD-018 recorded.

## In progress / next

- Prospective validation: accumulate 13 clean weekly rebalances
  (gate review 2026-09-09). `paper_trader.py` remains the system of
  record; cutover to `paper.run_cycle` after two consecutive clean
  weekly rebalances match in shadow (first candidate: 2026-07-17).
- WP-006 (layered configuration) — reserved, not built.
- Phase 6 after cutover: engine-mediated paper fills, write-ahead
  journaling (TD-013a), reconciliation.

## Tracking

- Per-work-package reports: `docs/00_governance/Program Status Reports/`
- Open risks: `docs/00_governance/Risk Register.md`
- Known debt: `docs/00_governance/Technical Debt Register.md`
- ADRs: `docs/adr/` (031+) and Constitution Part VI (001–030)
