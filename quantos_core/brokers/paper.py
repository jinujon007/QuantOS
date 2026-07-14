"""PaperBrokerAdapter (WP-008) -- ADR-011 implementation #1.

Deterministic simulated fills against a supplied market-price map:
a buy fills only if limit >= market, a sell only if limit <= market
(both fill AT the market price -- you never pay worse than your
limit); otherwise the order rests OPEN. Cash and holdings are tracked
so overspend/oversell are real rejections, exactly the discipline live
adapters inherit (ADR-010: paper is a rehearsal of live, not a lower
bar).

ponytail: single-shot fills, no partial fills / order book / queue --
Phase 6's real order lifecycle upgrades this when slippage metrics
arrive.
"""

from collections.abc import Mapping
from itertools import count

from quantos_core.brokers.orders import LimitOrder, OrderReceipt, OrderRejectedError, OrderSide


class PaperBrokerAdapter:
    """Composes OrderPlacer + AccountReader against in-memory state."""

    def __init__(self, market_prices: Mapping[str, float], cash: float) -> None:
        if cash < 0:
            raise OrderRejectedError(f"Paper broker cannot start with negative cash ({cash})")
        self._prices = dict(market_prices)
        self._cash = cash
        self._holdings: dict[str, int] = {}
        self._ids = count(1)

    def place_order(self, order: LimitOrder) -> OrderReceipt:
        market = self._prices.get(order.ticker)
        if market is None:
            raise OrderRejectedError(f"No market price for {order.ticker!r} -- cannot simulate a fill")
        order_id = f"PAPER-{next(self._ids):06d}"

        if order.side is OrderSide.BUY:
            cost = market * order.quantity
            if order.limit_price < market:
                return OrderReceipt(broker_order_id=order_id, status="OPEN", filled_quantity=0, average_price=None)
            if cost > self._cash:
                raise OrderRejectedError(
                    f"Insufficient paper cash for {order.ticker}: need {cost:.2f}, have {self._cash:.2f}"
                )
            self._cash -= cost
            self._holdings[order.ticker] = self._holdings.get(order.ticker, 0) + order.quantity
        else:
            held = self._holdings.get(order.ticker, 0)
            if order.quantity > held:
                raise OrderRejectedError(f"Cannot sell {order.quantity} {order.ticker}: hold only {held}")
            if order.limit_price > market:
                return OrderReceipt(broker_order_id=order_id, status="OPEN", filled_quantity=0, average_price=None)
            self._cash += market * order.quantity
            remaining = held - order.quantity
            if remaining:
                self._holdings[order.ticker] = remaining
            else:
                del self._holdings[order.ticker]

        return OrderReceipt(
            broker_order_id=order_id, status="FILLED", filled_quantity=order.quantity, average_price=market
        )

    def holdings(self) -> dict[str, int]:
        return dict(self._holdings)

    def available_cash(self) -> float:
        return self._cash
