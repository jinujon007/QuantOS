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
        # Kite accepts asynchronously; fills are confirmed later via the
        # order book. OPEN is the only honest status at placement time.
        return OrderReceipt(broker_order_id=str(data["order_id"]), status="OPEN", filled_quantity=0, average_price=None)

    def _get(self, path: str, context: str) -> dict[str, Any]:
        try:
            response = self._session.get(f"{_BASE}{path}", headers=self._headers, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            raise BrokerConnectionError(f"Kite unreachable on {context}: {exc}") from exc
        return self._parse(response, context)

    def holdings(self) -> dict[str, int]:
        rows = self._get("/portfolio/holdings", "holdings")["data"]
        return {str(row["tradingsymbol"]): int(row["quantity"]) for row in rows}

    def available_cash(self) -> float:
        data = self._get("/user/margins", "margins")["data"]
        return float(data["equity"]["available"]["live_balance"])
