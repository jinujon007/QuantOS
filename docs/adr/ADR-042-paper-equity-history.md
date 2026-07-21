---
type: adr
number: 042
date: 2026-07-21
status: accepted
supersedes: none
---

# ADR-042 — Daily Paper-Equity History Is Captured as a True-Append CSV (WP-017)

## Decision

Every completed daily paper run appends one row —
`date, total_value, cash, positions, degraded` — to
`data/paper_equity_history.csv` (`paper_trader.log_equity_snapshot`).
`tools/paper_metrics.py` reads that history and reports observation
count, total return, annualized Sharpe (rf = 0, √252), and max
drawdown — making the Sept-9 gate's "paper Sharpe > 1.0" a computable
number for the first time.

Supporting rules:

1. **True append, never rewrite** — same audit-trail rule as
   `data/paper_trades.csv` (a mid-write kill must not destroy history).
   A `--force` rerun therefore writes a second row for the same date;
   **readers keep the LAST row per date** (last-write-wins dedup in
   `load_history`).
2. **Degraded runs still record, flagged** — a run whose valuation fell
   back to stale entry prices writes its row with `degraded=True`.
   Skipping it would silently bias the return series toward healthy
   days; the metrics tool counts degraded rows and warns instead.
3. **The row is written only after `save_state`** — history must
   describe a day that durably persisted.
4. **Zero-volatility Sharpe is undefined (`None`), not infinite** — an
   all-cash account produces "n/a", never a division crash.
5. **Freeze-safe** — capture is pure logging inside the frozen script:
   reads nothing back, alters no signal, state transition, or trading
   decision. CONTEXT.md's Prospective Validation rule explicitly permits
   this class of change; the validation clock does not restart.

## Context

The Sept-9 go/no-go gate requires "paper Sharpe > 1.0", but the live
paper loop overwrote `portfolio_value` in `paper_state.json` on every
run — no equity series existed anywhere, so the gate metric was
uncomputable (2026-07-21 due-diligence finding; WP-017 was the audit's
recommended next package). WP-014's daily backups snapshot whole state
files but only started 07-21 and live off-repo; the shadow book's
`cycle_reports.jsonl` records `value` per cycle but for the shadow
account only. The system of record needed its own series.

## Alternatives Considered

- **Reconstruct history from WP-014 backups.** Rejected: backups start
  2026-07-21 (no more history than the CSV will accrue), live in an
  operator-owned directory possibly off-machine, and reconstruction
  code is more surface than a one-line append.
- **Store history inside `paper_state.json`.** Rejected: state is
  untracked (ADR-040) and rewritten atomically each run — history in a
  rewritten file inherits rewrite risk, and mixing an ever-growing
  series into hot state bloats every read/write.
- **Capture in the shadow cycle instead.** Rejected: the shadow is not
  the system of record until the Phase 6 cutover; gate evidence must
  come from the account being validated. (Post-cutover, `CycleReport`
  already carries `value/cash/positions` — the same capture becomes a
  one-line shell append.)

## Consequences

- History starts accruing 2026-07-21; by the Sept-9 review it holds
  ~7 weeks of daily observations. (Sharpe over ~35 points is noisy —
  the gate reviewer sees the observation count printed first.)
- `python tools/paper_metrics.py` is the gate query; exit 1 = no or
  insufficient history, so it can sit in a checklist script.
- `data/paper_equity_history.csv` follows the ADR-040 rule for
  daily-mutated operational state: gitignored (a tracked file the
  15:40 task appends to would dirty the tree every run — exactly what
  WP-015 eliminated) and added to the WP-014 backup set
  (`tools/backup_state.ps1`), which is where its durability lives.
- `tests/test_paper_equity_history.py` pins the append/dedup/Sharpe
  semantics (10 tests).
