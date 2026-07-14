"""Execution engine: order lifecycle from gated intent to journaled
broker receipt.

WP-008 (ADR-034 demo vertical slice): ExecutionEngine places CNC limit
orders through any OrderPlacer with a mandatory injected PreTradeGate
(no gate, no engine) and journals every attempt -- filled, open,
rejected, blocked -- through storage. Phase 6 hardens this into the
full order lifecycle (reconciliation, slippage metrics, SAFE_MODE).
Depends on brokers/storage/utils/monitoring only (ADR-032).
"""

from quantos_core.execution.engine import (
    ExecutionBlockedError,
    ExecutionEngine,
    OrderJournalEntry,
    PreTradeGate,
)

__all__ = [
    "ExecutionBlockedError",
    "ExecutionEngine",
    "OrderJournalEntry",
    "PreTradeGate",
]
