"""Pure T+1 accounting transitions (WP-012, ADR-037).

The semantics here ARE the audited paper-trading loop's -- fills at the
next session's close with the delivery cost model, one live order per
ticker, fail-toward-doing-nothing on every ambiguity. No I/O, no clock
reads, no mutation: every function takes state + market facts and
returns a new state plus a record of what happened.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from quantos_core.portfolio.costs import CostModel
from quantos_core.portfolio.state import PendingOrder, PortfolioState, Position
from quantos_core.strategies import TargetWeights


@dataclass(frozen=True)
class Fill:
    """One executed order -- the trade-log record."""

    side: str
    ticker: str
    price: float
    shares: float
    value: float
    reason: str


@dataclass(frozen=True)
class FillOutcome:
    state: PortfolioState
    fills: tuple[Fill, ...] = ()
    dropped: tuple[str, ...] = ()  # human-readable reasons, for the report


@dataclass(frozen=True)
class QueueOutcome:
    state: PortfolioState
    queued: tuple[str, ...] = field(default_factory=tuple)  # "SELL TICKER (reason)" entries


def total_value(state: PortfolioState, prices: Mapping[str, float]) -> float:
    """Cash + positions at the given prices; a missing price falls back
    to entry price (the frozen loop's convention -- stale, but never a
    crash or a zero)."""
    position_value = sum(pos.shares * prices.get(ticker, pos.entry_price) for ticker, pos in state.positions.items())
    return state.cash + position_value


def fill_pending(
    state: PortfolioState,
    latest_close: Mapping[str, float],
    bar_date: str,
    costs: CostModel,
) -> FillOutcome:
    """Execute the T+1 queue against the newest price bar.

    Invariants (each one was a live corruption path in the 2026-07-14
    audit until fixed; here they are structural):
    - an order fills only on a bar strictly NEWER than its queued_on --
      a same-day re-run or a holiday's forward-filled close is the
      look-ahead the queue exists to prevent;
    - a SELL without a matching position is dropped, never credited;
    - a BUY for a ticker already held is dropped, never double-debited;
    - an unaffordable BUY is dropped (backtest semantics), never left
      pending at a stale allocation;
    - an unpriceable order stays queued for the next session.
    """
    if not state.pending:
        return FillOutcome(state=state)

    cash = state.cash
    positions = dict(state.positions)
    still_pending: list[PendingOrder] = []
    fills: list[Fill] = []
    dropped: list[str] = []

    for order in state.pending:
        if bar_date <= order.queued_on:
            still_pending.append(order)  # no new bar since queue -- hold
            continue
        price = latest_close.get(order.ticker)
        if price is None or price <= 0:
            still_pending.append(order)  # retry next session
            continue

        if order.side == "SELL":
            position = positions.pop(order.ticker, None)
            if position is None:
                dropped.append(f"SELL {order.ticker}: no matching position")
                continue
            shares = order.shares if order.shares is not None else position.shares
            value = shares * price
            cash += value * (1 - costs.sell_rate) - costs.dp_per_scrip
            fills.append(
                Fill(side="SELL", ticker=order.ticker, price=price, shares=shares, value=value, reason=order.reason)
            )
        else:  # BUY
            if order.ticker in positions:
                dropped.append(f"BUY {order.ticker}: already held")
                continue
            allocation = order.allocation if order.allocation is not None else 0.0
            cost = allocation * (1 + costs.buy_rate)
            if cash < cost:
                dropped.append(f"BUY {order.ticker}: insufficient cash ({cash:.2f} < {cost:.2f})")
                continue
            shares = allocation / price
            cash -= cost
            positions[order.ticker] = Position(shares=shares, entry_price=price)
            fills.append(
                Fill(side="BUY", ticker=order.ticker, price=price, shares=shares, value=allocation, reason=order.reason)
            )

    new_state = state.model_copy(update={"cash": cash, "positions": positions, "pending": still_pending})
    return FillOutcome(state=new_state, fills=tuple(fills), dropped=tuple(dropped))


def _queue_sells(state: PortfolioState, tickers: list[str], reason: str, today: str) -> QueueOutcome:
    queued_tickers = state.queued_tickers()
    pending = list(state.pending)
    queued: list[str] = []
    for ticker in sorted(tickers):  # sorted: deterministic queue order (ADR-019)
        if ticker in queued_tickers or ticker not in state.positions:
            continue
        pending.append(
            PendingOrder(
                side="SELL",
                ticker=ticker,
                shares=state.positions[ticker].shares,
                reason=reason,
                queued_on=today,
            )
        )
        queued_tickers.add(ticker)
        queued.append(f"SELL {ticker} ({reason})")
    return QueueOutcome(state=state.model_copy(update={"pending": pending}), queued=tuple(queued))


def queue_stop_losses(
    state: PortfolioState,
    prices: Mapping[str, float],
    stop_loss_pct: float,
    today: str,
) -> QueueOutcome:
    """Queue an exit for every position at or below its stop. A missing
    price queues nothing for that ticker (unmonitored, the caller's
    degraded-run signal covers it)."""
    triggered = [
        ticker
        for ticker, pos in state.positions.items()
        if (price := prices.get(ticker)) is not None and price <= pos.entry_price * (1 - stop_loss_pct)
    ]
    return _queue_sells(state, triggered, "stop_loss", today)


def queue_cash_exit(state: PortfolioState, today: str) -> QueueOutcome:
    """Bear regime: queue full liquidation. Callers must only invoke
    this on a CONFIRMED bear -- an unknown regime must never liquidate."""
    return _queue_sells(state, list(state.positions), "bear_market_exit", today)


def queue_rebalance(
    state: PortfolioState,
    target: TargetWeights,
    portfolio_value: float,
    today: str,
) -> QueueOutcome:
    """Queue the trades that move the book toward the target weights:
    exits for held tickers not in the target, entries (rupee allocation
    = weight x portfolio value) for target tickers not held."""
    if target.stance != "rebalance":
        raise ValueError(f"queue_rebalance requires stance 'rebalance', got {target.stance!r}")

    target_tickers = set(target.weights)
    exits = _queue_sells(state, [t for t in state.positions if t not in target_tickers], "rebalance_exit", today)

    queued_tickers = exits.state.queued_tickers()
    pending = list(exits.state.pending)
    queued = list(exits.queued)
    for ticker in sorted(target_tickers):
        if ticker in exits.state.positions or ticker in queued_tickers:
            continue
        allocation = portfolio_value * target.weights[ticker]
        pending.append(
            PendingOrder(side="BUY", ticker=ticker, allocation=allocation, reason="rebalance_entry", queued_on=today)
        )
        queued.append(f"BUY {ticker} (rebalance_entry {allocation:.0f})")
    return QueueOutcome(state=exits.state.model_copy(update={"pending": pending}), queued=tuple(queued))
