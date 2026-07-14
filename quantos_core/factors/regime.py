"""Trend-regime filter math (WP-009).

VERBATIM port of the frozen regime logic: the uptrend series from
`momentum_backtest.load_nifty50_regime` (close > rolling MA, dropna)
and the as-of lookup from `run_backtest` step 2 (last available regime
value at or before the date; True when no value is available yet --
that permissive default is the frozen script's exact behavior,
preserved by ADR-003, not a new decision).

Pure functions: the index series is supplied by the caller; fetching/
caching it stays in the imperative shell.
"""

import pandas as pd


def uptrend_series(index_close: "pd.Series[float]", ma_days: int) -> "pd.Series[bool]":
    """True where the index closes above its ma_days-day simple MA.

    The MA warm-up window is dropped EXPLICITLY: `close > NaN` compares as
    False on a bool series and .dropna() is then a no-op, so the naive port
    silently reported the first ma_days-1 dates as BEAR. The frozen script
    masked this by always pre-fetching extra history; this pure function
    can't assume that. Output is byte-identical to the frozen script for
    pre-warmed input (parity preserved); for short input, dates without a
    valid MA now correctly have no value (is_uptrend then applies its
    documented permissive default).
    """
    ma = index_close.rolling(ma_days).mean()
    result: "pd.Series[bool]" = (index_close > ma)[ma.notna()]
    return result


def is_uptrend(uptrend: "pd.Series[bool]", as_of: pd.Timestamp) -> bool:
    """The regime in force at as_of: last value at or before it.

    True when the series has no value yet -- frozen-script behavior.
    """
    avail = uptrend.index[uptrend.index <= as_of]
    return bool(uptrend.loc[avail[-1]]) if len(avail) else True
