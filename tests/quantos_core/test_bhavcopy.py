"""Bhavcopy adapter + trading calendar + archive tool (WP-018, ADR-044).

The golden fixture is 6 rows cut verbatim from the real
BhavCopy_NSE_CM_0_0_0_20260720_F_0000.csv downloaded from NSE's
archive on 2026-07-21 — the parser is pinned against the actual
published format, not a hand-imagined one. Everything here is offline:
fetch paths are exercised with stubbed transport.
"""

import io
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import quantos_core.data.bhavcopy as bhavcopy_module
import tools.fetch_bhavcopy as fetch_tool
from quantos_core.data import DataFetchError, bhavcopy_url, fetch_bhavcopy_zip, load_bhavcopy
from quantos_core.utils import is_trading_session, most_recent_session

GOLDEN = Path(__file__).resolve().parents[1] / "golden" / "bhavcopy_20260720_sample.csv"
MEMBER = "BhavCopy_NSE_CM_0_0_0_20260720_F_0000.csv"


def zip_of(csv_text: str, member: str = MEMBER) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member, csv_text)
    return buffer.getvalue()


def golden_zip() -> bytes:
    return zip_of(GOLDEN.read_text(encoding="utf-8"))


# ── parsing ──────────────────────────────────────────────────────────────


def test_golden_parse_matches_published_values() -> None:
    bhav = load_bhavcopy(golden_zip())
    assert bhav.trade_date == date(2026, 7, 20)
    # Values as published by NSE for 2026-07-20, verified at download time.
    assert bhav.equities.loc["RELIANCE", "close"] == pytest.approx(1323.10)
    assert bhav.equities.loc["RELIANCE", "prev_close"] == pytest.approx(1327.20)
    assert bhav.equities.loc["RELIANCE", "isin"] == "INE002A01018"
    assert int(bhav.equities.loc["RELIANCE", "volume"]) == 14305844
    assert bhav.equities.loc["SYRMA", "close"] == pytest.approx(1340.80)
    assert list(bhav.equities.index) == sorted(bhav.equities.index), "symbols must be sorted"


def test_default_series_takes_eq_and_be_excludes_bonds() -> None:
    bhav = load_bhavcopy(golden_zip())
    assert "AAREYDRUGS" in bhav.equities.index  # BE series
    assert "SGBJUN28" not in bhav.equities.index  # GB (gold bond) excluded


def test_eq_only_series_excludes_be() -> None:
    bhav = load_bhavcopy(golden_zip(), series=frozenset({"EQ"}))
    assert "AAREYDRUGS" not in bhav.equities.index
    assert "RELIANCE" in bhav.equities.index


def test_not_a_zip_fails_closed() -> None:
    with pytest.raises(DataFetchError, match="not a valid zip"):
        load_bhavcopy(b"this is not a zip")


def test_two_csv_members_fails_closed() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.csv", "x")
        archive.writestr("b.csv", "y")
    with pytest.raises(DataFetchError, match="exactly one CSV"):
        load_bhavcopy(buffer.getvalue())


def test_missing_required_column_fails_closed() -> None:
    text = GOLDEN.read_text(encoding="utf-8").replace("ClsPric", "Renamed")
    with pytest.raises(DataFetchError, match="missing required columns"):
        load_bhavcopy(zip_of(text))


def test_mixed_trade_dates_fail_closed() -> None:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    lines.append(lines[1].replace("2026-07-20", "2026-07-17"))
    with pytest.raises(DataFetchError, match="distinct TradDt"):
        load_bhavcopy(zip_of("\n".join(lines)))


def test_duplicate_symbol_fails_closed() -> None:
    lines = GOLDEN.read_text(encoding="utf-8").splitlines()
    lines.append(lines[1])  # RELIANCE twice
    with pytest.raises(DataFetchError, match="Duplicate symbols"):
        load_bhavcopy(zip_of("\n".join(lines)))


def test_non_positive_close_fails_closed() -> None:
    text = GOLDEN.read_text(encoding="utf-8").replace(",1323.10,", ",0.00,")
    with pytest.raises(DataFetchError, match="Non-positive or missing close"):
        load_bhavcopy(zip_of(text))


