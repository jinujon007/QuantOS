"""Broker-facing order domain types and typed errors (WP-008).

Limit orders only: the SEBI/NSE retail-algo framework (in force
2026-04-01) prohibits plain market orders for API flow, so the type
system simply does not offer one -- a market order is unrepresentable
rather than merely discouraged.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

NSE_TICK = 0.05


def to_tick(price: float, tick: float = NSE_TICK) -> float:
    """Round a price DOWN to the exchange tick grid.

    NSE rejects limit prices off the tick grid; rounding down is the
    conservative direction for buys (never pay above intent) and for
    the seller it only concedes one tick. Raises on non-positive input
    rather than returning a zero price.
    """
    if price <= 0:
        raise ValueError(f"Cannot tick-round non-positive price {price}")
    ticks = int(round(price / tick, 6))  # 6dp guard against float dust before flooring
    if ticks * tick > price + 1e-9:
        ticks -= 1
    return round(max(ticks, 1) * tick, 2)


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

    ticker: str = Field(min_length=1)  # NSE trading symbol, no suffix (e.g. "RELIANCE")
    side: OrderSide
    quantity: PositiveInt
    limit_price: float = Field(gt=0)
    product: Literal["CNC"] = "CNC"


class OrderReceipt(BaseModel):
    """What a broker acknowledged about one placed order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_order_id: str
    status: Literal["FILLED", "OPEN", "REJECTED"]
    filled_quantity: int
    average_price: float | None
