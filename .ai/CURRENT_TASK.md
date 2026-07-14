# Current Task

**WP-005 — Import Boundary Enforcement: complete** (2026-07-14).
TD-010 closed: the ADR-032 import matrix is now mechanically enforced
in the CI-blocking suite (`tests/quantos_core/test_import_boundaries.py`,
stdlib-ast, no new dependency). With WP-002/003/004 also done,
**Phase 1 is fully closed.** No work package is currently open.

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

1. **Phase 2 — Data Platform** (`DataProvider` port, point-in-time
   universe store; closes audit findings F1/F9) — next roadmap item,
   first on the critical path toward live broker integration (Phase 8).
2. **WP-006 — Layered Configuration** (reserved; can ride alongside
   Phase 2 when a real consumer needs it).

India execution-landscape research (OpenAlgo vs native SmartAPI
adapter, SEBI retail-algo compliance state, broker pick) ran
2026-07-14 — see `docs/03_research/` for the report; it feeds the
Phase 8 SEBI checklist and the Phase 6/8 BrokerAdapter decisions.

## Out of scope for this document

Phase 2+ specifications. See `AI_CONTEXT.md` for the frozen roadmap.
