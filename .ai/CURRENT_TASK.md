# Current Task

**WP-004 — Structured Logging: complete** (2026-07-14). With it,
**Phase 1's stated scope (config, storage, utils) is complete.** No
work package is currently open.

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

1. **WP-005 — Architectural Import Boundary Enforcement** — highest
   priority: TD-010 is Medium and rising; config, storage, and utils
   now all carry real code with no mechanical boundary enforcement.
2. **WP-006 — Layered Configuration** (reserved).
3. **Phase 2 — Data Platform** (`DataProvider` port, point-in-time
   universe store; closes audit findings F1/F9) — the first phase on
   the critical path toward live broker integration (Phase 8).

## Out of scope for this document

Phase 2+ specifications. See `AI_CONTEXT.md` for the frozen roadmap.
