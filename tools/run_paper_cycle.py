"""Shadow paper cycle (WP-013, ADR-038).

    python tools/run_paper_cycle.py

Runs quantos_core's `paper.run_cycle` beside the legacy loop with the
SAME kind of fetched inputs, its own state under data/shadow/, and then
compares its books to data/paper_state.json. paper_trader.py remains
the system of record; this shadow accumulates the side-by-side evidence
that gates cutover (two consecutive clean weekly rebalances matching).

Exit codes: 0 = books match (or first-day seed / halted), 1 = divergence
or error -- surfaces as DEGRADED in the daily-run console tile.

Reuses the frozen script's own fetchers (tools may import root scripts;
quantos_core may not) so both systems see the same market inputs.
"""

import json
import sys
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import paper_trader  # noqa: E402  (frozen script -- fetchers reused for input parity)
from api.collectors import production_kill_switch  # noqa: E402
from quantos_core.factors import momentum_12m1m  # noqa: E402
from quantos_core.paper import CycleReport, MarketSnapshot, run_cycle  # noqa: E402
from quantos_core.portfolio import (  # noqa: E402
    PendingOrder,
    PortfolioState,
    Position,
    ZerodhaDeliveryCostModel,
)
from quantos_core.storage import EntityNotFoundError, SqliteRepository  # noqa: E402
from quantos_core.strategies import MomentumV1, load_momentum_params  # noqa: E402

SHADOW_DIR = REPO / "data" / "shadow"
ACCOUNT_ID = "paper"
COVERAGE_FLOOR = 0.8  # same refusal threshold as paper_trader.compute_momentum_scores


def seed_from_legacy_state(store: SqliteRepository[PortfolioState]) -> PortfolioState:
    """First run: adopt the legacy account's books verbatim."""
    legacy = json.loads((REPO / "data" / "paper_state.json").read_text())
    positions = {
        ticker: Position(shares=h["shares"], entry_price=h["entry_price"])
        for ticker, h in legacy.get("holdings", {}).items()
    }
    pending = [
        PendingOrder(
            side=o["type"],
            ticker=o["ticker"],
            shares=o.get("shares") if o["type"] == "SELL" else None,
            allocation=o.get("allocation") if o["type"] == "BUY" else None,
            reason=o.get("reason", "seeded"),
            queued_on=o.get("queued_on", ""),
        )
        for o in legacy.get("pending_orders", [])
    ]
    state = PortfolioState(
        id=ACCOUNT_ID,
        cash=legacy["cash"],
        positions=positions,
        pending=pending,
        start_date=legacy.get("start_date", str(date.today())),
        last_updated="",  # let the shadow run today even if legacy already did
        last_rebalance_date=legacy.get("last_rebalance_date", ""),
    )
    store.save(state)
    print(f"Seeded shadow account from data/paper_state.json (cash {state.cash:,.0f}, {len(positions)} positions)")
    return state


def build_market_snapshot(state: PortfolioState, rebalance_may_be_due: bool) -> MarketSnapshot:
    tickers = sorted(set(state.positions) | state.queued_tickers())
    frame = paper_trader._fetch_close_frame(tickers) if tickers else None
    latest_close: dict[str, float] = {}
    bar_date = ""
    if frame is not None and not frame.empty:
        bar_date = str(frame.index[-1].date())
        latest = frame.ffill().iloc[-1]
        latest_close = {t: float(latest[t]) for t in tickers if t in latest and not pd.isna(latest[t])}

    regime = paper_trader.check_regime()

    prices: pd.DataFrame | None = None
    if rebalance_may_be_due and regime is True:
        universe = pd.read_csv(REPO / "nifty500_universe.csv")["yf_ticker"].tolist()
        try:
            raw = yf.download(universe, period="14mo", auto_adjust=True, progress=False)
            close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            params = load_momentum_params(REPO / "strategies_registry" / "momentum_v1.yaml")
            scores = momentum_12m1m(
                close,
                pd.Timestamp.today(),
                lookback_months=params.lookback_months,
                skip_months=params.skip_months,
                min_observations=params.min_observations,
            )
            if len(scores) >= COVERAGE_FLOOR * len(universe):
                prices = close
            else:
                print(f"  Shadow: universe coverage too low ({len(scores)}/{len(universe)}) - refusing to rank.")
        except Exception as exc:  # fetch failure = signals unavailable, cycle degrades
            print(f"  Shadow: signal fetch failed ({exc}) - signals unavailable.")

    return MarketSnapshot(latest_close=latest_close, bar_date=bar_date, market_uptrend=regime, prices=prices)


def compare_books(shadow: PortfolioState) -> list[str]:
    legacy = json.loads((REPO / "data" / "paper_state.json").read_text())
    diffs: list[str] = []
    if abs(shadow.cash - legacy["cash"]) > 0.01:
        diffs.append(f"cash: shadow {shadow.cash:.2f} vs legacy {legacy['cash']:.2f}")
    legacy_holdings = legacy.get("holdings", {})
    if set(shadow.positions) != set(legacy_holdings):
        diffs.append(f"positions: shadow {sorted(shadow.positions)} vs legacy {sorted(legacy_holdings)}")
    else:
        for ticker, pos in shadow.positions.items():
            if abs(pos.shares - legacy_holdings[ticker]["shares"]) > 1e-6:
                diffs.append(f"{ticker} shares: shadow {pos.shares} vs legacy {legacy_holdings[ticker]['shares']}")
    shadow_pending = {(o.side, o.ticker) for o in shadow.pending}
    legacy_pending = {(o["type"], o["ticker"]) for o in legacy.get("pending_orders", [])}
    if shadow_pending != legacy_pending:
        diffs.append(f"pending: shadow {sorted(shadow_pending)} vs legacy {sorted(legacy_pending)}")
    return diffs


def append_report(report: CycleReport, diffs: list[str], seeded: bool) -> None:
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    record = {**asdict(report), "diffs": diffs, "seeded": seeded}
    with (SHADOW_DIR / "cycle_reports.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def main() -> int:
    today = date.today()
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    store: SqliteRepository[PortfolioState] = SqliteRepository(SHADOW_DIR / "portfolio.db", "portfolio", PortfolioState)

    seeded = False
    try:
        state = store.get(ACCOUNT_ID)
    except EntityNotFoundError:
        state = seed_from_legacy_state(store)
        seeded = True

    params = load_momentum_params(REPO / "strategies_registry" / "momentum_v1.yaml")
    last_friday = today - timedelta(days=(today.weekday() - 4) % 7)
    rebalance_may_be_due = today.weekday() >= 4 and state.last_rebalance_date < last_friday.isoformat()
    market = build_market_snapshot(state, rebalance_may_be_due)

    report = run_cycle(
        today,
        store=store,
        market=market,
        strategy=MomentumV1(params),
        kill_switch=production_kill_switch(),
        stop_loss_pct=params.stop_loss_pct,
        costs=ZerodhaDeliveryCostModel(),
        account_id=ACCOUNT_ID,
    )
    print(
        f"Shadow cycle {report.as_of}: {report.status} stance={report.stance} "
        f"fills={len(report.fills)} queued={len(report.queued)} value={report.value:,.0f}"
    )
    for note in report.degraded:
        print(f"  degraded: {note}")

    if report.status == "HALTED":
        append_report(report, [], seeded)
        return 0  # legacy loop halted too; nothing to compare

    diffs = compare_books(store.get(ACCOUNT_ID))
    append_report(report, diffs, seeded)
    if diffs:
        print("DIVERGENCE from legacy books:")
        for diff in diffs:
            print(f"  {diff}")
        return 1
    print("Books MATCH data/paper_state.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