def test_no_equity_rows_fails_closed() -> None:
    with pytest.raises(DataFetchError, match="no rows in series"):
        load_bhavcopy(golden_zip(), series=frozenset({"ZZ"}))


# ── fetch shell (stubbed transport) ──────────────────────────────────────


class _StubResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


def test_bhavcopy_url_is_the_verified_archive_pattern() -> None:
    assert (
        bhavcopy_url(date(2026, 7, 20))
        == "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20260720_F_0000.csv.zip"
    )


def test_fetch_404_is_a_typed_holiday_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bhavcopy_module.requests, "get", lambda *a, **k: _StubResponse(404, b""))
    with pytest.raises(DataFetchError, match="trading holiday, or not yet published"):
        fetch_bhavcopy_zip(date(2026, 1, 26))


def test_fetch_non_200_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bhavcopy_module.requests, "get", lambda *a, **k: _StubResponse(503, b"x"))
    with pytest.raises(DataFetchError, match="HTTP 503"):
        fetch_bhavcopy_zip(date(2026, 7, 20))


def test_fetch_empty_body_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bhavcopy_module.requests, "get", lambda *a, **k: _StubResponse(200, b""))
    with pytest.raises(DataFetchError, match="empty body"):
        fetch_bhavcopy_zip(date(2026, 7, 20))


# ── trading calendar ─────────────────────────────────────────────────────


def test_calendar_sessions_and_holidays() -> None:
    assert is_trading_session(date(2026, 7, 20)) is True  # Monday
    assert is_trading_session(date(2026, 7, 19)) is False  # Sunday
    assert is_trading_session(date(2026, 1, 26)) is False  # Republic Day


def test_most_recent_session_rolls_weekend_back_to_friday() -> None:
    assert most_recent_session(date(2026, 7, 19)) == date(2026, 7, 17)
    assert most_recent_session(date(2026, 7, 20)) == date(2026, 7, 20)


# ── archive tool ─────────────────────────────────────────────────────────


def test_tool_archives_then_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    calls = {"n": 0}

    def fake_fetch(session: date, **kwargs: object) -> bytes:
        calls["n"] += 1
        return golden_zip()

    monkeypatch.setattr(fetch_tool, "fetch_bhavcopy_zip", fake_fetch)
    assert fetch_tool.main(["--date", "2026-07-20", "--out-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Archived" in out and "RELIANCE" not in out.split("equity rows")[0]
    assert (tmp_path / MEMBER).with_suffix(".csv.zip").name  # filename derived from URL
    archived = list(tmp_path.iterdir())
    assert len(archived) == 1 and archived[0].name == MEMBER + ".zip"

    # Second run: no re-fetch, same summary, still exit 0.
    assert fetch_tool.main(["--date", "2026-07-20", "--out-dir", str(tmp_path)]) == 0
    assert calls["n"] == 1, "an archived session must never be re-fetched (immutable raw store)"
    assert "Already archived" in capsys.readouterr().out


def test_tool_rejects_non_session_date(tmp_path: Path, capsys) -> None:
    assert fetch_tool.main(["--date", "2026-07-19", "--out-dir", str(tmp_path)]) == 1
    assert "not an NSE trading session" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_tool_detects_session_vs_content_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(fetch_tool, "fetch_bhavcopy_zip", lambda session, **k: golden_zip())
    # 2026-07-17 is a real session, but the (stubbed) payload is dated 07-20.
    assert fetch_tool.main(["--date", "2026-07-17", "--out-dir", str(tmp_path)]) == 1
    assert "archive dated 2026-07-20" in capsys.readouterr().out


def test_golden_fixture_is_verbatim_udiff() -> None:
    """The fixture must keep the full 34-column UDiFF header — trimming
    columns would let the parser drift from the real published format."""
    header = GOLDEN.read_text(encoding="utf-8").splitlines()[0]
    expected_prefix = ["TradDt", "BizDt", "Sgmt", "Src", "FinInstrmTp", "FinInstrmId", "ISIN", "TckrSymb", "SctySrs"]
    assert header.split(",")[:9] == expected_prefix
    assert len(header.split(",")) == 34
    frame = pd.read_csv(GOLDEN)
    assert len(frame) == 6
