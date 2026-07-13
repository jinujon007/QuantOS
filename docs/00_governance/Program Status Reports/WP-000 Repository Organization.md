---
type: work-package
id: WP-000
date: 2026-07-13
status: complete
phase: pre-Phase-1 (repository organization)
---

# WP-000 — Repository Organization

## Objective

Reorganize the repository into the docs/ hierarchy and scaffold empty
`quantos_core` package directories, in preparation for Phase 1, without
migrating any trading logic, without touching any frozen subsystem, and
without changing observable behavior.

## Scope

**In scope:**
- Move remaining governance/audit/report documents (19 files) into
  `docs/{00_governance,01_audits,03_research}/`, completing the doc
  reorganization started in the prior session (5 files already moved).
- Create empty `quantos_core/` package (15 subpackages) plus top-level
  `services/`, `dashboard/`, `research/`, `api/`, `experiments/`,
  `strategies_registry/`, `infra/`, `docs/adr/` — structure and directory
  names, `__init__.py` docstrings only, zero logic.
- Resolve two ambiguities discovered during scaffolding via ADR-031
  (chat-pasted tree vs. frozen Blueprint conflict; Blueprint's own
  `research`/`api` tree omission vs. its module specs).
- Update `tools/generate_inventory.py`'s classifier for the new structure.
- Stand up the Technical Debt Register and Risk Register as living
  documents.

**Out of scope (explicitly not done):**
- No file under `momentum_backtest.py`, `paper_trader.py`,
  `transaction_costs.py`, `fetch_universe.py`, `download_data.py`,
  `factor_attribution.py` was touched.
- No code moved into `quantos_core/` — it is empty.
- `CONTEXT.md`, `PRD.md`, `EXECUTION_PLAN.md`, `README.md`,
  `INVENTORY.md` stay at repo root — not governance/audit/architecture/
  report documents per the literal instruction scope.
- `My_terminal/trading_backtests/` untouched (outside this repo's git
  scope, per the confirmed Phase 0 decision).

## Files affected

19 documents moved (`git mv`, history preserved) + 1 already-existing file
edited (`tools/generate_inventory.py`) + 21 new files created (20
`__init__.py`/`. gitkeep` scaffold placeholders + 1 ADR) + 2 new registers
+ `INVENTORY.md` regenerated. Zero files under the six frozen scripts
touched. Full list: `git show --stat` on this work package's commit(s).

## Dependencies

None. This work package has no dependency on any other in-flight work —
it's pure repository structure, no code changes to anything already
running.

## Risks

- **Cross-reference breakage.** Mitigated: grepped for hardcoded
  relative-path references to every moved file before moving it; none
  found (only Obsidian-style name references, vault-wide resolution,
  unaffected by directory moves). Logged as R-004 in the Risk Register,
  status: mitigated.
- **Frozen-tree/chat-tree conflict silently resolved wrong.** Mitigated:
  resolved explicitly via ADR-031 rather than picking one silently;
  reasoning and alternatives recorded there, reversible if wrong.
- **Golden-file/determinism drift from unrelated scaffolding.** Mitigated:
  re-ran the full test suite and a fresh determinism check after every
  change in this work package; hash matched the pre-existing baseline
  exactly at every checkpoint (see Validation below).

## Implementation

1. Moved 19 root-level `.md` files into `docs/00_governance/` (2),
   `docs/01_audits/` (1), `docs/03_research/` (16) via `git mv`.
2. Wrote ADR-031, resolving the package-structure ambiguity by deferring
   to the Blueprint's literal tree (one of the six frozen documents) over
   the informal chat-pasted alternative (not a frozen document), and
   gap-filling `research/`/`api/` as top-level siblings per their module
   specs' own dependency shape.
3. Created `quantos_core/` + 15 subpackages
   (config/data/factors/strategies/portfolio/risk/execution/brokers/
   paper/live/analytics/validation/monitoring/storage/utils), each with an
   `__init__.py` docstring restating its Blueprint §5 purpose verbatim —
   no logic, no imports beyond what Python requires for a valid package.
4. Created top-level `services/`, `dashboard/`, `research/`, `api/`
   (`__init__.py` docstrings) and `experiments/`, `strategies_registry/`,
   `infra/` (`.gitkeep`, non-Python content directories).
5. Extended `tools/generate_inventory.py`'s classifier: new `scaffold`
   bucket (path-prefix matched, not per-filename) for the empty skeleton;
   fixed a real, previously-undetected gap where the tool's own Phase 0
   output (`tests/`, `tools/`, `CODEOWNERS`, `requirements-lock.txt`) had
   been silently landing in "Other Python"/"Unclassified" since it was
   added, because I hadn't been checking the generator's exit code after
   each change.
