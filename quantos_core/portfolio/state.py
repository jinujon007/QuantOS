"""Portfolio aggregate: positions, cash, and the T+1 pending-order
queue (WP-012, ADR-037).

Everything is immutable (Entity rigor); transitions live in
``accounting.py`` and return new states. Dates are ISO strings because
they are compared lexicographically against price-bar dates, exactly
as the audited paper loop does.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quantos_core.storage import Entity


class Position(BaseModel):
    """One open holding. Fractional shares are intentional -- the paper
    account sizes by allocation/price, matching the backtest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shares: float = Field(gt=0)
    entry_price: float = Field(gt=0)


class PendingOrder(BaseModel):
    """One queued T+1 order. SELLs carry the share count captured at
    queue time; BUYs carry a rupee allocation (shares are determined by
    the fill price, ADR-037)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    side: Literal["BUY", "SELL"]
    ticker: str = Field(min_length=1)
    shares: float | None = Field(default=None, gt=0)
    allocation: float | None = Field(default=None, gt=0)
    reason: str
    queued_on: str  # ISO date -- fills require a strictly newer bar

    @model_validator(mode="after")
    def _side_carries_the_right_quantity(self) -> "PendingOrder":
        if self.side == "SELL" and (self.shares is None or self.allocation is not None):
            raise ValueError("SELL orders carry shares, not an allocation")
        if self.side == "BUY" and (self.allocation is None or self.shares is not None):
            raise ValueError("BUY orders carry an allocation, not shares")
        return self


class PortfolioState(Entity):
    """The paper account book: the aggregate the validation record
    lives in. One instance per account (id = account name)."""

    cash: float = Field(ge=0)
    positions: dict[str, Position] = Field(default_factory=dict)
    pending: list[PendingOrder] = Field(default_factory=list)
    start_date: str
    last_updated: str = ""
    last_rebalance_date: str = ""

    def queued_tickers(self) -> set[str]:
        """Tickers with a live pending order -- queueing one of these
        again would create the duplicate-order book corruption the
        2026-07-14 audit found."""
        return {order.ticker for order in self.pending}
