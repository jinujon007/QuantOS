"""The data platform: ingestion, point-in-time storage, corporate
actions, quality validation, caching.

WP-007 implements the Phase 2 opening slice (ADR-033): segregated
DataProvider ports (`UniverseProvider`, `PriceProvider`), the typed
`DataFetchError`, the point-in-time `SqliteUniverseStore` (structural
fix for F1/F9 going forward), and the fail-closed
`CsvCachePriceProvider` over the existing audited cache layout.
WP-018 adds the bhavcopy-primary fetch adapter (ADR-044): official
NSE UDiFF bhavcopy as the immutable EOD source, yfinance quarantined
to cross-check duty. WP-019/020/021 (ADR-045) complete the Phase 2
scope: archive-derived corporate-action adjustment, fail-closed
quality validation, and the `BhavcopyPriceProvider` serving adjusted,
validated closes from the raw archive. The six frozen scripts are
untouched (ADR-003).
"""

from quantos_core.data.bhavcopy import (
    EQUITY_SERIES,
    Bhavcopy,
    bhavcopy_url,
    fetch_bhavcopy_zip,
    load_bhavcopy,
)
from quantos_core.data.bhavcopy_prices import BhavcopyPriceProvider
from quantos_core.data.corporate_actions import (
    AdjustmentEvent,
    CorporateActionRecord,
    adjustment_multipliers,
    events_from_records,
    factor_from_purpose,
    has_price_effect_risk,
    parse_bc_csv,
)
from quantos_core.data.errors import DataFetchError
from quantos_core.data.nse_pr import extract_bc_csv, fetch_pr_zip, pr_url
from quantos_core.data.prices import CsvCachePriceProvider
from quantos_core.data.provider import PriceProvider, Ticker, UniverseProvider
from quantos_core.data.quality import DEFAULT_MAX_ABS_RETURN, DataQualityError, validate_close_frame
from quantos_core.data.universe_store import SqliteUniverseStore

__all__ = [
    "DEFAULT_MAX_ABS_RETURN",
    "EQUITY_SERIES",
    "AdjustmentEvent",
    "Bhavcopy",
    "BhavcopyPriceProvider",
    "CorporateActionRecord",
    "CsvCachePriceProvider",
    "DataFetchError",
    "DataQualityError",
    "PriceProvider",
    "SqliteUniverseStore",
    "Ticker",
    "UniverseProvider",
    "adjustment_multipliers",
    "bhavcopy_url",
    "events_from_records",
    "extract_bc_csv",
    "factor_from_purpose",
    "fetch_bhavcopy_zip",
    "fetch_pr_zip",
    "has_price_effect_risk",
    "load_bhavcopy",
    "parse_bc_csv",
    "pr_url",
    "validate_close_frame",
]
