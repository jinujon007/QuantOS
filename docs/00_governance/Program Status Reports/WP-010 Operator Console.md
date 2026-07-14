---
type: work-package
id: WP-010
date: 2026-07-14
status: complete
phase: ui-slice (ADR-035; read-only precursor to Phase 9)
---

# WP-010 — Operator Console (UI/UX) + Kill-Switch CLI

## Objective

Operator direction: build the project's UI/frontend, taking
inspiration from the existing open-source repos. Delivered as
ADR-035's static read-only console — one page, zero servers, zero new
dependencies — plus the Constitution-mandated kill-switch operator
CLI (Part V).

## Delivered

- **`tools/build_dashboard.py`** — generator: reads paper account
  state, strategy registry, the determinism-pinned equity curve, PIT
  universe snapshots, the order journal, and production kill-switch
  state → writes self-contained `dashboard/index.html` (git-ignored
  build artifact). Every section degrades gracefully ("run X to
  populate"), never blank, never guessed.
- **`dashboard/template.html`** — the design (source-controlled):
  ledger identity (serif/mono, saffron accent), light+dark themes,
  paper-mode banner, derived one-word system state (ACTIVE—IN CASH /
  ACTIVE—INVESTED / HALTED), Indian-grouping rupee format everywhere,
  client-computed freshness pills (paper state, universe snapshot),
  single-series SVG equity chart with crosshair tooltip + recessive
  grid + endpoint label, order blotter with outcome tags, broker
  readiness table, operator runbook. **Kill switch engaged → entire
  page tints red with the release command in the banner** (verified
  live via the real CLI during this WP).
- **`tools/kill_switch.py`** — status / engage "reason" / release
  "reason"; reason mandatory (audit trail); persisted via
  `quantos_core.risk` over `data/risk.db`.

## Design inputs (operator-requested)

Agent sweep of the three cloned OSS frontends (OpenAlgo 50+ pages,
ai-hedge-fund's IDE workbench, Vibe-Trading's web console). Adopted
as reimplemented patterns: OpenAlgo's mode-tinted theme + data-
readiness pill + Indian number format; Vibe-Trading Runtime's status
grammar (tiles → derived state → freshness ages). Rejected: all three
navigation models — findings confirmed every repo buries "am I OK
right now?" at least one click deep; this console is one page,
answer-first. Full verdicts in ADR-035.

## Verification

Rendered in a real headless browser (gstack browse): zero console
errors, light theme + halted state screenshotted and eyeballed;
computed backtest stats on the page (₹5,83,819 / 34.3% / 1.46 /
−23.6%) independently match the pinned reproducible run — the console
cannot show numbers the gates didn't produce.

| Gate | Result |
|---|---|
| `ruff` / `format` | Clean (E501 per-file-ignore for HTML f-string blocks, documented in pyproject) |
| `mypy --strict -p quantos_core` | Success — 39 files (unchanged; console is tools/dashboard, not core) |
| `pytest -m "not network"` | **178 passed** (4 new: inr grouping, outcome tags, CLI round-trip, console smoke) |
| `tools/verify_determinism.py 3` | Baseline sha unchanged |
| Six frozen scripts | Untouched |

## Files

Created: `tools/build_dashboard.py`, `tools/kill_switch.py`,
`dashboard/template.html`, `tests/test_operator_console.py`,
`docs/adr/ADR-035-operator-console.md`, this report.
Modified: `.gitignore` (+dashboard/index.html, data/demo/,
data/risk.db), `pyproject.toml` (per-file-ignore), `.ai/*`,
`INVENTORY.md`. Zero dependency changes; zero quantos_core changes.

## Next

Phase 9 later turns these sections into live `api` read models; until
then the console refreshes with one command:
`python tools/build_dashboard.py --open`.
