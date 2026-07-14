"""Broker-facing order domain types and typed errors (WP-008).

Limit orders only: the SEBI/NSE retail-algo framework (in force
2026-04-01) prohibits plain market orders for API flow, so the type
system simply does not offer one -- a market order is unrepresentable
rather than merely discouraged.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, PositiveInt


class BrokerError(Exception):
    """Base for every broker failure. Fail-closed: an ambiguous broker
    state is an exception, never a guessed order status."""


class BrokerAuthError(BrokerError):
    """Login/session/token failure -- distinct so callers can attempt
    re-auth instead of treating it as an order rejection."""


class BrokerConnectionError(BrokerError):
    """Network/transport failure. The order state is UNKNOWN to the
    caller -- reconciliation required before that ticker trades again
    (Constitution Part V); never assume filled or cancelled."""


class OrderRejectedError(BrokerError):
    """The broker actively rejected the order (margin, circuit, RMS)."""


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class LimitOrder(BaseModel):
    """One CNC delivery limit order. Immutable, strict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticker: str  # NSE trading symbol, no suffix (e.g. "RELIANCE")
    side: OrderSide
    quantity: PositiveInt
    limit_price: float
    product: Literal["CNC"] = "CNC"


class OrderReceipt(BaseModel):
    """What a broker acknowledged about one placed order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_order_id: str
    status: Literal["FILLED", "OPEN", "REJECTED"]
    filled_quantity: int
    average_price: float | None
