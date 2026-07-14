"""Broker-facing order domain types and typed errors (WP-008).

Limit orders only: the SEBI/NSE retail-algo framework (in force
2026-04-01) prohibits plain market orders for API flow, so the type
system simply does not offer one -- a market order is unrepresentable
rather than merely discouraged.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

NSE_TICK = 0.05  # legacy flat grid; still correct for the >= Rs250 band


def nse_tick_size(price: float) -> float:
    """NSE equity tick by price band (reform effective 2024-06-10):
    Rs0.01 below Rs250, Rs0.05 at or above. The old flat 5-paise
    assumption floors sub-Rs25 limit prices below market, where a buy
    rests unfilled forever."""
    if price <= 0:
        raise ValueError(f"No tick size for non-positive price {price}")
    return 0.01 if price < 250.0 else 0.05


def to_tick(price: float, tick: float | None = None) -> float:
    """Round a price DOWN to the exchange tick grid (band-aware by default).

    NSE rejects limit prices off the tick grid; rounding down is the
    conservative direction for sells (only concedes one tick). Raises on
    non-positive input rather than returning a zero price.
    """
    if price <= 0:
        raise ValueError(f"Cannot tick-round non-positive price {price}")
    t = nse_tick_size(price) if tick is None else tick
    ticks = int(round(price / t, 6))  # 6dp guard against float dust before flooring
    if ticks * t > price + 1e-9:
        ticks -= 1
    return round(max(ticks, 1) * t, 2)


def to_tick_up(price: float, tick: float | None = None) -> float:
    """Round a price UP to the exchange tick grid (band-aware by default).

    The right direction for BUY limits: flooring a buy limit can land it
    BELOW the market price, where it can never fill -- silently excluding
    the ticker from the portfolio. Ceiling concedes at most one tick.
    """
    if price <= 0:
        raise ValueError(f"Cannot tick-round non-positive price {price}")
    t = nse_tick_size(price) if tick is None else tick
    ticks = int(round(price / t, 6))
    if ticks * t < price - 1e-9:
        ticks += 1
    return round(max(ticks, 1) * t, 2)


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
