---
type: adr
number: 032
date: 2026-07-14
status: accepted
supersedes: none
---

# ADR-032 — Enforced Import-Boundary Matrix (WP-005)

## Decision

The CI import-boundary gate (Constitution Part II item 4, ADR-029)
enforces, mechanically, exactly this matrix of **allowed internal
imports** for `quantos_core` modules:

| Module | May import (within quantos_core) |
|---|---|
| `utils` | — (nothing) |
| `monitoring` | `utils` |
| `config` | `utils`, `monitoring` |
| `storage` | `utils`, `monitoring` |
| `brokers` | `utils` (Constitution verbatim: "nothing else in the tree except utils") |
| `data` | `utils`, `monitoring` |
| `factors` | `utils`, `monitoring` |
| `strategies` | `factors`, `data`, `utils`, `monitoring` |
| `portfolio` | `strategies`, `risk`, `storage`, `utils`, `monitoring` |
| `risk` | `storage`, `utils`, `monitoring` |
| `execution` | `brokers`, `storage`, `utils`, `monitoring` |
| `paper` | `strategies`, `portfolio`, `risk`, `execution`, `brokers`, `utils`, `monitoring` |
| `live` | identical to `paper` (ADR-010: same dependency graph) |
| `analytics` | `storage`, `factors`, `utils`, `monitoring` |
| `validation` | `strategies`, `data`, `analytics`, `utils`, `monitoring` |

Additionally, **nothing in `quantos_core` may import** (any form):
`services`, `api`, `dashboard`, `experiments`, `tools`, `research`,
`tests`, or any of the six frozen root scripts (`momentum_backtest`,
`paper_trader`, `transaction_costs`, `fetch_universe`, `download_data`,
`factor_attribution`).

Widening any cell of this matrix requires editing the matrix in the
gate **and** citing an ADR in the same change — never a silent edit.

## Context

The Blueprint §5 module specs state each module's dependency set; the
Constitution (Part II, Dependency Rules) adds two universal edges:
every module may depend on `utils` (`services → quantos_core.* →
quantos_core.utils`) and every module may emit to `monitoring`
("every other module depends on (emits to) monitoring", which itself
has "no upward dependency"). TD-010 has risen to Medium: three modules
(`config`, `storage`, `utils`) now carry real code with no mechanical
boundary enforcement — the exact condition ADR-029 exists to prevent.

## Alternatives Considered

- **`import-linter` package.** Rejected for now: adds a dependency (and
  re-triggers TD-011's broken editable install) for what ~100 lines of
  stdlib `ast` achieves; the Due Diligence standing rule prefers native
  reimplementation of narrow patterns. Revisit if contract complexity
  outgrows the native scanner.
- **Encode only the modules that currently have code.** Rejected: the
  matrix is cheapest to freeze while most modules are still empty —
  every future WP then lands inside an already-enforced boundary.
- **Blueprint deps verbatim with no universal `utils`/`monitoring`
  grant** (e.g., `factors` lists "none beyond numpy/pandas"). Rejected:
  the Constitution's universal clauses are explicit and it is the
  governing standards document; encoding both sources' intersection
  would contradict it.

## Rationale

Convention already failed once at this exact failure mode (18 research
files mixed into production folders; a fabricated universe function
feeding live strategies). A mechanical gate cannot be bypassed under
deadline pressure. Doing it as a pytest keeps it inside the existing
CI-blocking suite with zero new infrastructure.

## Consequences

- `tests/quantos_core/test_import_boundaries.py` is the gate; it scans
  every `quantos_core/**/*.py` via `ast` (absolute and relative imports
  both resolved) and fails on any edge outside the matrix.
- The scanner guards itself: a self-test feeds it a synthetic violating
  module and asserts detection (ADR-018's mutation-test spirit).
- `services`/`tools`/`experiments` inward-import enforcement (the other
  half of ADR-029) becomes testable the moment those trees contain
  Python files; the same test covers `quantos_core` outward imports
  today.
