"""Tests for the desktop app server (WP-011).

FastAPI TestClient, fully offline: state payload shape, kill-switch
write control round-trip (against a temp risk db via monkeypatch),
broker connect endpoints with faked adapters, and the Zerodha token
exchange's request construction. No network anywhere.
"""

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import api.server as server  # noqa: E402
from quantos_core.brokers import BrokerAuthError, exchange_request_token, kite_login_url  # noqa: E402
from quantos_core.risk import KillSwitch, KillSwitchState  # noqa: E402
from quantos_core.storage import SqliteRepository  # noqa: E402

client = TestClient(server.app)


def test_index_serves_the_app() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "QuantOS" in response.text
    assert "api/state" in response.text


def test_state_payload_shape() -> None:
    payload = client.get("/api/state").json()
    for key in ("paper", "kill_switch", "strategy", "equity", "universe", "journal", "brokers"):
        assert key in payload
    assert payload["strategy"]["params"]["top_n"] == 10


def test_kill_switch_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState)
    switch = KillSwitch(repo)
    monkeypatch.setattr(server, "production_kill_switch", lambda: switch)

    engaged = client.post("/api/killswitch", json={"action": "engage", "reason": "test halt"})
    assert engaged.status_code == 200 and engaged.json()["engaged"] is True
    released = client.post("/api/killswitch", json={"action": "release", "reason": "test resume"})
    assert released.json()["engaged"] is False


def test_kill_switch_requires_reason() -> None:
    assert client.post("/api/killswitch", json={"action": "engage", "reason": ""}).status_code == 422


def test_foreign_host_header_rejected() -> None:
    """DNS-rebinding guard: a rebound hostname must never reach a handler."""
    response = client.post(
        "/api/killswitch",
        json={"action": "release", "reason": "drive-by"},
        headers={"host": "attacker.example"},
    )
    assert response.status_code == 400


def test_non_json_content_type_rejected_on_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Form/simple-request CSRF guard: text/plain bodies must not flip the switch.

    This property currently comes from FastAPI's strict content-type default --
    pin it so a dependency or config change can't silently remove it.
    """
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(tmp_path / "risk.db", "kill_switch", KillSwitchState)
    switch = KillSwitch(repo)
    switch.engage("pinned halt")
    monkeypatch.setattr(server, "production_kill_switch", lambda: switch)

    response = client.post(
        "/api/killswitch",
        content='{"action": "release", "reason": "csrf"}',
        headers={"content-type": "text/plain"},
    )
    assert response.status_code in (415, 422)
    assert switch.is_engaged() is True


class FakeAdapter:
    def holdings(self) -> dict[str, int]:
        return {"TCS": 5}

    def available_cash(self) -> float:
        return 12345.0


def test_zerodha_connect_uses_exchange_and_verifies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server, "exchange_request_token", lambda k, s, r: "TOKEN123")
    monkeypatch.setattr(server, "ZerodhaKiteAdapter", lambda key, token: FakeAdapter())
    response = client.post(
        "/api/broker/zerodha/connect",
        json={"api_key": "k", "api_secret": "s", "request_token": "r", "access_token": ""},
    )
    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["connected"] and snapshot["holdings"] == {"TCS": 5}
    assert client.get("/api/broker/status").json() == {"zerodha": True}
    client.post("/api/broker/disconnect", json={"broker": "zerodha"})
    assert client.get("/api/broker/status").json() == {}


def test_zerodha_connect_maps_broker_error_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(k: str, s: str, r: str) -> str:
        raise BrokerAuthError("bad checksum")

    monkeypatch.setattr(server, "exchange_request_token", boom)
    response = client.post(
        "/api/broker/zerodha/connect",
        json={"api_key": "k", "api_secret": "s", "request_token": "r", "access_token": ""},
    )
    assert response.status_code == 502
    assert "bad checksum" in response.json()["detail"]


def test_angel_connect_with_fake_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAngel(FakeAdapter):
        def __init__(self, api_key: str, client_code: str, symbol_tokens: dict) -> None: ...
        def login(self, pin: str, totp_code: str) -> None: ...

    monkeypatch.setattr(server, "AngelOneSmartApiAdapter", FakeAngel)
    response = client.post(
        "/api/broker/angel/connect",
        json={"api_key": "k", "client_code": "C1", "pin": "1234", "totp": "654321"},
    )
    assert response.status_code == 200
    assert response.json()["available_cash"] == 12345.0
    client.post("/api/broker/disconnect", json={"broker": "angel"})


def test_login_url_shape() -> None:
    assert kite_login_url("abc") == "https://kite.zerodha.com/connect/login?v=3&api_key=abc"
    response = client.post("/api/broker/zerodha/login-url", json={"api_key": "abc"})
    assert response.json()["url"].endswith("api_key=abc")


def test_token_exchange_builds_correct_checksum() -> None:
    import hashlib

    captured: dict[str, Any] = {}

    class FakeSession:
        def post(self, url: str, **kwargs: Any) -> Any:
            captured.update(kwargs["data"])
            captured["url"] = url

            class R:
                status_code = 200

                def json(self) -> dict:
                    return {"status": "success", "data": {"access_token": "AT"}}

            return R()

    token = exchange_request_token("key", "secret", "req", session=FakeSession())  # type: ignore[arg-type]
    assert token == "AT"
    assert captured["url"].endswith("/session/token")
    assert captured["checksum"] == hashlib.sha256(b"keyreqsecret").hexdigest()


def test_token_exchange_refuses_blanks() -> None:
    with pytest.raises(BrokerAuthError):
        exchange_request_token("", "", "")
