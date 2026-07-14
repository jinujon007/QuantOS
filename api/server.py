"""QuantOS Desktop -- local application server (WP-011, ADR-036).

FastAPI bound to 127.0.0.1 ONLY (Constitution Part III/Security: the
api module binds local-only by default; public exposure would need its
own ADR). Serves the desktop UI (api/app.html) and a small JSON API:

  GET  /api/state                     everything the UI shows
  GET  /api/broker/status             which broker sessions exist
  POST /api/broker/zerodha/login-url  daily-login URL for the operator
  POST /api/broker/zerodha/connect    request-token exchange + verify
  POST /api/broker/angel/connect      TOTP login + verify
  POST /api/broker/disconnect         drop the in-memory session
  POST /api/killswitch                the ONE write control (ADR-028)

Credential policy: broker secrets live in process memory for the app's
lifetime only -- never written to disk, never logged, never echoed
back. Closing the app forgets them (Kite tokens expire daily anyway).
"""

from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from api.collectors import REPO, collect_all, production_kill_switch
from quantos_core.brokers import (
    AngelOneSmartApiAdapter,
    BrokerError,
    ZerodhaKiteAdapter,
    exchange_request_token,
    kite_login_url,
)

app = FastAPI(title="QuantOS Desktop", docs_url=None, redoc_url=None)

# DNS-rebinding guard: 127.0.0.1 binding alone does not stop a browser the
# operator is already running from reaching this server via a rebound
# hostname (attacker.com -> 127.0.0.1 is same-origin to the attacker page,
# so no CORS preflight protects the kill switch). Reject any Host header
# that isn't the loopback names this app is actually served on.
# "testserver" is FastAPI TestClient's default Host.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

# In-memory broker sessions: {"zerodha": adapter, "angel": adapter}
_sessions: dict[str, Any] = {}


def _account_snapshot(adapter: Any) -> dict:
    """Read-only proof of connection: holdings + cash. Places nothing."""
    holdings = adapter.holdings()
    return {
        "connected": True,
        "holdings": holdings,
        "positions": len(holdings),
        "available_cash": adapter.available_cash(),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "app.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state() -> dict:
    payload = collect_all()
    payload["brokers"] = {name: True for name in _sessions}
    return payload


@app.get("/api/broker/status")
def broker_status() -> dict:
    return {name: True for name in _sessions}


class ZerodhaLoginUrl(BaseModel):
    api_key: str = Field(min_length=1)


@app.post("/api/broker/zerodha/login-url")
def zerodha_login_url(body: ZerodhaLoginUrl) -> dict:
    return {"url": kite_login_url(body.api_key)}


class ZerodhaConnect(BaseModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(default="")
    request_token: str = Field(default="")
    access_token: str = Field(default="")


@app.post("/api/broker/zerodha/connect")
def zerodha_connect(body: ZerodhaConnect) -> dict:
    try:
        token = body.access_token
        if not token:
            token = exchange_request_token(body.api_key, body.api_secret, body.request_token)
        adapter = ZerodhaKiteAdapter(body.api_key, token)
        snapshot = _account_snapshot(adapter)
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc
    _sessions["zerodha"] = adapter
    return snapshot


class AngelConnect(BaseModel):
    api_key: str = Field(min_length=1)
    client_code: str = Field(min_length=1)
    pin: str = Field(min_length=1)
    totp: str = Field(min_length=4)


@app.post("/api/broker/angel/connect")
def angel_connect(body: AngelConnect) -> dict:
    try:
        adapter = AngelOneSmartApiAdapter(body.api_key, body.client_code, symbol_tokens={})
        adapter.login(pin=body.pin, totp_code=body.totp)
        snapshot = _account_snapshot(adapter)
    except BrokerError as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc
    _sessions["angel"] = adapter
    return snapshot


class Disconnect(BaseModel):
    broker: Literal["zerodha", "angel"]


@app.post("/api/broker/disconnect")
def disconnect(body: Disconnect) -> dict:
    _sessions.pop(body.broker, None)
    return {"disconnected": body.broker}


class KillSwitchAction(BaseModel):
    action: Literal["engage", "release"]
    reason: str = Field(min_length=3, description="Goes in the audit record")


@app.post("/api/killswitch")
def kill_switch(body: KillSwitchAction) -> dict:
    switch = production_kill_switch()
    if body.action == "engage":
        switch.engage(body.reason)
    else:
        switch.release(body.reason)
    return {"engaged": switch.is_engaged()}


def main() -> None:
    import uvicorn

    assert REPO.is_dir()  # collectors resolved the repo root
    uvicorn.run(app, host="127.0.0.1", port=8742, log_level="warning")


if __name__ == "__main__":
    main()
