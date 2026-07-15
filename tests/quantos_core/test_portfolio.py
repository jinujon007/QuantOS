"""Portfolio accounting tests (WP-012, ADR-037).

Three layers:
1. Cost parity -- ZerodhaDeliveryCostModel's derived rates must be
   bit-identical to the frozen transaction_costs.py (the validation
   record's arithmetic).
2. Behavior parity -- fill_pending must produce the same cash/holdings
   as paper_trader.fill_pending_orders on identical scenarios (the six
   audited invariants).
3. State/queue semantics -- immutability, dedup, stop-loss boundary,
   rebalance sizing, repository round-trip.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import paper_trader  # noqa: E402  (frozen script; tests may import it, core may not)
import transaction_costs as frozen_costs  # noqa: E402
from quantos_core.portfolio import (  # noqa: E402
    PendingOrder,
    PortfolioState,
    Position,
    ZerodhaDeliveryCostModel,
    fill_pending,
    queue_cash_exit,
    queue_rebalance,
    queue_stop_losses,
    total_value,
)
from quantos_core.storage import SqliteRepository  # noqa: E402
from quantos_core.strategies import TargetWeights  # noqa: E402

COSTS = ZerodhaDeliveryCostModel()


def make_state(**overrides: object) -> PortfolioState:
    defaults: dict = {"id": "paper", "cash": 100_000.0, "start_date": "2026-06-09"}
    defaults.update(overrides)
    return PortfolioState(**defaults)


# ── 1. cost parity with the frozen script ─────────────────────────────────


def test_cost_rates_bit_identical_to_frozen_script() -> None:
    assert COSTS.buy_rate == frozen_costs.BUY_RATE
    assert COSTS.sell_rate == frozen_costs.SELL_RATE
    assert COSTS.dp_per_scrip == frozen_costs.DP_CHARGE_PER_SCRIP
    assert COSTS.buy_cost(10_000.0) == pytest.approx(frozen_costs.buy_cost(10_000.0))
    assert COSTS.sell_cost(10_000.0, num_scrips=1) == pytest.approx(frozen_costs.sell_cost(10_000.0, 1))


# ── 2. behavior parity with the audited paper loop ────────────────────────


def _run_frozen_fill(cash: float, holdings: dict, pending: list, price: float, bar: str) -> tuple[float, dict, list]:
    """Run paper_trader.fill_pending_orders with a canned price frame."""
    frame = pd.DataFrame({o["ticker"]: [price] for o in pending}, index=[pd.Timestamp(bar)])
    orig_fetch, orig_log = paper_trader._fetch_close_frame, paper_trader.log_trade
    paper_trader._fetch_close_frame = lambda tickers: frame
    paper_trader.log_trade = lambda *a, **k: None
    try:
        return paper_trader.fill_pending_orders(cash, holdings, pending)
    finally:
        paper_trader._fetch_close_frame, paper_trader.log_trade = orig_fetch, orig_log


@pytest.mark.parametrize(
    ("scenario", "cash", "position", "order_kwargs"),
    [
        ("sell_fills_t_plus_1", 0.0, ("TEST.NS", 10.0, 100.0), {"side": "SELL", "shares": 10.0}),
        ("buy_fills_t_plus_1", 1_000.0, None, {"side": "BUY", "allocation": 900.0}),
        ("buy_insufficient_cash_dropped", 100.0, None, {"side": "BUY", "allocation": 900.0}),
        ("sell_without_position_dropped", 0.0, None, {"side": "SELL", "shares": 10.0}),
        ("buy_already_held_dropped", 1_000.0, ("TEST.NS", 5.0, 80.0), {"side": "BUY", "allocation": 900.0}),
    ],
)
def test_fill_parity_with_frozen_loop(scenario: str, cash: float, position: tuple | None, order_kwargs: dict) -> None:
    reason = "stop_loss" if order_kwargs["side"] == "SELL" else "rebalance_entry"
    price, queued_on, bar = 90.0, "2026-01-01", "2026-01-02"

    # frozen loop
    frozen_holdings = {position[0]: {"shares": position[1], "entry_price": position[2]}} if position else {}
    frozen_pending = [{"type": order_kwargs["side"], "ticker": "TEST.NS", "reason": reason, "queued_on": queued_on}]
    if "shares" in order_kwargs:
        frozen_pending[0]["shares"] = order_kwargs["shares"]
    if "allocation" in order_kwargs:
        frozen_pending[0]["allocation"] = order_kwargs["allocation"]
    f_cash, f_holdings, f_pending = _run_frozen_fill(cash, dict(frozen_holdings), frozen_pending, price, bar)

    # portfolio core
    positions = {position[0]: Position(shares=position[1], entry_price=position[2])} if position else {}
    state = make_state(
        cash=cash,
        positions=positions,
        pending=[PendingOrder(ticker="TEST.NS", reason=reason, queued_on=queued_on, **order_kwargs)],
    )
    outcome = fill_pending(state, {"TEST.NS": price}, bar, COSTS)

    assert outcome.state.cash == pytest.approx(f_cash), scenario
    assert set(outcome.state.positions) == set(f_holdings), scenario
    for ticker, pos in outcome.state.positions.items():
        assert pos.shares == pytest.approx(f_holdings[ticker]["shares"]), scenario
        assert pos.entry_price == pytest.approx(f_holdings[ticker]["entry_price"]), scenario
    assert len(outcome.state.pending) == len(f_pending), scenario


def test_same_bar_fill_refused_matches_frozen_loop() -> None:
    order = PendingOrder(side="SELL", ticker="TEST.NS", shares=10.0, reason="stop_loss", queued_on="2026-01-02")
    state = make_state(positions={"TEST.NS": Position(shares=10.0, entry_price=100.0)}, pending=[order])
    outcome = fill_pending(state, {"TEST.NS": 90.0}, "2026-01-02", COSTS)  # bar == queued_on
    assert outcome.state.pending == [order] and outcome.state.cash == state.cash
    assert outcome.fills == ()


def test_unpriceable_order_stays_queued() -> None:
    order = PendingOrder(side="SELL", ticker="GONE.NS", shares=5.0, reason="stop_loss", queued_on="2026-01-01")
    state = make_state(positions={"GONE.NS": Position(shares=5.0, entry_price=50.0)}, pending=[order])
    outcome = fill_pending(state, {}, "2026-01-02", COSTS)
    assert outcome.state.pending == [order]
    assert "GONE.NS" in outcome.state.positions


# ── 3. queue and state semantics ──────────────────────────────────────────


def test_state_is_immutable_and_transitions_return_new_state() -> None:
    state = make_state()
    with pytest.raises(Exception):
        state.cash = 0.0  # type: ignore[misc]
    out = queue_cash_exit(make_state(positions={"A": Position(shares=1.0, entry_price=10.0)}), today="2026-07-15")
    assert out.state is not state and len(out.state.pending) == 1


def test_pending_order_shape_is_validated() -> None:
    with pytest.raises(Exception):
        PendingOrder(side="SELL", ticker="A", allocation=100.0, reason="x", queued_on="2026-01-01")
    with pytest.raises(Exception):
        PendingOrder(side="BUY", ticker="A", shares=1.0, reason="x", queued_on="2026-01-01")


def test_queue_dedup_one_live_order_per_ticker() -> None:
    """A ticker with a live pending order must never be queued again --
    the duplicate-order corruption path from the 2026-07-14 audit."""
    existing = PendingOrder(side="SELL", ticker="A", shares=1.0, reason="stop_loss", queued_on="2026-07-10")
    state = make_state(positions={"A": Position(shares=1.0, entry_price=10.0)}, pending=[existing])
    assert queue_stop_losses(state, {"A": 1.0}, 0.08, "2026-07-15").state.pending == [existing]
    assert queue_cash_exit(state, "2026-07-15").state.pending == [existing]


def test_stop_loss_boundary_inclusive() -> None:
    state = make_state(
        positions={
            "AT_STOP": Position(shares=1.0, entry_price=100.0),
            "ABOVE": Position(shares=1.0, entry_price=100.0),
        }
    )
    out = queue_stop_losses(state, {"AT_STOP": 92.0, "ABOVE": 92.01}, 0.08, "2026-07-15")
    assert [o.ticker for o in out.state.pending] == ["AT_STOP"]


def test_rebalance_queues_exits_and_sized_entries() -> None:
    state = make_state(cash=50_000.0, positions={"OLD": Position(shares=100.0, entry_price=500.0)})
    target = TargetWeights(stance="rebalance", weights={"NEW1": 0.5, "NEW2": 0.5})
    out = queue_rebalance(state, target, portfolio_value=100_000.0, today="2026-07-17")
    orders = {o.ticker: o for o in out.state.pending}
    assert orders["OLD"].side == "SELL" and orders["OLD"].reason == "rebalance_exit"
    assert orders["NEW1"].side == "BUY" and orders["NEW1"].allocation == pytest.approx(50_000.0)
    assert orders["NEW2"].allocation == pytest.approx(50_000.0)


def test_rebalance_keeps_held_target_tickers_untouched() -> None:
    state = make_state(positions={"KEEP": Position(shares=10.0, entry_price=100.0)})
    target = TargetWeights(stance="rebalance", weights={"KEEP": 0.5, "NEW": 0.5})
    out = queue_rebalance(state, target, portfolio_value=100_000.0, today="2026-07-17")
    assert [o.ticker for o in out.state.pending] == ["NEW"]


def test_rebalance_refuses_non_rebalance_stance() -> None:
    with pytest.raises(ValueError, match="rebalance"):
        queue_rebalance(make_state(), TargetWeights(stance="cash"), 100_000.0, "2026-07-17")


def test_total_value_falls_back_to_entry_price() -> None:
    state = make_state(cash=1_000.0, positions={"A": Position(shares=2.0, entry_price=50.0)})
    assert total_value(state, {}) == pytest.approx(1_100.0)
    assert total_value(state, {"A": 60.0}) == pytest.approx(1_120.0)


def test_portfolio_state_repository_round_trip(tmp_path: Path) -> None:
    repo: SqliteRepository[PortfolioState] = SqliteRepository(tmp_path / "p.db", "portfolio", PortfolioState)
    state = make_state(
        positions={"A": Position(shares=1.5, entry_price=10.0)},
        pending=[
            PendingOrder(side="BUY", ticker="B", allocation=10_000.0, reason="rebalance_entry", queued_on="2026-07-17")
        ],
        last_updated=str(date(2026, 7, 15)),
    )
    repo.save(state)
    loaded = repo.get("paper")
    assert loaded == state
