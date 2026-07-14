"""Signal-parity suite (WP-009): the ported strategy must reproduce
the frozen script's signals EXACTLY, on the real cached data.

This is the ADR-003/ADR-005 gate for the Phase 3 port: momentum scores
byte-equal, top-10 selection identical, regime series identical, and
the registry's pinned parameters equal to the frozen constants. Any
divergence is a hard failure -- there is no tolerance, because the
operations are meant to be the same operations.

Uses the real data/cache (no network). The frozen script is imported,
never modified.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import momentum_backtest as frozen  # noqa: E402  (import-safe: __main__-guarded)
from quantos_core.factors import is_uptrend, momentum_12m1m, uptrend_series  # noqa: E402
from quantos_core.strategies import MomentumV1, StrategyContext, load_momentum_params  # noqa: E402

PARAMS = load_momentum_params(REPO / "strategies_registry" / "momentum_v1.yaml")

# A spread of real rebalance Fridays: early (thin history), COVID bull,
# 2022 chop, 2023 recovery, and the last cached week.
PARITY_DATES = ["2019-06-28", "2020-06-26", "2021-12-31", "2022-06-24", "2023-09-29", "2024-12-27"]


@pytest.fixture(scope="module")
def matrix() -> pd.DataFrame:
    prices = frozen.load_price_matrix()
    assert prices is not None and not prices.empty
    return prices


@pytest.fixture(scope="module")
def index_close() -> "pd.Series[float]":
    cache = REPO / "data" / "cache_index" / "NSEI.csv"
    series = pd.read_csv(cache, index_col=0, parse_dates=True)["Close"]
    return series.astype(float)


def test_registry_params_match_frozen_constants() -> None:
    assert PARAMS.top_n == frozen.TOP_N
    assert PARAMS.lookback_months == frozen.LOOKBACK_MONTHS
    assert PARAMS.skip_months == frozen.SKIP_MONTHS
    assert PARAMS.min_observations == frozen.MIN_TRADING_DAYS // 2
    assert PARAMS.stop_loss_pct == frozen.STOP_LOSS_PCT
    assert PARAMS.trend_ma_days == frozen.TREND_MA_DAYS


@pytest.mark.parametrize("date", PARITY_DATES)
def test_momentum_scores_byte_equal(matrix: pd.DataFrame, date: str) -> None:
    as_of = pd.Timestamp(date)
    expected = frozen.momentum_score(matrix, as_of)
    got = momentum_12m1m(
        matrix,
        as_of,
        lookback_months=PARAMS.lookback_months,
        skip_months=PARAMS.skip_months,
        min_observations=PARAMS.min_observations,
    )
    assert got.equals(expected), f"momentum scores diverged from frozen script on {date}"


@pytest.mark.parametrize("date", PARITY_DATES)
def test_top10_selection_identical(matrix: pd.DataFrame, index_close: "pd.Series[float]", date: str) -> None:
    as_of = pd.Timestamp(date)
    regime = uptrend_series(index_close, PARAMS.trend_ma_days)
    ctx = StrategyContext(as_of=as_of, prices=matrix, market_uptrend=is_uptrend(regime, as_of))
    target = MomentumV1(PARAMS).generate_signals(ctx)

    expected_scores = frozen.momentum_score(matrix, as_of)
    if not is_uptrend(regime, as_of):
        assert target.stance == "cash"
        return
    if len(expected_scores) < frozen.TOP_N:
        assert target.stance == "hold"
        return
    expected = {str(t) for t in expected_scores.nlargest(frozen.TOP_N).index}
    assert target.stance == "rebalance"
    assert set(target.weights) == expected, f"selection diverged from frozen script on {date}"
    assert all(w == 1.0 / frozen.TOP_N for w in target.weights.values())


def test_regime_series_identical_to_frozen_math(index_close: "pd.Series[float]") -> None:
    # Frozen construction: close > rolling MA, dropna. On a bool series
    # .dropna() is a no-op, so the frozen output also carries ma_days-1
    # warm-up rows that read False only because `x > NaN` is False --
    # not because the market was below its MA. The port drops the
    # warm-up EXPLICITLY (2026-07-14 audit): byte-identical everywhere a
    # real MA value exists, which is the only region any signal reads
    # (the backtest window starts well after the cache's warm-up).
    ma = index_close.rolling(frozen.TREND_MA_DAYS).mean()
    expected = (index_close > ma)[ma.notna()]
    got = uptrend_series(index_close, PARAMS.trend_ma_days)
    assert got.equals(expected)
    # Warm-up dates must be ABSENT (permissive default applies there),
    # never silently False (bear).
    assert not got.index.isin(index_close.index[: frozen.TREND_MA_DAYS - 1]).any()


def test_regime_as_of_lookup_matches_frozen_inline_logic(index_close: "pd.Series[float]") -> None:
    regime = uptrend_series(index_close, PARAMS.trend_ma_days)
    for date in PARITY_DATES:
        as_of = pd.Timestamp(date)
        avail = regime.index[regime.index <= as_of]  # frozen run_backtest step 2, verbatim
        expected = bool(regime.loc[avail[-1]]) if len(avail) else True
        assert is_uptrend(regime, as_of) == expected


def test_known_regime_states() -> None:
    # Pinned from the cached ^NSEI series: 2024-12-27 was a bear week
    # (the reason live paper trading held cash), 2024-09-27 a bull week.
    cache = REPO / "data" / "cache_index" / "NSEI.csv"
    series = pd.read_csv(cache, index_col=0, parse_dates=True)["Close"].astype(float)
    regime = uptrend_series(series, PARAMS.trend_ma_days)
    assert is_uptrend(regime, pd.Timestamp("2024-12-27")) is False
    assert is_uptrend(regime, pd.Timestamp("2024-09-27")) is True
