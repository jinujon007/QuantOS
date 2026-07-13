# Current Task

**WP-001 — Repository Foundation: complete** (2026-07-13). Phase 1 —
quantos-core skeleton — remains the active phase. No work package has been
filed for its remaining scope yet.

## What WP-001 delivered

`mypy --strict` on all of `quantos_core`, CI-blocking. An import smoke
test (`tests/quantos_core/test_package_imports.py`) covering the root
package + all 15 subpackages, CI-blocking. Both gate real code the moment
it lands. No logic was added — `quantos_core` is still 15 empty,
docstring-only stubs. Zero change to the six frozen scripts.

Import-boundary enforcement (Constitution Part II item 4, ADR-029) was
explicitly scoped out of WP-001 per Technical Review Board direction and
reserved as **WP-005 — Architectural Import Boundary Enforcement**
(name only, not specified).

## Remaining scope of Phase 1

Extract `config`, `storage`, and `utils` (logging) into `quantos_core`
with zero change to the six frozen scripts' observable behavior. Each
extraction step is gated by the existing golden-file/determinism checks
(ADR-005) plus WP-001's new strict-typing and import-smoke-test gates.

## Not yet started

No work package has been opened for the extraction above. That is the
next action, not a task in progress.

## Out of scope for this document

Phase 2 (Data Platform) and beyond, and WP-005's own specification, are
not described here. See `AI_CONTEXT.md` for the full frozen roadmap.
