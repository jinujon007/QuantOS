"""QuantOS end-to-end demo (WP-008, ADR-034).

    .\\venv\\Scripts\\python.exe tools\\demo_pipeline.py

Runs the real machinery end to end with ZERO network and ZERO capital
risk: point-in-time universe -> cached prices -> momentum ranking ->
limit orders -> pre-trade risk gate -> paper broker fills -> persisted
order journal -> kill-switch drill. Everything printed is produced by
the same quantos_core modules live trading will use; only the broker
adapter is the paper one (ADR-010).

The ranking below is a DEMO approximation of 12M-1M momentum for
display purposes ONLY. The validated strategy remains frozen in
paper_trader.py (Prospective Validation rule) -- demo output is never
a trading signal.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantos_core.brokers import LimitOrder, OrderSide, PaperBrokerAdapter, to_tick  # noqa: E402
from quantos_core.config import load_config  # noqa: E402
from quantos_core.data import CsvCachePriceProvider, SqliteUniverseStore  # noqa: E402
from quantos_core.execution import ExecutionBlockedError, ExecutionEngine, OrderJournalEntry  # noqa: E402
from quantos_core.risk import KillSwitch, KillSwitchGate, KillSwitchState  # noqa: E402
from quantos_core.storage import SqliteRepository  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO / "data" / "demo"
CAPITAL = 100_000.0
TOP_N = 10
AS_OF = date(2024, 12, 27)  # inside the cached 2019-2024 window -- fully offline


def banner(text: str) -> None:
    print(f"\n{'=' * 68}\n  {text}\n{'=' * 68}")


def main() -> int:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    # Unique per invocation: journal ids embed the run_id, and a re-run
    # must append to the audit trail, never collide with a prior run.
    run_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    log_path = DEMO_DIR / f"{run_id}.events.jsonl"
    log_stream = log_path.open("w", encoding="utf-8")

    banner("1. CONFIG -- typed, validated, fail-closed (WP-002)")
    config = load_config(env="dev")
    print(f"  environment={config.environment}  (immutable AppConfig; invalid env would refuse to boot)")

    banner("2. POINT-IN-TIME UNIVERSE (WP-007 -- survivorship-bias fix)")
    store = SqliteUniverseStore(REPO / "data" / "universe_pit.db")
    snapshot = store.latest_snapshot_date(date.today())
    universe = store.get_universe(date.today())
    print(f"  snapshot {snapshot.isoformat()}: {len(universe)} Nifty 500 tickers")
    print("  (a 2019 query would FAIL LOUDLY -- no snapshot existed; membership is never guessed)")

    banner("3. PRICES -- fail-closed cache reader (WP-007)")
    prices = CsvCachePriceProvider(REPO / "data" / "cache")
    lookback_start = AS_OF - timedelta(days=400)
    served: dict[str, float] = {}
    momentum: dict[str, float] = {}
    skipped = 0
    for ticker in universe:
        try:
            frame = prices.get_prices([ticker], lookback_start, AS_OF)
        except Exception:
            skipped += 1  # ticker not in the 2019-2024 cache (new listing etc.) -- visible, counted
            continue
        series = frame[str(ticker)].dropna()
        if len(series) < 260:
            skipped += 1
            continue
        latest = float(series.iloc[-1])
        one_month_ago = float(series.iloc[-22])
        twelve_months_ago = float(series.iloc[0])
        served[str(ticker)] = latest
        momentum[str(ticker)] = (one_month_ago / twelve_months_ago) - 1.0
    print(f"  {len(served)} tickers with full history served; {skipped} skipped (counted, not silent)")

    banner(f"4. DEMO MOMENTUM RANK (12M-1M approximation) as of {AS_OF.isoformat()}")
    top = sorted(momentum.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_N]
    if not top:
        print("  FAIL-CLOSED: zero tickers ranked (price cache missing?) -- nothing to trade, stopping.")
        return 1
    print("  DEMO ONLY -- validated strategy stays frozen in paper_trader.py")
    for rank, (ticker, score) in enumerate(top, 1):
        print(
            f"  {rank:2d}. {ticker.removesuffix('.NS'):<12} momentum {score * 100:7.1f}%   last {served[ticker]:10.2f}"
        )

    banner("5. RISK -- persisted kill switch + pre-trade gate (ADR-009)")
    kill_switch = KillSwitch(SqliteRepository(DEMO_DIR / "risk.db", "kill_switch", KillSwitchState))
    kill_switch.release("demo start")
    gate = KillSwitchGate(kill_switch)
    print(f"  kill switch engaged: {kill_switch.is_engaged()}  (state survives restarts; unreadable = BLOCK)")

    banner("6. EXECUTION -- limit orders through the gated engine (paper broker)")
    market = {t.removesuffix(".NS"): p for t, p in served.items()}
    broker = PaperBrokerAdapter(market, cash=CAPITAL)
    journal: SqliteRepository[OrderJournalEntry] = SqliteRepository(
        DEMO_DIR / "journal.db", "order_journal", OrderJournalEntry
    )
    engine = ExecutionEngine(broker, gate, journal, run_id=run_id)
    # Re-point the engine's logger (same named logger) at the run's
    # event file so the console stays a clean demo narrative.
    from quantos_core.utils import get_logger  # noqa: E402

    get_logger("execution", run_id=run_id, stream=log_stream)
    per_stock = CAPITAL / TOP_N
    for ticker, _ in top:
        symbol = ticker.removesuffix(".NS")
        price = market[symbol]
        quantity = int(per_stock // price)
        if quantity == 0:
            print(f"  {symbol:<12} SKIPPED -- one share ({price:.2f}) exceeds the {per_stock:.0f} slot")
            continue
        # 0.2% above market, rounded DOWN to the NSE 0.05 tick grid --
        # an off-grid limit price is an exchange rejection, not a fill.
        order = LimitOrder(ticker=symbol, side=OrderSide.BUY, quantity=quantity, limit_price=to_tick(price * 1.002))
        receipt = engine.execute(order)
        print(
            f"  {symbol:<12} BUY {quantity:4d} @ limit {order.limit_price:10.2f}"
            f" -> {receipt.status}  [{receipt.broker_order_id}]"
        )
    print(f"\n  Portfolio: {len(broker.holdings())} positions, cash left {broker.available_cash():,.2f}")

    banner("7. KILL-SWITCH DRILL -- the no-bypass rule, live")
    kill_switch.engage("operator demo drill")
    drill = LimitOrder(ticker=top[0][0].removesuffix(".NS"), side=OrderSide.BUY, quantity=1, limit_price=1.0)
    try:
        engine.execute(drill)
        print("  !! ORDER WENT THROUGH -- THIS WOULD BE A BUG")
        return 1
    except ExecutionBlockedError as exc:
        print(f"  Order BLOCKED as designed: {exc}")
    kill_switch.release("drill complete")

    banner("8. AUDIT TRAIL -- every attempt journaled, incl. the blocked one")
    entries = journal.query({"run_id": run_id})
    for entry in entries[-4:]:
        print(f"  {entry.id}: {entry.side} {entry.quantity} {entry.ticker} -> {entry.outcome}")
    total = len(journal.query({}))
    print(f"  {len(entries)} rows this run ({total} all-time) at {DEMO_DIR / 'journal.db'}")
    log_stream.close()
    print(f"  Structured JSON event log: {log_path}")

    banner("DEMO COMPLETE")
    print(
        "  Same engine, same gate, same journal run live -- only the broker\n"
        "  adapter swaps (ZerodhaKiteAdapter / AngelOneSmartApiAdapter are\n"
        "  built, tested, and waiting for API keys; see tools/broker_connect_check.py)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
