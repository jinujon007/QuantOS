---
type: adr
number: 035
date: 2026-07-14
status: accepted
supersedes: none
---

# ADR-035 — Static Read-Only Operator Console Ahead of Phase 9 (WP-010)

## Decision

Ship the operator UI now as a **generated static page**
(`tools/build_dashboard.py` + `dashboard/template.html` →
`dashboard/index.html`, git-ignored build artifact): no server, no
`api` module, no new dependencies, no JS framework. Refresh = re-run
the generator. The page is strictly read-only; the single permitted
write control (ADR-028's kill switch) ships as the separately
mandated operator CLI (`tools/kill_switch.py`, Constitution Part V),
not as a web control.

## Context

Operator direction (Jinu, 2026-07-14): build the UI/UX now. ADR-028
sequences the dashboard last (Phase 9) specifically to avoid building
observability UI "before there is real telemetry to show" — but that
predicate has flipped: the system now produces real artifacts worth
showing (paper account state, order journal, PIT snapshots, the
determinism-pinned equity curve, kill-switch state, registry params).
A static page over existing artifacts adds zero servers, zero attack
surface, zero runtime dependencies — none of the costs ADR-028 exists
to defer. Phase 9's live `api`+`dashboard` (websockets, real
telemetry feeds) remains where it is; this console is its read-only
precursor, not its replacement.

## Design inputs

Reviewed the operator UIs of OpenAlgo, ai-hedge-fund, and
Vibe-Trading (2026-07-14 agent sweep of the cloned repos). Adopted as
patterns (reimplemented, nothing copied): mode-tinted page state
(OpenAlgo's analyzer-mode tint → our paper-mode banner that turns red
site-wide when the kill switch is engaged), Vibe-Trading Runtime's
status grammar (summary tiles → derived one-word system state instead
of raw flags → freshness ages), OpenAlgo's data-readiness pill (→
client-computed staleness pills for paper state and universe
snapshots) and Indian-grouping number format. Rejected: all three
repos' navigation models (9-tab sprawl / IDE workbench / marketing
chrome) — the console is one page, no nav, answer-first.

## Consequences

- `dashboard/index.html` is a build artifact (git-ignored); the
  template and generator are source.
- The chart is a single-series SVG with crosshair tooltip, computed
  from `data/results/equity_curve.csv` at build time — the same
  determinism-gated artifact CI pins, so the console can never show
  numbers the gates didn't produce.
- Every section degrades gracefully (missing artifact → explicit
  "run X to populate" line, never a blank or a guess).
- When Phase 9 arrives, this generator's sections become the read
  models the live `api` serves; the page design carries over.
