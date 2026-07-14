"""Fail-closed price provider over the existing audited CSV cache (WP-007).

Reads the layout download_data.py already writes (`data/cache/
<TICKER>_NS.csv`, columns `Date,Close`) without touching that frozen
script. Every failure -- missing ticker file, unreadable/columnless
CSV, empty window -- is a typed DataFetchError, never a silently
narrower or empty frame (the exact anti-pattern of download_data.py:64
that this module structurally retires for new code).
"""

from datetime import date
from pathlib import Path

import pandas as pd

from quantos_core.data.errors import DataFetchError
from quantos_core.data.provider import Ticker


class CsvCachePriceProvider:
    """PriceProvider adapter over a directory of per-ticker close CSVs."""

    def __init__(self, cache_dir: Path) -> None:
        if not cache_dir.is_dir():
            raise DataFetchError(f"Price cache directory does not exist: {cache_dir}")
        self._cache_dir = cache_dir

    def _path_for(self, ticker: Ticker) -> Path:
        # download_data.py's naming: RELIANCE.NS -> RELIANCE_NS.csv
        return self._cache_dir / f"{str(ticker).replace('.', '_')}.csv"

    def _load_one(self, ticker: Ticker) -> "pd.Series[float]":
        path = self._path_for(ticker)
        if not path.is_file():
            raise DataFetchError(f"No cached prices for {ticker!s} (expected {path.name})")
        try:
            frame = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
            closes = frame["Close"].astype(float)
        except (ValueError, KeyError, OSError) as exc:
            raise DataFetchError(f"Unreadable price cache for {ticker!s} ({path.name}): {exc}") from exc
        if closes.empty:
            raise DataFetchError(f"Price cache for {ticker!s} is empty ({path.name})")
        return closes

    def get_prices(self, tickers: list[Ticker], start: date, end: date) -> pd.DataFrame:
        if not tickers:
            raise DataFetchError("get_prices called with an empty ticker list")
        if end < start:
            raise DataFetchError(f"Invalid window: end {end.isoformat()} before start {start.isoformat()}")
        columns = {str(t): self._load_one(t) for t in sorted(set(tickers))}
        frame = pd.DataFrame(columns).loc[pd.Timestamp(start) : pd.Timestamp(end)]
        if frame.empty:
            raise DataFetchError(
                f"No cached prices in window {start.isoformat()}..{end.isoformat()} for requested tickers"
            )
        # Index union can leave one ticker fully absent from the window
        # while others fill it -- an all-NaN column is a per-ticker
        # failure, never a silently narrower answer.
        for name in frame.columns:
            if bool(frame[name].isna().all()):
                raise DataFetchError(f"No cached prices for {name} in window {start.isoformat()}..{end.isoformat()}")
        return frame
