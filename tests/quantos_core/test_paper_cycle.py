"""paper.run_cycle tests (WP-013, ADR-038).

Each test pins one of the failure modes the 2026-07-14 audit found in
the legacy daily loop -- here they must be structural properties of the
cycle, not patches.
"""

from datetime import date
from pathlib import Path

import pytest

from quantos_core.paper import MarketSnapshot, run_cycle
from quantos_core.portfolio import (
    PendingOrder,
    PortfolioState,
    Position,
    ZerodhaDeliveryCostModel,
)
from quantos_core.risk import KillSwitch, KillSwitchState
from quantos_core.storage import SqliteRepository, StorageError
from quantos_core.strategies import StrategyContext, StrategyMeta, TargetWeights

COSTS = ZerodhaDeliveryCostModel()
FRIDAY = date(2026, 7, 17)
SATURDAY = date(2026, 7, 18)
TUESDAY = date(2026, 7, 14)


class DictStore:
    def __init__(self, state: PortfolioState | None = None) -> None:
        self.entities: dict[str, PortfolioState] = {}
        self.saves = 0
        if state is not None:
            self.entities[state.id] = state

    def get(self, entity_id: str) -> PortfolioState:
        return self.entities[entity_id]

    def save(self, entity: PortfolioState) -> None:
        self.saves += 1
        self.entities[entity.id] = entity


class FixedStrategy:
    def __init__(self, target: TargetWeights) -> None:
        self._target = target
        self.calls = 0

    def generate_signals(self, ctx: StrategyContext) -> TargetWeights:
        self.calls += 1
        return self._target

    def metadata(self) -> StrategyMeta:
        return StrategyMeta(name="fixed", version="0", params={})


@pytest.fixture
def kill_switch(tmp_path: Path) -> KillSwitch:
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState)
    return KillSwitch(repo)


def make_state(**overrides: object) -> PortfolioState:
    defaults: dict = {"id": "paper", "cash": 100_000.0, "start_date": "2026-06-09"}
    defaults.update(overrides)
    return PortfolioState(**defaults)


def bull_market(**overrides: object) -> MarketSnapshot:
    defaults: dict = {"latest_close": {}, "bar_date": "2026-07-14", "market_uptrend": True, "prices": None}
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


def run(as_of: date, store: DictStore, market: MarketSnapshot, kill_switch: KillSwitch, strategy=None):
    return run_cycle(
        as_of,
        store=store,
        market=market,
        strategy=strategy or FixedStrategy(TargetWeights(stance="hold")),
        kill_switch=kill_switch,
        stop_loss_pct=0.08,
        costs=COSTS,
    )


# ── the audit invariants ──────────────────────────────────────────────────


def test_engaged_kill_switch_halts_before_any_state_read(kill_switch: KillSwitch) -> None:
    kill_switch.engage("test halt")
    store = DictStore()  # empty: a state read would raise KeyError
    report = run(TUESDAY, store, bull_market(), kill_switch)
    assert report.status == "HALTED" and store.saves == 0


def test_unreadable_kill_switch_halts_fail_closed() -> None:
    class BrokenRepo:
        def get(self, entity_id: str) -> KillSwitchState:
            raise StorageError("disk gone")

        def save(self, entity: KillSwitchState) -> None:
            raise StorageError("disk gone")

        def query(self, filter: object) -> list[KillSwitchState]:
            raise StorageError("disk gone")

    store = DictStore(make_state())
    report = run(TUESDAY, store, bull_market(), KillSwitch(BrokenRepo()))
    assert report.status == "HALTED" and store.saves == 0


def test_missing_state_fails_loud_never_reinitializes(kill_switch: KillSwitch) -> None:
    with pytest.raises(KeyError):
        run(TUESDAY, DictStore(), bull_market(), kill_switch)


def test_same_day_rerun_is_idempotent(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(last_updated="2026-07-14"))
    report = run(TUESDAY, store, bull_market(), kill_switch)
    assert report.status == "ALREADY_RAN" and store.saves == 0


def test_fills_are_persisted_before_signal_work(kill_switch: KillSwitch) -> None:
    """Fill, then crash-equivalent (strategy raises): the fill must
    already be on disk so the next run cannot re-fill it."""

    class ExplodingStrategy(FixedStrategy):
        def generate_signals(self, ctx: StrategyContext) -> TargetWeights:
            raise RuntimeError("signal fetch died mid-cycle")

    pending = [
        PendingOrder(side="BUY", ticker="A", allocation=10_000.0, reason="rebalance_entry", queued_on="2026-07-16")
    ]
    store = DictStore(make_state(pending=pending))
    market = bull_market(latest_close={"A": 100.0}, bar_date="2026-07-17", prices="not-none-sentinel")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        run(FRIDAY, store, market, kill_switch, strategy=ExplodingStrategy(TargetWeights(stance="hold")))
    persisted = store.entities["paper"]
    assert "A" in persisted.positions and persisted.pending == []  # fill survived the crash


def test_unknown_regime_takes_no_actions_and_degrades(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(positions={"A": Position(shares=10.0, entry_price=100.0)}))
    report = run(FRIDAY, store, bull_market(latest_close={"A": 100.0}, market_uptrend=None), kill_switch)
    assert report.status == "DEGRADED"
    assert store.entities["paper"].pending == []  # no liquidation, no rebalance
    assert store.entities["paper"].last_rebalance_date == ""  # date NOT consumed -> weekend retry


