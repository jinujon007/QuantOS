"""One paper-trading day as a single orchestrated cycle (WP-013,
ADR-038; Blueprint module 09: ``run_cycle(as_of) -> CycleReport``).

Every dependency is injected -- market data arrives as a value, state
through a store port, signals through the Strategy port -- so the cycle
itself is deterministic and testable to the exact edge cases the
2026-07-14 audit found in the legacy loop. ``live.run_cycle`` will be
this cycle with a different snapshot builder and fill path (ADR-010).

Order of operations is load-bearing:
kill switch -> same-day guard -> T+1 fills (persisted immediately) ->
stop-losses -> regime actions -> Friday/catch-up rebalance -> persist.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Protocol

import pandas as pd

from quantos_core.portfolio import (
    CostModel,
    Fill,
    PortfolioState,
    fill_pending,
    queue_cash_exit,
    queue_rebalance,
    queue_stop_losses,
    total_value,
)
from quantos_core.risk import KillSwitch
from quantos_core.strategies import Strategy, StrategyContext


class StateStore(Protocol):
    """Structural slice of Repository[PortfolioState] -- paper's frozen
    ADR-032 cell excludes storage, so the port is declared here and any
    repository satisfies it structurally."""

    def get(self, entity_id: str) -> PortfolioState: ...

    def save(self, entity: PortfolioState) -> None: ...


@dataclass(frozen=True)
class MarketSnapshot:
    """Everything the cycle may know about the market, supplied by the
    shell (Constitution Part II item 5: the domain never fetches).

    latest_close: newest close per ticker (holdings + pending).
    bar_date: ISO date of the newest price bar ("" when no prices came
      back -- nothing fills, orders wait).
    market_uptrend: True/False from the regime check, None = UNKNOWN
      (an outage must never read as a stance).
    prices: 14-month close matrix for signal generation; None when
      unavailable or below the universe-coverage floor.
    """

    latest_close: Mapping[str, float]
    bar_date: str
    market_uptrend: bool | None
    prices: "pd.DataFrame | None" = None


@dataclass(frozen=True)
class CycleReport:
    """What one cycle did -- the shell's journal/log record."""

    as_of: str
    status: Literal["OK", "DEGRADED", "HALTED", "ALREADY_RAN"]
    stance: str  # rebalance / cash / hold / none
    rebalanced: bool
    fills: tuple[Fill, ...]
    dropped: tuple[str, ...]
    queued: tuple[str, ...]
    degraded: tuple[str, ...]
    cash: float
    value: float
    positions: int
    pending: int


def _report(
    as_of: date,
    status: Literal["OK", "DEGRADED", "HALTED", "ALREADY_RAN"],
    state: PortfolioState | None,
    value: float = 0.0,
    stance: str = "none",
    rebalanced: bool = False,
    fills: tuple[Fill, ...] = (),
    dropped: tuple[str, ...] = (),
    queued: tuple[str, ...] = (),
    degraded: tuple[str, ...] = (),
) -> CycleReport:
    return CycleReport(
        as_of=as_of.isoformat(),
        status=status,
        stance=stance,
        rebalanced=rebalanced,
        fills=fills,
        dropped=dropped,
        queued=queued,
        degraded=degraded,
        cash=state.cash if state else 0.0,
        value=value,
        positions=len(state.positions) if state else 0,
        pending=len(state.pending) if state else 0,
    )


def run_cycle(
    as_of: date,
    *,
    store: StateStore,
    market: MarketSnapshot,
    strategy: Strategy,
    kill_switch: KillSwitch,
    stop_loss_pct: float,
    costs: CostModel,
    account_id: str = "paper",
) -> CycleReport:
    """Run one daily cycle. Raises on storage failure (fail loud, never
    trade against guessed state); every market ambiguity degrades toward
    doing nothing and is named in the report."""
    # 1. The halt control halts THIS loop -- is_engaged() is already
    #    fail-closed on unreadable state.
    if kill_switch.is_engaged():
        return _report(as_of, "HALTED", None)

    state = store.get(account_id)
    today = as_of.isoformat()

    # 2. Same-day idempotence: a second run would race state writes and
    #    re-decide on the same bar.
    if state.last_updated == today:
        return _report(as_of, "ALREADY_RAN", state, value=total_value(state, market.latest_close))

    degraded: list[str] = []

    # 3. T+1 fills, persisted before any slow signal work -- a crash
    #    after this point must never re-fill these orders.
    outcome = fill_pending(state, market.latest_close, market.bar_date, costs)
    state = outcome.state
    store.save(state)

    if state.positions and not market.latest_close:
        degraded.append("price fetch failed - stop-losses unmonitored this cycle")
    value = total_value(state, market.latest_close)

    # 4. Stop-losses (queued, fill next session).
    stops = queue_stop_losses(state, market.latest_close, stop_loss_pct, today)
    state = stops.state
    queued = list(stops.queued)

    # 5. Regime: liquidate only on a CONFIRMED bear; UNKNOWN acts on nothing.
    if market.market_uptrend is None:
        degraded.append("regime unknown - no regime actions this cycle")
    elif market.market_uptrend is False and state.positions:
        bear = queue_cash_exit(state, today)
        state = bear.state
        queued.extend(bear.queued)

    # 6. Weekly rebalance, with weekend catch-up for a missed Friday.
    last_friday = as_of - timedelta(days=(as_of.weekday() - 4) % 7)
    due = as_of.weekday() >= 4 and state.last_rebalance_date < last_friday.isoformat()
    stance = "none"
    rebalanced = False
    if due and market.market_uptrend is None:
        degraded.append("rebalance due but regime unknown - retry next run")
    elif due and market.market_uptrend is False:
        stance = "cash"  # deliberate bear skip; exits queued above; date consumed
        state = state.model_copy(update={"last_rebalance_date": last_friday.isoformat()})
    elif due:
        if market.prices is None:
            degraded.append("rebalance due but signals unavailable - retry next run")
        else:
            target = strategy.generate_signals(
                StrategyContext(as_of=pd.Timestamp(as_of), prices=market.prices, market_uptrend=True)
            )
            stance = target.stance
            if target.stance == "rebalance":
                rebalance = queue_rebalance(state, target, value, today)
                state = rebalance.state
                queued.extend(rebalance.queued)
                rebalanced = True
            # "hold" is a decision, not a failure -- the date is consumed.
            state = state.model_copy(update={"last_rebalance_date": last_friday.isoformat()})

    # 7. Persist the day.
    state = state.model_copy(update={"last_updated": today})
    store.save(state)

    return _report(
        as_of,
        "DEGRADED" if degraded else "OK",
        state,
        value=value,
        stance=stance,
        rebalanced=rebalanced,
        fills=outcome.fills,
        dropped=outcome.dropped,
        queued=tuple(queued),
        degraded=tuple(degraded),
    )
