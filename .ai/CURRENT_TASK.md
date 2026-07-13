# Current Task

**WP-002 — Configuration System: complete** (2026-07-13). Phase 1 —
quantos-core skeleton — remains the active phase. No work package has
been filed for its remaining scope yet.

## What WP-002 delivered

`quantos_core.config` — `AppConfig` (typed, immutable, `extra="forbid"`,
one field: `environment: Literal["dev","paper","live"]`), `ConfigError`,
`load_config(env=None)` resolving from an explicit argument or
`QUANTOS_ENV`. Fail-closed on missing/invalid environment. No file I/O,
no layering, no persistence format — deliberately deferred and reserved
as **WP-006 — Layered Configuration** (name only, not specified). No
consumer wired up yet; zero change to the six frozen scripts.

Two pre-existing, unrelated issues were discovered and tracked (not
silently fixed): **TD-011** — `pip install -e ".[dev]"` (the documented
lockfile-regeneration method) is broken by WP-000's flat multi-package
layout; worked around for this WP, needs its own fix. **TD-012** —
`tools/generate_inventory.py`'s scaffold classifier now mislabels real
`quantos_core/config/*.py` files as empty stubs.

## Remaining scope of Phase 1

`storage` and `utils` (logging) still need extracting into `quantos_core`,
zero change to the six frozen scripts' behavior. Config's own layering
(base + environment-overlay + persistence format) is reserved as WP-006,
not yet scoped in detail.

## Not yet started

No work package has been opened for `storage`, `utils`, or WP-006/WP-005.
That is the next decision, not a task in progress.

## Out of scope for this document

Phase 2 (Data Platform) and beyond, and WP-005/WP-006's own specifications,
are not described here. See `AI_CONTEXT.md` for the full frozen roadmap.
