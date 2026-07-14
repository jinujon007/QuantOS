# Current Task

**WP-010 — Operator Console (UI) + Kill-Switch CLI: complete**
(2026-07-14, ADR-035). One-page static read-only console:
`python tools/build_dashboard.py --open` — derived system state,
freshness pills, equity chart from the determinism-pinned CSV, order
blotter, broker readiness, runbook; page tints red site-wide when the
kill switch is engaged. Kill-switch CLI (Constitution Part V):
`python tools/kill_switch.py status|engage|release`. Browser-verified,
zero console errors. OSS UI sweep (OpenAlgo/ai-hedge-fund/
Vibe-Trading) recorded in ADR-035.

Earlier same day — **WP-009 — Strategy Platform: complete**. Phase 3 open.
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

## Latest: WP-011 — QuantOS Desktop: complete (2026-07-14, ADR-036)

Local app at 127.0.0.1:8742 (`python tools/desktop_app.py`, Desktop
shortcut via tools/create_desktop_shortcut.ps1): Overview/Brokers/
Orders/Strategy/System. Broker connect flows (Zerodha request-token
exchange, Angel TOTP) verified read-only; credentials in-memory only.
Kill switch operable from the UI (the one write control), drilled live
UI↔CLI. Shared read models in api/collectors.py feed both the app and
the static console. fastapi/uvicorn now pinned deps.

## Next work (operator-ratified, interview 2026-07-14)

**Automation loop**, in order:
1. **WP-012 — Portfolio module** — target-weights → order diffing with
   stop-loss carry; completes the weekly cycle against the engine.
2. **WP-013 — run_cycle wiring** (ADR-010) — weekly cycle through the
   new pipeline, parity period alongside paper_trader.py.
3. Scheduler hardening (daily task registered 2026-07-14:
   "QuantOS Daily Paper Run", weekdays 15:40, tools/daily_run.ps1 —
   live paper trading runs unattended from 2026-07-15).

Then: Phase 2 finish (corporate actions, fetch adapter), Phase 4 risk
table, TD-013 live hardening. Operator to create Zerodha API key this
week; capital plan ₹3L for Oct go-live if the Sept 9 gate passes.

India execution-landscape research (OpenAlgo vs native SmartAPI
adapter, SEBI retail-algo compliance state, broker pick) ran
2026-07-14 — see `docs/03_research/` for the report; it feeds the
Phase 8 SEBI checklist and the Phase 6/8 BrokerAdapter decisions.

## Out of scope for this document

Phase 2+ specifications. See `AI_CONTEXT.md` for the frozen roadmap.
