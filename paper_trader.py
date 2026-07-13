"""
Paper Trading Monitor — run daily after market close (3:30 PM IST).
Tracks positions, calculates signals, logs decisions to data/paper_trades.csv.
No real orders — purely for validation before going live.

Usage:  python paper_trader.py          (check signals + update positions)
        python paper_trader.py --status  (just show current holdings)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, date
from pathlib import Path
from transaction_costs import BUY_RATE, SELL_RATE, DP_CHARGE_PER_SCRIP

# ── Parameters (must match momentum_backtest.py) ──────────────────────────────
TOP_N = 10
LOOKBACK_MONTHS = 12
SKIP_MONTHS = 1
STOP_LOSS_PCT = 0.08
TREND_MA_DAYS = 100         # Nifty 50 SMA period for bear market gate
INITIAL_CAPITAL = 100_000   # Virtual capital
# ─────────────────────────────────────────────────────────────────────────────

_DIR = Path(__file__).parent
STATE_FILE = _DIR / "data/paper_state.json"
LOG_FILE   = _DIR / "data/paper_trades.csv"
(_DIR / "data").mkdir(exist_ok=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        state.setdefault("pending_orders", [])
        return state
    return {"cash": float(INITIAL_CAPITAL), "holdings": {}, "pending_orders": [], "start_date": str(date.today())}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log_trade(action: str, ticker: str, price: float, shares: float, reason: str = ""):
    row = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "ticker": ticker,
        "price": round(price, 2),
        "shares": round(shares, 4),
        "value": round(price * shares, 2),
        "reason": reason,
    }
    df_new = pd.DataFrame([row])
    if LOG_FILE.exists():
        df_existing = pd.read_csv(LOG_FILE)
        pd.concat([df_existing, df_new], ignore_index=True).to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, index=False)


def fetch_current_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest close prices from yfinance."""
    if not tickers:
        return {}
    try:
        raw = yf.download(tickers, period="5d", auto_adjust=True, progress=False)
        if raw.empty:
            return {}
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw[["Close"]].rename(columns={"Close": tickers[0]})
        latest = close.ffill().iloc[-1]
        return {t: float(latest[t]) for t in tickers if t in latest and not pd.isna(latest[t])}
    except Exception as e:
        print(f"Price fetch error: {e}")
        return {}


def compute_momentum_scores() -> pd.Series:
    """Compute 12M-1M momentum for Nifty 500 universe using 1yr of data."""
    if not Path("nifty500_universe.csv").exists():
        print("ERROR: nifty500_universe.csv not found. Run fetch_universe.py first.")
        return pd.Series(dtype=float)

    universe = pd.read_csv("nifty500_universe.csv")
    tickers = universe["yf_ticker"].tolist()

    print(f"Fetching 14-month history for {len(tickers)} stocks...")
    try:
        raw = yf.download(tickers, period="14mo", auto_adjust=True, progress=False)
        if raw.empty:
            return pd.Series(dtype=float)
        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"]
        else:
            close = raw

        today = pd.Timestamp.today()
        end_dt = today - pd.DateOffset(months=SKIP_MONTHS)
        start_dt = end_dt - pd.DateOffset(months=LOOKBACK_MONTHS)

        p_end = close.loc[:end_dt].iloc[-1]
        p_start = close.loc[:start_dt].iloc[-1]
        momentum = p_end / p_start - 1

        valid = close.loc[start_dt:end_dt].count() >= 120
        return momentum[valid].dropna().sort_values(ascending=False)
    except Exception as e:
        print(f"Momentum compute error: {e}")
        return pd.Series(dtype=float)


