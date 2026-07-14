# Current Task

**WP-007 — Data Platform Foundation: complete** (2026-07-14). Phase 2
is now open. Same day: WP-003 (storage), WP-004 (logging), WP-005
(import boundaries — TD-010 closed) all completed; **Phase 1 fully
closed.** No work package is currently open.

WP-007 delivered (ADR-033): segregated `UniverseProvider`/
`PriceProvider` ports, `DataFetchError`, `SqliteUniverseStore` (PIT
membership snapshots — F1/F9 structural fix going forward; first real
snapshot 2026-07-14, 504 tickers, committed as `data/universe_pit.db`),
`CsvCachePriceProvider` (fail-closed reader over the audited cache),
`tools/seed_universe_snapshot.py`. **Operational: seed a fresh
snapshot every Friday** alongside the paper-trader run.

## What WP-004 delivered

`quantos_core.utils` — `JsonLineFormatter` (one JSON object per line,
sorted keys, `default=str` fallback, exception capture) and
`get_logger(module, run_id, stream, level)` (run-id stamped on every
record via filter, `propagate=False`, handlers reconfigured never
duplicated). Event convention: message = event name, event data via
`extra={"data": {...}}`. 9 tests; quantos_core remains at 100%
coverage (117 stmts, 22 strict-mypy files). Zero change to the six
frozen scripts; zero dependency changes.

## Next decision (not yet a task in progress)

1. **Phase 2 continuation** — corporate-actions adjustment, data
   quality validators, network fetch adapter behind `PriceProvider`.
2. **WP-006 — Layered Configuration** (reserved; ride alongside
   Phase 2 when a real consumer needs it).

India execution-landscape research (OpenAlgo vs native SmartAPI
adapter, SEBI retail-algo compliance state, broker pick) ran
2026-07-14 — see `docs/03_research/` for the report; it feeds the
Phase 8 SEBI checklist and the Phase 6/8 BrokerAdapter decisions.

## Out of scope for this document

Phase 2+ specifications. See `AI_CONTEXT.md` for the frozen roadmap.
