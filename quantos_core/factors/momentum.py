"""12M-1M momentum factor (WP-009).

VERBATIM port of `momentum_backtest.momentum_score` (ADR-003,
strangler-fig): identical pandas operations in identical order, with
the module-level constants replaced by injected parameters whose
frozen values live in `strategies_registry/momentum_v1.yaml`. Signal
parity with the frozen script is pinned by
tests/quantos_core/test_strategy_parity.py -- any drift is a test
failure, not a judgment call.

Pure function: no I/O, no clock, no randomness (ADR-006/019).
"""

import pandas as pd


def momentum_12m1m(
    prices: pd.DataFrame,
    as_of: pd.Timestamp,
    *,
    lookback_months: int,
    skip_months: int,
    min_observations: int,
) -> "pd.Series[float]":
    """Return from (lookback+skip months ago) to (skip months ago),
    per ticker, filtered to tickers with enough observations in the
    window. Empty Series when history is insufficient."""
    end_dt = as_of - pd.DateOffset(months=skip_months)
    start_dt = end_dt - pd.DateOffset(months=lookback_months)

    subset = prices.loc[:end_dt]
    if subset.empty:
        return pd.Series(dtype=float)
    p_end = subset.iloc[-1]

    subset_start = prices.loc[:start_dt]
    if subset_start.empty:
        return pd.Series(dtype=float)
    p_start = subset_start.iloc[-1]

    mom = p_end / p_start - 1

    window = prices.loc[start_dt:end_dt]
    sufficient = window.count() >= min_observations
    return mom[sufficient].dropna()
