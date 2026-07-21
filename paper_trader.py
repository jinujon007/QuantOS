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

from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from transaction_costs import BUY_RATE, DP_CHARGE_PER_SCRIP, SELL_RATE

# ── Parameters (must match momentum_backtest.py) ──────────────────────────────
TOP_N = 10
LOOKBACK_MONTHS = 12
SKIP_MONTHS = 1
STOP_LOSS_PCT = 0.08
TREND_MA_DAYS = 100  # Nifty 50 SMA period for bear market gate
INITIAL_CAPITAL = 100_000  # Virtual capital
# ─────────────────────────────────────────────────────────────────────────────

_DIR = Path(__file__).parent
STATE_FILE = _DIR / "data/paper_state.json"
LOG_FILE = _DIR / "data/paper_trades.csv"
EQUITY_FILE = _DIR / "data/paper_equity_history.csv"
(_DIR / "data").mkdir(exist_ok=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # Corrupt state (e.g. power loss mid-write). Silently reinitializing
            # to Rs 1L would erase the validation account — fail loud instead.
            bad = STATE_FILE.with_name(STATE_FILE.name + ".bad")
            STATE_FILE.replace(bad)
            print(f"ERROR: {STATE_FILE} is corrupt ({e}). Moved to {bad} — restore it manually before running.")
            raise SystemExit(1)
        state.setdefault("pending_orders", [])
        return state
    return {"cash": float(INITIAL_CAPITAL), "holdings": {}, "pending_orders": [], "start_date": str(date.today())}


def save_state(state: dict):
    # Atomic write: a crash mid-write must never leave truncated JSON behind.
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


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
    # True append — the old read-concat-rewrite pattern rewrote the whole
    # audit trail on every trade, so one mid-write kill destroyed it all.
    pd.DataFrame([row]).to_csv(LOG_FILE, mode="a", header=not LOG_FILE.exists(), index=False)


def log_equity_snapshot(day: str, total_value: float, cash: float, positions: int, degraded: bool = False) -> None:
    """Append one end-of-day equity row (WP-017, ADR-042) — the series the
    Sept-9 gate's "paper Sharpe > 1.0" is computed from (tools/paper_metrics.py).
    Pure logging: reads nothing back, alters no signal, state, or trading
    decision (CONTEXT.md freeze rule: permitted, clock intact). True append,
    same audit-trail rule as log_trade — a --force rerun writes a second row
    for the same date; readers keep the LAST row per date."""
    row = {
        "date": day,
        "total_value": round(total_value, 2),
        "cash": round(cash, 2),
        "positions": positions,
        "degraded": degraded,
    }
    pd.DataFrame([row]).to_csv(EQUITY_FILE, mode="a", header=not EQUITY_FILE.exists(), index=False)


def _fetch_close_frame(tickers: list[str]) -> pd.DataFrame | None:
    """Last ~5 sessions of closes (rows=dates, columns=tickers). None on failure."""
    if not tickers:
        return None
    try:
        raw = yf.download(tickers, period="5d", auto_adjust=True, progress=False)
        if raw.empty:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            return raw["Close"]
        return raw[["Close"]].rename(columns={"Close": tickers[0]})
    except Exception as e:
        print(f"Price fetch error: {e}")
        return None


def fetch_current_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest close prices from yfinance."""
    frame = _fetch_close_frame(tickers)
    if frame is None:
        return {}
    latest = frame.ffill().iloc[-1]
    return {t: float(latest[t]) for t in tickers if t in latest and not pd.isna(latest[t])}


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
        scores = momentum[valid].dropna().sort_values(ascending=False)

        # Coverage floor: yfinance rate-limiting can silently return a subset
        # of the universe. Ranking a partial universe produces a confidently
        # wrong top-10 — refuse rather than trade on it.
        if len(scores) < 0.8 * len(tickers):
            print(f"  Universe coverage too low: {len(scores)}/{len(tickers)} tickers ranked — refusing to rank.")
            return pd.Series(dtype=float)
        return scores
    except Exception as e:
        print(f"Momentum compute error: {e}")
        return pd.Series(dtype=float)


def check_regime() -> bool | None:
    """True = uptrend (Nifty 50 > 100-day MA), False = bear market,
    None = UNKNOWN (data unavailable). An unknown regime must never be
    guessed: assuming bull during an outage would keep buying through a
    real bear market — the exact failure the filter exists to prevent."""
    try:
        t = yf.Ticker("^NSEI")
        df = t.history(period=f"{TREND_MA_DAYS + 30}d", auto_adjust=True)
        if df.empty:
            t = yf.Ticker("NIFTYBEES.NS")
            df = t.history(period=f"{TREND_MA_DAYS + 30}d", auto_adjust=True)
        if df.empty:
            print("  Regime check failed — regime UNKNOWN (no trading actions this run).")
            return None
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
        print(f"  Regime check error: {e} — regime UNKNOWN (no trading actions this run).")
        return None


def fill_pending_orders(cash: float, holdings: dict, pending: list) -> tuple[float, dict, list]:
    """Execute orders queued on a PRIOR run at TODAY's fetched price. This is the
    T+1 fill: a signal decided on yesterday's close can only fill today — same-day
    fill on the close that produced the signal is look-ahead bias (a live order
    can't be placed until after the market that set that close has shut)."""
    if not pending:
        return cash, holdings, pending

    frame = _fetch_close_frame([o["ticker"] for o in pending])
    if frame is None or frame.empty:
        return cash, holdings, pending  # no prices at all — retry next run
    # The date of the newest price bar. An order may only fill on a bar
    # NEWER than the one it was queued on — otherwise a same-day re-run or
    # a market-holiday ffill executes at the very close that produced the
    # signal (the look-ahead this queue exists to prevent).
    bar_date = str(frame.index[-1].date())
    latest = frame.ffill().iloc[-1]

    still_pending = []
    for o in pending:
        if bar_date <= o.get("queued_on", ""):
            still_pending.append(o)  # no new bar since queue — hold
            continue
        px = latest.get(o["ticker"])
        if px is None or pd.isna(px) or px <= 0:
            still_pending.append(o)  # retry on next run
            continue
        px = float(px)
        if o["type"] == "SELL":
            if o["ticker"] not in holdings:
                # Holding already gone (e.g. exited via an earlier order).
                # Crediting a second time would corrupt the cash books.
                print(f"  DROPPED SELL {o['ticker']} — no matching holding.")
                continue
            proceeds = o["shares"] * px * (1 - SELL_RATE) - DP_CHARGE_PER_SCRIP
            cash += proceeds
            log_trade("SELL", o["ticker"], px, o["shares"], f"{o['reason']}_filled")
            print(f"  FILLED SELL {o['ticker']} @ ₹{px:.2f}  (queued: {o['reason']})")
            holdings.pop(o["ticker"])
        elif o["type"] == "BUY":
            if o["ticker"] in holdings:
                print(f"  DROPPED BUY {o['ticker']} — already held (duplicate order).")
                continue
            cost = o["allocation"] * (1 + BUY_RATE)
            if cash >= cost:
                shares = o["allocation"] / px
                cash -= cost
                holdings[o["ticker"]] = {"shares": shares, "entry_price": px}
                log_trade("BUY", o["ticker"], px, shares, f"{o['reason']}_filled")
                print(f"  FILLED BUY  {o['ticker']} @ ₹{px:.2f}  (queued: {o['reason']})")
            else:
                # Same semantics as the backtest: when cash runs short the
                # buy simply doesn't happen this cycle. Leaving it pending
                # forever would fill weeks later at a stale allocation.
                print(f"  DROPPED BUY {o['ticker']} — insufficient cash (₹{cash:,.0f} < ₹{cost:,.0f}).")
    return cash, holdings, still_pending


def run_daily_update(force: bool = False):
    # ── Kill switch — the operator's halt must halt THIS system too ──────────
    try:
        from api.collectors import production_kill_switch

        halted = production_kill_switch().is_engaged()
    except Exception as e:
        print(f"  Kill-switch state unreadable ({e}) — refusing to run (fail closed).")
        raise SystemExit(1)
    if halted:
        print("  KILL SWITCH ENGAGED — daily run halted. Release via tools/kill_switch.py or the desktop app.")
        raise SystemExit(2)

    state = load_state()
    cash = state["cash"]
    holdings = state["holdings"]  # {ticker: {shares, entry_price}}
    pending = state["pending_orders"]
    degraded: list[str] = []

    today = str(date.today())
    if state.get("last_updated") == today and not force:
        print(f"  Already ran today ({today}) — skipping to avoid concurrent state writes. Use --force to rerun.")
        return

    print(f"\n{'=' * 60}")
    print(f"  PAPER TRADER — {today}")
    print(f"{'=' * 60}")

    # ── Fill anything queued on the previous run, before today's signals ─────
    if pending:
        print(f"\n  Filling {len(pending)} order(s) queued last session...")
        cash, holdings, pending = fill_pending_orders(cash, holdings, pending)
        # Persist fills IMMEDIATELY: log_trade already wrote the trade rows,
        # and the Friday signal fetch below can run for minutes — a crash or
        # scheduler kill in between would re-fill these orders on the next run.
        state.update(cash=cash, holdings=holdings, pending_orders=pending)
        save_state(state)

    # ── Regime check ─────────────────────────────────────────────────────────
    regime = check_regime()  # True=bull, False=bear, None=unknown
    bull_market = regime is True
    if regime is None:
        degraded.append("regime unknown — no trading actions taken")

    # ── Current prices ────────────────────────────────────────────────────────
    all_tickers = list(holdings.keys())
    current_prices = fetch_current_prices(all_tickers) if all_tickers else {}
    if all_tickers and not current_prices:
        degraded.append("price fetch failed — stop-losses unmonitored this run")

    # ── Portfolio value ───────────────────────────────────────────────────────
    pos_value = sum(holdings[t]["shares"] * current_prices.get(t, holdings[t]["entry_price"]) for t in holdings)
    total_value = cash + pos_value
    initial = state.get("peak_value", INITIAL_CAPITAL)
    pnl_pct = (total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

    print(f"\n  Total Value:  ₹{total_value:>10,.0f}  ({pnl_pct:+.1f}% vs start)")
    print(f"  Cash:         ₹{cash:>10,.0f}")
    print(f"  Positions:    {len(holdings)}")

    if holdings:
        print("\n  Current Holdings:")
        for ticker, h in holdings.items():
            px = current_prices.get(ticker, h["entry_price"])
            pnl = (px / h["entry_price"] - 1) * 100
            stop = h["entry_price"] * (1 - STOP_LOSS_PCT)
            flag = " ⚠ NEAR STOP" if px < h["entry_price"] * (1 - STOP_LOSS_PCT * 0.7) else ""
            print(
                f"    {ticker:<20} entry ₹{h['entry_price']:>8.2f}  now ₹{px:>8.2f}  {pnl:>+6.1f}%  stop ₹{stop:>8.2f}{flag}"
            )

    # ── Stop loss check — queue for fill next session, don't fill today ──────
    # Seeded from orders still pending from prior sessions: queueing a ticker
    # that already has a live pending order would create duplicates, and a
    # duplicate SELL double-credits cash / duplicate BUY double-debits it.
    already_queued: set[str] = {o["ticker"] for o in pending}

    def queue_sell(ticker: str, reason: str):
        if ticker in already_queued:
            return
        pending.append(
            {
                "type": "SELL",
                "ticker": ticker,
                "shares": holdings[ticker]["shares"],
                "reason": reason,
                "queued_on": today,
            }
        )
        already_queued.add(ticker)

    def queue_buy(ticker: str, allocation: float, reason: str):
        pending.append(
            {"type": "BUY", "ticker": ticker, "allocation": allocation, "reason": reason, "queued_on": today}
        )
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
    # Only on a CONFIRMED bear regime. An unknown regime must not liquidate —
    # a yfinance outage would otherwise dump the whole portfolio.
    if regime is False and holdings:
        print("\n  BEAR MARKET — queuing exit on all positions (fills next session).")
        for ticker in list(holdings.keys()):
            if ticker not in already_queued:
                queue_sell(ticker, "bear_market_exit")
                print(f"  QUEUE SELL {ticker}")

    # ── Weekly rebalance check (Fridays; Sat/Sun catch up a missed Friday) ────
    weekday = date.today().weekday()  # 0=Mon, 4=Fri
    last_friday = date.today() - timedelta(days=(weekday - 4) % 7)
    # Catch-up: if the machine was asleep/logged-out at Friday 15:40, the
    # scheduler fires later (StartWhenAvailable). A weekend run must still do
    # the week's rebalance — signals off Friday's close, fills Monday — or the
    # validation record silently loses a week. last_rebalance_date guards
    # against double-rebalancing when Friday's run DID happen.
    is_rebalance_day = weekday >= 4 and state.get("last_rebalance_date", "") < str(last_friday)

    if is_rebalance_day and regime is None:
        print("\n  Rebalance due but regime UNKNOWN — refusing to trade blind. Will retry next run.")
    elif is_rebalance_day and regime is False:
        print("\n  Bear market — skipping rebalance. Holding cash.")
        state["last_rebalance_date"] = str(last_friday)
    elif is_rebalance_day:
        print("\n  REBALANCE DAY — computing signals...")
        scores = compute_momentum_scores()

        if scores.empty:
            print("  Could not compute signals. Check data.")
            degraded.append("rebalance due but signals unavailable")
        else:
            state["last_rebalance_date"] = str(last_friday)
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

            print("\n  Top 10 momentum scores today:")
            for t, s in scores.nlargest(TOP_N).items():
                held = "✓" if t in holdings else " "
                print(f"    [{held}] {t:<20} {s * 100:>+7.1f}%")
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
    # Equity history AFTER state is durably saved: the row must describe a
    # day that actually persisted. Degraded runs still record (flagged) —
    # a gap would silently bias the Sharpe series toward healthy days.
    log_equity_snapshot(today, total_value, cash, len(holdings), degraded=bool(degraded))
    if pending:
        print(f"\n  {len(pending)} order(s) queued — will fill at next session's open prices.")
    print(f"  State saved → {STATE_FILE}")

    if degraded:
        # Exit nonzero so the unattended runner logs FAILED instead of OK —
        # a silent degraded run is indistinguishable from a healthy one in
        # data/daily_run.log otherwise. State is already saved above.
        print(f"\n  DEGRADED RUN: {'; '.join(degraded)}")
        raise SystemExit(1)


def show_status():
    state = load_state()
    holdings = state["holdings"]
    cash = state["cash"]

    tickers = list(holdings.keys())
    prices = fetch_current_prices(tickers)
    pos_value = sum(holdings[t]["shares"] * prices.get(t, holdings[t]["entry_price"]) for t in holdings)
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
    Also pins the book-integrity guards: same-bar fills refused, orphan SELLs and
    duplicate/unaffordable BUYs dropped. Monkeypatches _fetch_close_frame/log_trade
    so it needs no network or disk."""
    module = sys.modules[__name__]
    orig_fetch, orig_log = module._fetch_close_frame, module.log_trade

    frame = pd.DataFrame({"TEST.NS": [90.0]}, index=[pd.Timestamp("2026-01-02")])
    module._fetch_close_frame = lambda tickers: frame
    module.log_trade = lambda *a, **k: None
    try:
        # 1) T+1 SELL fills at fetch-time price (queued before the newest bar)
        holdings = {"TEST.NS": {"shares": 10.0, "entry_price": 100.0}}
        pending = [
            {"type": "SELL", "ticker": "TEST.NS", "shares": 10.0, "reason": "stop_loss", "queued_on": "2026-01-01"}
        ]
        cash, holdings, still_pending = fill_pending_orders(0.0, holdings, pending)
        assert still_pending == [], "order should fill when a price is available"
        assert "TEST.NS" not in holdings, "sold ticker must leave holdings only on fill, not on queue"
        expected = 10.0 * 90.0 * (1 - SELL_RATE) - DP_CHARGE_PER_SCRIP
        assert abs(cash - expected) < 1e-6, f"fill used wrong price: got {cash}, expected {expected}"

        # 2) Same-bar fill refused: queued on the newest bar's date → must hold
        pending = [
            {"type": "SELL", "ticker": "TEST.NS", "shares": 10.0, "reason": "stop_loss", "queued_on": "2026-01-02"}
        ]
        cash2, _, still2 = fill_pending_orders(0.0, {"TEST.NS": {"shares": 10.0, "entry_price": 100.0}}, pending)
        assert still2 == pending, "same-bar fill is look-ahead — order must stay pending"
        assert cash2 == 0.0, "no cash may move on a refused fill"

        # 3) SELL with no matching holding is dropped, cash untouched
        orphan = [
            {"type": "SELL", "ticker": "TEST.NS", "shares": 10.0, "reason": "stop_loss", "queued_on": "2026-01-01"}
        ]
        cash3, _, still3 = fill_pending_orders(0.0, {}, orphan)
        assert still3 == [] and cash3 == 0.0, "orphan SELL must be dropped without crediting cash"

        # 4) T+1 BUY fills at fetch-time price
        pending4 = [
            {
                "type": "BUY",
                "ticker": "TEST.NS",
                "allocation": 900.0,
                "reason": "rebalance_entry",
                "queued_on": "2026-01-01",
            }
        ]
        cash4, holdings4, still4 = fill_pending_orders(1000.0, {}, pending4)
        assert still4 == []
        assert holdings4["TEST.NS"]["entry_price"] == 90.0, "buy must fill at fetch-time price, not queue-time price"

        # 5) Unaffordable BUY is dropped (backtest semantics), never pends forever
        broke = [
            {
                "type": "BUY",
                "ticker": "TEST.NS",
                "allocation": 900.0,
                "reason": "rebalance_entry",
                "queued_on": "2026-01-01",
            }
        ]
        cash5, holdings5, still5 = fill_pending_orders(100.0, {}, broke)
        assert still5 == [] and holdings5 == {} and cash5 == 100.0, "unaffordable buy must be dropped, cash untouched"

        # 6) BUY for an already-held ticker is dropped (duplicate guard)
        dup = [
            {
                "type": "BUY",
                "ticker": "TEST.NS",
                "allocation": 900.0,
                "reason": "rebalance_entry",
                "queued_on": "2026-01-01",
            }
        ]
        held = {"TEST.NS": {"shares": 5.0, "entry_price": 80.0}}
        cash6, holdings6, still6 = fill_pending_orders(1000.0, held, dup)
        assert still6 == [] and cash6 == 1000.0 and holdings6["TEST.NS"]["shares"] == 5.0, (
            "duplicate buy must not double-debit cash or overwrite the holding"
        )
        print("[PASS] test_pending_order_fill")
    finally:
        module._fetch_close_frame, module.log_trade = orig_fetch, orig_log


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        test_pending_order_fill()
        raise SystemExit(0)

    if "--status" in sys.argv:
        show_status()
    else:
        run_daily_update(force="--force" in sys.argv)
