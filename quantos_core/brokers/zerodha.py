"""ZerodhaKiteAdapter (WP-008) -- ADR-011 implementation #2.

Native Kite Connect v3 HTTP adapter (no kiteconnect SDK dependency;
~150 lines cover our CNC-limit weekly use). Personal plan: order/
portfolio APIs free; access_token obtained via the daily browser
request-token flow and passed in ready-made -- this adapter never
handles the login redirect itself.

No POST retries anywhere: a connection error mid-placement leaves the
order state UNKNOWN (BrokerConnectionError) for the caller to
reconcile -- retrying a possibly-accepted order is a duplicate-order
bug, not resilience (Constitution Part V, ambiguous fill state).
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

_BASE = "https://api.kite.trade"
_TIMEOUT = 15.0


def kite_login_url(api_key: str) -> str:
    """The browser URL where the operator logs in daily; Zerodha
    redirects back with a request_token to exchange below."""
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"


def exchange_request_token(
    api_key: str, api_secret: str, request_token: str, session: requests.Session | None = None
) -> str:
    """Kite Connect v3 daily token exchange: request_token -> access_token.

    checksum = sha256(api_key + request_token + api_secret). The secret
    is used transiently and never stored or logged by this function.
    Raises BrokerAuthError on any failure -- never a guessed token.
    """
    import hashlib

    if not (api_key and api_secret and request_token):
        raise BrokerAuthError("Token exchange requires api_key, api_secret and request_token")
    checksum = hashlib.sha256((api_key + request_token + api_secret).encode()).hexdigest()
    http = session or requests.Session()
    try:
        response = http.post(
            f"{_BASE}/session/token",
            data={"api_key": api_key, "request_token": request_token, "checksum": checksum},
            headers={"X-Kite-Version": "3"},
            timeout=_TIMEOUT,
        )
        payload: dict[str, Any] = response.json()
    except requests.RequestException as exc:
        raise BrokerConnectionError(f"Kite unreachable during token exchange: {exc}") from exc
    except ValueError as exc:
        raise BrokerAuthError("Kite returned non-JSON during token exchange") from exc
    token = payload.get("data", {}).get("access_token") if payload.get("status") == "success" else None
    if not token:
        raise BrokerAuthError(f"Kite token exchange failed: {payload.get('message', 'unknown error')}")
    return str(token)


class ZerodhaKiteAdapter:
    """Composes OrderPlacer + AccountReader against Kite Connect v3."""

    def __init__(self, api_key: str, access_token: str, session: requests.Session | None = None) -> None:
        if not api_key or not access_token:
            raise BrokerAuthError("Zerodha adapter requires both api_key and access_token -- refusing to construct")
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
        }
        self._session = session or requests.Session()

    def _parse(self, response: Any, context: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exc:
            raise BrokerConnectionError(f"Kite returned non-JSON for {context} (HTTP {response.status_code})") from exc
        if payload.get("status") == "success":
            data: dict[str, Any] | list[Any] = payload.get("data", {})
            return {"data": data}
        error_type = payload.get("error_type", "")
        message = payload.get("message", "unknown Kite error")
        if error_type == "TokenException" or response.status_code in (401, 403):
            raise BrokerAuthError(f"Kite auth failure on {context}: {message}")
        if response.status_code >= 500 or error_type in ("NetworkException", "GeneralException", "DataException"):
            # Kite's own backend/OMS errors: the request may or may not
            # have been processed. That is UNKNOWN state, never a
            # rejection -- treating it as rejected licenses a re-place,
            # which is the duplicate-order bug.
            raise BrokerConnectionError(f"Kite backend error on {context} -- state UNKNOWN, reconcile: {message}")
        raise OrderRejectedError(f"Kite rejected {context}: {message}")

    def place_order(self, order: LimitOrder) -> OrderReceipt:
        form = {
            "tradingsymbol": order.ticker,
            "exchange": "NSE",
            "transaction_type": order.side.value,
            "order_type": "LIMIT",
            "quantity": str(order.quantity),
            "price": f"{order.limit_price:.2f}",
            "product": "CNC",
            "validity": "DAY",
        }
        try:
            response = self._session.post(f"{_BASE}/orders/regular", data=form, headers=self._headers, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            raise BrokerConnectionError(
                f"Kite unreachable placing {order.ticker} order -- state UNKNOWN: {exc}"
            ) from exc
        data = self._parse(response, f"place_order({order.ticker})")["data"]
        order_id = data.get("order_id") if isinstance(data, dict) else None
        if not order_id:
            raise BrokerConnectionError(
                f"Kite accepted place_order({order.ticker}) but returned no order_id -- state UNKNOWN, reconcile"
            )
        # Kite accepts asynchronously; fills are confirmed later via the
        # order book. OPEN is the only honest status at placement time.
        return OrderReceipt(broker_order_id=str(order_id), status="OPEN", filled_quantity=0, average_price=None)

    def _get(self, path: str, context: str) -> dict[str, Any]:
        try:
            response = self._session.get(f"{_BASE}{path}", headers=self._headers, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            raise BrokerConnectionError(f"Kite unreachable on {context}: {exc}") from exc
        return self._parse(response, context)

    def holdings(self) -> dict[str, int]:
        rows = self._get("/portfolio/holdings", "holdings")["data"]
        # "status": "success" with "data": null (or a non-list shape) is an
        # ambiguous body, not an empty portfolio -- returning {} here would
        # disguise a failure as "all positions gone" (same guard as Angel).
        if not isinstance(rows, list):
            raise BrokerConnectionError("Kite holdings returned success without a holdings list -- state ambiguous")
        try:
            return {str(row["tradingsymbol"]): int(row["quantity"]) for row in rows}
        except (KeyError, TypeError) as exc:
            raise BrokerConnectionError(f"Kite holdings row missing expected fields: {exc}") from exc

    def available_cash(self) -> float:
        data = self._get("/user/margins", "margins")["data"]
        try:
            return float(data["equity"]["available"]["live_balance"])
        except (KeyError, TypeError) as exc:
            # Missing intermediate keys / data:null: ambiguous margin state
            # must be a typed failure, never a raw KeyError (Angel parity).
            raise BrokerConnectionError(f"Kite margins response missing expected fields: {exc}") from exc
