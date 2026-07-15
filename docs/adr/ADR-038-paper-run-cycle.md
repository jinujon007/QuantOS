---
type: adr
number: 038
date: 2026-07-15
status: accepted
supersedes: none
---

# ADR-038 — paper.run_cycle: One Injected-I/O Daily Cycle + Shadow Cutover (WP-013)

## Decision

`quantos_core/paper` gains **`run_cycle(as_of, ...) -> CycleReport`** —
the Blueprint module 09 interface — orchestrating one paper trading
day entirely from injected dependencies:

1. Kill switch first (fail-closed: unreadable = engaged = halted run,
   state untouched) — the interlock the daily loop lacked until the
   2026-07-14 audit, now structural instead of bolted on.
2. Same-day idempotence (`last_updated == as_of` → report, no writes).
3. Fill the T+1 queue (ADR-037 accounting) and **persist immediately**,
   before any slow signal work.
4. Stop-losses; bear-regime cash exit **only on a confirmed bear**;
   UNKNOWN regime = no trading actions + degraded report.
5. Friday rebalance with weekend catch-up (`last_rebalance_date` <
   most recent Friday), stances from the parity-proven `Strategy` port:
   `rebalance` → queue equal-weight entries/exits, `hold` → record the
   decision, signals unavailable → degraded, no date consumed.

Market data arrives as a **`MarketSnapshot` value** (latest closes +
bar date + regime + optional 14-month close matrix) built by the shell
— `paper` imports no data module, per its frozen ADR-032 cell, which is
also exactly the "same dependency graph live will use" property of
ADR-010: `live.run_cycle` swaps the snapshot builder and the fill path,
not the cycle.

**Cutover is evidence-gated, not declared.** `tools/run_paper_cycle.py`
runs the new cycle daily as a **shadow**: same fetched inputs as
`paper_trader.py`, its own state in `data/shadow/`, every divergence
from `data/paper_state.json` reported and exit-coded so it surfaces in
the daily-run tile. `paper_trader.py` remains the system of record
until the shadow matches it through **two consecutive clean weekly
rebalances**; the switch is then an operator decision recorded in
CONTEXT.md. The validation clock is unaffected throughout — shadow mode
places nothing and mutates nothing outside `data/shadow/`.

## Context

WP-009 proved signal parity but left the validated core unwired — the
audit's whole critical section existed because the thing that trades
daily was still the legacy script. This WP gives the core a daily cycle
with the audit fixes as first-class semantics, and a mechanical path to
retiring the script without betting the validation record on a big-bang
swap.

## Alternatives Considered

- **Routing fills through `ExecutionEngine` + `PaperBrokerAdapter`
  now.** Rejected for this slice: the engine places limit orders filled
  at market instantly; the validation record's semantics are T+1 fills
  at the next session's close with the delivery cost model. Swapping
  fill semantics mid-clock would be a frozen-list execution change.
  Engine-mediated paper execution is the Phase 6 step, after cutover,
  as its own versioned change.
- **`run_cycle` fetches its own data.** Rejected: breaks the ADR-032
  cell and Constitution Part II item 5 (a strategy/cycle cannot fetch
  or guess its own data); injected snapshots are also what make the
  cycle testable to the edge cases the audit found.
- **Immediate cutover (delete `paper_trader.py` now).** Rejected: no
  side-by-side evidence would exist; a porting bug would corrupt the
  validation record it exists to protect.

## Consequences

- `tools/daily_run.ps1` gains a read-only shadow step after the real
  run; a divergence exit-codes as DEGRADED in the console tile.
- The paper/live symmetry of ADR-010 becomes concrete: `live.run_cycle`
  is now a snapshot-builder + fill-path swap, not a new system.
- After cutover, `paper_trader.py` joins the frozen scripts as
  reference-only; TD-002 (its zero test coverage) closes by
  supersession, as planned since Phase 0.
