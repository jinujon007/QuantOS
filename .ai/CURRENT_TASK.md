# Current Task

**WP-009 — Strategy Platform: complete** (2026-07-14). Phase 3 open.
The VALIDATED Momentum v1.0 now drives the pipeline behind the
`Strategy` port: verbatim signal-math port (factors: momentum_12m1m,
uptrend_series/is_uptrend), params externalized to
`strategies_registry/momentum_v1.yaml` (ADR-015 — editing it restarts
the validation clock), parity with the frozen script proven byte-equal
on 6 real dates (`test_strategy_parity.py`). Demo replays both
regimes: bear week → CASH stance, bull week → real top-10 through the
gated engine. Freeze untouched; paper_trader.py remains system of
record. New dep: pyyaml==6.0.3.

Earlier: WP-008 (ADR-034 execution slice) — Paper/Zerodha/Angel
adapters behind one port, kill switch, gated engine, demo tool;
review-hardened same day (UNKNOWN-state taxonomy, tick grid, journal
append). Broker choice deliberately open per operator.

Earlier same day: WP-003 (storage), WP-004 (logging), WP-005 (import
boundaries — TD-010 closed) → **Phase 1 fully closed**; WP-007 opened
Phase 2 (PIT universe store, first snapshot 2026-07-14). No work
package currently open.

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

1. **Portfolio module slice** — target-weights → order diffing with
   stop-loss carry; completes the weekly cycle against the engine.
2. **Phase 2 continuation** — corporate actions, data quality
   validators, network fetch adapter behind `PriceProvider`.
3. **WP-006 — Layered Configuration** (reserved).

India execution-landscape research (OpenAlgo vs native SmartAPI
adapter, SEBI retail-algo compliance state, broker pick) ran
2026-07-14 — see `docs/03_research/` for the report; it feeds the
Phase 8 SEBI checklist and the Phase 6/8 BrokerAdapter decisions.

## Out of scope for this document

Phase 2+ specifications. See `AI_CONTEXT.md` for the frozen roadmap.
