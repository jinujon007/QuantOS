---
type: work-package
id: WP-001
date: 2026-07-13
status: complete
phase: 1
---

# WP-001 — Repository Foundation

## Objective

Stand up the mechanical typing and test-pyramid foundation `quantos_core`
requires before it can safely receive real logic: strict typing
enforcement and a test-pyramid entry point. Zero business logic. Zero
changes to the six frozen scripts.

## Repository Evidence

- `quantos_core/{...}/` — 15 subpackages, each an empty `__init__.py`
  docstring, zero logic (WP-000). Confirmed still true at WP-001 start.
- `import quantos_core` succeeded before this WP; no CI step verified it.
- `pyproject.toml`'s `[tool.mypy]` had no strict override for
  `quantos_core` prior to this WP.
- `.github/workflows/ci.yml`'s mypy step ran only against the six frozen
  scripts, non-blocking; no step touched `quantos_core`.
- `tests/` contained zero references to `quantos_core` prior to this WP.
- Constitution Part III, Typing: `mypy --strict` on all of `quantos_core`
  is a CI-blocking gate, not advisory — was unmet, now met.
- Technical Debt Register TD-005/TD-006/TD-008 were deferred to "Phase 1,
  once `quantos_core`'s real test pyramid exists" — this WP is that
  precondition, not their resolution.

## Scope

1. `mypy --strict` scoped to `quantos_core.*`, CI-blocking.
2. One new blocking CI step: `mypy --strict -p quantos_core`.
3. Import smoke test (`tests/quantos_core/test_package_imports.py`) —
   root package + all 15 subpackages.
4. `INVENTORY.md` regenerated.
5. Technical Debt Register updated (TD-010 added).
6. AIOS (`.ai/AI_CONTEXT.md`, `.ai/PROJECT_STATE.yaml`,
   `.ai/CURRENT_TASK.md`) updated.

## Out of Scope

**Import-linter, in any form** — no dependency, no contracts, no CI step.
Scoped out per Technical Review Board direction (2026-07-13 review of the
initial WP-001 spec) and reserved as **WP-005 — Architectural Import
Boundary Enforcement**, name only, not specified. Also out of scope: any
real implementation inside any `quantos_core` subpackage; any change to
the six frozen scripts; coverage-floor enforcement (TD-008 stays open);
zero-magic-number lint on `quantos_core/strategies/` (no code there yet);
`services/` wiring.

## Files Created

- `tests/quantos_core/test_package_imports.py`
- `docs/00_governance/Program Status Reports/WP-001 Repository Foundation.md` (this report)

## Files Modified

- `pyproject.toml` — `[[tool.mypy.overrides]]` for `quantos_core.*`, `strict = true`
- `.github/workflows/ci.yml` — new blocking step `mypy --strict (quantos_core)`
- `INVENTORY.md` — regenerated (557 → 558 tracked files; also picked up
  drift from prior-session commits (`PROJECT_INDEX.md`, `STATUS.md`,
  `LICENSE`, WP-000 report, both registers) that had never been run
  through the generator since WP-000 — pre-existing drift, not introduced
  by this WP, corrected as part of the same regeneration step)
- `docs/00_governance/Technical Debt Register.md` — TD-010 added,
  `updated_by` header changed
- `.ai/AI_CONTEXT.md`, `.ai/PROJECT_STATE.yaml`, `.ai/CURRENT_TASK.md`

Zero files under the six frozen scripts touched. Zero files moved.
`requirements-lock.txt` unchanged — no new dependency introduced.

## Dependencies

None new. Upstream: WP-000 (complete).

## Implementation

1. Added `[[tool.mypy.overrides]]` strict block for `quantos_core.*` to `pyproject.toml`.
2. Added the blocking CI step, positioned after the existing ruff steps,
   before the legacy non-blocking mypy step (left untouched).
3. Wrote `tests/quantos_core/test_package_imports.py` — parametrized over
   all 15 subpackages plus one root-package test; asserts each imports
   cleanly and carries the purpose docstring WP-000 established. No
   placeholder code, no speculative abstraction — every line executes a
   real, currently-true assertion.
4. Ran the full gate suite locally (see Validation).
5. Regenerated `INVENTORY.md`.
6. Added TD-010 to the Technical Debt Register, documenting the
   import-boundary-enforcement gap and its reservation as WP-005.
7. Updated the three AIOS files.

## Risks

- **`mypy --strict` on docstring-only stubs** — resolved: 0 issues, 16
  source files checked.
- **Import-boundary enforcement remains unmet** — accepted, by Board
  direction; zero real code exists in `quantos_core` yet, so nothing can
  currently violate a boundary that isn't checked. Tracked as TD-010,
  reserved as WP-005 — not silently dropped.
- **Risk Register R-005** ("no GitHub remote") and **TD-007** (same
  topic) are both stale — a remote now exists. Not touched in this WP;
  flagged here for a separate, explicit update outside WP-001's scope.

## Validation

All gates run locally against the working tree, in this order:

| Gate | Result |
|---|---|
| `ruff check .` | All checks passed |
| `ruff format --check .` | 34 files already formatted |
| `mypy` (6 frozen scripts, informational) | 51 pre-existing errors — unchanged from baseline, non-blocking |
| `mypy --strict -p quantos_core` | Success: no issues found in 16 source files |
| `coverage run -m pytest -m "not network"` | 28 passed, 1 deselected (16 new import-smoke tests included) |
| `coverage report -m` | 25% total — unchanged from Phase 0 baseline (stubs contribute 0/0) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; `equity_curve.csv` sha256 `e3d29859aa00...` — matches the recorded Phase 0 baseline exactly |
| `git diff` on the six frozen scripts | Empty |

Two result CSVs (`data/results/equity_curve.csv`,
`data/results/equity_comparison.csv`) were regenerated by the local
determinism run with platform (CRLF) line endings; `git diff
--ignore-space-at-eol` confirmed zero real content difference. Reverted
via `git checkout --` to keep this commit to its declared file list —
these files are a side effect of local verification, not a WP-001
deliverable.

## Exit Criteria — all met

- [x] Package imports pass (16/16, root + 15 subpackages)
- [x] Strict mypy passes (`mypy --strict -p quantos_core`)
- [x] CI config passes locally-equivalent gate sequence in full
- [x] Golden tests pass (`test_momentum_backtest_characterization.py`, unchanged)
- [x] Determinism passes (3/3 byte-identical, baseline-matching hash)
- [x] No frozen files changed
- [x] AIOS updated (3 files only)
- [x] Git tag created (`wp-001-repository-foundation`, this commit)

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| `quantos_core` importability | Unverified by CI | Verified every push, 16 imports |
| Typing rigor on `quantos_core` | None (repo-wide `check_untyped_defs` only) | `mypy --strict`, CI-blocking |
| CI coverage of `quantos_core` | 0 steps | 1 new blocking step + 16 new tests |
| Migration risk for next WP | Extraction would land with no typing/import gate | Any regression caught at CI, not discovered later |
| Behavioral impact on frozen scripts | N/A | None — determinism hash unchanged |
| Import-boundary enforcement | Unenforced | Still unenforced — tracked as TD-010, reserved as WP-005 |

## Next

No work package filed yet for Phase 1's remaining scope (extract
`config`/`storage`/`utils` into `quantos_core`). Reserved: **WP-005 —
Architectural Import Boundary Enforcement** (name only).
