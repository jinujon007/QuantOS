---
type: adr
number: 037
date: 2026-07-15
status: accepted
supersedes: none
---

# ADR-037 — Portfolio Module: T+1 Accounting Core + Shared CostModel (WP-012)

## Decision

`quantos_core/portfolio` is implemented as a **pure accounting core**
(ADR-006: functional core, imperative shell) whose semantics are the
frozen paper-trading loop's, hardened by the 2026-07-14 audit:

- **`PortfolioState`** — an `Entity` aggregate (immutable, strict):
  cash, positions (`{ticker: Position}`), the pending T+1 order queue,
  `start_date` / `last_updated` / `last_rebalance_date`. Persisted via
  the existing `Repository[T]` port; storage outage = fail loud, never
  allocate against guessed state (Blueprint module 05, failure clause).
- **Pure transition functions** in `accounting.py`, each returning a
  NEW state (no mutation, no I/O, no clock reads — every date is a
  parameter): `fill_pending`, `queue_stop_losses`, `queue_cash_exit`,
  `queue_rebalance`, `total_value`.
- **The audit-hardened queue invariants are the spec**, encoded in
  code and pinned by tests: an order fills only on a price bar NEWER
  than its `queued_on` (same-day/holiday fills are look-ahead); one
  live order per ticker (duplicate SELL double-credits, duplicate BUY
  double-debits); a SELL without a matching position is dropped, never
  credited; an unaffordable BUY is dropped (backtest semantics), never
  left pending at a stale allocation.
- **`CostModel` port (ADR-016)** lives here (`portfolio/costs.py`) with
  the single concrete `ZerodhaDeliveryCostModel`. Its rates are built
  from the same primitive charges by the same expressions as the frozen
  `transaction_costs.py`, so the derived floats are bit-identical —
  asserted by a parity test that imports the frozen script (tests may;
  core may not, ADR-032). A second CostModel implementation is a
  review-blocking finding (Constitution).

## Context

WP-012 was set as build priority by the 2026-07-14 operator interview
(portfolio → run_cycle → scheduler hardening). The 2026-07-14 program
audit found the validation record's book-keeping lived in one legacy
script with five silent-corruption paths; the fixes were applied there,
but the typed core still had **no notion of a portfolio at all** —
`quantos_core` could sign and gate orders it had no books for.

Placement of `CostModel`: the Blueprint names portfolio/execution as
its home. ADR-032 forbids portfolio↔execution imports in either
direction, so it must live in exactly one. Portfolio is the consumer
that exists today (fill accounting); execution's future use (Phase 6
fill-cost reconciliation) can take the model as an injected dependency
without importing this module's internals.

## Alternatives Considered

- **Multi-strategy `allocate(signals, state) -> OrderIntent[]` now**
  (Blueprint module 05's full interface). Rejected for this WP: exactly
  one strategy exists; the cross-strategy book is Phase 5. The pending
  queue + equal-weight sizing is the whole of today's real behavior.
  The full allocator can wrap this accounting core later without
  rewriting it.
- **Mutable state objects** (simpler in-place updates). Rejected:
  the frozen/dumped/revalidated Entity pattern is what makes crash
  recovery and the shadow comparison (ADR-038) trustworthy.
- **Reusing broker `OrderReceipt`/`LimitOrder` types for the queue.**
  Rejected: the T+1 paper queue is allocation-based (₹ per ticker,
  shares determined at fill), not quantity-based limit orders; forcing
  one type onto both would misrepresent both. Phase 6 maps queue
  entries to `LimitOrder`s at the boundary.

## Consequences

- The paper cycle (ADR-038) composes these functions instead of
  reimplementing book-keeping; the live cycle will compose the same
  ones (ADR-010).
- Costs parity is now mechanically pinned; if Zerodha changes charges,
  the frozen script and the model must change together or the parity
  test fails.
- `portfolio` imports only `strategies` (TargetWeights), `storage`
  (Entity), `utils` — within its frozen ADR-032 cell.
