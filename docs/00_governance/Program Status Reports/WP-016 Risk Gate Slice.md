---
type: report
work_package: WP-016
date: 2026-07-21
status: complete
adr: ADR-041
---

# WP-016 — Phase 4 Slice: Position Limit + Composable Gates

## What was built

- `quantos_core/risk/limits.py`: `check_position_limit` (pure math,
  exactly-at-limit allowed, ambiguity blocks), `PositionLimitGate`
  (BUYs capped at `limit_pct` of NAV; SELLs never blocked — exits
  reduce the exposure the limit bounds; unreadable book = typed
  fail-closed block), `CompositeGate` (first breach blocks; empty
  stack refused at construction), `BookView`/`OrderLike`/`Checkable`
  structural protocols keeping risk's ADR-032 cell clean (no
  portfolio/brokers imports).
- `tools/demo_pipeline.py`: engine now runs behind
  `CompositeGate([KillSwitchGate, PositionLimitGate(PaperBook, 0.15)])`
  with a live `BookView` over the paper broker; new section 7b drills
  an oversized (~20% NAV) order — BLOCKED and journaled.
- 16 new tests (`tests/quantos_core/test_risk_limits.py`): pure-math
  boundaries, SELL pass-through, fail-closed on broken book, composite
  ordering/empty-stack refusal, and an engine integration test proving
  a limit breach journals as BLOCKED without the broker ever seeing
  the order.

## Scope honesty

One real control, not the full Part V table: sector maps, ADV,
intraday NAV, and paper-equity history do not exist yet as data —
those gates arrive with their data dependencies, additively, in the
same composite (ADR-041). The paper daily cycle stays un-gated by
design: it does not route orders through the engine until Phase 6
cutover, and its semantics are frozen with the validation clock.

## Verification evidence

- 249 tests pass (233 prior + 16 new); import-boundary suite green
  (risk still imports only gate-internal + stdlib).
- `mypy --strict`: clean, 44 source files.
- ruff + format: clean.
- Demo end-to-end: 10 fills through the composed stack; kill-switch
  drill BLOCKED; position-limit drill BLOCKED
  (`TARIL projected exposure 29,918 exceeds 15% of NAV (15,000)`);
  journal rows `...-0011`/`...-0012` show both BLOCKED entries.

## Freeze compliance

No strategy, signal, paper-cycle, or state-file change. New code is
only reachable through `ExecutionEngine` callers (demo today, live
later per ADR-010).
