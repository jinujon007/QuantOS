"""Tests for the WP-008 execution vertical slice (ADR-034).

Paper broker fill/reject/rest semantics, kill-switch fail-closed
behavior, engine gate-journal-place flow, and both real broker
adapters exercised against fake transports -- zero network anywhere.
"""

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from quantos_core.brokers import (
    AngelOneSmartApiAdapter,
    BrokerAuthError,
    BrokerConnectionError,
    LimitOrder,
    OrderPlacer,
    OrderRejectedError,
    OrderSide,
    PaperBrokerAdapter,
    ZerodhaKiteAdapter,
)
from quantos_core.execution import ExecutionBlockedError, ExecutionEngine, OrderJournalEntry
from quantos_core.risk import KillSwitch, KillSwitchGate, KillSwitchState, RiskLimitBreach
from quantos_core.storage import SqliteRepository, StorageError


def buy(ticker: str = "RELIANCE", qty: int = 10, limit: float = 100.0) -> LimitOrder:
    return LimitOrder(ticker=ticker, side=OrderSide.BUY, quantity=qty, limit_price=limit)


def sell(ticker: str = "RELIANCE", qty: int = 10, limit: float = 100.0) -> LimitOrder:
    return LimitOrder(ticker=ticker, side=OrderSide.SELL, quantity=qty, limit_price=limit)


# ── paper broker ──────────────────────────────────────────────────────────


def test_paper_buy_fills_at_market_within_limit() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=1000.0)
    receipt = broker.place_order(buy(limit=100.0))
    assert receipt.status == "FILLED"
    assert receipt.average_price == 95.0
    assert broker.holdings() == {"RELIANCE": 10}
    assert broker.available_cash() == 1000.0 - 950.0


def test_paper_buy_rests_open_when_limit_below_market() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 105.0}, cash=10000.0)
    receipt = broker.place_order(buy(limit=100.0))
    assert receipt.status == "OPEN"
    assert broker.holdings() == {}


def test_paper_buy_insufficient_cash_rejected() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=100.0)
    with pytest.raises(OrderRejectedError, match="Insufficient"):
        broker.place_order(buy())


def test_paper_sell_round_trip_and_oversell_rejected() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 100.0}, cash=1000.0)
    broker.place_order(buy(qty=10, limit=100.0))
    with pytest.raises(OrderRejectedError, match="hold only"):
        broker.place_order(sell(qty=11, limit=90.0))
    receipt = broker.place_order(sell(qty=10, limit=90.0))
    assert receipt.status == "FILLED"
    assert broker.holdings() == {}
    assert broker.available_cash() == 1000.0


def test_paper_unknown_ticker_rejected() -> None:
    broker = PaperBrokerAdapter({}, cash=1000.0)
    with pytest.raises(OrderRejectedError, match="No market price"):
        broker.place_order(buy())


def test_market_orders_are_unrepresentable() -> None:
    with pytest.raises(Exception):
        LimitOrder(ticker="X", side=OrderSide.BUY, quantity=1, limit_price=1.0, product="MIS")  # type: ignore[arg-type]


# ── kill switch ───────────────────────────────────────────────────────────


@pytest.fixture
def kill_switch(tmp_path: Path) -> KillSwitch:
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState)
    return KillSwitch(repo)


def test_kill_switch_never_engaged_defaults_to_trading(kill_switch: KillSwitch) -> None:
    assert kill_switch.is_engaged() is False


def test_kill_switch_engage_release_persists(tmp_path: Path, kill_switch: KillSwitch) -> None:
    kill_switch.engage("demo halt")
    reopened = KillSwitch(SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState))
    assert reopened.is_engaged() is True
    reopened.release("resume")
    assert kill_switch.is_engaged() is False


def test_kill_switch_unreadable_state_blocks() -> None:
    class BrokenRepo:
        def get(self, entity_id: str) -> KillSwitchState:
            raise StorageError("disk gone")

        def save(self, entity: KillSwitchState) -> None:
            raise StorageError("disk gone")

        def query(self, filter: Any) -> list[KillSwitchState]:
            raise StorageError("disk gone")

    assert KillSwitch(BrokenRepo()).is_engaged() is True  # fail-closed


# ── engine ────────────────────────────────────────────────────────────────


@pytest.fixture
def journal(tmp_path: Path) -> SqliteRepository[OrderJournalEntry]:
    return SqliteRepository(tmp_path / "journal.db", "order_journal", OrderJournalEntry)


