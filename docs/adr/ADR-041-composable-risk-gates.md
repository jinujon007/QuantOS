---
type: adr
number: 041
date: 2026-07-21
status: accepted
supersedes: none
---

# ADR-041 — Part V Controls Land Incrementally as Composable Gates (WP-016)

## Decision

The Phase 4 risk engine is built as **small, single-control gate classes
composed by `CompositeGate`** (first breach blocks), not one monolithic
risk checker. WP-016 ships the first control — `PositionLimitGate`
(single-name exposure ≤ `limit_pct` of NAV, Part V default 15%) — plus
the composition mechanism. Sector exposure, cross-strategy aggregation,
drawdown flags, circuit breakers, liquidity and the SEBI Algo-ID gate
each arrive as further gates in the same stack when their data
dependencies exist.

Two supporting rules:

1. **Thresholds are injected at the composition root** (constructor
   parameters), because the layered config system is WP-006 (reserved).
   The injected value is the Part V policy default; when WP-006 lands,
   the composition root reads it from config instead — gate code
   unchanged. Changing a threshold still requires an ADR (ADR-025).
2. **`risk` sees books and orders structurally** (`BookView`,
   `OrderLike` Protocols): the ADR-032 matrix forbids risk→portfolio
   and risk→brokers imports, so the composition root adapts concrete
   types. Same precedent as gate.py's untyped order parameter.
3. **SELLs are never blocked by exposure limits** — an exit reduces the
   exposure the limit bounds; blocking it would deepen a breach.
   (Kill-switch and future compliance gates still block everything.)
4. **An empty composite is a construction error** — a gate stack with
   zero controls silently allows everything, which is wiring, not
   configuration.

## Context

Phase 4's exit criterion needs the pre-trade gate to demonstrably block
a constructed breach. WP-008 built the seam (`PreTradeGate` protocol,
engine requires a gate at construction); until now the only control was
the kill switch. Of the Part V table, only the single-name position
limit is implementable today without new data (sector maps, ADV,
intraday NAV, equity history are future dependencies) — so the honest
slice is one real control plus the composition pattern that makes the
rest additive.

## Alternatives Considered

- **One `RiskEngine` class evaluating the whole Part V table.**
  Rejected: forces stubs for controls whose data doesn't exist
  (banned: no placeholder implementations), and every new control
  would edit tested code instead of adding a file.
- **Waiting for Phase 4 proper.** Rejected: the composition mechanism
  is what later controls plug into; landing it with the first real
  control de-risks the phase the same way ADR-034 de-risked brokers.
- **Passing `PortfolioState` into risk directly.** Rejected: violates
  the ADR-032 matrix; structural `BookView` keeps the dependency
  arrow pointing the right way.

## Consequences

- `ExecutionEngine` callers swap `KillSwitchGate(...)` for
  `CompositeGate([KillSwitchGate(...), PositionLimitGate(...)])` —
  demo updated, engine untouched.
- The paper daily cycle (ADR-038) is deliberately NOT wired through
  these gates: it doesn't route orders through the engine until the
  Phase 6 cutover step, and its T+1 queue semantics are frozen with
  the validation clock. Gates apply to every engine-mediated order —
  which is the only path live capital will ever use (ADR-010).
- Phase 4 exit criterion ("kill switch demonstrably blocks an order in
  an integration test") now has a sibling: the position limit blocks a
  constructed breach in `test_risk_limits.py` and journals BLOCKED
  through the real engine.
