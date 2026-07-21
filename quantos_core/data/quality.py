"""Fail-closed data-quality validation for price frames (WP-020, ADR-045).

The Constitution lists data-quality failure among the conditions that
may engage the kill switch automatically (Part V) and bans silent
degradation everywhere (Part III). This module is the Phase 2 slice of
that mandate: a validator that either passes a close-price frame or
raises a typed ``DataQualityError`` naming exactly what is wrong —
never a warning, never a silently narrowed frame.

Pure: frame in, None or typed exception out. Callers (the bhavcopy
provider first, every later provider the same way) validate before any
price series reaches a strategy.
"""

from datetime import date

import pandas as pd

from quantos_core.data.errors import DataFetchError

#: Largest single-session absolute return accepted on an already
#: corporate-action-adjusted series. NSE circuit bands cap most names at
#: +/-20%; only no-band (F&O) names can exceed it, and a move past 35%
#: on an adjusted series is either a missed adjustment or a day that
#: deserves a human before any strategy trades on it.
DEFAULT_MAX_ABS_RETURN = 0.35

_MAX_LISTED = 5  # cap symbol/date lists inside exception messages


class DataQualityError(DataFetchError):
    """A price series failed validation: calendar gaps, missing or
    non-positive values, or an unexplained extreme move. Subclasses
    DataFetchError so every existing fail-closed handler treats it as
    the hard stop it is."""


def _preview(items: list[str]) -> str:
    shown = ", ".join(items[:_MAX_LISTED])
    return shown + (f", ... ({len(items)} total)" if len(items) > _MAX_LISTED else "")


def validate_close_frame(
    frame: pd.DataFrame,
    *,
    expected_sessions: list[date],
    max_abs_return: float = DEFAULT_MAX_ABS_RETURN,
) -> None:
    """Validate a Date-indexed close frame (one column per symbol).

    Raises DataQualityError when the frame's index does not exactly
    match ``expected_sessions``, when any cell is missing or
    non-positive, or when any single-session return exceeds
    ``max_abs_return`` in magnitude. Passing means: every requested
    symbol has a positive close on every expected session and no move
    is beyond the configured band.
    """
    if frame.empty:
        raise DataQualityError("Close frame is empty")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise DataQualityError(f"Close frame index must be a DatetimeIndex, got {type(frame.index).__name__}")

    expected = pd.DatetimeIndex([pd.Timestamp(s) for s in expected_sessions])
    missing = expected.difference(frame.index)
    extra = frame.index.difference(expected)
    if len(missing) or len(extra):
        parts = []
        if len(missing):
            parts.append(f"missing sessions {_preview([str(d.date()) for d in missing])}")
        if len(extra):
            parts.append(f"unexpected dates {_preview([str(d.date()) for d in extra])}")
        raise DataQualityError(f"Close frame does not match the trading calendar: {'; '.join(parts)}")
    if bool(frame.index.has_duplicates):
        raise DataQualityError("Close frame has duplicate dates")
    if not bool(frame.index.is_monotonic_increasing):
        raise DataQualityError("Close frame dates are unsorted")

    for name in frame.columns:
        try:
            column = frame[name].astype(float)
        except (ValueError, TypeError) as exc:
            raise DataQualityError(f"{name}: non-numeric close values ({exc})") from exc
        holes = column.isna()
        if bool(holes.any()):
            days = [str(d.date()) for d in frame.index[holes]]
            raise DataQualityError(f"{name}: no close for sessions {_preview(days)} (suspension or archive gap)")
        if bool((column <= 0).any()):
            days = [str(d.date()) for d in frame.index[column <= 0]]
            raise DataQualityError(f"{name}: non-positive close on {_preview(days)}")
        returns = column.pct_change().iloc[1:]
        wild = returns.abs() > max_abs_return
        if bool(wild.any()):
            worst_day = returns[wild].abs().idxmax()
            worst = float(returns.loc[worst_day])
            raise DataQualityError(
                f"{name}: single-session return {worst:+.1%} on {worst_day.date()} exceeds "
                f"the +/-{max_abs_return:.0%} band — missed corporate action or data defect"
            )
