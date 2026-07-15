---
type: work-package
id: WP-013
date: 2026-07-15
status: complete
phase: Phase 6 slice (ADR-038; Blueprint module 09 interface)
---

# WP-013 — paper.run_cycle + Shadow Cutover Harness

## Objective

One orchestrated daily cycle over the WP-012 accounting core —
`run_cycle(as_of) -> CycleReport` with every dependency injected —
plus the shadow harness that accumulates the evidence to retire
`paper_trader.py` as system of record without betting the validation
clock on a big-bang swap (ADR-038).

## Delivered

- **`quantos_core/paper/cycle.py`** — `run_cycle`: kill switch first
  (fail-closed, before any state read) → same-day idempotence → T+1
  fills persisted BEFORE signal work → stop-losses → regime actions
  (liquidate only on CONFIRMED bear; UNKNOWN acts on nothing) →
  Friday rebalance with weekend catch-up via `last_rebalance_date`
  (hold = a decision that consumes the date; signals-unavailable =
  degraded retry that doesn't). `MarketSnapshot` value carries all
  market facts in; `StateStore` Protocol keeps `paper`'s ADR-032 cell
  storage-free while the production `SqliteRepository` satisfies it
  structurally (pinned by test).
- **`tools/run_paper_cycle.py`** — the shadow: seeds from
  `data/paper_state.json`, reuses the frozen script's own fetchers for
  input parity, runs the cycle against `data/shadow/portfolio.db`
  (git-ignored), appends `CycleReport`s to
  `data/shadow/cycle_reports.jsonl`, compares books to the legacy
  state, exits 1 on divergence.
- **`tools/daily_run.ps1`** — shadow step added after the real run;
  a divergence surfaces as DEGRADED on the console's last-run tile.
  Also fixed: the run's end marker now precedes the console rebuild,
  so a run no longer renders as INCOMPLETE during its own rebuild.

## Verification

- 16 cycle tests — every 2026-07-14 audit failure mode as a structural
  property: halt-before-state-read, fail-closed on unreadable switch,
  missing state fails loud (never reinitializes), same-day idempotence,
  fills survive a mid-cycle crash, unknown regime acts on nothing and
  keeps the rebalance date unconsumed, bear Friday consumes it,
  Saturday catch-up works and never double-rebalances, weekday never
  rebalances, real-SqliteRepository end-to-end.
- **Live run 2026-07-15:** seeded from legacy books, regime BULL
  (Nifty 24,087 > MA100 23,985), cycle OK, **books MATCH**, exit 0.
- Full suite 237 passing; `mypy --strict` clean; boundary gate green.

## Cutover gate (operator decision, not in this WP)

`paper_trader.py` remains the system of record. Switch when the shadow
matches through **two consecutive clean weekly rebalances** (first
candidate rebalance: Friday 2026-07-17). Record the decision in
CONTEXT.md; TD-002 then closes by supersession. Engine-mediated fills
(PaperBrokerAdapter) are the Phase 6 step after cutover — a fill-
semantics change, versioned separately.