def check_regime() -> bool:
    """Return True if market is in uptrend (Nifty 50 > 100-day MA). False = bear market."""
    try:
        t = yf.Ticker("^NSEI")
        df = t.history(period=f"{TREND_MA_DAYS + 30}d", auto_adjust=True)
        if df.empty:
            t = yf.Ticker("NIFTYBEES.NS")
            df = t.history(period=f"{TREND_MA_DAYS + 30}d", auto_adjust=True)
        if df.empty:
            print("  Regime check failed — assuming bull market.")
            return True
        close = df["Close"].copy()
        idx = pd.to_datetime(close.index)
        if idx.tz is not None:
            idx = idx.tz_convert(None)
        close.index = idx
        ma = close.rolling(TREND_MA_DAYS).mean()
        current = float(close.iloc[-1])
        current_ma = float(ma.iloc[-1])
        bull = current > current_ma
        status = "BULL" if bull else "BEAR"
        print(f"  Regime: Nifty {current:.0f} vs MA{TREND_MA_DAYS} {current_ma:.0f} → {status}")
        return bull
    except Exception as e:
        print(f"  Regime check error: {e} — assuming bull market.")
        return True


def fill_pending_orders(cash: float, holdings: dict, pending: list) -> tuple[float, dict, list]:
    """Execute orders queued on a PRIOR run at TODAY's fetched price. This is the
    T+1 fill: a signal decided on yesterday's close can only fill today — same-day
    fill on the close that produced the signal is look-ahead bias (a live order
    can't be placed until after the market that set that close has shut)."""
    if not pending:
        return cash, holdings, pending

    fill_prices = fetch_current_prices([o["ticker"] for o in pending])
    still_pending = []
    for o in pending:
        px = fill_prices.get(o["ticker"])
        if px is None or px <= 0:
            still_pending.append(o)  # retry on next run
            continue
        if o["type"] == "SELL":
            proceeds = o["shares"] * px * (1 - SELL_RATE) - DP_CHARGE_PER_SCRIP
            cash += proceeds
            log_trade("SELL", o["ticker"], px, o["shares"], f"{o['reason']}_filled")
            print(f"  FILLED SELL {o['ticker']} @ ₹{px:.2f}  (queued: {o['reason']})")
            holdings.pop(o["ticker"], None)
        elif o["type"] == "BUY":
            cost = o["allocation"] * (1 + BUY_RATE)
            if cash >= cost:
                shares = o["allocation"] / px
                cash -= cost
                holdings[o["ticker"]] = {"shares": shares, "entry_price": px}
                log_trade("BUY", o["ticker"], px, shares, f"{o['reason']}_filled")
                print(f"  FILLED BUY  {o['ticker']} @ ₹{px:.2f}  (queued: {o['reason']})")
            else:
                still_pending.append(o)  # insufficient cash, retry
    return cash, holdings, still_pending


