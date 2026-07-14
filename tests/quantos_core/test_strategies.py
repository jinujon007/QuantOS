"""Unit tests for the strategy platform types and registry (WP-009).

Synthetic-data tests for TargetWeights invariants, the momentum factor
edge cases, regime defaults, and registry fail-closed loading. Parity
with the frozen script lives in test_strategy_parity.py.
"""

from pathlib import Path

import pandas as pd
import pytest

from quantos_core.factors import is_uptrend, momentum_12m1m, uptrend_series
from quantos_core.strategies import (
    MomentumParams,
    MomentumV1,
    Strategy,
    StrategyContext,
    StrategyRegistryError,
    TargetWeights,
    load_momentum_params,
)

PARAMS = MomentumParams(
    version="test",
    top_n=2,
    lookback_months=12,
    skip_months=1,
    min_observations=5,
    stop_loss_pct=0.08,
    trend_ma_days=100,
)


def make_prices() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", "2021-06-30", freq="B")
    frame = pd.DataFrame(
        {
            "WINNER": [100 * (1.004**i) for i in range(len(dates))],
            "FLAT": [100.0] * len(dates),
            "LOSER": [100 * (0.999**i) for i in range(len(dates))],
        },
        index=dates,
    )
    return frame


# ── TargetWeights invariants ─────────────────────────────────────────────


def test_cash_and_hold_carry_no_weights() -> None:
    assert TargetWeights(stance="cash").weights == {}
    with pytest.raises(ValueError, match="no weights"):
        TargetWeights(stance="cash", weights={"X": 0.5})


def test_rebalance_requires_valid_weights() -> None:
    with pytest.raises(ValueError, match="requires weights"):
        TargetWeights(stance="rebalance")
    with pytest.raises(ValueError, match="positive"):
        TargetWeights(stance="rebalance", weights={"X": -0.1})
    with pytest.raises(ValueError, match="sum above"):
        TargetWeights(stance="rebalance", weights={"X": 0.6, "Y": 0.6})


def test_weights_are_immutable() -> None:
    target = TargetWeights(stance="rebalance", weights={"X": 0.5})
    with pytest.raises(TypeError):
        target.weights["Y"] = 0.5  # type: ignore[index]


# ── momentum factor edges ────────────────────────────────────────────────


def test_momentum_ranks_winner_over_loser() -> None:
    prices = make_prices()
    scores = momentum_12m1m(prices, pd.Timestamp("2021-06-25"), lookback_months=12, skip_months=1, min_observations=5)
    assert scores["WINNER"] > scores["FLAT"] > scores["LOSER"]


def test_momentum_empty_before_history_starts() -> None:
    prices = make_prices()
    scores = momentum_12m1m(prices, pd.Timestamp("2019-06-01"), lookback_months=12, skip_months=1, min_observations=5)
    assert scores.empty


def test_momentum_quality_filter_drops_sparse_ticker() -> None:
    prices = make_prices()
    sparse = prices.copy()
    sparse.loc[sparse.index < "2021-05-20", "LOSER"] = float("nan")
    scores = momentum_12m1m(sparse, pd.Timestamp("2021-06-25"), lookback_months=12, skip_months=1, min_observations=50)
    assert "LOSER" not in scores.index
    assert "WINNER" in scores.index


# ── regime edges ─────────────────────────────────────────────────────────


def test_regime_true_before_any_data() -> None:
    series = uptrend_series(pd.Series([1.0, 2.0], index=pd.to_datetime(["2021-01-01", "2021-01-02"])), 100)
    assert is_uptrend(series, pd.Timestamp("2020-01-01")) is True  # frozen permissive default


def test_regime_warmup_has_no_value_not_bear() -> None:
    """The MA warm-up window must be ABSENT from the uptrend series, not
    silently False: `close > NaN` is False on a bool series and .dropna()
    is a no-op there, so the naive port reported the first ma_days-1 dates
    as BEAR — weeks of wrongful cash stance for any caller that doesn't
    pre-fetch extra history (2026-07-14 audit)."""
    idx = pd.date_range("2021-01-01", periods=10, freq="D")
    rising = pd.Series([float(i) for i in range(1, 11)], index=idx)
    series = uptrend_series(rising, 5)
    assert series.index[0] == idx[4], "warm-up rows must be dropped, not reported False"
    assert is_uptrend(series, idx[2]) is True  # warm-up -> no value -> permissive default
    assert bool(series.loc[idx[4]]) is True  # rising series sits above its MA


# ── strategy behavior on synthetic data ──────────────────────────────────


def test_bear_regime_goes_to_cash() -> None:
    ctx = StrategyContext(as_of=pd.Timestamp("2021-06-25"), prices=make_prices(), market_uptrend=False)
    assert MomentumV1(PARAMS).generate_signals(ctx).stance == "cash"


def test_insufficient_ranked_tickers_holds() -> None:
    wide_params = PARAMS.model_copy(update={"top_n": 10})
    ctx = StrategyContext(as_of=pd.Timestamp("2021-06-25"), prices=make_prices(), market_uptrend=True)
    assert MomentumV1(wide_params).generate_signals(ctx).stance == "hold"


def test_bull_regime_rebalances_equal_weight() -> None:
    ctx = StrategyContext(as_of=pd.Timestamp("2021-06-25"), prices=make_prices(), market_uptrend=True)
    target = MomentumV1(PARAMS).generate_signals(ctx)
    assert target.stance == "rebalance"
    assert set(target.weights) == {"WINNER", "FLAT"}
    assert all(w == 0.5 for w in target.weights.values())


def test_momentum_v1_satisfies_the_port() -> None:
    def accepts(strategy: Strategy) -> Strategy:
        return strategy

    concrete = MomentumV1(PARAMS)
    assert accepts(concrete) is concrete
    meta = concrete.metadata()
    assert meta.name == "nifty500-weekly-momentum"
    assert meta.params["top_n"] == 2


# ── registry loading, fail-closed ────────────────────────────────────────


def test_registry_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(StrategyRegistryError, match="Cannot read"):
        load_momentum_params(tmp_path / "absent.yaml")


def test_registry_malformed_yaml_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("just a string", encoding="utf-8")
    with pytest.raises(StrategyRegistryError, match="mapping"):
        load_momentum_params(bad)


def test_registry_unknown_param_fails(tmp_path: Path) -> None:
    entry = tmp_path / "entry.yaml"
    entry.write_text(
        "version: '9.9'\nparams:\n  top_n: 10\n  lookback_months: 12\n  skip_months: 1\n"
        "  min_observations: 75\n  stop_loss_pct: 0.08\n  trend_ma_days: 100\n  surprise: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(StrategyRegistryError, match="schema"):
        load_momentum_params(entry)


def test_registry_out_of_range_param_fails(tmp_path: Path) -> None:
    entry = tmp_path / "entry.yaml"
    entry.write_text(
        "version: '9.9'\nparams:\n  top_n: 0\n  lookback_months: 12\n  skip_months: 1\n"
        "  min_observations: 75\n  stop_loss_pct: 0.08\n  trend_ma_days: 100\n",
        encoding="utf-8",
    )
    with pytest.raises(StrategyRegistryError, match="schema"):
        load_momentum_params(entry)


def test_real_registry_entry_loads() -> None:
    repo = Path(__file__).resolve().parents[2]
    params = load_momentum_params(repo / "strategies_registry" / "momentum_v1.yaml")
    assert params.version == "1.0"
    assert params.top_n == 10
