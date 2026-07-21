"""PR bundle fetch shell + Bc extraction (WP-019, ADR-045). Offline:
fetch paths are exercised with stubbed transport."""

import io
import zipfile
from datetime import date

import pytest

import quantos_core.data.nse_pr as nse_pr_module
from quantos_core.data import DataFetchError, extract_bc_csv, fetch_pr_zip, pr_url


class _StubResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


def zip_with(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in members.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def test_pr_url_is_the_verified_archive_pattern() -> None:
    assert pr_url(date(2026, 7, 20)) == "https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR200726.zip"


def test_fetch_404_is_a_typed_holiday_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_pr_module.requests, "get", lambda *a, **k: _StubResponse(404, b""))
    with pytest.raises(DataFetchError, match="trading holiday, or not yet published"):
        fetch_pr_zip(date(2026, 1, 26))


def test_fetch_non_200_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_pr_module.requests, "get", lambda *a, **k: _StubResponse(503, b"x"))
    with pytest.raises(DataFetchError, match="HTTP 503"):
        fetch_pr_zip(date(2026, 7, 20))


def test_fetch_empty_body_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_pr_module.requests, "get", lambda *a, **k: _StubResponse(200, b""))
    with pytest.raises(DataFetchError, match="empty body"):
        fetch_pr_zip(date(2026, 7, 20))


def test_extract_bc_handles_both_naming_eras() -> None:
    # 2025-era: Bc250825.csv; 2026-era: bc20072026.csv — both must match.
    assert extract_bc_csv(zip_with({"Bc250825.csv": "x", "Readme.txt": "r"})) == b"x"
    assert extract_bc_csv(zip_with({"bc20072026.csv": "y", "Pd200726.csv": "p"})) == b"y"


def test_extract_bc_not_a_zip_fails_closed() -> None:
    with pytest.raises(DataFetchError, match="not a valid zip"):
        extract_bc_csv(b"html error page")


def test_extract_bc_zero_or_two_members_fail_closed() -> None:
    with pytest.raises(DataFetchError, match="exactly one Bc"):
        extract_bc_csv(zip_with({"Pd200726.csv": "p"}))
    with pytest.raises(DataFetchError, match="exactly one Bc"):
        extract_bc_csv(zip_with({"Bc250825.csv": "x", "bc20072026.csv": "y"}))
