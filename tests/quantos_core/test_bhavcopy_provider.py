"""BhavcopyPriceProvider over a synthetic archive (WP-021, ADR-045).

Fixtures are minimal UDiFF CSVs plus PR bundles (with real-shape Bc
corporate-action members) zipped under the exact published filenames
in tmp directories — the provider is exercised end to end: archive
read, parse, official-record adjustment, quality validation. Dates are
real XBOM sessions (Mon 2026-07-13 .. Wed 2026-07-15).
"""

import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from quantos_core.data import (
    BhavcopyPriceProvider,
    DataFetchError,
    DataQualityError,
    Ticker,
    bhavcopy_url,
    pr_url,
)

D1, D2, D3 = date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15)

UDIFF_HEADER = "TradDt,ISIN,TckrSymb,SctySrs,ClsPric,PrvsClsgPric,TtlTradgVol"
BC_HEADER = "SERIES,SYMBOL,SECURITY,RECORD_DT,BC_STRT_DT,BC_END_DT,EX_DT,ND_STRT_DT,ND_END_DT,PURPOSE"


def udiff_zip(day: date, rows: list[tuple[str, float, float]]) -> bytes:
    """rows: (symbol, close, prev_close)."""
    lines = [UDIFF_HEADER] + [
        f"{day.isoformat()},INE{i:03d}TEST,{symbol},EQ,{close},{prev},1000"
        for i, (symbol, close, prev) in enumerate(rows)
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"BhavCopy_NSE_CM_0_0_0_{day.strftime('%Y%m%d')}_F_0000.csv", "\n".join(lines))
    return buffer.getvalue()


def pr_zip(day: date, actions: list[tuple[str, date, str]]) -> bytes:
    """actions: (symbol, ex_date, purpose) — rendered as real Bc rows."""
    lines = [BC_HEADER] + [
        f"EQ,{symbol},{symbol} Ltd,,,,{ex_date.isoformat()},,,{purpose}" for symbol, ex_date, purpose in actions
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(f"Bc{day.strftime('%d%m%y')}.csv", "\n".join(lines))
        archive.writestr("Readme.txt", "stub")
    return buffer.getvalue()


def write_day(
    root: Path,
    day: date,
    rows: list[tuple[str, float, float]],
    actions: list[tuple[str, date, str]] | None = None,
) -> None:
    bhav_dir, pr_dir = root / "bhavcopy", root / "nse_pr"
    bhav_dir.mkdir(exist_ok=True)
    pr_dir.mkdir(exist_ok=True)
    (bhav_dir / bhavcopy_url(day).rsplit("/", 1)[-1]).write_bytes(udiff_zip(day, rows))
    (pr_dir / pr_url(day).rsplit("/", 1)[-1]).write_bytes(pr_zip(day, actions or []))


def provider(root: Path, **kwargs: float) -> BhavcopyPriceProvider:
    return BhavcopyPriceProvider(root / "bhavcopy", root / "nse_pr", **kwargs)


def tickers(*names: str) -> list[Ticker]:
    return [Ticker(n) for n in names]


@pytest.fixture()
def archive(tmp_path: Path) -> Path:
    # AAA runs a 1:1 bonus ex D3: closed 102 on D2, halves to 51-52 on
    # D3. The official record rides in D2's (forward-looking) and D3's
    # Bc files — the dedup path is exercised by default. BBB: no action.
    bonus = ("AAA", D3, "BONUS 1:1")
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0), ("BBB", 50.0, 49.5)])
    write_day(tmp_path, D2, [("AAA", 102.0, 100.0), ("BBB", 50.5, 50.0)], actions=[bonus])
    write_day(tmp_path, D3, [("AAA", 52.0, 102.0), ("BBB", 51.0, 50.5)], actions=[bonus])
    return tmp_path


def test_serves_adjusted_validated_closes(archive: Path) -> None:
    frame = provider(archive).get_prices(tickers("AAA", "BBB"), D1, D3)
    assert list(frame.columns) == ["AAA", "BBB"]
    assert list(frame.index) == [pd.Timestamp(D1), pd.Timestamp(D2), pd.Timestamp(D3)]
    # AAA's pre-bonus closes are halved into the post-bonus basis —
    # and the record listed in two Bc files is applied exactly once.
    assert list(frame["AAA"]) == pytest.approx([50.0, 51.0, 52.0])
    # BBB had no action: raw closes pass through.
    assert list(frame["BBB"]) == pytest.approx([50.0, 50.5, 51.0])


def test_missing_record_means_quality_failure_not_garbage(tmp_path: Path) -> None:
    # Same halving, but no official record: the -49% raw move must be a
    # typed quality failure, never a silently served series.
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)])
    write_day(tmp_path, D2, [("AAA", 102.0, 100.0)])
    write_day(tmp_path, D3, [("AAA", 52.0, 102.0)])
    with pytest.raises(DataQualityError, match="AAA: single-session return -49"):
        provider(tmp_path).get_prices(tickers("AAA"), D1, D3)


def test_uncomputable_record_is_named_on_quality_failure(tmp_path: Path) -> None:
    # A demerger-style record has no computable factor; when the move
    # breaks the band, the failure must name the official record.
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)])
    write_day(tmp_path, D2, [("AAA", 102.0, 100.0)])
    write_day(tmp_path, D3, [("AAA", 52.0, 102.0)], actions=[("AAA", D3, "SCHEME OF ARRANGEMENT")])
    with pytest.raises(DataQualityError, match="uncomputable corporate-action records.*SCHEME OF ARRANGEMENT"):
        provider(tmp_path).get_prices(tickers("AAA"), D1, D3)


