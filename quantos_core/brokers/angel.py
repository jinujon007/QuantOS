"""AngelOneSmartApiAdapter (WP-008) -- ADR-011 implementation #3.

Native SmartAPI HTTP adapter (no smartapi-python dependency -- that
SDK is 17 months stale per the 2026-07-14 verified research). Login is
an explicit method taking the current TOTP code; the adapter refuses
every call until a session exists (fail-closed, never a silent guess).

SmartAPI quirks encoded here (pattern-verified against the OpenAlgo
broker/angel reference tree, reimplemented not copied):
- every request carries the X-PrivateKey (api key) header block;
- equities trade as "<SYMBOL>-EQ" with a numeric symboltoken from the
  instrument master -- tokens are injected via constructor mapping
  until Phase 8 hardening adds the master download;
- product type for delivery is DELIVERY (not CNC).

No POST retries: same UNKNOWN-state rule as the Zerodha adapter.
"""

from typing import Any

import requests

from quantos_core.brokers.orders import (
    BrokerAuthError,
    BrokerConnectionError,
    LimitOrder,
    OrderReceipt,
    OrderRejectedError,
)

_BASE = "https://apiconnect.angelone.in"
_TIMEOUT = 15.0


class AngelOneSmartApiAdapter:
    """Composes OrderPlacer + AccountReader against Angel One SmartAPI."""

    def __init__(
        self,
        api_key: str,
        client_code: str,
        symbol_tokens: dict[str, str],
        session: requests.Session | None = None,
    ) -> None:
        if not api_key or not client_code:
            raise BrokerAuthError("Angel adapter requires api_key and client_code -- refusing to construct")
        self._api_key = api_key
        self._client_code = client_code
        self._symbol_tokens = dict(symbol_tokens)
        self._session = session or requests.Session()
        self._jwt: str | None = None

    def _headers(self, authorized: bool) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self._api_key,
        }
        if authorized:
            if self._jwt is None:
                raise BrokerAuthError("Angel session not established -- call login() first")
            headers["Authorization"] = f"Bearer {self._jwt}"
        return headers

    def _parse(self, response: Any, context: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise BrokerConnectionError(
                f"SmartAPI returned non-JSON for {context} (HTTP {response.status_code})"
            ) from exc
        if payload.get("status") is True:
            return payload
        message = f"{payload.get('errorcode', '')} {payload.get('message', 'unknown SmartAPI error')}".strip()
        if response.status_code in (401, 403) or str(payload.get("errorcode", "")).startswith("AG8"):
            raise BrokerAuthError(f"SmartAPI auth failure on {context}: {message}")
        raise OrderRejectedError(f"SmartAPI rejected {context}: {message}")

    def _post(self, path: str, body: dict[str, Any], context: str, authorized: bool = True) -> dict[str, Any]:
        try:
            response = self._session.post(
                f"{_BASE}{path}", json=body, headers=self._headers(authorized), timeout=_TIMEOUT
            )
        except requests.RequestException as exc:
            raise BrokerConnectionError(f"SmartAPI unreachable on {context} -- state UNKNOWN: {exc}") from exc
        return self._parse(response, context)

    def login(self, pin: str, totp_code: str) -> None:
        """Establish the daily session (SEBI: 2FA per API session)."""
        payload = self._post(
            "/rest/auth/angelbroking/user/v1/loginByPassword",
            {"clientcode": self._client_code, "password": pin, "totp": totp_code},
            "login",
            authorized=False,
        )
        token = payload.get("data", {}).get("jwtToken")
        if not token:
            raise BrokerAuthError("SmartAPI login succeeded but returned no jwtToken -- refusing ambiguous session")
        self._jwt = str(token)

    def place_order(self, order: LimitOrder) -> OrderReceipt:
        token = self._symbol_tokens.get(order.ticker)
        if token is None:
            raise OrderRejectedError(f"No SmartAPI symboltoken known for {order.ticker!r} -- refusing to guess")
        body = {
            "variety": "NORMAL",
            "tradingsymbol": f"{order.ticker}-EQ",
            "symboltoken": token,
            "transactiontype": order.side.value,
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": f"{order.limit_price:.2f}",
            "quantity": str(order.quantity),
        }
        payload = self._post("/rest/secure/angelbroking/order/v1/placeOrder", body, f"place_order({order.ticker})")
        order_id = payload.get("data", {}).get("orderid")
        if not order_id:
            raise BrokerConnectionError(f"SmartAPI accepted {order.ticker} order but returned no orderid -- UNKNOWN")
        return OrderReceipt(broker_order_id=str(order_id), status="OPEN", filled_quantity=0, average_price=None)

    def _get(self, path: str, context: str) -> dict[str, Any]:
        try:
            response = self._session.get(f"{_BASE}{path}", headers=self._headers(True), timeout=_TIMEOUT)
        except requests.RequestException as exc:
            raise BrokerConnectionError(f"SmartAPI unreachable on {context}: {exc}") from exc
        return self._parse(response, context)

    def holdings(self) -> dict[str, int]:
        payload = self._get("/rest/secure/angelbroking/portfolio/v1/getAllHolding", "holdings")
        rows = payload.get("data", {}).get("holdings", []) or []
        return {str(row["tradingsymbol"]).removesuffix("-EQ"): int(row["quantity"]) for row in rows}

    def available_cash(self) -> float:
        payload = self._get("/rest/secure/angelbroking/user/v1/getRMS", "funds")
        return float(payload.get("data", {}).get("availablecash", 0.0) or 0.0)
