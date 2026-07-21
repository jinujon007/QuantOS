"""The data platform: ingestion, point-in-time storage, corporate
actions, quality validation, caching.

WP-007 implements the Phase 2 opening slice (ADR-033): segregated
DataProvider ports (`UniverseProvider`, `PriceProvider`), the typed
`DataFetchError`, the point-in-time `SqliteUniverseStore` (structural
fix for F1/F9 going forward), and the fail-closed
`CsvCachePriceProvider` over the existing audited cache layout.
WP-018 adds the bhavcopy-primary fetch adapter (ADR-044): official
NSE UDiFF bhavcopy as the immutable EOD source, yfinance quarantined
to cross-check duty. Corporate actions and quality validators are
later Phase 2 work packages. The six frozen scripts are untouched
(ADR-003).
"""

from quantos_core.data.bhavcopy import (
    EQUITY_SERIES,
    Bhavcopy,
    bhavcopy_url,
    fetch_bhavcopy_zip,
    load_bhavcopy,
)
from quantos_core.data.errors import DataFetchError
from quantos_core.data.prices import CsvCachePriceProvider
from quantos_core.data.provider import PriceProvider, Ticker, UniverseProvider
from quantos_core.data.universe_store import SqliteUniverseStore

__all__ = [
    "EQUITY_SERIES",
    "Bhavcopy",
    "CsvCachePriceProvider",
    "DataFetchError",
    "PriceProvider",
    "SqliteUniverseStore",
    "Ticker",
    "UniverseProvider",
    "bhavcopy_url",
    "fetch_bhavcopy_zip",
    "load_bhavcopy",
]