def test_engine_places_and_journals(kill_switch: KillSwitch, journal: SqliteRepository[OrderJournalEntry]) -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=10000.0)
    engine = ExecutionEngine(broker, KillSwitchGate(kill_switch), journal, run_id="t1")
    receipt = engine.execute(buy())
    assert receipt.status == "FILLED"
    entries = journal.query({})
    assert len(entries) == 1
    assert entries[0].outcome == "FILLED"
    assert entries[0].broker_order_id == receipt.broker_order_id


def test_engine_blocks_when_kill_switch_engaged(
    kill_switch: KillSwitch, journal: SqliteRepository[OrderJournalEntry]
) -> None:
    kill_switch.engage("test")
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=10000.0)
    engine = ExecutionEngine(broker, KillSwitchGate(kill_switch), journal, run_id="t2")
    with pytest.raises(ExecutionBlockedError):
        engine.execute(buy())
    assert broker.holdings() == {}  # order never reached the broker
    assert journal.query({})[0].outcome == "BLOCKED"


def test_engine_journals_broker_rejection_and_reraises(
    kill_switch: KillSwitch, journal: SqliteRepository[OrderJournalEntry]
) -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=1.0)
    engine = ExecutionEngine(broker, KillSwitchGate(kill_switch), journal, run_id="t3")
    with pytest.raises(OrderRejectedError):
        engine.execute(buy())
    assert journal.query({})[0].outcome == "FAILED"


def test_engine_journals_unknown_on_non_broker_exception(
    kill_switch: KillSwitch, journal: SqliteRepository[OrderJournalEntry]
) -> None:
    class ExplodingBroker:
        def place_order(self, order: LimitOrder) -> None:
            raise KeyError("order_id")  # an adapter bug, not a BrokerError

    engine = ExecutionEngine(ExplodingBroker(), KillSwitchGate(kill_switch), journal, run_id="t4")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        engine.execute(buy())
    entries = journal.query({"run_id": "t4"})
    assert len(entries) == 1
    assert entries[0].outcome == "UNKNOWN"


def test_gate_raises_risk_limit_breach(kill_switch: KillSwitch) -> None:
    kill_switch.engage("halt")
    with pytest.raises(RiskLimitBreach):
        KillSwitchGate(kill_switch).check(buy())


# ── real adapters against fake transports ─────────────────────────────────


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


