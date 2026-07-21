---
type: adr
number: 043
date: 2026-07-21
status: accepted
supersedes: "ADR-022, ADR-023 (Constitution ADR ledger) — amended, not repealed"
---

# ADR-043 — Metrics by Ported Formula, Not Dependency; Experiment Tracking Native, Not MLflow

## Decision

Two Constitution-era ADRs are amended on the 2026-07-21 due-diligence
evidence (both were written against the 2026-07-13 OSS review and
flagged "verified stale — revisit before Phase 5" by that audit):

1. **ADR-022 (was: adopt `empyrical`/`pyfolio` for metrics) →
   metric formulas are ported natively, with the source cited at the
   definition site.** The bug class ADR-022 targeted (hand-rolled
   annualization errors, e.g. the documented 1691% CAGR incident) is
   closed by citing the de-facto standard formula, not by importing a
   maintenance-mode library into the decision path.
   `tools/paper_metrics.py` (WP-017) is the pattern's first instance:
   annualized Sharpe = mean(daily returns)/std(daily returns)·√252,
   rf = 0 — empyrical's definition, hand-computation pinned by test.
   `quantstats` remains available per the DD verdict as a
   version-pinned **report sidecar only** (weekly HTML tearsheet),
   never inside the decision path.
2. **ADR-023 (was: adopt MLflow at Phase 5) → MLflow is rejected.**
   Phase 5 experiment tracking is a native run-manifest: run_id,
   config hash, git SHA, data-snapshot id, metrics table — ~50 lines
   against existing `storage`. Scope lands with Phase 5, not before
   (no speculative code now).

## Context

- `empyrical`/`pyfolio-reloaded`: 116/599 stars, last release 2025-12,
  maintenance mode (DD §9.1). Importing it puts an unmaintained
  dependency inside gate-evidence computation; the formulas themselves
  are two lines each.
- MLflow 3.x pivoted to GenAI/LLM tracing (DD §9.1). For a
  deterministic, single-operator system whose experiments are already
  reproducible by construction (pinned lockfile, byte-identical runs,
  git SHAs), MLflow's server/UI/artifact machinery is weight with no
  offsetting value — the exact framework-vs-value test ADR-020/024
  already apply elsewhere.
- WP-017 shipped a natively-computed Sharpe before this amendment was
  filed; this ADR is what makes that governance-clean rather than a
  silent drift from ADR-022.

## Alternatives Considered

- **Keep ADR-022 and depend on empyrical anyway.** Rejected: an
  unmaintained metrics library inside the Sept-9 gate computation is
  a worse correctness risk than cited two-line formulas with pinned
  tests — the dependency's value was its maintenance, which ended.
- **Adopt quantstats for decision-path metrics too.** Rejected: DD
  verdict scopes it to report sidecar; decision-path math stays
  native, tested, and dependency-free.
- **Build the run-manifest now.** Rejected: Phase 5 scope; landing it
  early is speculative code (Constitution: no placeholder/future
  infrastructure).

## Consequences

- Every native metric definition must cite its source formula at the
  definition site and pin a hand-computed value in tests
  (`tools/paper_metrics.py` + `tests/test_paper_equity_history.py`
  are the template).
- The Constitution's ADR ledger entries 022/023 stand as written
  (frozen document) with this ADR as the controlling amendment —
  the ledger's next regeneration notes "amended by ADR-043".
- Phase 5's dependency list shrinks by two (empyrical, MLflow);
  `quantstats` enters only if/when the weekly tearsheet is built,
  pinned, outside the decision path.
- The DD action item "revisit ADR-022/023 before Phase 5" is closed.
