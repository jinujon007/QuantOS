"""Paper-account performance metrics from the equity history (WP-017, ADR-042).

    python tools/paper_metrics.py [--file PATH]

The Sept-9 go/no-go gate needs "paper Sharpe > 1.0" to be a computable
number. paper_trader.py appends one equity row per completed run
(data/paper_equity_history.csv); this tool reads that history and reports
observation count, total return, annualized Sharpe (rf = 0, sqrt(252)),
and max drawdown.

The history is true-append: a --force rerun writes a second row for the
same date, so rows are deduplicated keeping the LAST row per date.
Degraded rows (valuations that fell back to stale entry prices) are
included in the series but counted and flagged in the output — a Sharpe
built mostly on degraded rows is not gate evidence.

Exit codes: 0 = metrics computed, 1 = no or insufficient history.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
DEFAULT_FILE = REPO / "data" / "paper_equity_history.csv"
TRADING_DAYS_PER_YEAR = 252
MIN_OBSERVATIONS = 2  # a return series needs at least two equity points


def load_history(path: Path) -> pd.DataFrame:
    """One row per date, last-write-wins, sorted ascending by date."""
    frame = pd.read_csv(path)
    frame = frame.drop_duplicates(subset="date", keep="last").sort_values("date")
    return frame.reset_index(drop=True)


@dataclass(frozen=True)
class Metrics:
    total_return: float
    sharpe: float | None  # None = undefined (zero daily volatility), not infinite
    max_drawdown: float


def compute_metrics(values: pd.Series) -> Metrics:
    """Metrics over an ordered equity series (one value per trading day).

    Formulas per empyrical's standard definitions (ADR-043: cite the
    math, skip the maintenance-mode dependency): annualized Sharpe =
    mean(daily returns) / std(daily returns, ddof=1) * sqrt(252), rf=0;
    max drawdown = min(value / running peak - 1).
    """
    returns = values.pct_change().dropna()
    std = float(returns.std())
    sharpe = float(returns.mean()) / std * TRADING_DAYS_PER_YEAR**0.5 if std > 0 else None
    drawdown = float((values / values.cummax() - 1.0).min())
    total_return = float(values.iloc[-1] / values.iloc[0] - 1.0)
    return Metrics(total_return=total_return, sharpe=sharpe, max_drawdown=drawdown)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Paper-account metrics from the equity history CSV.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="equity history CSV (default: data/)")
    args = parser.parse_args(argv)

    if not args.file.exists():
        print(f"No equity history at {args.file} — it starts accruing with the next paper run.")
        return 1
    history = load_history(args.file)
    if len(history) < MIN_OBSERVATIONS:
        print(f"Insufficient history: {len(history)} day(s) recorded, need >= {MIN_OBSERVATIONS} to compute returns.")
        return 1

    metrics = compute_metrics(history["total_value"].astype(float))
    degraded = int(history["degraded"].sum()) if "degraded" in history else 0

    print(f"Paper equity history: {len(history)} days ({history['date'].iloc[0]} -> {history['date'].iloc[-1]})")
    print(f"  Start value:    {history['total_value'].iloc[0]:>12,.2f}")
    print(f"  End value:      {history['total_value'].iloc[-1]:>12,.2f}")
    print(f"  Total return:   {metrics.total_return * 100:>11.2f}%")
    sharpe_text = f"{metrics.sharpe:>12.2f}" if metrics.sharpe is not None else "         n/a (zero volatility)"
    print(f"  Sharpe (ann.):  {sharpe_text}")
    print(f"  Max drawdown:   {metrics.max_drawdown * 100:>11.2f}%")
    if degraded:
        print(f"  WARNING: {degraded}/{len(history)} rows are degraded (stale-price valuation) — weigh before gating.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
