---
type: work-package
id: WP-007
date: 2026-07-14
status: complete
phase: 2
---

# WP-007 — Data Platform Foundation (Phase 2 opening)

## Objective

Open Phase 2 (Data Platform) with the ADR-033 slice: segregated
`DataProvider` ports, typed `DataFetchError`, the point-in-time
`SqliteUniverseStore` (the structural fix for F1/F9 going forward),
and the fail-closed `CsvCachePriceProvider` over the existing audited
cache layout. WP-006 (Layered Configuration) remains reserved; WP
numbering skips it intentionally.

## Scope

1. **ADR-033** — DataProvider port: segregated Protocols
   (`UniverseProvider`, `PriceProvider`; `FundamentalsProvider`
   deliberately deferred until a consumer exists), PIT-only universe
   access (no argument-less "current" call — ADR-017 verbatim).
2. `quantos_core/data/errors.py` — `DataFetchError` (the typed
   replacement, in new code, for `download_data.py:64`'s silent
   `except Exception: return pd.DataFrame()`).
3. `quantos_core/data/provider.py` — `Ticker` NewType + both ports.
4. `quantos_core/data/universe_store.py` — `SqliteUniverseStore`:
   dated membership snapshots (stdlib sqlite3, data's own adapter
   I/O per ADR-032 — not `quantos_core.storage`); `get_universe(as_of)`
   resolves latest snapshot ≤ as_of; queries before any snapshot fail
   loudly; snapshots immutable without explicit `replace=True`;
   `latest_snapshot_date()` exposed so staleness is visible, per the
   2026-07-12 survivorship decision record.
5. `quantos_core/data/prices.py` — `CsvCachePriceProvider`: reads the
   frozen `download_data.py` cache layout (`Date,Close`,
   `TICKER_NS.csv`) without touching that script; missing ticker /
   unreadable file / empty window all raise — never a silently
   narrower frame.
6. `tools/seed_universe_snapshot.py` — records dated snapshots from
   `nifty500_universe.csv`. **First real snapshot seeded: 2026-07-14,
   504 tickers → `data/universe_pit.db`** (committed: PIT history is
   unreproducible later by definition). Real point-in-time value
   accumulates from today forward; pre-history remains flagged
   survivorship-biased.
7. Full test coverage (see Validation).

## Out of Scope

Corporate actions, data-quality validators, network fetch adapters
(yfinance/NSE), Parquet, wiring any consumer, historical constituent
backfill (blocked upstream; schema supports it when obtained).

## Files Created

`quantos_core/data/{errors,provider,universe_store,prices}.py`,
`tests/quantos_core/test_data_platform.py`,
`tools/seed_universe_snapshot.py`,
`docs/adr/ADR-033-dataprovider-port.md`, `data/universe_pit.db`
(seeded artifact), this report.

## Files Modified

`quantos_core/data/__init__.py` (docstring + exports), `INVENTORY.md`,
`.ai/*` (3 files). Zero dependency changes; zero frozen-script
changes.

## Validation

| Gate | Result |
|---|---|
| `ruff check .` / `format --check` | Clean / all files formatted |
| `mypy --strict -p quantos_core` | Success — **26** source files (was 22) |
| `coverage run -m pytest -m "not network"` | **94 passed**, 1 deselected (21 new cases) |
| `coverage report` | `quantos_core/*` — **100%** (210 stmts, 0 miss) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; baseline sha `e3d29859aa00...` unchanged |
| `git diff` six frozen scripts | Empty |
| Import boundary gate (WP-005) | Green — data imports only stdlib/pandas + own module |

PIT correctness suite covers the Blueprint's stated test spec: a
delisted ticker is excluded from later-date queries; intermediate
dates are served by the earlier snapshot; pre-history queries fail
loudly; snapshots are immutable without `replace=True`.

## Exit Criteria — all met

- [x] ADR-033 filed; ports defined as Protocols; PIT-only access
- [x] Universe store + price provider fully tested, fail-closed
- [x] First real PIT snapshot recorded and committed
- [x] All gates green; determinism baseline unchanged
- [x] AIOS updated; git tag `wp-007-data-platform-foundation`

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| PIT universe capability | None (F1/F9 class open) | Store + port live; real PIT history accumulating from 2026-07-14 |
| Fail-closed data access | Anti-pattern present in frozen script | Structural replacement available for all new code |
| Typing coverage | 22 strict files | 26 |
| Test count | 73 | 94 (+21) |
| quantos_core coverage | 100% (145 stmts) | 100% (210 stmts) |

## Next

Phase 2 continuation: corporate-actions adjustment + data-quality
validators + network fetch adapter behind `PriceProvider` (each its
own WP). Operational: seed a fresh universe snapshot weekly (Friday,
alongside the paper-trader run) so PIT history accumulates.
