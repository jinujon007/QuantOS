---
type: work-package
id: WP-004
date: 2026-07-14
status: complete
phase: 1
---

# WP-004 — Structured Logging (utils)

## Objective

Implement `quantos_core/utils`'s logging slice per Constitution Part III
(Logging): structured JSON lines, one object per line, every record
carrying timestamp (UTC), level, module, event, and the correlation/run
id, with event-specific data as a nested field. Built on stdlib
`logging` — zero new dependencies. This closes the last empty stub in
Phase 1's stated scope (config → WP-002, storage → WP-003, utils →
this WP).

## Repository Evidence (at start)

- `quantos_core/utils/__init__.py` — docstring-only stub (ADR-031).
- No structured logging exists anywhere; the frozen scripts print plain
  text to stdout (untouched by this WP — ADR-003).
- Constitution Part III/Logging specifies the exact field set and the
  secrets prohibition; Part II/Event Design makes structured log lines
  the system's event mechanism (no message bus, by design).

## Scope

1. `JsonLineFormatter` — stdlib `logging.Formatter` emitting one JSON
   object per line, keys sorted (stable, diffable), `default=str`
   fallback for non-serializable values, exception text captured when
   `exc_info` is passed.
2. `get_logger(module, run_id, stream=None, level=INFO)` — returns the
   `quantos.<module>` logger with the formatter attached and a filter
   stamping `run_id` on every record; reconfigures (never duplicates)
   handlers on repeat calls; `propagate=False` so lines are emitted
   exactly once.
3. Event convention documented on the function: message = event name,
   event data via `extra={"data": {...}}`.
4. Full test coverage (see Validation).

## Out of Scope

Calendar/`Clock` port (Part V, arrives with the phase that needs it),
determinism helpers, metrics/`AlertSink` (module `monitoring`, Phase 7),
log-file rotation/shipping (deployment concern, Phase 7), wiring into
any frozen script.

## Files Created

- `quantos_core/utils/logging.py`
- `tests/quantos_core/test_utils_logging.py`
- this report

## Files Modified

- `quantos_core/utils/__init__.py` — real docstring + exports
- `INVENTORY.md` — regenerated (571 → 574 tracked files)
- `.ai/AI_CONTEXT.md`, `.ai/CURRENT_TASK.md`, `.ai/PROJECT_STATE.yaml`

Zero dependency changes. Zero files under the six frozen scripts
touched. Zero files moved.

## Implementation Notes

- `quantos_core/utils/logging.py` intentionally shares its name with the
  stdlib module it wraps; Python 3's absolute-import default makes the
  internal `import logging` unambiguous, and the public surface is
  imported via `quantos_core.utils` anyway.
- Wall-clock timestamps in log lines are imperative-shell I/O, not
  domain math — no determinism implication (verified: baseline hash
  unchanged).
- The secrets prohibition (Part III) is documented at the module level;
  enforcement is caller discipline plus review, same as the Constitution
  frames it.

## Validation

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 43 files already formatted |
| `mypy --strict -p quantos_core` | Success: no issues found in **22** source files (was 21 after WP-003) |
| `coverage run -m pytest -m "not network"` | **69 passed**, 1 deselected (9 new `test_utils_logging.py` cases) |
| `coverage report` | `quantos_core/*` — **100%** (117 stmts, 0 miss) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; `equity_curve.csv` sha256 `e3d29859aa00...` — baseline unchanged |
| `git diff` on the six frozen scripts | Empty |

Determinism runs regenerated `data/results/*.csv` (CRLF side effect,
same as WP-002/003); reverted via `git checkout --`.

## Exit Criteria — all met

- [x] JSON-line contract tested: required fields, UTC ISO timestamps,
      data pass-through, level filtering, exception capture, sorted
      keys, no handler duplication
- [x] Strict mypy passes (22 source files)
- [x] Full gate sequence green locally
- [x] Determinism 3/3, baseline hash unchanged
- [x] No frozen files changed; no dependency changes
- [x] AIOS updated (3 files only)
- [x] Git tag created (`wp-004-structured-logging`)

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| Logging | Plain-text prints in frozen scripts only | Structured JSON-lines logger, run-id-correlated, ready for every future module |
| Typing coverage | 21 strict-checked files | 22 |
| Test count | 60 | 69 (+9) |
| quantos_core coverage | 100% (87 stmts) | 100% (117 stmts) |
| Dependencies | 6 runtime | 6 runtime (unchanged) |
| Behavioral impact on frozen scripts | N/A | None — determinism hash unchanged |

## Next

**Phase 1's stated scope (config, storage, utils) is now complete.**
Next decisions, in priority order per the governing docs:

1. **WP-005 — Architectural Import Boundary Enforcement** (reserved;
   TD-010 Medium and rising with every real module added — three
   modules now carry real, unenforced code).
2. **WP-006 — Layered Configuration** (reserved).
3. Phase 2 — Data Platform (`DataProvider` port, point-in-time universe
   store — closes audit findings F1/F9).
