---
type: work-package
id: WP-005
date: 2026-07-14
status: complete
phase: 1
---

# WP-005 — Architectural Import Boundary Enforcement

## Objective

Close TD-010: make the Constitution's dependency rules (Part II item 4,
ADR-029) mechanically enforced instead of conventional. Reserved since
WP-001; priority rose to Medium when WP-002 landed the first real,
unenforced module code, and three modules now carry real code.

## Scope

1. **ADR-032** — the enforced import matrix, derived from Blueprint §5
   per-module dependency specs + the Constitution's two universal edges
   (everything may import `utils`; everything may emit to `monitoring`;
   `brokers` restricted to `utils` verbatim; `paper`/`live` identical
   per ADR-010). Widening any cell requires an ADR cited in the diff.
2. `tests/quantos_core/test_import_boundaries.py` — stdlib-`ast`
   scanner, no new dependency (native reimplementation per standing
   Due-Diligence rule; `import-linter` rejected in ADR-032):
   - every `quantos_core/**/*.py` scanned; absolute AND relative
     imports resolved;
   - internal edges checked against the ADR-032 matrix;
   - imports of outer layers (`services`, `api`, `dashboard`,
     `experiments`, `tools`, `research`, `tests`) and of the six frozen
     root scripts forbidden entirely;
   - drift guard: test fails if quantos_core's package set and the
     matrix ever diverge;
   - scanner self-test: synthetic violating module must be detected
     (ADR-018 mutation spirit).

Runs in the default pytest suite → already CI-blocking via the existing
gate. No CI config change needed.

## Out of Scope

I/O-purity linting of the domain core (no `sqlite3`/`requests` inside
`factors` etc.) — a future detector; `services`/`tools` inward-import
enforcement activates automatically once those trees contain Python.

## Files Created

- `docs/adr/ADR-032-enforced-import-boundary-matrix.md`
- `tests/quantos_core/test_import_boundaries.py`
- this report

## Files Modified

- `INVENTORY.md` — regenerated (574 → 578 tracked files)
- `.ai/AI_CONTEXT.md`, `.ai/CURRENT_TASK.md`, `.ai/PROJECT_STATE.yaml`

Zero dependency changes. Zero frozen-script changes. Zero files moved.

## Validation

| Gate | Result |
|---|---|
| `ruff check .` / `ruff format --check .` | All checks passed / 44 files formatted |
| `mypy --strict` on the new test | Success (test tree is strict-clean too) |
| `coverage run -m pytest -m "not network"` | **73 passed**, 1 deselected (4 new cases) |
| `tools/verify_determinism.py 3` | 3/3 byte-identical; baseline sha `e3d29859aa00...` unchanged |
| `git diff` on the six frozen scripts | Empty |
| Gate proves itself | Current tree: zero violations; synthetic violation: caught |

## Exit Criteria — all met

- [x] ADR-032 filed with the full matrix and widening rule
- [x] Scanner enforces matrix + forbidden layers + frozen scripts
- [x] Relative imports resolved, not ignored
- [x] Drift guard between package set and matrix
- [x] Scanner self-test passes
- [x] Determinism unchanged; frozen scripts untouched
- [x] AIOS updated; git tag `wp-005-import-boundaries`

## Engineering Impact

| Dimension | Before | After |
|---|---|---|
| Boundary enforcement | Convention + review discipline | Mechanical, CI-blocking, ADR-gated matrix |
| TD-010 | Medium, rising | **Closed** |
| Test count | 69 | 73 (+4) |

## Next

Phase 1 fully closed (stated scope + both reserved WPs' blocker debt).
WP-006 (Layered Configuration) remains reserved. **Phase 2 — Data
Platform (`DataProvider` port, point-in-time universe store, closes
F1/F9) is the next roadmap item and the first on the critical path to
Phase 8 live broker integration.**