def run_daily_update():
    state = load_state()
    cash = state["cash"]
    holdings = state["holdings"]  # {ticker: {shares, entry_price}}
    pending = state["pending_orders"]

    today = str(date.today())
    print(f"\n{'='*60}")
    print(f"  PAPER TRADER — {today}")
    print(f"{'='*60}")

    # ── Fill anything queued on the previous run, before today's signals ─────
    if pending:
        print(f"\n  Filling {len(pending)} order(s) queued last session...")
        cash, holdings, pending = fill_pending_orders(cash, holdings, pending)

    # ── Regime check ─────────────────────────────────────────────────────────
    bull_market = check_regime()

    # ── Current prices ────────────────────────────────────────────────────────
    all_tickers = list(holdings.keys())
    current_prices = fetch_current_prices(all_tickers) if all_tickers else {}

    # ── Portfolio value ───────────────────────────────────────────────────────
    pos_value = sum(
        holdings[t]["shares"] * current_prices.get(t, holdings[t]["entry_price"])
        for t in holdings
    )
    total_value = cash + pos_value
    initial = state.get("peak_value", INITIAL_CAPITAL)
    pnl_pct = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print(f"\n  Total Value:  ₹{total_value:>10,.0f}  ({pnl_pct:+.1f}% vs start)")
    print(f"  Cash:         ₹{cash:>10,.0f}")
    print(f"  Positions:    {len(holdings)}")

    if holdings:
        print(f"\n  Current Holdings:")
        for ticker, h in holdings.items():
            px = current_prices.get(ticker, h["entry_price"])
            pnl = (px / h["entry_price"] - 1) * 100
            stop = h["entry_price"] * (1 - STOP_LOSS_PCT)
            flag = " ⚠ NEAR STOP" if px < h["entry_price"] * (1 - STOP_LOSS_PCT * 0.7) else ""
            print(f"    {ticker:<20} entry ₹{h['entry_price']:>8.2f}  now ₹{px:>8.2f}  {pnl:>+6.1f}%  stop ₹{stop:>8.2f}{flag}")

    # ── Stop loss check — queue for fill next session, don't fill today ──────
    already_queued: set[str] = set()

    def queue_sell(ticker: str, reason: str):
        if ticker in already_queued:
            return
        pending.append({"type": "SELL", "ticker": ticker, "shares": holdings[ticker]["shares"], "reason": reason})
        already_queued.add(ticker)

    def queue_buy(ticker: str, allocation: float, reason: str):
        pending.append({"type": "BUY", "ticker": ticker, "allocation": allocation, "reason": reason})
        already_queued.add(ticker)

    triggered = []
    for ticker in list(holdings.keys()):
        px = current_prices.get(ticker)
        if px is None:
            continue
        entry = holdings[ticker]["entry_price"]
        if px <= entry * (1 - STOP_LOSS_PCT):
            print(f"\n  ⚠ STOP LOSS: {ticker} — entry ₹{entry:.2f}, now ₹{px:.2f}  (queued, fills next session)")
            queue_sell(ticker, "stop_loss")
            triggered.append(ticker)

    if triggered:
        print(f"  Stop losses triggered: {triggered}")

    # ── Bear market: queue full liquidation ───────────────────────────────────
    if not bull_market and holdings:
        print("\n  BEAR MARKET — queuing exit on all positions (fills next session).")
        for ticker in list(holdings.keys()):
            if ticker not in already_queued:
                queue_sell(ticker, "bear_market_exit")
                print(f"  QUEUE SELL {ticker}")

    # ── Weekly rebalance check (runs on Fridays) ──────────────────────────────
    weekday = date.today().weekday()  # 0=Mon, 4=Fri
    is_rebalance_day = (weekday == 4)

    if is_rebalance_day and not bull_market:
        print("\n  Bear market — skipping rebalance. Holding cash.")
    elif is_rebalance_day:
        print(f"\n  REBALANCE DAY — computing signals...")
        scores = compute_momentum_scores()

        if scores.empty:
            print("  Could not compute signals. Check data.")
        else:
            target = set(scores.nlargest(TOP_N).index)
            current = set(holdings.keys())

            to_sell = (current - target) - already_queued
            to_buy = target - current - already_queued

            # sorted(), not raw set iteration — Python randomizes string-hash
            # seed per process, so unsorted order would make fill order (and
            # therefore which orders succeed if cash runs short) non-deterministic.
            # Queue exits (fill next session)
            for ticker in sorted(to_sell):
                queue_sell(ticker, "rebalance_exit")
                print(f"  QUEUE SELL {ticker}")

            # Queue entries — allocation sized on TODAY's total value, filled at
            # tomorrow's price (shares = allocation / tomorrow's price)
            for ticker in sorted(to_buy):
                allocation = total_value / TOP_N
                queue_buy(ticker, allocation, "rebalance_entry")
                print(f"  QUEUE BUY  {ticker}  (₹{allocation:.0f} target allocation)")

            print(f"\n  Top 10 momentum scores today:")
            for t, s in scores.nlargest(TOP_N).items():
                held = "✓" if t in holdings else " "
                print(f"    [{held}] {t:<20} {s*100:>+7.1f}%")
    elif bull_market:
        days_to_friday = (4 - weekday) % 7
        print(f"\n  Next rebalance: Friday ({days_to_friday} days)")

    # ── Save state ────────────────────────────────────────────────────────────
    state["cash"] = cash
    state["holdings"] = holdings
    state["pending_orders"] = pending
    state["last_updated"] = today
    state["portfolio_value"] = total_value
    save_state(state)
    if pending:
        print(f"\n  {len(pending)} order(s) queued — will fill at next session's open prices.")
    print(f"  State saved → {STATE_FILE}")


