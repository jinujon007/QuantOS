"""QuantOS end-to-end demo (WP-008/WP-009).

    .\\venv\\Scripts\\python.exe tools\\demo_pipeline.py

Runs the REAL system end to end with ZERO network and ZERO capital
risk: point-in-time universe -> cached prices -> the validated
Momentum v1.0 strategy (parameters from strategies_registry, signal
math proven byte-equal to the frozen script by the parity suite) ->
limit orders -> pre-trade risk gate -> paper broker fills -> persisted
order journal -> kill-switch drill. Only the broker adapter is the
paper one (ADR-010); everything else is what live trading will use.

Two historical dates are replayed to show both behaviors: a bear week
(regime filter refuses to trade) and a bull week (top-10 rebalance).
Signals are historical replays over the frozen 2019-2024 cache -- not
current trading advice; the live paper record stays with
paper_trader.py until Phase 6 swaps execution paths.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantos_core.brokers import LimitOrder, OrderSide, PaperBrokerAdapter, to_tick_up  # noqa: E402
from quantos_core.config import load_config  # noqa: E402
from quantos_core.data import CsvCachePriceProvider, SqliteUniverseStore  # noqa: E402
from quantos_core.execution import ExecutionBlockedError, ExecutionEngine, OrderJournalEntry  # noqa: E402
from quantos_core.factors import is_uptrend, uptrend_series  # noqa: E402
from quantos_core.risk import KillSwitch, KillSwitchGate, KillSwitchState  # noqa: E402
from quantos_core.storage import SqliteRepository  # noqa: E402
from quantos_core.strategies import MomentumV1, StrategyContext, load_momentum_params  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEMO_DIR = REPO / "data" / "demo"
CAPITAL = 100_000.0
BEAR_DATE = date(2024, 12, 27)  # regime filter active -- strategy holds cash
BULL_DATE = date(2024, 9, 27)  # uptrend -- strategy rebalances
AS_OF = BULL_DATE  # orders are placed for the bull replay


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
    lookback_start = AS_OF - timedelta(days=440)
    columns: dict[str, "pd.Series[float]"] = {}
    skipped = 0
    for ticker in universe:
        try:
            frame = prices.get_prices([ticker], lookback_start, AS_OF)
        except Exception:
            skipped += 1  # ticker not in the 2019-2024 cache (new listing etc.) -- visible, counted
            continue
        columns[str(ticker).removesuffix(".NS")] = frame[str(ticker)]
    matrix = pd.DataFrame(columns)
    print(f"  {len(columns)} tickers served; {skipped} skipped (counted, not silent)")

    banner("4. THE VALIDATED STRATEGY -- Momentum v1.0 (WP-009)")
    params = load_momentum_params(REPO / "strategies_registry" / "momentum_v1.yaml")
    strategy = MomentumV1(params)
    print(f"  {strategy.metadata().name} v{params.version} -- params from strategies_registry (ADR-015)")
    print("  Signal math proven byte-equal to the frozen script (test_strategy_parity.py, 6 dates)")

    index_close = pd.read_csv(REPO / "data" / "cache_index" / "NSEI.csv", index_col=0, parse_dates=True)[
        "Close"
    ].astype(float)
    regime = uptrend_series(index_close, params.trend_ma_days)

    bear_up = is_uptrend(regime, pd.Timestamp(BEAR_DATE))
    bear_target = strategy.generate_signals(
        StrategyContext(as_of=pd.Timestamp(BEAR_DATE), prices=matrix, market_uptrend=bear_up)
    )
    print(f"\n  Replay {BEAR_DATE.isoformat()} -- Nifty below its {params.trend_ma_days}-day MA (uptrend={bear_up}):")
    print(f"    stance = {bear_target.stance.upper()}  ->  liquidate everything, hold cash. No picks in a bear.")

    bull_up = is_uptrend(regime, pd.Timestamp(BULL_DATE))
    target = strategy.generate_signals(
        StrategyContext(as_of=pd.Timestamp(BULL_DATE), prices=matrix, market_uptrend=bull_up)
    )
    print(f"\n  Replay {BULL_DATE.isoformat()} -- uptrend={bull_up}:  stance = {target.stance.upper()}")
    if target.stance != "rebalance":
        print("  FAIL-CLOSED: no rebalance signal on the bull replay -- stopping.")
        return 1
    last_close = matrix.loc[: pd.Timestamp(BULL_DATE)].iloc[-1]
    top = list(target.weights)
    for rank, ticker in enumerate(top, 1):
        print(
            f"  {rank:2d}. {ticker:<12} weight {target.weights[ticker] * 100:4.0f}%   close {last_close[ticker]:10.2f}"
        )

    banner("5. RISK -- persisted kill switch + pre-trade gate (ADR-009)")
    kill_switch = KillSwitch(SqliteRepository(DEMO_DIR / "risk.db", "kill_switch", KillSwitchState))
    kill_switch.release("demo start")
    gate = KillSwitchGate(kill_switch)
    print(f"  kill switch engaged: {kill_switch.is_engaged()}  (state survives restarts; unreadable = BLOCK)")

    banner(f"6. EXECUTION -- the strategy's {BULL_DATE.isoformat()} weights through the gated engine (paper broker)")
    market = {symbol: float(last_close[symbol]) for symbol in top}
    broker = PaperBrokerAdapter(market, cash=CAPITAL)
    journal: SqliteRepository[OrderJournalEntry] = SqliteRepository(
        DEMO_DIR / "journal.db", "order_journal", OrderJournalEntry
    )
    engine = ExecutionEngine(broker, gate, journal, run_id=run_id)
    # Re-point the engine's logger (same named logger) at the run's
    # event file so the console stays a clean demo narrative.
    from quantos_core.utils import get_logger  # noqa: E402

    get_logger("execution", run_id=run_id, stream=log_stream)
    for symbol in top:
        price = market[symbol]
        slot = CAPITAL * target.weights[symbol]
        quantity = int(slot // price)
        if quantity == 0:
            print(f"  {symbol:<12} SKIPPED -- one share ({price:.2f}) exceeds the {slot:.0f} slot")
            continue
        # 0.2% above market, rounded UP to the band-aware NSE tick grid --
        # an off-grid limit is an exchange rejection, and a buy limit
        # floored BELOW market rests unfilled forever (sub-Rs25 names).
        order = LimitOrder(ticker=symbol, side=OrderSide.BUY, quantity=quantity, limit_price=to_tick_up(price * 1.002))
        receipt = engine.execute(order)
        print(
            f"  {symbol:<12} BUY {quantity:4d} @ limit {order.limit_price:10.2f}"
            f" -> {receipt.status}  [{receipt.broker_order_id}]"
        )
    print(f"\n  Portfolio: {len(broker.holdings())} positions, cash left {broker.available_cash():,.2f}")

    banner("7. KILL-SWITCH DRILL -- the no-bypass rule, live")
    kill_switch.engage("operator demo drill")
    drill = LimitOrder(ticker=top[0], side=OrderSide.BUY, quantity=1, limit_price=1.0)
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
