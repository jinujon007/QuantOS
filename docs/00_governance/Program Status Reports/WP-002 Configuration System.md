---
type: work-package
id: WP-002
date: 2026-07-13
status: complete
phase: 1
---

# WP-002 — Configuration System

## Objective

Implement `quantos_core/config`'s environment-resolution core: a typed,
immutable, strictly-validated `AppConfig`, constructed directly from a
resolved environment name (`QUANTOS_ENV` or an explicit argument), failing
closed on anything ambiguous. No file I/O, no layering, no persistence
format — per Technical Review Board direction, those are reserved as
WP-006.

## Repository Evidence (at start)

- `quantos_core/config/__init__.py` — docstring-only stub, no code.
- No config-loading code existed anywhere; frozen scripts each hardcode
  their own constants (unaffected by this WP either way — ADR-015
  territory, not config).
- `pydantic` was importable in the venv (2.13.4) but undeclared in
  `pyproject.toml`/`requirements-lock.txt` — a transitive install, not
  part of the locked closure.
- ADR-013 (governing, unsuperseded) specifies the full layered design;
  this WP deliberately implements only the environment-resolution slice
  of it, per Board direction — not an architectural deviation.

## Scope

1. `AppConfig` (pydantic, frozen, `extra="forbid"`, one field:
   `environment: Literal["dev","paper","live"]`).
2. `ConfigError` — one typed exception covering every failure mode.
3. `load_config(env: str | None = None) -> AppConfig` — resolves
   `env`/`QUANTOS_ENV`, constructs `AppConfig` directly via
   `model_validate`, wraps `pydantic.ValidationError` as `ConfigError`.
4. `__init__.py` docstring/exports updated.
5. Full test coverage (see Validation).

## Out of Scope

YAML (any form), layered merge, persistence format, env-var-reference
substitution for secrets, wiring into any frozen script, strategy-param
migration, logging/storage/DI work, any new CI step.

## Files Created

- `quantos_core/config/schema.py`
- `quantos_core/config/loader.py`
- `tests/quantos_core/test_config.py`
- `docs/00_governance/Program Status Reports/WP-002 Configuration System.md` (this report)

## Files Modified

- `quantos_core/config/__init__.py` — real docstring + exports
- `pyproject.toml` — `pydantic==2.13.4` added to `[project.dependencies]`;
  `plugins = ["pydantic.mypy"]` added to `[tool.mypy]`
- `requirements-lock.txt` — regenerated (see Implementation, step 2 —
  documented method was broken, worked around; TD-011)
- `INVENTORY.md` — regenerated (563 → 566 tracked files)
- `docs/00_governance/Technical Debt Register.md` — TD-010 severity
  updated (Low → Medium, its own stated trigger fired); TD-011, TD-012
  added
- `.ai/AI_CONTEXT.md`, `.ai/PROJECT_STATE.yaml`, `.ai/CURRENT_TASK.md`

Zero files under the six frozen scripts touched. Zero files moved.

## Dependencies

`pydantic==2.13.4` (runtime) — ADR-013-mandated. No other new dependency.
`PyYAML` explicitly not added (Board direction). Upstream: WP-001 (complete).

## Implementation

1. Added `pydantic` to `pyproject.toml` + `pydantic.mypy` plugin.
   **Caught and fixed a placement bug during implementation**: the plugin
   line was first inserted after `[[tool.mypy.overrides]]` had already
   opened, which TOML would have silently attached to the override table
   instead of `[tool.mypy]` itself. Caught before running any gate, moved
   to the correct location above the overrides block.