def test_dividend_records_do_not_adjust_prices(archive: Path) -> None:
    write_day(archive, D2, [("AAA", 102.0, 100.0), ("BBB", 50.5, 50.0)], actions=[("BBB", D3, "DIV - RS 2 PER SH")])
    write_day(archive, D3, [("AAA", 52.0, 102.0), ("BBB", 51.0, 50.5)], actions=[("AAA", D3, "BONUS 1:1")])
    frame = provider(archive).get_prices(tickers("BBB"), D1, D3)
    assert list(frame["BBB"]) == pytest.approx([50.0, 50.5, 51.0])


def test_future_dated_records_are_not_applied(tmp_path: Path) -> None:
    # Bc files list actions days ahead; an ex-date beyond the window
    # end must not rescale anything.
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)], actions=[("AAA", date(2026, 7, 16), "BONUS 1:1")])
    write_day(tmp_path, D2, [("AAA", 101.0, 100.0)], actions=[("AAA", date(2026, 7, 16), "BONUS 1:1")])
    frame = provider(tmp_path).get_prices(tickers("AAA"), D1, D2)
    assert list(frame["AAA"]) == pytest.approx([100.0, 101.0])


def test_missing_bhavcopy_file_names_the_fetch_tool(archive: Path) -> None:
    (archive / "bhavcopy" / bhavcopy_url(D2).rsplit("/", 1)[-1]).unlink()
    with pytest.raises(DataFetchError, match=r"bhavcopy for session 2026-07-14.*fetch_bhavcopy\.py"):
        provider(archive).get_prices(tickers("AAA"), D1, D3)


def test_missing_pr_file_names_the_fetch_tool(archive: Path) -> None:
    (archive / "nse_pr" / pr_url(D2).rsplit("/", 1)[-1]).unlink()
    with pytest.raises(DataFetchError, match=r"PR bundle for session 2026-07-14.*fetch_bhavcopy\.py"):
        provider(archive).get_prices(tickers("AAA"), D1, D3)


def test_symbol_absent_one_session_is_a_quality_failure(archive: Path) -> None:
    write_day(archive, D2, [("BBB", 50.5, 50.0)])  # overwrite: AAA missing on D2
    with pytest.raises(DataQualityError, match="AAA: no close for sessions 2026-07-14"):
        provider(archive).get_prices(tickers("AAA", "BBB"), D1, D3)


def test_unknown_symbol_is_a_quality_failure(archive: Path) -> None:
    with pytest.raises(DataQualityError, match="NOSUCH: no close"):
        provider(archive).get_prices(tickers("NOSUCH"), D1, D3)


def test_archive_content_date_mismatch_fails_closed(tmp_path: Path) -> None:
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)])
    name = bhavcopy_url(D1).rsplit("/", 1)[-1]
    (tmp_path / "bhavcopy" / name).write_bytes(udiff_zip(D2, [("AAA", 100.0, 99.0)]))
    with pytest.raises(DataFetchError, match="dated 2026-07-14 — corrupt archive"):
        provider(tmp_path).get_prices(tickers("AAA"), D1, D1)


def test_empty_tickers_and_inverted_window_fail(archive: Path) -> None:
    with pytest.raises(DataFetchError, match="empty ticker list"):
        provider(archive).get_prices([], D1, D3)
    with pytest.raises(DataFetchError, match="Invalid window"):
        provider(archive).get_prices(tickers("AAA"), D3, D1)


def test_window_with_no_sessions_fails(archive: Path) -> None:
    with pytest.raises(DataFetchError, match="No NSE sessions"):
        provider(archive).get_prices(tickers("AAA"), date(2026, 7, 18), date(2026, 7, 19))


def test_missing_archive_dirs_fail_at_construction(tmp_path: Path) -> None:
    (tmp_path / "bhavcopy").mkdir()
    with pytest.raises(DataFetchError, match="PR bundle archive directory"):
        BhavcopyPriceProvider(tmp_path / "bhavcopy", tmp_path / "nope")
    with pytest.raises(DataFetchError, match="Bhavcopy archive directory"):
        BhavcopyPriceProvider(tmp_path / "nope", tmp_path / "bhavcopy")


def test_record_listed_only_before_window_is_still_applied(tmp_path: Path) -> None:
    # ADV-2, confirmed live (MOS/USASEEDS bonuses ex 2025-09-26 absent
    # from their own ex-date file): a record whose only listing is in a
    # pre-window session's Bc file must still adjust via the lookback.
    d0 = date(2026, 7, 10)  # Friday before the D1..D3 window
    write_day(tmp_path, d0, [("AAA", 99.0, 98.0)], actions=[("AAA", D3, "BONUS 1:1")])
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)])
    write_day(tmp_path, D2, [("AAA", 102.0, 100.0)])
    write_day(tmp_path, D3, [("AAA", 52.0, 102.0)])
    frame = provider(tmp_path).get_prices(tickers("AAA"), D1, D3)
    assert list(frame["AAA"]) == pytest.approx([50.0, 51.0, 52.0])


def test_out_of_calendar_window_is_a_typed_failure(archive: Path) -> None:
    # ADV-7: exchange-calendars' own out-of-bounds errors must not
    # escape the PriceProvider contract untyped.
    with pytest.raises(DataFetchError, match="Trading-calendar failure"):
        provider(archive).get_prices(tickers("AAA"), date(1800, 1, 1), date(1800, 2, 1))


def test_max_abs_return_is_tunable(tmp_path: Path) -> None:
    write_day(tmp_path, D1, [("AAA", 100.0, 99.0)])
    write_day(tmp_path, D2, [("AAA", 60.0, 100.0)])  # -40%, genuine crash
    frame = provider(tmp_path, max_abs_return=0.50).get_prices(tickers("AAA"), D1, D2)
    assert list(frame["AAA"]) == pytest.approx([100.0, 60.0])
