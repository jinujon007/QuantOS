"""Tests for quantos_core.data (WP-007).

Point-in-time correctness is the load-bearing suite here (Blueprint
module 02 test spec: "a ticker delisted mid-window is excluded from
later-date queries"): membership must come from the latest snapshot at
or before the asked date, and a query before any snapshot must fail
loudly. Price provider tests pin the fail-closed contract that retires
the download_data.py:64 anti-pattern for new code.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from quantos_core.data import (
    CsvCachePriceProvider,
    DataFetchError,
    PriceProvider,
    SqliteUniverseStore,
    Ticker,
    UniverseProvider,
)

T2019 = date(2019, 6, 28)
T2020 = date(2020, 6, 26)
T2021 = date(2021, 6, 25)


@pytest.fixture
def store(tmp_path: Path) -> SqliteUniverseStore:
    s = SqliteUniverseStore(tmp_path / "universe.db")
    s.record_snapshot(T2019, [Ticker("AAA.NS"), Ticker("DELISTED.NS")])
    s.record_snapshot(T2020, [Ticker("AAA.NS"), Ticker("NEWLISTING.NS")])
    return s


def test_point_in_time_membership(store: SqliteUniverseStore) -> None:
    assert store.get_universe(T2019) == [Ticker("AAA.NS"), Ticker("DELISTED.NS")]
    assert store.get_universe(T2020) == [Ticker("AAA.NS"), Ticker("NEWLISTING.NS")]


def test_delisted_ticker_excluded_from_later_queries(store: SqliteUniverseStore) -> None:
    assert Ticker("DELISTED.NS") not in store.get_universe(T2021)


def test_intermediate_date_served_by_earlier_snapshot(store: SqliteUniverseStore) -> None:
    assert store.get_universe(date(2019, 12, 31)) == store.get_universe(T2019)
    assert store.latest_snapshot_date(date(2019, 12, 31)) == T2019


def test_query_before_first_snapshot_fails_loudly(store: SqliteUniverseStore) -> None:
    with pytest.raises(DataFetchError, match="No universe snapshot"):
        store.get_universe(date(2018, 1, 1))


def test_empty_snapshot_refused(store: SqliteUniverseStore) -> None:
    with pytest.raises(DataFetchError, match="empty"):
        store.record_snapshot(T2021, [])


def test_duplicate_snapshot_requires_replace(store: SqliteUniverseStore) -> None:
    with pytest.raises(DataFetchError, match="replace=True"):
        store.record_snapshot(T2019, [Ticker("BBB.NS")])
    store.record_snapshot(T2019, [Ticker("BBB.NS")], replace=True)
    assert store.get_universe(T2019) == [Ticker("BBB.NS")]


def test_universe_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "u.db"
    SqliteUniverseStore(path).record_snapshot(T2019, [Ticker("AAA.NS")])
    assert SqliteUniverseStore(path).get_universe(T2019) == [Ticker("AAA.NS")]


def test_store_satisfies_universe_provider_port(store: SqliteUniverseStore) -> None:
    def accepts(provider: UniverseProvider) -> UniverseProvider:
        return provider

    assert accepts(store) is store


def test_unreachable_database_fails_closed_at_construction(tmp_path: Path) -> None:
    with pytest.raises(DataFetchError, match="unavailable"):
        SqliteUniverseStore(tmp_path)  # a directory, not a db file


def test_sqlite_failures_wrapped_on_every_operation(
    store: SqliteUniverseStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_connect(*args: Any, **kwargs: Any) -> Any:
        raise sqlite3.OperationalError("disk gone")

    monkeypatch.setattr(store, "latest_snapshot_date", lambda as_of: T2020)
    monkeypatch.setattr(sqlite3, "connect", broken_connect)
    with pytest.raises(DataFetchError):
        store.record_snapshot(T2021, [Ticker("AAA.NS")])
    with pytest.raises(DataFetchError):
        store.get_universe(T2020)  # its own read wrap, snapshot resolution stubbed
    monkeypatch.undo()
    monkeypatch.setattr(sqlite3, "connect", broken_connect)
    with pytest.raises(DataFetchError):
        store.latest_snapshot_date(T2020)


# ── prices ────────────────────────────────────────────────────────────────


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    d = tmp_path / "cache"
    d.mkdir()
    (d / "AAA_NS.csv").write_text("Date,Close\n2019-01-01,100.0\n2019-01-02,101.5\n2019-01-03,99.0\n", encoding="utf-8")
    (d / "BBB_NS.csv").write_text("Date,Close\n2019-01-02,50.0\n2019-01-03,51.0\n", encoding="utf-8")
    return d


def test_prices_window_and_columns(cache_dir: Path) -> None:
    provider = CsvCachePriceProvider(cache_dir)
    frame = provider.get_prices([Ticker("AAA.NS"), Ticker("BBB.NS")], date(2019, 1, 2), date(2019, 1, 3))
    assert list(frame.columns) == ["AAA.NS", "BBB.NS"]
    assert len(frame) == 2
    assert frame.loc["2019-01-02", "BBB.NS"] == 50.0


def test_missing_ticker_fails_loudly_not_narrower(cache_dir: Path) -> None:
    provider = CsvCachePriceProvider(cache_dir)
    with pytest.raises(DataFetchError, match="CCC.NS"):
        provider.get_prices([Ticker("AAA.NS"), Ticker("CCC.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_unreadable_csv_fails_loudly(cache_dir: Path) -> None:
    (cache_dir / "BAD_NS.csv").write_text("garbage,columns\n1,2\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="BAD"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("BAD.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_header_only_csv_fails_loudly(cache_dir: Path) -> None:
    (cache_dir / "HOLLOW_NS.csv").write_text("Date,Close\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="empty"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("HOLLOW.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_missing_close_column_fails_loudly(cache_dir: Path) -> None:
    (cache_dir / "NOCLOSE_NS.csv").write_text("Date,Open\n2019-01-01,1.0\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="NOCLOSE"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("NOCLOSE.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_empty_window_fails_loudly(cache_dir: Path) -> None:
    with pytest.raises(DataFetchError, match="No cached prices in window"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("AAA.NS")], date(2025, 1, 1), date(2025, 1, 2))


def test_non_positive_close_fails_loudly(cache_dir: Path) -> None:
    """A stray 0.0 close (yfinance artifact) would become +inf momentum and
    rank the corrupt ticker #1 -- the provider must refuse it (2026-07-14 audit)."""
    (cache_dir / "ZERO_NS.csv").write_text("Date,Close\n2019-01-01,0.0\n2019-01-02,101.0\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="Non-positive close"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("ZERO.NS")], date(2019, 1, 1), date(2019, 1, 3))
    (cache_dir / "NEG_NS.csv").write_text("Date,Close\n2019-01-01,-5.0\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="Non-positive close"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("NEG.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_duplicate_dates_fail_loudly(cache_dir: Path) -> None:
    """Duplicate index rows (interrupted cache re-write) must be a typed
    failure, not a raw pandas reindex error downstream."""
    (cache_dir / "DUP_NS.csv").write_text(
        "Date,Close\n2019-01-01,100.0\n2019-01-01,100.5\n2019-01-02,101.0\n", encoding="utf-8"
    )
    with pytest.raises(DataFetchError, match="Duplicate dates"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("DUP.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_unsorted_dates_fail_loudly(cache_dir: Path) -> None:
    """An unsorted index silently mis-slices .loc windows -- refuse it."""
    (cache_dir / "SHUF_NS.csv").write_text(
        "Date,Close\n2019-01-03,99.0\n2019-01-01,100.0\n2019-01-02,101.0\n", encoding="utf-8"
    )
    with pytest.raises(DataFetchError, match="Unsorted dates"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("SHUF.NS")], date(2019, 1, 1), date(2019, 1, 3))


def test_ticker_absent_from_window_fails_per_ticker_not_silently(cache_dir: Path) -> None:
    # AAA has 2019-01-01..03; LATE lists only from 2019-06-01. Asking for
    # January must fail on LATE, not return an all-NaN column beside AAA.
    (cache_dir / "LATE_NS.csv").write_text("Date,Close\n2019-06-01,10.0\n", encoding="utf-8")
    with pytest.raises(DataFetchError, match="LATE.NS"):
        CsvCachePriceProvider(cache_dir).get_prices(
            [Ticker("AAA.NS"), Ticker("LATE.NS")], date(2019, 1, 1), date(2019, 1, 3)
        )


def test_invalid_window_rejected(cache_dir: Path) -> None:
    with pytest.raises(DataFetchError, match="Invalid window"):
        CsvCachePriceProvider(cache_dir).get_prices([Ticker("AAA.NS")], date(2019, 1, 3), date(2019, 1, 1))


def test_empty_ticker_list_rejected(cache_dir: Path) -> None:
    with pytest.raises(DataFetchError, match="empty ticker list"):
        CsvCachePriceProvider(cache_dir).get_prices([], date(2019, 1, 1), date(2019, 1, 3))


def test_missing_cache_dir_rejected(tmp_path: Path) -> None:
    with pytest.raises(DataFetchError, match="does not exist"):
        CsvCachePriceProvider(tmp_path / "nope")


def test_provider_satisfies_price_port(cache_dir: Path) -> None:
    def accepts(provider: PriceProvider) -> PriceProvider:
        return provider

    concrete = CsvCachePriceProvider(cache_dir)
    assert accepts(concrete) is concrete


def test_real_repo_cache_is_readable_end_to_end() -> None:
    # Integration against the actual audited cache (no network): one
    # known ticker, one known window.
    repo_cache = Path(__file__).resolve().parents[2] / "data" / "cache"
    provider = CsvCachePriceProvider(repo_cache)
    frame = provider.get_prices([Ticker("RELIANCE.NS")], date(2020, 1, 1), date(2020, 12, 31))
    assert not frame.empty
    assert frame["RELIANCE.NS"].notna().all()
