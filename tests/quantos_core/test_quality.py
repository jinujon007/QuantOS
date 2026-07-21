"""Fail-closed price-frame quality validation (WP-020, ADR-045)."""

from datetime import date

import pandas as pd
import pytest

from quantos_core.data import DataQualityError, validate_close_frame

SESSIONS = [date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15)]


def frame_of(columns: dict[str, list[float]], dates: list[date] = SESSIONS) -> pd.DataFrame:
    return pd.DataFrame(columns, index=pd.DatetimeIndex([pd.Timestamp(d) for d in dates]))


def test_clean_frame_passes() -> None:
    validate_close_frame(
        frame_of({"AAA": [100.0, 101.0, 99.5], "BBB": [50.0, 50.0, 51.0]}),
        expected_sessions=SESSIONS,
    )


def test_empty_frame_fails() -> None:
    with pytest.raises(DataQualityError, match="empty"):
        validate_close_frame(pd.DataFrame(), expected_sessions=SESSIONS)


def test_non_datetime_index_fails() -> None:
    frame = pd.DataFrame({"AAA": [1.0, 2.0, 3.0]}, index=[1, 2, 3])
    with pytest.raises(DataQualityError, match="DatetimeIndex"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_missing_session_fails() -> None:
    frame = frame_of({"AAA": [100.0, 101.0]}, dates=SESSIONS[:2])
    with pytest.raises(DataQualityError, match="missing sessions.*2026-07-15"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_unexpected_date_fails() -> None:
    weekend = SESSIONS + [date(2026, 7, 19)]
    frame = frame_of({"AAA": [100.0, 101.0, 99.5, 99.0]}, dates=weekend)
    with pytest.raises(DataQualityError, match="unexpected dates.*2026-07-19"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_duplicate_dates_fail() -> None:
    dates = [SESSIONS[0], SESSIONS[1], SESSIONS[1], SESSIONS[2]]
    frame = frame_of({"AAA": [100.0, 101.0, 101.0, 99.5]}, dates=dates)
    with pytest.raises(DataQualityError, match="duplicate dates"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_missing_value_names_symbol_and_session() -> None:
    frame = frame_of({"AAA": [100.0, float("nan"), 99.5]})
    with pytest.raises(DataQualityError, match="AAA: no close for sessions 2026-07-14"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_non_positive_close_fails() -> None:
    frame = frame_of({"AAA": [100.0, 0.0, 99.5]})
    with pytest.raises(DataQualityError, match="AAA: non-positive close on 2026-07-14"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_extreme_move_fails_with_symbol_and_date() -> None:
    frame = frame_of({"AAA": [100.0, 60.0, 61.0]})  # -40% in one session
    with pytest.raises(DataQualityError, match=r"AAA: single-session return -40\.0% on 2026-07-14"):
        validate_close_frame(frame, expected_sessions=SESSIONS)


def test_move_inside_band_passes() -> None:
    validate_close_frame(frame_of({"AAA": [100.0, 70.0, 71.0]}), expected_sessions=SESSIONS)  # -30%


def test_band_is_tunable() -> None:
    frame = frame_of({"AAA": [100.0, 90.0, 91.0]})  # -10%
    with pytest.raises(DataQualityError, match="exceeds"):
        validate_close_frame(frame, expected_sessions=SESSIONS, max_abs_return=0.05)


def test_non_numeric_values_are_a_typed_failure() -> None:
    # ADV-7: the validator's whole contract is typed failure — an
    # object column from a future provider must not escape as ValueError.
    frame = pd.DataFrame(
        {"AAA": [100.0, "oops", 99.5]},
        index=pd.DatetimeIndex([pd.Timestamp(d) for d in SESSIONS]),
    )
    with pytest.raises(DataQualityError, match="AAA: non-numeric close values"):
        validate_close_frame(frame, expected_sessions=SESSIONS)