def test_confirmed_bear_queues_full_exit_and_consumes_friday(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(positions={"A": Position(shares=10.0, entry_price=100.0)}))
    report = run(FRIDAY, store, bull_market(latest_close={"A": 100.0}, market_uptrend=False), kill_switch)
    state = store.entities["paper"]
    assert [o.ticker for o in state.pending] == ["A"] and state.pending[0].reason == "bear_market_exit"
    assert state.last_rebalance_date == FRIDAY.isoformat()
    assert report.stance == "cash"


def test_friday_rebalance_queues_target(kill_switch: KillSwitch) -> None:
    import pandas as pd

    store = DictStore(make_state())
    strategy = FixedStrategy(TargetWeights(stance="rebalance", weights={"N1": 0.5, "N2": 0.5}))
    market = bull_market(prices=pd.DataFrame({"N1": [1.0]}, index=[pd.Timestamp("2026-07-16")]))
    report = run(FRIDAY, store, market, kill_switch, strategy=strategy)
    state = store.entities["paper"]
    assert report.rebalanced and {o.ticker for o in state.pending} == {"N1", "N2"}
    assert all(o.allocation == pytest.approx(50_000.0) for o in state.pending)
    assert state.last_rebalance_date == FRIDAY.isoformat()


def test_saturday_catches_up_a_missed_friday(kill_switch: KillSwitch) -> None:
    import pandas as pd

    store = DictStore(make_state(last_rebalance_date="2026-07-10"))  # previous week's Friday
    strategy = FixedStrategy(TargetWeights(stance="rebalance", weights={"N1": 1.0}))
    market = bull_market(prices=pd.DataFrame({"N1": [1.0]}, index=[pd.Timestamp("2026-07-17")]))
    report = run(SATURDAY, store, market, kill_switch, strategy=strategy)
    assert report.rebalanced
    assert store.entities["paper"].last_rebalance_date == FRIDAY.isoformat()


def test_saturday_after_successful_friday_does_not_double_rebalance(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(last_rebalance_date=FRIDAY.isoformat(), last_updated=FRIDAY.isoformat()))
    strategy = FixedStrategy(TargetWeights(stance="rebalance", weights={"N1": 1.0}))
    report = run(SATURDAY, store, bull_market(), kill_switch, strategy=strategy)
    assert not report.rebalanced and strategy.calls == 0


def test_weekday_never_rebalances(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state())
    strategy = FixedStrategy(TargetWeights(stance="rebalance", weights={"N1": 1.0}))
    report = run(TUESDAY, store, bull_market(), kill_switch, strategy=strategy)
    assert not report.rebalanced and strategy.calls == 0


def test_signals_unavailable_on_friday_degrades_and_retries(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state())
    report = run(FRIDAY, store, bull_market(prices=None), kill_switch)
    assert report.status == "DEGRADED"
    assert store.entities["paper"].last_rebalance_date == ""  # date not consumed


def test_hold_stance_is_a_decision_and_consumes_the_date(kill_switch: KillSwitch) -> None:
    import pandas as pd

    store = DictStore(make_state())
    strategy = FixedStrategy(TargetWeights(stance="hold"))
    market = bull_market(prices=pd.DataFrame({"N1": [1.0]}, index=[pd.Timestamp("2026-07-16")]))
    report = run(FRIDAY, store, market, kill_switch, strategy=strategy)
    assert report.status == "OK" and report.stance == "hold" and not report.rebalanced
    assert store.entities["paper"].last_rebalance_date == FRIDAY.isoformat()


def test_missing_prices_with_positions_degrades(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(positions={"A": Position(shares=10.0, entry_price=100.0)}))
    report = run(TUESDAY, store, bull_market(latest_close={}), kill_switch)
    assert report.status == "DEGRADED"
    assert any("stop-losses unmonitored" in d for d in report.degraded)


def test_stop_loss_queues_exit(kill_switch: KillSwitch) -> None:
    store = DictStore(make_state(positions={"A": Position(shares=10.0, entry_price=100.0)}))
    run(TUESDAY, store, bull_market(latest_close={"A": 91.0}), kill_switch)
    state = store.entities["paper"]
    assert [(o.ticker, o.reason) for o in state.pending] == [("A", "stop_loss")]


def test_cycle_works_against_the_real_sqlite_repository(tmp_path: Path, kill_switch: KillSwitch) -> None:
    """StateStore is structural -- the production SqliteRepository must
    satisfy it end to end."""
    repo: SqliteRepository[PortfolioState] = SqliteRepository(tmp_path / "p.db", "portfolio", PortfolioState)
    repo.save(make_state())
    report = run_cycle(
        TUESDAY,
        store=repo,
        market=bull_market(),
        strategy=FixedStrategy(TargetWeights(stance="hold")),
        kill_switch=kill_switch,
        stop_loss_pct=0.08,
        costs=COSTS,
    )
    assert report.status == "OK"
    assert repo.get("paper").last_updated == TUESDAY.isoformat()
