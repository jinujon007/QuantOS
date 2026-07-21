"""Position-limit gate + composition (WP-016, ADR-041).

The Part V contract under test: single-name exposure <= limit_pct of
NAV, SELLs never blocked by the limit, every ambiguity fails closed,
and a composed stack blocks on the first breach. Uses the real
LimitOrder type end-to-end so the structural OrderLike slice is proven
against the type the engine actually passes.
"""

from pathlib import Path

import pytest

from quantos_core.brokers import LimitOrder, OrderSide
from quantos_core.execution import ExecutionBlockedError, ExecutionEngine, OrderJournalEntry
from quantos_core.risk import (
    CompositeGate,
    KillSwitch,
    KillSwitchGate,
    KillSwitchState,
    PositionLimitGate,
    RiskLimitBreach,
    check_position_limit,
)
from quantos_core.storage import SqliteRepository


class StaticBook:
    """BookView test double: fixed NAV, fixed per-ticker exposure."""

    def __init__(self, nav: float, exposures: dict[str, float] | None = None) -> None:
        self._nav = nav
        self._exposures = exposures or {}

    def nav(self) -> float:
        return self._nav

    def exposure(self, ticker: str) -> float:
        return self._exposures.get(ticker, 0.0)


class BrokenBook:
    """BookView whose reads fail -- the fail-closed scenario."""

    def nav(self) -> float:
        raise RuntimeError("storage offline")

    def exposure(self, ticker: str) -> float:
        raise RuntimeError("storage offline")


def buy(ticker: str = "TCS", quantity: int = 10, price: float = 100.0) -> LimitOrder:
    return LimitOrder(ticker=ticker, side=OrderSide.BUY, quantity=quantity, limit_price=price)


def sell(ticker: str = "TCS", quantity: int = 10, price: float = 100.0) -> LimitOrder:
    return LimitOrder(ticker=ticker, side=OrderSide.SELL, quantity=quantity, limit_price=price)


# ── pure function ─────────────────────────────────────────────────────────


def test_within_limit_allowed() -> None:
    check_position_limit(order_value=10_000, current_exposure=0.0, nav=100_000, limit_pct=0.15, ticker="TCS")


def test_exactly_at_limit_allowed() -> None:
    check_position_limit(order_value=15_000, current_exposure=0.0, nav=100_000, limit_pct=0.15, ticker="TCS")


def test_above_limit_blocked_and_names_the_numbers() -> None:
    with pytest.raises(RiskLimitBreach, match="TCS.*15%"):
        check_position_limit(order_value=15_001, current_exposure=0.0, nav=100_000, limit_pct=0.15, ticker="TCS")


def test_existing_exposure_counts_toward_limit() -> None:
    with pytest.raises(RiskLimitBreach):
        check_position_limit(order_value=6_000, current_exposure=10_000, nav=100_000, limit_pct=0.15, ticker="TCS")


def test_non_positive_nav_fails_closed() -> None:
    with pytest.raises(RiskLimitBreach, match="fail closed"):
        check_position_limit(order_value=1_000, current_exposure=0.0, nav=0.0, limit_pct=0.15, ticker="TCS")


def test_non_positive_order_value_fails_closed() -> None:
    with pytest.raises(RiskLimitBreach, match="not positive"):
        check_position_limit(order_value=0.0, current_exposure=0.0, nav=100_000, limit_pct=0.15, ticker="TCS")


# ── PositionLimitGate ─────────────────────────────────────────────────────


def test_gate_blocks_oversized_buy() -> None:
    gate = PositionLimitGate(StaticBook(nav=100_000), limit_pct=0.15)
    with pytest.raises(RiskLimitBreach):
        gate.check(buy(quantity=200, price=100.0))  # 20,000 > 15,000


def test_gate_allows_buy_within_limit() -> None:
    gate = PositionLimitGate(StaticBook(nav=100_000), limit_pct=0.15)
    gate.check(buy(quantity=100, price=100.0))  # 10,000 <= 15,000


def test_gate_counts_existing_position() -> None:
    gate = PositionLimitGate(StaticBook(nav=100_000, exposures={"TCS": 10_000}), limit_pct=0.15)
    with pytest.raises(RiskLimitBreach):
        gate.check(buy(quantity=60, price=100.0))  # 10,000 + 6,000 > 15,000


def test_gate_never_blocks_sells_even_when_breached() -> None:
    gate = PositionLimitGate(StaticBook(nav=100_000, exposures={"TCS": 40_000}), limit_pct=0.15)
    gate.check(sell(quantity=400, price=100.0))  # exits reduce the breach


def test_gate_fails_closed_on_unreadable_book() -> None:
    gate = PositionLimitGate(BrokenBook(), limit_pct=0.15)
    with pytest.raises(RiskLimitBreach, match="fail closed"):
        gate.check(buy())


def test_gate_rejects_nonsense_limit_pct() -> None:
    with pytest.raises(ValueError):
        PositionLimitGate(StaticBook(nav=1.0), limit_pct=0.0)
    with pytest.raises(ValueError):
        PositionLimitGate(StaticBook(nav=1.0), limit_pct=1.5)


# ── CompositeGate ─────────────────────────────────────────────────────────


def test_composite_refuses_empty_stack() -> None:
    with pytest.raises(ValueError, match="empty stack"):
        CompositeGate([])


def test_composite_blocks_on_first_breach(tmp_path: Path) -> None:
    switch = KillSwitch(SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState))
    switch.engage("drill")
    stack = CompositeGate([KillSwitchGate(switch), PositionLimitGate(StaticBook(nav=100_000), 0.15)])
    with pytest.raises(RiskLimitBreach, match="kill switch"):
        stack.check(buy())


def test_composite_runs_every_gate_when_clean(tmp_path: Path) -> None:
    switch = KillSwitch(SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState))
    stack = CompositeGate([KillSwitchGate(switch), PositionLimitGate(StaticBook(nav=100_000), 0.15)])
    stack.check(buy())  # both pass
    with pytest.raises(RiskLimitBreach, match="Position limit"):
        stack.check(buy(quantity=200))  # kill switch passes, limit blocks


# ── engine integration: composite satisfies the PreTradeGate seam ─────────


def test_engine_journals_position_limit_block(tmp_path: Path) -> None:
    """The composed stack drops into ExecutionEngine unchanged, and a
    limit block is journaled as BLOCKED exactly like a kill-switch
    block -- every path journals (WP-008 contract)."""

    class RefusingBroker:
        def place_order(self, order: LimitOrder) -> None:
            raise AssertionError("broker must never see a blocked order")

    journal: SqliteRepository[OrderJournalEntry] = SqliteRepository(
        tmp_path / "journal.db", "order_journal", OrderJournalEntry
    )
    switch = KillSwitch(SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState))
    stack = CompositeGate([KillSwitchGate(switch), PositionLimitGate(StaticBook(nav=100_000), 0.15)])
    engine = ExecutionEngine(RefusingBroker(), stack, journal, run_id="test-risk")

    with pytest.raises(ExecutionBlockedError, match="Position limit"):
        engine.execute(buy(quantity=200, price=100.0))

    entries = journal.query({"run_id": "test-risk"})
    assert len(entries) == 1
    assert entries[0].outcome == "BLOCKED"
    assert "Position limit" in entries[0].detail
