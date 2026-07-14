"""Broker integration: one segregated port set (ADR-012), many
adapters (ADR-011) -- Paper (#1), Zerodha Kite (#2), Angel One
SmartAPI (#3), all substitutable with zero caller-side branching.

WP-008 (ADR-034 demo vertical slice). Limit orders only by type
construction (SEBI/NSE algo rules). Real adapters refuse to construct
without credentials and never retry POSTs (UNKNOWN-state rule,
Constitution Part V). Depends on nothing else in quantos_core except
utils (ADR-032).
"""

from quantos_core.brokers.angel import AngelOneSmartApiAdapter
from quantos_core.brokers.orders import (
    BrokerAuthError,
    BrokerConnectionError,
    BrokerError,
    LimitOrder,
    OrderReceipt,
    OrderRejectedError,
    OrderSide,
)
from quantos_core.brokers.paper import PaperBrokerAdapter
from quantos_core.brokers.ports import AccountReader, OrderPlacer
from quantos_core.brokers.zerodha import ZerodhaKiteAdapter

__all__ = [
    "AccountReader",
    "AngelOneSmartApiAdapter",
    "BrokerAuthError",
    "BrokerConnectionError",
    "BrokerError",
    "LimitOrder",
    "OrderPlacer",
    "OrderReceipt",
    "OrderRejectedError",
    "OrderSide",
    "PaperBrokerAdapter",
    "ZerodhaKiteAdapter",
]
