---
type: adr
number: 033
date: 2026-07-14
status: accepted
supersedes: none
---

# ADR-033 — DataProvider Port: Segregated Protocols, PIT-Only Universe Access (WP-007)

## Decision

The Blueprint's `DataProvider` port (module 02, `data`) is implemented
as **segregated Protocols** — `UniverseProvider` (`get_universe(as_of)
-> list[Ticker]`) and `PriceProvider` (`get_prices(tickers, start, end)
-> DataFrame`) — rather than one fat interface. `FundamentalsProvider`
is deliberately not defined until a consumer exists (no current
strategy reads fundamentals). Universe access is **point-in-time only**:
there is no argument-less "current universe" call anywhere (ADR-017
verbatim), and a query with no snapshot at-or-before `as_of` raises
`DataFetchError` — never an empty list.

First concrete adapters (WP-007):
- `SqliteUniverseStore` — point-in-time index-membership snapshots
  (`snapshot_date`, `ticker`) in SQLite via stdlib `sqlite3`;
  `get_universe(as_of)` resolves the latest snapshot ≤ `as_of`.
  Snapshots are immutable once written (re-recording a date must be
  explicit, `replace=True`, never silent).
- `CsvCachePriceProvider` — typed, fail-closed reader over the existing
  audited `data/cache/*.csv` layout (`Date,Close`, `<TICKER>_NS.csv`);
  a missing ticker or empty frame raises `DataFetchError` — the direct
  structural replacement, in new code, of `download_data.py:64`'s
  silent `except Exception: return pd.DataFrame()`.

## Context

Phase 2 (Data Platform) exists to close F1/F9 — both survivorship-bias
defects rooted in "current data where point-in-time was required." The
Constitution requires an ADR for any new port. Blueprint deps for
`data`: adapters only; no dependency on strategies/portfolio — and per
ADR-032 the `data` module may import only `utils`/`monitoring`
internally, so its persistence is its own adapter I/O (stdlib sqlite3),
not `quantos_core.storage` (whose `Repository[T]` serves domain
aggregates: portfolio, orders, trades, kill-switch).

## Alternatives Considered

- **One `DataProvider` interface with all three methods.** Rejected:
  every consumer would depend on methods it doesn't use; the Blueprint
  itself set the segregation precedent for `BrokerAdapter` (ADR-012).
- **Universe store on `quantos_core.storage.Repository[T]`.** Rejected:
  violates the frozen ADR-032 matrix; membership snapshots are bulk
  time-series data, not a domain aggregate.
- **Seeding the store from historical NSE constituent circulars.**
  Deferred, not rejected: automated access is blocked (5 documented
  attempts, Decision Record 2026-07-12). The store's schema supports
  backfill the day that data is obtained; until then snapshots begin
  at first seeding and pre-history remains flagged survivorship-biased.

## Consequences

- Strategies (Phase 3 port) will receive their universe only through
  `UniverseProvider` — F9's "strategy defines its own universe" becomes
  structurally impossible, per Constitution Part II item 5.
- `tools/seed_universe_snapshot.py` records the current
  `nifty500_universe.csv` as the first dated snapshot; every future
  weekly snapshot accumulates real PIT history going forward.
- Corporate actions, data-quality validators, and the yfinance/NSE
  fetch adapters remain later Phase 2 work packages.