class FakeSession:
    """Records requests; replays scripted responses. Raises if used
    more times than scripted (catches unwanted retries)."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def _next(self, **call: Any) -> Any:
        self.calls.append(call)
        if not self._responses:
            raise AssertionError("adapter made more HTTP calls than scripted (retry bug?)")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url: str, **kwargs: Any) -> Any:
        return self._next(method="POST", url=url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> Any:
        return self._next(method="GET", url=url, **kwargs)


def test_zerodha_requires_credentials() -> None:
    with pytest.raises(BrokerAuthError):
        ZerodhaKiteAdapter(api_key="", access_token="")


def test_zerodha_place_order_builds_correct_request() -> None:
    session = FakeSession([FakeResponse({"status": "success", "data": {"order_id": "240714000001"}})])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    receipt = adapter.place_order(buy("TCS", 5, 4100.5))
    assert receipt.broker_order_id == "240714000001"
    assert receipt.status == "OPEN"
    call = session.calls[0]
    assert call["url"].endswith("/orders/regular")
    assert call["data"] == {
        "tradingsymbol": "TCS",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "quantity": "5",
        "price": "4100.50",
        "product": "CNC",
        "validity": "DAY",
    }
    assert call["headers"]["Authorization"] == "token key:token"
    assert call["headers"]["X-Kite-Version"] == "3"


def test_zerodha_token_failure_maps_to_auth_error() -> None:
    session = FakeSession(
        [FakeResponse({"status": "error", "error_type": "TokenException", "message": "expired"}, 403)]
    )
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerAuthError, match="expired"):
        adapter.place_order(buy())


def test_zerodha_backend_5xx_json_is_unknown_state_not_rejection() -> None:
    session = FakeSession(
        [FakeResponse({"status": "error", "error_type": "NetworkException", "message": "OMS unreachable"}, 503)]
    )
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerConnectionError, match="UNKNOWN"):
        adapter.place_order(buy())
    assert len(session.calls) == 1  # no retry on ambiguous state


def test_zerodha_success_without_order_id_is_unknown_state() -> None:
    session = FakeSession([FakeResponse({"status": "success", "data": {}})])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerConnectionError, match="no order_id"):
        adapter.place_order(buy())


def test_zerodha_network_failure_is_unknown_state_no_retry() -> None:
    session = FakeSession([requests.ConnectionError("boom")])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerConnectionError, match="UNKNOWN"):
        adapter.place_order(buy())
    assert len(session.calls) == 1  # exactly one attempt -- no duplicate-order retry


def test_zerodha_holdings_and_cash_parse() -> None:
    session = FakeSession(
        [
            FakeResponse({"status": "success", "data": [{"tradingsymbol": "INFY", "quantity": 12}]}),
            FakeResponse({"status": "success", "data": {"equity": {"available": {"live_balance": 54321.5}}}}),
        ]
    )
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    assert adapter.holdings() == {"INFY": 12}
    assert adapter.available_cash() == 54321.5


def test_angel_requires_credentials_and_session() -> None:
    with pytest.raises(BrokerAuthError):
        AngelOneSmartApiAdapter(api_key="", client_code="", symbol_tokens={})
    adapter = AngelOneSmartApiAdapter("key", "CLIENT1", symbol_tokens={}, session=FakeSession([]))  # type: ignore[arg-type]
    with pytest.raises(BrokerAuthError, match="login"):
        adapter.holdings()


def test_angel_login_then_place_order_builds_correct_request() -> None:
    session = FakeSession(
        [
            FakeResponse({"status": True, "data": {"jwtToken": "JWT123"}}),
            FakeResponse({"status": True, "data": {"orderid": "AO-777"}}),
        ]
    )
    adapter = AngelOneSmartApiAdapter(
        "key",
        "CLIENT1",
        symbol_tokens={"TCS": "11536"},
        session=session,  # type: ignore[arg-type]
    )
    adapter.login(pin="1234", totp_code="000000")
    receipt = adapter.place_order(buy("TCS", 5, 4100.5))
    assert receipt.broker_order_id == "AO-777"
    login_call, order_call = session.calls
    assert login_call["json"]["clientcode"] == "CLIENT1"
    body = order_call["json"]
    assert body["tradingsymbol"] == "TCS-EQ"
    assert body["symboltoken"] == "11536"
    assert body["producttype"] == "DELIVERY"
    assert body["ordertype"] == "LIMIT"
    assert order_call["headers"]["Authorization"] == "Bearer JWT123"
    assert order_call["headers"]["X-PrivateKey"] == "key"


def test_angel_unknown_symbol_token_refused() -> None:
    session = FakeSession([FakeResponse({"status": True, "data": {"jwtToken": "J"}})])
    adapter = AngelOneSmartApiAdapter("key", "C", symbol_tokens={}, session=session)  # type: ignore[arg-type]
    adapter.login(pin="1", totp_code="2")
    with pytest.raises(OrderRejectedError, match="symboltoken"):
        adapter.place_order(buy("TCS"))


def test_angel_auth_errorcode_maps_to_auth_error() -> None:
    session = FakeSession(
        [
            FakeResponse({"status": True, "data": {"jwtToken": "J"}}),
            FakeResponse({"status": False, "errorcode": "AG8001", "message": "Invalid Token"}),
        ]
    )
    adapter = AngelOneSmartApiAdapter("key", "C", symbol_tokens={"TCS": "1"}, session=session)  # type: ignore[arg-type]
    adapter.login(pin="1", totp_code="2")
    with pytest.raises(BrokerAuthError, match="Invalid Token"):
        adapter.place_order(buy("TCS"))


def test_all_three_adapters_satisfy_the_same_port() -> None:
    def accepts(placer: OrderPlacer) -> OrderPlacer:
        return placer

    paper = PaperBrokerAdapter({}, cash=0.0)
    zerodha = ZerodhaKiteAdapter("k", "t", session=FakeSession([]))  # type: ignore[arg-type]
    angel = AngelOneSmartApiAdapter("k", "c", symbol_tokens={}, session=FakeSession([]))  # type: ignore[arg-type]
    assert accepts(paper) is paper
    assert accepts(zerodha) is zerodha
    assert accepts(angel) is angel


def test_paper_negative_starting_cash_rejected() -> None:
    with pytest.raises(OrderRejectedError, match="negative"):
        PaperBrokerAdapter({}, cash=-1.0)


def test_paper_sell_rests_open_when_limit_above_market() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 100.0}, cash=2000.0)
    broker.place_order(buy(qty=10, limit=100.0))
    receipt = broker.place_order(sell(qty=4, limit=110.0))
    assert receipt.status == "OPEN"
    assert broker.holdings() == {"RELIANCE": 10}


def test_paper_partial_sell_keeps_remainder() -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 100.0}, cash=2000.0)
    broker.place_order(buy(qty=10, limit=100.0))
    broker.place_order(sell(qty=4, limit=90.0))
    assert broker.holdings() == {"RELIANCE": 6}


def test_zerodha_non_json_response_is_connection_error() -> None:
    session = FakeSession([FakeResponse("<html>gateway timeout</html>", 502)])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerConnectionError, match="non-JSON"):
        adapter.place_order(buy())


def test_zerodha_non_auth_error_is_rejection() -> None:
    session = FakeSession([FakeResponse({"status": "error", "error_type": "InputException", "message": "bad qty"})])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(OrderRejectedError, match="bad qty"):
        adapter.place_order(buy())


def test_zerodha_get_network_failure_is_connection_error() -> None:
    session = FakeSession([requests.ConnectionError("down")])
    adapter = ZerodhaKiteAdapter("key", "token", session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerConnectionError):
        adapter.holdings()


def test_zerodha_data_null_reads_do_not_crash_or_disguise() -> None:
    """success + data:null (or a missing data key) is an ambiguous body, not
    an empty portfolio -- returning {} would read as 'all positions gone'
    (mirror of the Angel data:null hardening; 2026-07-14 audit)."""
    adapter = ZerodhaKiteAdapter(
        "key",
        "token",
        session=FakeSession([FakeResponse({"status": "success", "data": None})]),  # type: ignore[arg-type]
    )
    with pytest.raises(BrokerConnectionError, match="ambiguous"):
        adapter.holdings()
    adapter = ZerodhaKiteAdapter(
        "key",
        "token",
        session=FakeSession([FakeResponse({"status": "success"})]),  # type: ignore[arg-type]
    )
    with pytest.raises(BrokerConnectionError, match="ambiguous"):
        adapter.holdings()
    adapter = ZerodhaKiteAdapter(
        "key",
        "token",
        session=FakeSession([FakeResponse({"status": "success", "data": {"equity": {}}})]),  # type: ignore[arg-type]
    )
    with pytest.raises(BrokerConnectionError, match="missing expected fields"):
        adapter.available_cash()


def test_angel_login_rejection_is_auth_error_not_order_rejection() -> None:
    """SmartAPI rejects a wrong PIN/TOTP with HTTP 200 + AB-series codes;
    a login call places no order, so it must surface as BrokerAuthError."""
    session = FakeSession([FakeResponse({"status": False, "errorcode": "AB1007", "message": "Invalid totp"})])
    adapter = AngelOneSmartApiAdapter("k", "c", symbol_tokens={}, session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerAuthError, match="Invalid totp"):
        adapter.login(pin="0000", totp_code="123456")


def test_engine_journal_failure_after_placement_returns_receipt(
    kill_switch: KillSwitch,
) -> None:
    """A journal write failure AFTER the broker accepted must never mask the
    placement: raising StorageError would make a PLACED order look like it
    never happened, and a re-run would place it again (2026-07-14 audit)."""

    class BrokenJournal:
        def get(self, entity_id: str) -> OrderJournalEntry:
            raise StorageError("disk gone")

        def save(self, entity: OrderJournalEntry) -> None:
            raise StorageError("disk gone")

        def query(self, filter: Any) -> list[OrderJournalEntry]:
            return []  # constructor sequence-resume works; writes fail

    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=10000.0)
    engine = ExecutionEngine(broker, KillSwitchGate(kill_switch), BrokenJournal(), run_id="t-journal")  # type: ignore[arg-type]
    receipt = engine.execute(buy())
    assert receipt.status == "FILLED"  # placement truth outranks journal completeness
    assert broker.holdings() == {"RELIANCE": 10}


def test_engine_journal_failure_on_block_still_raises_blocked(
    kill_switch: KillSwitch,
) -> None:
    """A journal failure on the BLOCKED path must not replace
    ExecutionBlockedError with StorageError -- callers branch on the block
    signal (e.g. the kill-switch drill)."""

    class BrokenJournal:
        def get(self, entity_id: str) -> OrderJournalEntry:
            raise StorageError("disk gone")

        def save(self, entity: OrderJournalEntry) -> None:
            raise StorageError("disk gone")

        def query(self, filter: Any) -> list[OrderJournalEntry]:
            return []

    kill_switch.engage("halt")
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=10000.0)
    engine = ExecutionEngine(broker, KillSwitchGate(kill_switch), BrokenJournal(), run_id="t-blocked")  # type: ignore[arg-type]
    with pytest.raises(ExecutionBlockedError):
        engine.execute(buy())
    assert broker.holdings() == {}  # order never reached the broker


def angel_logged_in(responses: list[Any]) -> tuple[AngelOneSmartApiAdapter, FakeSession]:
    session = FakeSession([FakeResponse({"status": True, "data": {"jwtToken": "J"}}), *responses])
    adapter = AngelOneSmartApiAdapter("key", "C", symbol_tokens={"TCS": "1"}, session=session)  # type: ignore[arg-type]
    adapter.login(pin="1", totp_code="2")
    return adapter, session


def test_angel_non_json_response_is_connection_error() -> None:
    adapter, _ = angel_logged_in([FakeResponse("<html/>", 502)])
    with pytest.raises(BrokerConnectionError, match="non-JSON"):
        adapter.place_order(buy("TCS"))


def test_angel_non_auth_rejection_maps_to_order_rejected() -> None:
    adapter, _ = angel_logged_in([FakeResponse({"status": False, "errorcode": "AB1013", "message": "RMS block"})])
    with pytest.raises(OrderRejectedError, match="RMS block"):
        adapter.place_order(buy("TCS"))


def test_angel_transient_ab1004_is_unknown_state_not_rejection() -> None:
    adapter, session = angel_logged_in(
        [FakeResponse({"status": False, "errorcode": "AB1004", "message": "Something Went Wrong"})]
    )
    with pytest.raises(BrokerConnectionError, match="UNKNOWN"):
        adapter.place_order(buy("TCS"))
    assert len(session.calls) == 2  # login + one attempt, no retry


def test_angel_5xx_json_body_is_unknown_state() -> None:
    adapter, _ = angel_logged_in([FakeResponse({"status": False, "errorcode": "AB9999", "message": "oops"}, 500)])
    with pytest.raises(BrokerConnectionError, match="UNKNOWN"):
        adapter.place_order(buy("TCS"))


def test_angel_data_null_bodies_do_not_crash() -> None:
    # SmartAPI returns "status": true with "data": null in real life.
    session = FakeSession([FakeResponse({"status": True, "data": None})])
    adapter = AngelOneSmartApiAdapter("key", "C", symbol_tokens={}, session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerAuthError, match="jwtToken"):
        adapter.login(pin="1", totp_code="2")
    adapter2, _ = angel_logged_in(
        [
            FakeResponse({"status": True, "data": None}),  # place_order
            FakeResponse({"status": True, "data": None}),  # holdings
            FakeResponse({"status": True, "data": None}),  # cash
        ]
    )
    adapter2._symbol_tokens["TCS"] = "1"
    with pytest.raises(BrokerConnectionError, match="no orderid"):
        adapter2.place_order(buy("TCS"))
    assert adapter2.holdings() == {}  # null portfolio = legitimately empty
    with pytest.raises(BrokerConnectionError, match="availablecash"):
        adapter2.available_cash()


def test_angel_post_network_failure_is_unknown_state_no_retry() -> None:
    adapter, session = angel_logged_in([requests.ConnectionError("boom")])
    with pytest.raises(BrokerConnectionError, match="UNKNOWN"):
        adapter.place_order(buy("TCS"))
    assert len(session.calls) == 2  # login + exactly one placement attempt


def test_angel_login_without_token_refused() -> None:
    session = FakeSession([FakeResponse({"status": True, "data": {}})])
    adapter = AngelOneSmartApiAdapter("key", "C", symbol_tokens={}, session=session)  # type: ignore[arg-type]
    with pytest.raises(BrokerAuthError, match="jwtToken"):
        adapter.login(pin="1", totp_code="2")


def test_angel_place_order_without_orderid_is_unknown() -> None:
    adapter, _ = angel_logged_in([FakeResponse({"status": True, "data": {}})])
    with pytest.raises(BrokerConnectionError, match="no orderid"):
        adapter.place_order(buy("TCS"))


def test_angel_holdings_and_cash_parse() -> None:
    adapter, _ = angel_logged_in(
        [
            FakeResponse({"status": True, "data": {"holdings": [{"tradingsymbol": "TCS-EQ", "quantity": 3}]}}),
            FakeResponse({"status": True, "data": {"availablecash": "12345.67"}}),
        ]
    )
    assert adapter.holdings() == {"TCS": 3}
    assert adapter.available_cash() == 12345.67


def test_angel_get_network_failure_is_connection_error() -> None:
    adapter, _ = angel_logged_in([requests.ConnectionError("down")])
    with pytest.raises(BrokerConnectionError):
        adapter.holdings()


def test_journal_entry_round_trips_as_json() -> None:
    entry = OrderJournalEntry(
        id="r-0001",
        run_id="r",
        ticker="TCS",
        side="BUY",
        quantity=5,
        limit_price=4100.5,
        outcome="FILLED",
        broker_order_id="X",
        detail="filled=5",
    )
    assert json.loads(entry.model_dump_json())["outcome"] == "FILLED"


def test_engine_rerun_with_same_run_id_appends_not_overwrites(
    kill_switch: KillSwitch, journal: SqliteRepository[OrderJournalEntry]
) -> None:
    broker = PaperBrokerAdapter({"RELIANCE": 95.0}, cash=100000.0)
    ExecutionEngine(broker, KillSwitchGate(kill_switch), journal, run_id="rr").execute(buy())
    # New engine instance, same run_id, same journal -- must append.
    ExecutionEngine(broker, KillSwitchGate(kill_switch), journal, run_id="rr").execute(buy())
    entries = journal.query({"run_id": "rr"})
    assert len(entries) == 2
    assert len({e.id for e in entries}) == 2


def test_order_validators_reject_garbage() -> None:
    with pytest.raises(Exception):
        LimitOrder(ticker="", side=OrderSide.BUY, quantity=1, limit_price=1.0)
    with pytest.raises(Exception):
        LimitOrder(ticker="TCS", side=OrderSide.BUY, quantity=1, limit_price=0.0)
    with pytest.raises(Exception):
        LimitOrder(ticker="TCS", side=OrderSide.BUY, quantity=1, limit_price=-5.0)


def test_to_tick_rounds_down_to_nse_grid() -> None:
    from quantos_core.brokers import to_tick

    # >= Rs250 band: 5-paise grid (unchanged by the 2024-06-10 reform)
    assert to_tick(547.02) == 547.00
    assert to_tick(547.04999) == 547.00
    assert to_tick(547.05) == 547.05
    # < Rs250 band: 1-paise grid — 196.29 is already on-grid post-reform
    assert to_tick(196.29) == 196.29
    assert to_tick(0.03) == 0.03
    assert to_tick(0.004) == 0.01  # floor of one tick, never zero
    # explicit tick override keeps the old flat-grid behavior available
    assert to_tick(196.29, tick=0.05) == 196.25
    assert to_tick(0.09999999, tick=0.05) == 0.05  # float-dust below a tick never rounds up past price
    with pytest.raises(ValueError):
        to_tick(0.0)
    with pytest.raises(ValueError):
        to_tick(-1.0)


def test_to_tick_up_never_lands_below_price() -> None:
    """A BUY limit floored below market rests unfilled forever — buy
    limits must round UP to the grid (finding: sub-Rs25 momentum names
    were silently excluded under the old flat 0.05 floor)."""
    from quantos_core.brokers import nse_tick_size, to_tick_up

    assert nse_tick_size(7.43) == 0.01
    assert nse_tick_size(249.99) == 0.01
    assert nse_tick_size(250.00) == 0.05
    # The IDEA-range scenario: market 7.43, +0.2% buffer = 7.44486.
    # Old behavior floored to 7.40 < market (never fills); now 7.45.
    assert to_tick_up(7.43 * 1.002) == 7.45
    assert to_tick_up(7.43 * 1.002) >= 7.43
    assert to_tick_up(547.02) == 547.05  # >= Rs250 band ceils on 0.05
    assert to_tick_up(547.05) == 547.05  # on-grid stays put
    assert to_tick_up(196.29) == 196.29
    with pytest.raises(ValueError):
        to_tick_up(0.0)


def test_angel_missing_availablecash_refuses_to_guess() -> None:
    adapter, _ = angel_logged_in([FakeResponse({"status": True, "data": {}})])
    with pytest.raises(BrokerConnectionError, match="availablecash"):
        adapter.available_cash()
