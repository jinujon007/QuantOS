---
type: work-package
id: WP-012
date: 2026-07-15
status: complete
phase: Phase 5 slice (ADR-037; operator interview 2026-07-14 build priority)
---

# WP-012 — Portfolio Accounting Core + Shared CostModel

## Objective

Give the typed core the books it never had: positions, cash, and the
T+1 pending-order queue behind immutable aggregates, with the audit-
hardened semantics of the legacy paper loop as pure, tested functions
(ADR-037). Home the ADR-016 CostModel port.

## Delivered

- **`quantos_core/portfolio/state.py`** — `Position`, `PendingOrder`
  (SELL carries shares, BUY carries a rupee allocation — validated),
  `PortfolioState(Entity)` (cash, positions, pending queue,
  start/last-updated/last-rebalance dates). Persists through the
  existing `Repository[T]` port; round-trip pinned by test.
- **`quantos_core/portfolio/accounting.py`** — pure transitions,
  each returning a NEW state: `fill_pending` (new-bar-only fills,
  orphan-SELL / duplicate-BUY / unaffordable-BUY dropped with reasons,
  unpriceable orders held), `queue_stop_losses`, `queue_cash_exit`,
  `queue_rebalance` (weight × portfolio value sizing, held targets
  untouched), `total_value` (entry-price fallback, frozen convention).
  One live order per ticker enforced at the queue, deterministic
  (sorted) queue order (ADR-019).
- **`quantos_core/portfolio/costs.py`** — `CostModel` Protocol +
  `ZerodhaDeliveryCostModel`, rates built by the same expressions as
  the frozen `transaction_costs.py`.

## Verification

- **Cost parity:** `buy_rate`/`sell_rate`/`dp_per_scrip` asserted
  **bit-identical** (`==`, not approx) to the frozen script's
  constants.
- **Behavior parity:** five fill scenarios (T+1 sell, T+1 buy,
  unaffordable buy, orphan sell, duplicate buy) run through BOTH
  `paper_trader.fill_pending_orders` and `fill_pending` on identical
  inputs — cash, positions, entry prices, and queue depth equal.
- 17 new tests; full suite 233 passing; `mypy --strict` clean;
  import-boundary gate green (portfolio cell: strategies, storage,
  utils — as frozen in ADR-032).

## Scope notes

Cross-strategy `allocate(signals, state)` (Blueprint module 05's full
interface) is deliberately NOT built — one strategy exists; the
allocator composes this core in Phase 5. See ADR-037 alternatives.