6. Wrote the Technical Debt Register and Risk Register (`docs/00_governance/`), seeded with every real, already-discovered item from this and the prior Phase 0 session — nothing new invented for this document, no speculative content.

## Tests

No new tests were required — this work package touches no executable
trading logic, only documentation, empty package scaffolding, and one
existing tool (`generate_inventory.py`). The existing 12-test offline
suite is the regression check that proves nothing was broken.

## Validation — quality gates

| Gate | Result |
|---|---|
| Golden tests | 6/6 pass, unchanged (`test_momentum_backtest_characterization.py`) |
| Determinism verification | 3x re-run post-change: `equity_curve.csv` sha256 `e3d29859aa00...` — **identical to the Phase 0 baseline hash**, confirming zero behavioral drift |
| Ruff (lint) | Clean — `ruff check .` passes, including the 20 new scaffold files (caught and fixed 23 real E501 violations in my own new `__init__.py` docstrings before commit — the gate did its job) |
| Ruff (format) | Clean — `ruff format --check .` passes |
| Mypy | Frozen scripts: 7 pre-existing errors, unchanged (documented, non-blocking, TD-006). New scaffold (`quantos_core`, `services`, `dashboard`, `research`, `api`): 0 errors, 20 files clean |
| Pytest | 12/13 pass (1 network-marked, excluded by default, unaffected) |
| Coverage | 25% overall, unchanged — no code was added under test scope (TD-008: no enforced floor yet, by design) |
| Import validation | All 20 new packages (`quantos_core` + 15 submodules + `services`/`dashboard`/`research`/`api`) import cleanly, verified directly (`python -c "import quantos_core..."`) |
| Dependency validation | Zero new third-party dependencies introduced; `pyproject.toml`/`requirements-lock.txt` unchanged and still resolve |
| Repository inventory validation | `tools/generate_inventory.py`: 551 files classified, **0 unclassified** |

## Rollback plan

Every change in this work package is either a `git mv` (reversible with
`git mv` back, or `git revert` on the commit) or a newly-added file
(reversible with `git rm`). No existing file's content was modified except
`tools/generate_inventory.py` (reversible via `git revert`). No database,
no external state, no live/paper-trading system touched — rollback is
pure git history manipulation, zero operational risk.

## Completion criteria

- [x] All governance/audit/report documents moved into `docs/` hierarchy.
- [x] `quantos_core/` + top-level module skeleton exists, matches the
      frozen Blueprint's structure (extended only via ADR-031's disclosed
      gap-fill).
- [x] Zero trading logic migrated.
- [x] All quality gates pass (see Validation table).
- [x] Golden outputs and determinism hash unchanged.
- [x] Technical Debt Register and Risk Register exist and reflect real,
      previously-discovered items.
- [x] ADR filed for the one genuine architecture ambiguity encountered.

## Remaining blockers before Phase 1 proper

Unchanged from the Phase 0 execution report, plus one new item from this
work package:

1. TD-001 — no trade-log artifact (Phase 6 territory).
2. TD-002/TD-003 — `paper_trader.py` live path and network-fetch utilities
   have zero coverage (superseded by Phase 2/6 modules, not retrofitted).
3. TD-004 — `My_terminal/trading_backtests/` has no Phase 0 safety net at
   all (new finding this work package, formalized in the register).
4. TD-007 — no GitHub remote, CI unexercised by a real runner.
5. R-001/R-002 — SEBI checklist and scheduler-gap root-cause, both
   pre-existing, both still open, both outside this work package's scope.

## Recommended next work package

**WP-001 — quantos_core/config: extract the config-loading skeleton
(Blueprint Phase 1, "config, storage, logging, CI" — config only, as the
smallest safe first slice).** Rationale: `config` is a dependency leaf
within `quantos_core` (nothing else in the domain core depends on it being
built first, but it depends on nothing else either — Constitution Part II,
Dependency Rules), so it's extractable without touching strategy logic and
without waiting on any other module. Concretely: implement
`quantos_core/config`'s `load_config(env) -> QuantOSConfig` per its module
spec, with a schema covering only the parameters that already exist as
scattered constants today (`TOP_N`, `STOP_LOSS_PCT`, etc. — read-only
extraction, the frozen scripts keep their own constants unchanged and
`config` isn't wired into them yet). This is the smallest slice that makes
real, Blueprint-ordered progress without requiring a decision on anything
not already specified. Awaiting approval before starting.
