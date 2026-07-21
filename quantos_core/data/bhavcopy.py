"""NSE UDiFF bhavcopy adapter (WP-018, ADR-044).

The official NSE capital-market bhavcopy is the primary EOD source
under the bhavcopy-primary architecture (ADR-044): an immutable daily
file that includes later-delisted stocks (survivorship channel closed
at the source) and never silently revises history the way the
quarantined yfinance path can (DD 2026-07-21 §9.3).

Format verified against the live archive 2026-07-21: UDiFF CM
(``BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip``, NSE's format since
July 2024). Fetching is a thin shell (`fetch_bhavcopy_zip`); parsing
(`load_bhavcopy`) is pure bytes-in/value-out and golden-file tested.
"""

import io
import zipfile
from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests

from quantos_core.data.errors import DataFetchError

_ARCHIVE_URL = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip"
# The archives host serves plain GETs (no cookie handshake, verified
# live 2026-07-21) but rejects default non-browser user agents.
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537"
_REQUIRED_COLUMNS = ("TradDt", "ISIN", "TckrSymb", "SctySrs", "ClsPric", "PrvsClsgPric", "TtlTradgVol")

#: Cash-market equity series: EQ (normal) + BE (trade-for-trade). Bonds,
#: gold bonds, mutual-fund units etc. carry other series codes and are
#: excluded from the equity slice by default.
EQUITY_SERIES = frozenset({"EQ", "BE"})


@dataclass(frozen=True)
class Bhavcopy:
    """One session's parsed equity slice.

    equities: indexed by symbol (sorted), columns
    ``close, prev_close, volume, isin, series``.
    """

    trade_date: date
    equities: pd.DataFrame


def bhavcopy_url(session: date) -> str:
    """Official archive URL for one session's UDiFF CM bhavcopy zip."""
    return _ARCHIVE_URL.format(ymd=session.strftime("%Y%m%d"))


def fetch_bhavcopy_zip(session: date, *, timeout_s: float = 30.0) -> bytes:
    """Download one session's bhavcopy zip, as published.

    Raises DataFetchError on any transport failure, on HTTP 404 (which
    the archive returns for holidays and not-yet-published sessions),
    and on an empty body — never returns a partial or empty payload.
    """
    url = bhavcopy_url(session)
    try:
        response = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout_s)
    except requests.RequestException as exc:
        raise DataFetchError(f"Bhavcopy fetch failed for {session.isoformat()}: {exc}") from exc
    if response.status_code == 404:
        raise DataFetchError(f"No bhavcopy published for {session.isoformat()} (trading holiday, or not yet published)")
    if response.status_code != 200:
        raise DataFetchError(f"Bhavcopy fetch for {session.isoformat()} returned HTTP {response.status_code}")
    payload = bytes(response.content)
    if not payload:
        raise DataFetchError(f"Bhavcopy fetch for {session.isoformat()} returned an empty body")
    return payload


def load_bhavcopy(zip_bytes: bytes, *, series: frozenset[str] = EQUITY_SERIES) -> Bhavcopy:
    """Parse a bhavcopy zip into its validated equity slice.

    Fail-closed on every structural surprise — bad zip, unexpected
    member count, missing columns (a format change must halt the
    pipeline, not feed it garbage), mixed trade dates, duplicate
    symbols, non-positive or missing closes.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            members = [m for m in archive.namelist() if m.lower().endswith(".csv")]
            if len(members) != 1:
                raise DataFetchError(f"Expected exactly one CSV inside the bhavcopy zip, found {members}")
            raw = archive.read(members[0])
    except zipfile.BadZipFile as exc:
        raise DataFetchError(f"Bhavcopy payload is not a valid zip: {exc}") from exc

    frame = pd.read_csv(io.BytesIO(raw))
    missing = [c for c in _REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise DataFetchError(f"Bhavcopy is missing required columns {missing} — NSE format change? Revisit ADR-044.")

    trade_dates = frame["TradDt"].dropna().unique()
    if len(trade_dates) != 1:
        raise DataFetchError(f"Bhavcopy contains {len(trade_dates)} distinct TradDt values, expected exactly 1")
    trade_date = date.fromisoformat(str(trade_dates[0]))

    equities = frame[frame["SctySrs"].isin(series)]
    if equities.empty:
        raise DataFetchError(f"Bhavcopy for {trade_date.isoformat()} has no rows in series {sorted(series)}")
    if bool(equities["TckrSymb"].duplicated().any()):
        dupes = sorted(equities.loc[equities["TckrSymb"].duplicated(), "TckrSymb"].astype(str).unique().tolist())
        raise DataFetchError(f"Duplicate symbols in bhavcopy equity slice: {dupes}")

    try:
        closes = equities["ClsPric"].astype(float)
        prev_closes = equities["PrvsClsgPric"].astype(float)
        volumes = equities["TtlTradgVol"].astype("int64")
    except (ValueError, TypeError) as exc:
        raise DataFetchError(f"Bhavcopy for {trade_date.isoformat()} has non-numeric price/volume data: {exc}") from exc
    if bool(closes.isna().any()) or bool((closes <= 0).any()):
        raise DataFetchError(f"Non-positive or missing close in bhavcopy for {trade_date.isoformat()}")

    out = pd.DataFrame(
        {
            "close": closes.to_numpy(),
            "prev_close": prev_closes.to_numpy(),
            "volume": volumes.to_numpy(),
            "isin": equities["ISIN"].astype(str).to_numpy(),
            "series": equities["SctySrs"].astype(str).to_numpy(),
        },
        index=pd.Index(equities["TckrSymb"].astype(str), name="symbol"),
    ).sort_index()
    return Bhavcopy(trade_date=trade_date, equities=out)
