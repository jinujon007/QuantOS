"""Capture golden files for the Momentum strategy's characterization test.

Runs the SAME public functions momentum_backtest.py's own __main__ block
calls (load_price_matrix, load_nifty50_regime, run_backtest, print_metrics)
against the current, unmodified source and cached data — never a modified
or re-derived computation — and pins the result under tests/golden/ as the
reference every future run is compared against.

This is a one-time (or deliberate re-run) capture tool, not a test itself.
Re-running it OVERWRITES the golden files — only do that with a reason
recorded in an ADR/commit message (per QuantOS Constitution, Part IV
Reproducibility / ADR-005), never silently.

Usage: python tools/capture_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import momentum_backtest as m  # noqa: E402

GOLDEN_DIR = ROOT / "tests" / "golden"


def _normalize_csv_text(path: Path) -> str:
    """Read a CSV and normalize line endings to LF before hashing/storing —
    Windows text-mode writes emit CRLF, which is an OS/platform artifact of
    how the file was written, not a difference in the computed values.
    Comparing normalized text is what makes 'byte-identical' mean 'the
    numbers are identical', not 'the OS wrote the same newline byte'."""
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    prices = m.load_price_matrix()
    if prices is None:
        print("ERROR: no cached price data in data/cache/ — cannot capture golden files.")
        raise SystemExit(1)

    regime = m.load_nifty50_regime(m.START_DATE, m.END_DATE)

    equity_baseline = m.run_backtest(prices, regime=None)
    equity_filtered = m.run_backtest(prices, regime=regime)
    metrics = m.print_metrics(equity_filtered)  # also writes data/results/equity_curve.csv, unchanged behavior

    # ── Portfolio history (equity curves) ────────────────────────────────
    equity_baseline.to_csv(GOLDEN_DIR / "momentum_equity_baseline.csv", lineterminator="\n")
    equity_filtered.to_csv(GOLDEN_DIR / "momentum_equity_filtered.csv", lineterminator="\n")

    # ── Metrics (from the filtered/live-strategy curve, matching __main__) ─
    metrics_json = {k: float(v) for k, v in metrics.items()}
    (GOLDEN_DIR / "momentum_metrics.json").write_text(
        json.dumps(metrics_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # ── Walk-forward CAGRs, both variants — same sub-windows/calls
    # walk_forward_test() itself makes internally, captured structurally
    # here instead of scraped from its print output ──────────────────────
    orig_start, orig_end = m.START_DATE, m.END_DATE
    try:
        m.START_DATE, m.END_DATE = "2019-01-01", "2021-12-31"
        p_train = prices.loc[m.START_DATE : m.END_DATE]
        cagr_train_base = m._cagr_of(m.run_backtest(p_train, regime=None), m.START_DATE, m.END_DATE)
        cagr_train_filt = m._cagr_of(m.run_backtest(p_train, regime=regime), m.START_DATE, m.END_DATE)

        m.START_DATE, m.END_DATE = "2022-01-01", "2024-12-31"
        p_test = prices.loc[m.START_DATE : m.END_DATE]
        cagr_test_base = m._cagr_of(m.run_backtest(p_test, regime=None), m.START_DATE, m.END_DATE)
        cagr_test_filt = m._cagr_of(m.run_backtest(p_test, regime=regime), m.START_DATE, m.END_DATE)
    finally:
        m.START_DATE, m.END_DATE = orig_start, orig_end

    walk_forward = {
        "baseline_train_cagr": cagr_train_base,
        "baseline_test_cagr": cagr_test_base,
        "filtered_train_cagr": cagr_train_filt,
        "filtered_test_cagr": cagr_test_filt,
    }
    (GOLDEN_DIR / "momentum_walk_forward.json").write_text(
        json.dumps(walk_forward, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # ── Note on scope: no separate "trade log" file exists in the current
    # codebase. run_backtest() tracks holdings internally and returns only
    # the equity curve — it does not persist a per-trade record anywhere.
    # This is documented, not fabricated: the Phase 0 execution report
    # flags trade-level journaling as a genuine gap the Blueprint's
    # `execution`/`storage` modules (Phase 6) are scoped to close. ────────

    print(f"Golden files written to {GOLDEN_DIR}:")
    for f in sorted(GOLDEN_DIR.glob("momentum_*")):
        print(f"  {f.name}")
    print("\nMetrics:", json.dumps(metrics_json, indent=2))


if __name__ == "__main__":
    main()
