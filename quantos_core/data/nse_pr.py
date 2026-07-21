"""NSE daily PR bundle fetch + Bc (corporate actions) extraction (WP-019, ADR-045).

The PR bundle (``PR<ddmmyy>.zip``) is published per session on the
same cookie-free archives host as the UDiFF bhavcopy. Its ``Bc*.csv``
member is NSE's official corporate-action record for the session:
symbol, ex-date, and a PURPOSE string ("BONUS 1:1", "FVSPLT FRM RS 5
TO RE 1", "DIV - RS 2 PER SH", ...) — the authoritative input for
price adjustment, verified live 2026-07-22 (the UDiFF bhavcopy's
PrvsClsgPric is *not* republished adjusted on ex-dates; see ADR-045's
disproven-hypothesis note).

Same shape as the bhavcopy adapter: fetching is a thin shell,
extraction is bytes-in/bytes-out and fail-closed on format surprises
(member naming drifts across eras — ``Bc020625.csv`` vs
``bc20072026.csv`` — so matching is case-insensitive on the prefix).
"""

import io
import zipfile
from datetime import date

import requests

from quantos_core.data.errors import DataFetchError

_PR_URL = "https://nsearchives.nseindia.com/archives/equities/bhavcopy/pr/PR{dmy}.zip"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537"


def pr_url(session: date) -> str:
    """Official archive URL for one session's PR bundle zip."""
    return _PR_URL.format(dmy=session.strftime("%d%m%y"))


def fetch_pr_zip(session: date, *, timeout_s: float = 30.0) -> bytes:
    """Download one session's PR bundle, as published. Fail-closed like
    the bhavcopy fetch: 404 (holiday / not yet published), non-200,
    empty body and transport errors are all typed failures."""
    url = pr_url(session)
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout_s)
    except requests.RequestException as exc:
        raise DataFetchError(f"PR bundle fetch failed for {session.isoformat()}: {exc}") from exc
    if response.status_code == 404:
        raise DataFetchError(
            f"No PR bundle published for {session.isoformat()} (trading holiday, or not yet published)"
        )
    if response.status_code != 200:
        raise DataFetchError(f"PR bundle fetch for {session.isoformat()} returned HTTP {response.status_code}")
    payload = bytes(response.content)
    if not payload:
        raise DataFetchError(f"PR bundle fetch for {session.isoformat()} returned an empty body")
    return payload


def extract_bc_csv(pr_zip_bytes: bytes) -> bytes:
    """The Bc (corporate actions) member of a PR bundle, fail-closed on
    a bad zip or on anything other than exactly one Bc member."""
    try:
        with zipfile.ZipFile(io.BytesIO(pr_zip_bytes)) as archive:
            members = [m for m in archive.namelist() if m.lower().startswith("bc") and m.lower().endswith(".csv")]
            if len(members) != 1:
                raise DataFetchError(f"Expected exactly one Bc*.csv member in the PR bundle, found {members}")
            return archive.read(members[0])
    except zipfile.BadZipFile as exc:
        raise DataFetchError(f"PR bundle payload is not a valid zip: {exc}") from exc
