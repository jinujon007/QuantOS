"""Interface-segregated broker ports (WP-008, ADR-012).

Order placement and account reads are separate Protocols a concrete
adapter composes -- a data-only context is never forced to stub order
methods. Any adapter (Paper, Zerodha, Angel One, future Fyers) must be
substitutable with zero caller-side branching (ADR-011, Liskov).
"""

from typing import Protocol

from quantos_core.brokers.orders import LimitOrder, OrderReceipt


class OrderPlacer(Protocol):
    """Places CNC limit orders."""

    def place_order(self, order: LimitOrder) -> OrderReceipt:
        """Place one order.

        Raises BrokerAuthError / BrokerConnectionError /
        OrderRejectedError; never returns a guessed status.
        """
        ...


class AccountReader(Protocol):
    """Reads holdings and available cash."""

    def holdings(self) -> dict[str, int]:
        """Ticker -> quantity currently held (CNC)."""
        ...

    def available_cash(self) -> float:
        """Cash available for delivery buys."""
        ...
