---
type: work-package
id: WP-003
date: 2026-07-14
status: complete
phase: 1
---

# WP-003 — Storage Foundation

## Objective

Implement `quantos_core/storage`'s core slice: the `Repository[T]` port
exactly as frozen in the Constitution (Part II, Interface Contracts —
`get(id) -> T · save(entity) · query(filter) -> list[T]`, one repository
per aggregate), typed `StorageError`/`EntityNotFoundError`, the `Entity`
base model persisted aggregates extend, and the first concrete adapter,
`SqliteRepository` (stdlib `sqlite3`, one table per aggregate,
transactional, fail-closed). No consumer wiring, no domain aggregates
(orders/portfolio/kill-switch are Phase 4/6 territory), no Parquet
(Phase 2, data platform).

## Repository Evidence (at start)

- `quantos_core/storage/__init__.py` — docstring-only stub (ADR-031).
- No repository/persistence abstraction existed anywhere; state today is
  scattered flat files (`data/paper_state.json`, CSVs) owned by frozen
  scripts — untouched by this WP (ADR-003, strangler-fig).
- Blueprint module 15 (storage) specifies: repositories over SQLite
  locally, Postgres only on an explicit concurrent-writer trigger;
  `StorageError` on write failure with full rollback, never a partial.

## Scope

1. `Entity` — pydantic base (frozen, `extra="forbid"`, one field: `id`),
   the mechanism that lets `save(entity)` honor the frozen contract
   (entity carries its own identity).
2. `Repository[T]` — generic `Protocol` (Part III: Protocols, not ABCs).
3. `StorageError`, `EntityNotFoundError` (subclass, so base-type handlers
   still fail closed).
4. `SqliteRepository[T]` — stdlib `sqlite3`; connection-per-operation,
   each op in a commit-or-rollback transaction; documents stored as the
   entity's pydantic JSON and **re-validated on every read** (a drifted/
   corrupt row is a `StorageError`, never a partial object); `query`
   rejects unknown filter fields loudly (a typo'd key must never return
   `[]` silently); results ordered by id (deterministic); aggregate names
   validated against `^[a-z][a-z0-9_]*$` before touching SQL.
5. Full test coverage (see Validation).

## Out of Scope

Postgres, Parquet, domain aggregates, kill-switch flag, migration of
`paper_state.json`, wiring into any frozen script, connection pooling
(single-writer solo scale; upgrade trigger is the Blueprint's own
concurrent-writers clause).

## Files Created

- `quantos_core/storage/errors.py`
- `quantos_core/storage/repository.py`
- `quantos_core/storage/sqlite.py`
- `tests/quantos_core/test_storage.py`
- this report

## Files Modified

- `quantos_core/storage/__init__.py` — real docstring + exports
- `INVENTORY.md` — regenerated (566 → 571 tracked files)
- `.ai/AI_CONTEXT.md`, `.ai/CURRENT_TASK.md`, `.ai/PROJECT_STATE.yaml`

Zero dependency changes (stdlib `sqlite3` + already-locked `pydantic`
only — TD-011's broken editable install not triggered). Zero files under
the six frozen scripts touched. Zero files moved.

## Implementation Notes

- `save(entity)` (not `save(id, entity)`) required each aggregate to be
  self-identifying — hence `Entity`. This is contract-following, not a
  new decision; recorded here rather than in an ADR because the frozen
  interface already dictates it.
- `SqliteRepository` is `Generic[T]` and satisfies `Repository[T]`
  structurally; the test suite pins this with a typed-assignment check
  that `mypy --strict` verifies.
- `query` filtering is Python-side equality over validated models, not
  SQL `json_extract` — at four-strategy weekly-rebalance scale the whole
  aggregate fits in memory trivially, and validating every row on read
  is exactly the fail-closed behavior the Blueprint's error clause asks
  for. Upgrade path (SQL-side filtering) exists if a real aggregate ever
  outgrows this; that would be its own reviewed change.
- TD-012 recurred exactly as predicted: `INVENTORY.md`'s classifier
  labels the four new real files "Module Scaffold (empty)". Not fixed
  (out of scope), already tracked.

## Validation

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 41 files already formatted |
| `mypy --strict -p quantos_core` | Success: no issues found in **21** source files (was 18 after WP-002) |
| `coverage run -m pytest -m "not network"` | **60 passed**, 1 deselected (22 new `test_storage.py` cases) |
| `coverage report` | `quantos_core/*` — **100%** across all 21 files (storage: 50 stmts, 0 miss) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; `equity_curve.csv` sha256 `e3d29859aa00...` — unchanged from WP-000/001/002 baseline |
| `git diff` on the six frozen scripts | Empty |

Determinism runs regenerated `data/results/*.csv` with CRLF endings
(same side effect as WP-002); confirmed zero content diff via
`--ignore-space-at-eol`, reverted via `git checkout --`.

## Exit Criteria — all met

- [x] `Repository[T]` port matches the Constitution's frozen signature
- [x] `SqliteRepository` passes round-trip/upsert/not-found/corrupt-row/
      filter-validation/determinism/cross-instance/injection-guard tests
- [x] Strict mypy passes (21 source files)
- [x] Full gate sequence green locally
- [x] Determinism 3/3, baseline hash unchanged
- [x] No frozen files changed; no dependency changes
- [x] AIOS updated (3 files only)
- [x] Git tag created (`wp-003-storage-foundation`)

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| Persistence abstraction | None (scattered flat files) | `Repository[T]` port + transactional SQLite adapter, fail-closed |
| Typing coverage | 18 strict-checked files | 21 |
| Test count | 38 | 60 (+22) |
| quantos_core coverage | config 100%, rest empty | 100% of all real code (87 stmts) |
| Dependencies | 6 runtime | 6 runtime (unchanged) |
| Behavioral impact on frozen scripts | N/A | None — determinism hash unchanged |

## Next

Phase 1 remaining scope after this WP: `utils` (structured logging) —
filed as WP-004. Reserved unchanged: WP-005 (import boundary), WP-006
(layered configuration).
