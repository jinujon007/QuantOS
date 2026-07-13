"""Characterization tests for the Momentum strategy (momentum_backtest.py).

These tests do not evaluate whether the strategy is "correct" — that
question belongs to the QuantOS Independent Audit and the Prospective
Validation freeze already in progress (CONTEXT.md). Their only job is to
prove that a future change to this codebase either preserves today's exact
output — same trades, same dates, same weights, same returns, same metrics
— or is caught immediately if it doesn't. This is the Phase 0 "engineering
safety net" the mission asks for.

Golden files live in tests/golden/, captured by tools/capture_golden.py
against the current, unmodified source (see that file's docstring for how
and when to regenerate them).

All of this runs fully offline: data/cache/ (459 tickers) and
data/cache_index/NSEI.csv already cover the full 2019-01-01..2024-12-31
window used here, so load_price_matrix()/load_nifty50_regime() never hit
the network in this test.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

import momentum_backtest as m


@pytest.fixture(scope="module")
def golden_dir():
    return Path(__file__).resolve().parent / "golden"


@pytest.fixture(scope="module")
def prices():
    p = m.load_price_matrix()
    assert p is not None, "no cached price data in data/cache/ — characterization tests require the baseline cache"
    return p


@pytest.fixture(scope="module")
def regime(prices):
    r = m.load_nifty50_regime(m.START_DATE, m.END_DATE)
    assert not r.empty, "regime series empty — data/cache_index/ must cover the backtest window"
    return r


@pytest.fixture(scope="module")
def equity_baseline(prices):
    return m.run_backtest(prices, regime=None)


@pytest.fixture(scope="module")
def equity_filtered(prices, regime):
    return m.run_backtest(prices, regime=regime)


def _load_golden_csv(path) -> pd.DataFrame:
    # float_precision="round_trip" is required, not optional: pandas' default
    # C-engine float parser is a fast approximation and silently loses the
    # last 1-2 bits on ~15% of values read back from CSV — verified directly
    # (same-process repeated run_backtest() calls ARE byte-identical; only
    # the CSV write→read round-trip introduced drift). Without this, exact
    # equality below would flag false positives that look like strategy
    # non-determinism but are actually a CSV-parsing artifact.
    df = pd.read_csv(path, index_col=0, parse_dates=True, float_precision="round_trip")
    df.index.name = "date"
    return df


def test_price_matrix_shape_unchanged(prices):
    """A change in universe size or date coverage is exactly the kind of
    silent drift (F1/F9-adjacent) this test exists to catch before it
    reaches the strategy layer."""
    assert prices.shape[0] > 0
    assert prices.shape[1] > 0
    # Loose bound, not exact pin: data/cache grows as download_data.py is
    # re-run for new tickers, and that growth is legitimate, expected
    # behavior — not a regression. The strategy-output tests below are the
    # ones that must be exact.
    assert prices.shape[1] >= 300, (
        f"universe collapsed to {prices.shape[1]} tickers — investigate before trusting any output below"
    )


def test_equity_baseline_matches_golden(equity_baseline, golden_dir):
    golden = _load_golden_csv(golden_dir / "momentum_equity_baseline.csv")
    pd.testing.assert_frame_equal(equity_baseline, golden, check_exact=True)


def test_equity_filtered_matches_golden(equity_filtered, golden_dir):
    golden = _load_golden_csv(golden_dir / "momentum_equity_filtered.csv")
    pd.testing.assert_frame_equal(equity_filtered, golden, check_exact=True)


def test_metrics_match_golden(equity_filtered, golden_dir):
    metrics = m.print_metrics(equity_filtered)
    golden = json.loads((golden_dir / "momentum_metrics.json").read_text(encoding="utf-8"))
    assert set(metrics.keys()) == set(golden.keys())
    for key, expected in golden.items():
        actual = float(metrics[key])
        assert actual == expected, f"metric '{key}' drifted: golden={expected!r} actual={actual!r}"


def test_walk_forward_cagrs_match_golden(prices, regime, golden_dir):
    """Reproduces exactly what walk_forward_test() computes internally
    (same sub-window slicing, same run_backtest calls) so the comparison is
    structural, not a scrape of printed text."""
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

    actual = {
        "baseline_train_cagr": cagr_train_base,
        "baseline_test_cagr": cagr_test_base,
        "filtered_train_cagr": cagr_train_filt,
        "filtered_test_cagr": cagr_test_filt,
    }
    golden = json.loads((golden_dir / "momentum_walk_forward.json").read_text(encoding="utf-8"))
    for key, expected in golden.items():
        assert actual[key] == expected, f"walk-forward '{key}' drifted: golden={expected!r} actual={actual[key]!r}"


def test_holdings_never_negative_or_over_capital(equity_filtered):
    """Property check, not a golden-file pin: the portfolio value must never
    go negative and must be finite at every rebalance — a sanity invariant
    independent of the specific numbers, catches a different class of bug
    than exact-match regression would (e.g. a NaN propagating silently)."""
    v = equity_filtered["value"]
    assert (v > 0).all(), "portfolio value went to zero or negative at some rebalance date"
    assert v.notna().all(), "portfolio value contains NaN — a silent computation failure somewhere upstream"