def show_status():
    state = load_state()
    holdings = state["holdings"]
    cash = state["cash"]

    tickers = list(holdings.keys())
    prices = fetch_current_prices(tickers)
    pos_value = sum(
        holdings[t]["shares"] * prices.get(t, holdings[t]["entry_price"])
        for t in holdings
    )
    total = cash + pos_value
    pnl = (total - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print(f"\n  Portfolio: ₹{total:,.0f}  ({pnl:+.1f}%)  |  Cash: ₹{cash:,.0f}")
    print(f"  Last updated: {state.get('last_updated', 'never')}\n")

    if holdings:
        print(f"  {'Ticker':<20} {'Shares':>8} {'Entry':>10} {'Now':>10} {'P&L':>8}")
        print("  " + "-" * 60)
        for t, h in holdings.items():
            px = prices.get(t, h["entry_price"])
            pnl_pos = (px / h["entry_price"] - 1) * 100
            print(f"  {t:<20} {h['shares']:>8.2f} ₹{h['entry_price']:>8.2f} ₹{px:>8.2f} {pnl_pos:>+7.1f}%")
    else:
        print("  No holdings.")

    if LOG_FILE.exists():
        log = pd.read_csv(LOG_FILE)
        print(f"\n  Trade log: {len(log)} entries → {LOG_FILE}")

    pending = state.get("pending_orders", [])
    if pending:
        print(f"\n  {len(pending)} order(s) queued, awaiting next session's fill.")


def test_pending_order_fill():
    """Self-check: an order queued on day N must fill at day N+1's fetched price,
    not the price that triggered the signal — that's the whole point of the queue.
    Monkeypatches fetch_current_prices/log_trade so it needs no network or disk."""
    module = sys.modules[__name__]
    orig_fetch, orig_log = module.fetch_current_prices, module.log_trade

    module.fetch_current_prices = lambda tickers: {"TEST.NS": 90.0}
    module.log_trade = lambda *a, **k: None
    try:
        holdings = {"TEST.NS": {"shares": 10.0, "entry_price": 100.0}}
        pending = [{"type": "SELL", "ticker": "TEST.NS", "shares": 10.0, "reason": "stop_loss"}]
        cash, holdings, still_pending = fill_pending_orders(0.0, holdings, pending)
        assert still_pending == [], "order should fill when a price is available"
        assert "TEST.NS" not in holdings, "sold ticker must leave holdings only on fill, not on queue"
        expected = 10.0 * 90.0 * (1 - SELL_RATE) - DP_CHARGE_PER_SCRIP
        assert abs(cash - expected) < 1e-6, f"fill used wrong price: got {cash}, expected {expected}"

        holdings2 = {}
        pending2 = [{"type": "BUY", "ticker": "TEST.NS", "allocation": 900.0, "reason": "rebalance_entry"}]
        cash2, holdings2, still2 = fill_pending_orders(1000.0, holdings2, pending2)
        assert still2 == []
        assert holdings2["TEST.NS"]["entry_price"] == 90.0, "buy must fill at fetch-time price, not queue-time price"
        print("[PASS] test_pending_order_fill")
    finally:
        module.fetch_current_prices, module.log_trade = orig_fetch, orig_log


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        test_pending_order_fill()
        raise SystemExit(0)

    if "--status" in sys.argv:
        show_status()
    else:
        run_daily_update()
