"""Broker connectivity probe -- READ-ONLY, places nothing (WP-008).

Run once real API credentials exist, to prove the native adapters
authenticate and read the account. Credentials come from environment
variables for this probe (never files, never git -- Constitution
Part III/Secrets; production wiring uses the OS credential store).

Zerodha (Kite Connect Personal -- free):
    $env:KITE_API_KEY      = "..."   # developers.kite.trade app
    $env:KITE_ACCESS_TOKEN = "..."   # from the daily request-token login
    python tools/broker_connect_check.py zerodha

Angel One (SmartAPI -- free):
    $env:ANGEL_API_KEY     = "..."
    $env:ANGEL_CLIENT_CODE = "..."
    $env:ANGEL_PIN         = "..."
    $env:ANGEL_TOTP        = "123456"   # current 6-digit code from the authenticator
    python tools/broker_connect_check.py angel
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantos_core.brokers import (  # noqa: E402
    AngelOneSmartApiAdapter,
    BrokerError,
    ZerodhaKiteAdapter,
)


def require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"Missing environment variable {name} -- see this file's docstring.")
    return value


def check_zerodha() -> None:
    adapter = ZerodhaKiteAdapter(require("KITE_API_KEY"), require("KITE_ACCESS_TOKEN"))
    print("Zerodha: authenticating + reading account (no orders will be placed)...")
    holdings = adapter.holdings()
    cash = adapter.available_cash()
    print(f"  CONNECTED. {len(holdings)} holdings, available cash {cash:,.2f}")


def check_angel() -> None:
    adapter = AngelOneSmartApiAdapter(require("ANGEL_API_KEY"), require("ANGEL_CLIENT_CODE"), symbol_tokens={})
    print("Angel One: logging in + reading account (no orders will be placed)...")
    adapter.login(pin=require("ANGEL_PIN"), totp_code=require("ANGEL_TOTP"))
    holdings = adapter.holdings()
    cash = adapter.available_cash()
    print(f"  CONNECTED. {len(holdings)} holdings, available cash {cash:,.2f}")


def main() -> int:
    target = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if target not in ("zerodha", "angel", "both"):
        raise SystemExit("Usage: python tools/broker_connect_check.py zerodha|angel|both")
    try:
        if target in ("zerodha", "both"):
            check_zerodha()
        if target in ("angel", "both"):
            check_angel()
    except BrokerError as exc:
        print(f"  FAILED (typed, fail-closed): {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
