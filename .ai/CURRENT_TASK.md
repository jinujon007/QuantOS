# Current Task

**Latest session 2026-07-22 — Phase 2 completed (WP-019/020/021,
ADR-045).** Full log: `docs/00_governance/(AI) Program Log -
2026-07-22.md`. Previous session (2026-07-21): DD audit +
WP-014..018 — see `(AI) Program Log - 2026-07-21.md`. All on branch
`docs/institutional-dd-2026-07-21` (PR #1, awaiting operator merge).

## Phase 2 close-out (2026-07-22)

- **WP-019 (ADR-045)**: corporate-action adjustment from NSE's
  official Bc records (PR bundle, same cookie-free archives host).
  BONUS/FVSPLT/FVCONS computed exactly; dividends price-neutral;
  rights/demergers deliberately halt via the quality band instead of
  being guessed. First design (UDiFF prev-close ratio) **disproven
  against the real archive** (HDFCBANK 1:1 bonus ex 2025-08-26
  published raw) and replaced same session — recorded in ADR-045.
- **WP-020 (ADR-045)**: `validate_close_frame` fail-closed quality
  gate — exact XBOM calendar coverage, dense positive closes, ±35%
  single-session band (tunable). `DataQualityError(DataFetchError)`.
- **WP-021 (ADR-045)**: `BhavcopyPriceProvider` — adjusted, validated
  closes from `data/bhavcopy/` + `data/nse_pr/` behind the frozen
  `PriceProvider` port; archive gaps and uncomputable-action quality
  failures name their cause. Two-file range-mode backfill in
  `tools/fetch_bhavcopy.py`; archives cover 2025-06-02 → present
  (~200 MB, gitignored, regenerable). Live-verified across the
  HDFCBANK bonus. Adversarial review: 7 findings fixed + test-pinned (ADR-045 hardening section); known halt: TVSMOTOR NCRPS bonus ex 2025-08-25 (uncomputable, operator item). 341 tests.
- **Remaining for Phase 6 cutover (named in ADR-045):** indices
  (regime) adapter; shadow-harness quantification of the
  price-return vs total-return divergence.

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

**Phase 2 is code-complete** (accepted limits: no pre-2026 PIT
universe history; price-return series; indices adapter deferred to
Phase 6 cutover prerequisites). Recommended next: Phase 3
continuation (migrate the next strategies from the sibling suite onto
the `Strategy` port) or Phase 4 risk-engine expansion (sector
exposure gate, drawdown monitor per Constitution Part V). WP-006
(layered configuration) remains reserved. Remaining open debt is
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
