---
type: work-package
id: WP-009
date: 2026-07-14
status: complete
phase: 3 (opening)
---

# WP-009 — Strategy Platform: Momentum v1.0 Behind the Port, Parity-Proven

## Objective

Make the system genuinely work end to end: the VALIDATED strategy —
not an approximation — driving the new pipeline. Opens Phase 3 with
the `Strategy` port and a verbatim (ADR-003) port of the frozen
momentum signal math, with signal parity proven mechanically, not
asserted.

## Delivered

**`quantos_core/factors`** (pure, zero I/O — ADR-006):
- `momentum_12m1m` — verbatim port of `momentum_backtest.momentum_score`
  (identical pandas ops in identical order; constants → injected params).
- `uptrend_series` / `is_uptrend` — verbatim port of the regime
  construction and the as-of lookup (including the frozen permissive
  True-before-data default, preserved not re-decided).

**`quantos_core/strategies`**:
- `Strategy` Protocol per the Constitution's frozen contract
  (`generate_signals(ctx) -> TargetWeights`, `metadata()`).
- `StrategyContext` (a strategy cannot fetch or define its own data —
  Part II item 5), `TargetWeights` with an explicit three-way stance
  (`rebalance` / `cash` / `hold`) mirroring the frozen script's three
  behaviors, weight invariants enforced, immutable.
- `MomentumV1` — zero numeric literals; all parameters from the
  registry.
- Registry loader: YAML → schema-validated `MomentumParams`
  (fail-closed, extra keys forbidden, typed `StrategyRegistryError`).

**`strategies_registry/momentum_v1.yaml`** — ADR-015 single source of
truth: top_n 10, lookback 12, skip 1, min_observations 75, stop-loss
0.08, MA 100, version "1.0", with the restart-the-clock warning inline.

**Parity suite** (`test_strategy_parity.py`, 16 cases, real cache, no
network): momentum scores **byte-equal** (`Series.equals`) to the
frozen script on 6 real rebalance Fridays spanning 2019–2024; top-10
selection identical; regime series and as-of lookup identical;
registry params equal to the frozen constants (incl.
`MIN_TRADING_DAYS // 2`); known regime states pinned (2024-12-27 bear,
2024-09-27 bull).

**Demo rewired** to the real strategy: replays a bear week (stance
CASH — refuses to trade) and a bull week (real top-10: TARIL,
COCHINSHIP, IFCI, GVT&D, WOCKPHARMA, RVNL, INOXWIND, GALLANTT, HUDCO,
OIL — 10 fills through the gated engine, kill-switch drill blocked,
all journaled). Ran clean end to end this WP.

## Freeze impact: none

This is a port with mechanically proven signal parity, not a strategy
change. `paper_trader.py` remains the running system of record; the
six frozen scripts have zero diffs; the Prospective Validation clock
continues uninterrupted. The registry pins the same values the freeze
protects — editing it restarts the clock by constitutional definition,
and the file says so.

## Dependencies

`pyyaml==6.0.3` added (runtime) — mandated by ADR-015's YAML registry;
already in the venv, pinned in `pyproject.toml` +
`requirements-lock.txt` (one-line insert; TD-011's broken editable
install not triggered — no resolver run needed for a leaf package
already present).

## Validation

| Gate | Result |
|---|---|
| `ruff check` / `format --check` | Clean (one import-sort fix during WP) |
| `mypy --strict -p quantos_core` | Success — **39** source files (was 34) |
| `pytest -m "not network"` | **174 passed** (32 new: 16 parity + 16 unit) |
| Coverage `quantos_core/*` | **100%** (596 stmts, 0 miss) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; baseline sha unchanged |
| Six frozen scripts | `git diff` empty |
| Demo | End-to-end pass with the real strategy, both regimes shown |

## Out of Scope (later Phase 3+ WPs)

Stop-loss and position-carry logic (portfolio module — the port here
covers signal generation, the Strategy port's exact contract); the
other 16 sibling-suite strategies; walk-forward/purged-CV integration
(Phase 5); swapping paper_trader.py's execution path (Phase 6).

## Next

Portfolio module slice: target-weights → orders diffing with
stop-loss carry (completes the weekly cycle against the engine), then
Phase 6 wiring of `run_cycle(as_of)` per ADR-010.
