---
type: adr
number: 031
date: 2026-07-13
status: accepted
supersedes: none
---

# ADR-031 — Package Skeleton Structure for Pre-Phase-1 Repository Organization

## Decision

The empty `quantos_core/` package skeleton and top-level module directories
created in this work package follow the **QuantOS Target Architecture
Blueprint's §3 literal repository tree** (reproduced verbatim in the
Constitution, Part III/Repository Structure) exactly, with two narrow,
disclosed gap-fills where that tree omits two modules its own §5 module
specifications require. An informal directory tree pasted into chat
earlier in this session — structurally different from the Blueprint's tree
(it nested a `core/` folder, omitted `strategies`/`paper`/`live`/
`experiments`, and added `docs/00_governance/{ADR,Engineering Standards.md,
Program Status Reports}` subfolders not in the Blueprint) — is **not**
used as the basis for the package structure. It is treated as an informal
sketch, not a frozen governing document.

## Context

This work package's mandate ("Create empty package directories for the
future QuantOS modules... do not redesign [frozen documents]... if
implementation reveals ambiguity, create an ADR instead of inventing a new
architecture") requires scaffolding package directories before any
frozen-document content has been consulted for exact names. Two conflicts
surfaced on inspection:

1. **Tree conflict.** The chat-pasted tree and the Blueprint's own §3 tree
   disagree on structure (see Decision above). Only the Blueprint is one
   of the six frozen governing documents; the chat-pasted tree is not.
2. **Internal Blueprint gap.** The Blueprint's §5 Module Specifications
   list 21 modules, including `research` (module 01) and `api` (module
   17), each with a stated purpose, dependency set, and interface. Its own
   §3 repository tree, however, does not show either as a directory
   anywhere — `quantos_core/` lists only 15 subpackages (config, data,
   factors, strategies, portfolio, risk, execution, brokers, paper, live,
   analytics, validation, monitoring, storage, utils), and the top-level
   list (`services/`, `dashboard/`, `experiments/`, `strategies_registry/`,
   `tests/`, `tools/`, `infra/`, `docs/adr/`) has no `research/` or `api/`
   entry either.

## Alternatives Considered

- **Follow the chat-pasted tree instead.** Rejected: it isn't a frozen
  document, and using it would mean two conflicting "target structures"
  existing in the repo's history with no principled way to choose between
  them later. The Blueprint is explicitly frozen; the chat sketch is not.
- **Leave `research` and `api` unscaffolded until Phase 1 resolves the
  Blueprint's own gap.** Rejected: their existence is a formally decided
  fact (§5 specifies both in full — purpose, responsibilities, interface),
  only their *directory placement* is missing. Declining to scaffold them
  would be treating a document's editorial omission as if it were a
  decision to exclude the module, which it evidently is not (both are
  cited elsewhere in the same document as real, planned modules).
- **Nest `research/` and `api/` inside `quantos_core/`.** Rejected: their
  own module specs place them outside quantos_core's dependency graph —
  `research` "imports nothing from strategies/portfolio/risk/execution"
  and depends on quantos_core only read-only (the same relationship
  `experiments`/`tools` have, and both of those are top-level siblings,
  not quantos_core subpackages); `api` serves `dashboard`, itself a
  top-level sibling. Placing them as top-level siblings is the placement
  consistent with how the Blueprint treats every other module with an
  identical dependency shape.

## Rationale

Resolving both conflicts by deferring to the Blueprint's literal tree,
extended only by the minimum needed to make its own module specs
internally consistent, is the option that adds zero new architectural
surface: `research/` and `api/` were already decided modules, this ADR
only decides *where the directory goes*, using the placement pattern the
Blueprint itself already established for structurally identical modules.

## Consequences

- `quantos_core/` gets exactly 15 empty subpackages (per Blueprint §3),
  each with an `__init__.py` docstring restating its Blueprint §5 purpose
  — no logic, no imports beyond stdlib, nothing migrated from the frozen
  scripts.
- Top-level siblings created: `services/`, `dashboard/`, `experiments/`,
  `strategies_registry/`, `infra/`, `research/`, `api/` (the last two per
  this ADR's gap-fill), plus `docs/adr/` (this file's own home). `tests/`
  and `tools/` already exist from Phase 0 and are untouched.
- If Phase 1 planning reaches module 01 (`research`) or module 17 (`api`)
  and finds a different placement was actually intended, that supersedes
  this ADR explicitly — this decision is the default absent further
  Blueprint clarification, not a claim that the Blueprint's omission was
  deliberate.
- No change to any frozen document. The Blueprint's own text is
  unmodified; this ADR only records how its literal tree was extended to
  match its own module list.
