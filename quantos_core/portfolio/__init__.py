"""Portfolio accounting: the paper account's book of record behind
typed, immutable aggregates (WP-012, ADR-037).

This slice is the T+1 accounting core -- positions, cash, the pending
order queue, and the shared CostModel port (ADR-016). Semantics are the
audited paper-trading loop's, as pure functions. The full cross-strategy
allocator (Blueprint module 05, `allocate(signals, state)`) arrives with
Phase 5; it will compose this core, not replace it.

Imports only strategies/storage/utils internally (ADR-032).
"""

from quantos_core.portfolio.accounting import (
    Fill,
    FillOutcome,
    QueueOutcome,
    fill_pending,
    queue_cash_exit,
    queue_rebalance,
    queue_stop_losses,
    total_value,
)
from quantos_core.portfolio.costs import CostModel, ZerodhaDeliveryCostModel
from quantos_core.portfolio.state import PendingOrder, PortfolioState, Position

__all__ = [
    "CostModel",
    "Fill",
    "FillOutcome",
    "PendingOrder",
    "PortfolioState",
    "Position",
    "QueueOutcome",
    "ZerodhaDeliveryCostModel",
    "fill_pending",
    "queue_cash_exit",
    "queue_rebalance",
    "queue_stop_losses",
    "total_value",
]
