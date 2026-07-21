"""Position-limit pre-trade gate + gate composition (WP-016 slice of
Phase 4, ADR-041).

First control from the Constitution's Part V table: single-name
exposure may not exceed ``limit_pct`` of book NAV. Pure math behind
structural types: risk's ADR-032 cell excludes ``portfolio`` and
``brokers``, so the live book arrives as a ``BookView`` protocol and
orders as an ``OrderLike`` — the composition root adapts the concrete
types (same pattern as gate.py's untyped order parameter).

Fail-closed per Part V (zero exceptions): an unreadable book, a
non-positive NAV, or a non-positive order valuation blocks the order
rather than guessing.
"""

from collections.abc import Sequence
from typing import Protocol

from quantos_core.risk.gate import RiskLimitBreach


class BookView(Protocol):
    """The minimum a limit check may know about the live book."""

    def nav(self) -> float:
        """Total book value (cash + positions), in rupees."""
        ...

    def exposure(self, ticker: str) -> float:
        """Current rupee value held in one ticker (0.0 when flat)."""
        ...


class OrderLike(Protocol):
    """Structural slice of brokers.LimitOrder (risk may not import it)."""

    @property
    def ticker(self) -> str: ...

    @property
    def quantity(self) -> int: ...

    @property
    def limit_price(self) -> float: ...

    @property
    def side(self) -> object: ...


class Checkable(Protocol):
    """Anything with the pre-trade gate contract: raise to block."""

    def check(self, order: OrderLike) -> None: ...


def check_position_limit(
    *,
    order_value: float,
    current_exposure: float,
    nav: float,
    limit_pct: float,
    ticker: str,
) -> None:
    """Pure single-name limit check: block when the post-fill exposure
    would exceed ``limit_pct`` of NAV. Exactly-at-limit is allowed
    (<=); ambiguous inputs (NAV or order value not positive) block."""
    if nav <= 0:
        raise RiskLimitBreach(f"Position limit cannot be evaluated: book NAV {nav:.2f} is not positive -- fail closed")
    if order_value <= 0:
        raise RiskLimitBreach(
            f"Position limit cannot be evaluated: order value {order_value:.2f} for {ticker} is not positive"
        )
    projected = current_exposure + order_value
    ceiling = nav * limit_pct
    if projected > ceiling:
        raise RiskLimitBreach(
            f"Position limit breach: {ticker} projected exposure {projected:,.0f} "
            f"exceeds {limit_pct:.0%} of NAV ({ceiling:,.0f})"
        )


class PositionLimitGate:
    """Blocks BUYs that would push one name past ``limit_pct`` of NAV.

    SELLs always pass -- they reduce the exposure this gate bounds, and
    blocking an exit on a limit breach would deepen the breach.
    Threshold is injected by the composition root (config-sourced per
    ADR-025; no layered config file exists until WP-006).
    """

    def __init__(self, book: BookView, limit_pct: float) -> None:
        if not 0 < limit_pct <= 1:
            raise ValueError(f"limit_pct must be in (0, 1], got {limit_pct}")
        self._book = book
        self._limit_pct = limit_pct

    def check(self, order: OrderLike) -> None:
        side = getattr(order.side, "value", order.side)
        if str(side) == "SELL":
            return
        try:
            nav = self._book.nav()
            exposure = self._book.exposure(order.ticker)
        except Exception as exc:
            # Typed re-raise, never a swallow (ADR-007): an unreadable
            # book is the Part V zero-exception fail-closed case.
            raise RiskLimitBreach(f"Position limit unevaluable: book unreadable ({exc}) -- fail closed") from exc
        check_position_limit(
            order_value=order.quantity * order.limit_price,
            current_exposure=exposure,
            nav=nav,
            limit_pct=self._limit_pct,
            ticker=order.ticker,
        )


class CompositeGate:
    """Runs every gate in order; the first breach blocks (raises).

    An empty stack is refused at construction -- a composed gate with
    zero controls would silently allow everything, which is a wiring
    bug, not a configuration."""

    def __init__(self, gates: Sequence[Checkable]) -> None:
        if not gates:
            raise ValueError("CompositeGate requires at least one gate -- an empty stack allows everything")
        self._gates = tuple(gates)

    def check(self, order: OrderLike) -> None:
        for gate in self._gates:
            gate.check(order)