2. Regenerated `requirements-lock.txt`. **The documented method
   (`pip install -e ".[dev]"` in a clean venv) is broken** — setuptools'
   flat-layout discovery finds 9 ambiguous top-level packages (WP-000
   scaffolding) and refuses to build. Not a WP-002 defect; not silently
   fixed (would be a `pyproject.toml` packaging-config change outside
   this WP's declared scope). Worked around: installed the exact pinned
   specifiers directly (bypassing project-editable-install), froze the
   result. Tracked as TD-011.
3. Wrote `quantos_core/config/schema.py` — `AppConfig`, `ConfigError`.
4. Wrote `quantos_core/config/loader.py` — `load_config()`. Used
   `AppConfig.model_validate({...})` rather than
   `AppConfig(environment=resolved)` specifically to avoid a
   `# type: ignore` at the one legitimate untyped-boundary point
   (Constitution Part III: `Any` permitted only at the adapter boundary
   where untyped external data first enters, converted to a typed domain
   object before crossing further in) — `model_validate` is pydantic's
   own idiom for exactly that conversion, cleaner than suppressing a
   real strict-mode signal.
5. Updated `__init__.py`.
6. Wrote `tests/quantos_core/test_config.py` — 10 cases. Verified the
   exact exception type pydantic raises for both "unknown field" and
   "frozen mutation" (`pydantic.ValidationError` in both cases, confirmed
   by direct execution) rather than asserting a bare `Exception`.
7. Ran the full gate suite (see Validation). `ruff format --check` first
   flagged `loader.py` (one line exceeded the wrap threshold) —
   reformatted via `ruff format`, re-verified clean.
8. Regenerated `INVENTORY.md` against the fully-staged tree. Noticed the
   scaffold classifier now mislabels the two new real files as "empty
   scaffold" — not fixed (out of scope), tracked as TD-012.
9. Updated the Technical Debt Register (TD-010 severity change; TD-011,
   TD-012 added) and the three AIOS files.

## Risks

- **`pip install -e ".[dev]"` broken** (TD-011) — resolved for this WP
  via workaround; will recur for every future WP touching dependencies
  until `pyproject.toml` gets explicit package discovery config, in its
  own reviewed WP.
- **`INVENTORY.md` scaffold-bucket mislabeling** (TD-012) — cosmetic,
  will recur each WP that adds real code under `quantos_core/*`.
- **TD-010 severity increase** — accepted, by Board direction in WP-001;
  no violation exists today, nothing would catch one if it did.
- **`pydantic.mypy` plugin / strict-mode interaction** — resolved clean:
  0 issues, 18 source files.

## Validation

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 1 file flagged (`loader.py`), reformatted, re-verified clean — 37 files formatted |
| `mypy` (6 frozen scripts, informational) | 51 pre-existing errors — unchanged from WP-001 baseline |
| `mypy --strict -p quantos_core` | Success: no issues found in **18** source files (was 16 after WP-001) |
| `coverage run -m pytest -m "not network"` | **38 passed**, 1 deselected (10 new `test_config.py` cases) |
| `coverage report -m` | `quantos_core/config/{__init__,loader,schema}.py` — **100%** each; total 26% (up from 25%) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; `equity_curve.csv` sha256 `e3d29859aa00...` — unchanged from WP-000/WP-001 baseline |
| `git diff` on the six frozen scripts | Empty |

Local test/determinism runs regenerated `data/results/*.csv` with
platform (CRLF) line endings twice during this WP; both reverted via
`git checkout --` (confirmed zero real content diff via
`--ignore-space-at-eol`) — side effects of local verification, not
WP-002 deliverables.

## Exit Criteria — all met

- [x] `AppConfig` constructs correctly for `dev`/`paper`/`live` via
      `QUANTOS_ENV`/explicit arg — no file I/O
- [x] Strict mypy passes (18 source files)
- [x] CI-equivalent gate sequence passes in full locally
- [x] Golden tests pass (unchanged)
- [x] Determinism passes (3/3, baseline-matching hash)
- [x] No frozen files changed
- [x] AIOS updated (3 files only)
- [x] Git tag created (`wp-002-configuration-system`)

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| Configuration mechanism | None | Real, tested, typed, validated, immutable `AppConfig` |
| Environment support | None | `dev`/`paper`/`live`, via arg or `QUANTOS_ENV` |
| Persistence format | None | Still none — WP-006 |
| Typing coverage | 16 strict-checked files | 18 (+`config/schema.py`, `config/loader.py`) |
| Test count | 28 | 38 (+10) |
| Coverage | 25% | 26%, config module at 100% |
| Dependency count | 5 runtime | 6 runtime (+`pydantic`) |
| Behavioral impact on frozen scripts | N/A | None — determinism hash unchanged |
| New tracked debt | — | TD-011 (broken editable install), TD-012 (inventory misclassification) |

## Next

No work package filed for `storage`/`utils` extraction or for WP-005/WP-006.
Reserved: **WP-005 — Architectural Import Boundary Enforcement**,
**WP-006 — Layered Configuration** (names only).
