---
type: crystallization
date: 2026-07-12
area: self
project: AlgoTrader
status: active
confidence: 0.8
sources: 1
last_confirmed: 2026-07-12
ai_generated: true
---

# QuantOS Foundation — Post-Stage-1

**Question:** what architecture, if any, does Stage 1's fixes expose as necessary before starting P1 (point-in-time universe, fundamentals correctness, walk-forward improvements)?

**Answer: almost none yet.** Stage 1 was 5 in-place fixes, no new modules, no shared library. That was correct — nothing in Stage 1 needed shared infrastructure. P1 is different: two of its three items (point-in-time universe, fundamentals correctness) are the *same underlying problem* — "where do we get data that reflects what was knowable at a past date" — showing up in two different codebases. That commonality is the only architecture decision actually load-bearing right now.

## What Stage 1 closed

1. Look-ahead bias — both `momentum_backtest.py` and `paper_trader.py` now fill trades one day after the signal that produced them, not same-day. Each has a self-check (`--selftest`).
2. Cost model — `paper_trader.py` now imports the same `transaction_costs.py` accurate Zerodha model the backtest uses, instead of a flat 0.1%.
3. Scheduler — `run_daily_traders.ps1` checks exit code + scans output for error/traceback text per strategy, writes a `LAST_RUN_FAILED.flag` on any failure, console banner in red. Verified against the exact failure mode that caused the original month-long silent break (exit 0 + traceback in output).
4. Quality Factor caveat — corrected in the process: the live P&L isn't look-ahead biased (that was my error in the original audit, conflating the live paper trader with a different, offline backtest script). The backtest's bias (T-006) turned out to already be fixed, confirmed by its dated results file, not by trusting the sibling repo's self-contradicting task tracker.
5. SEBI checklist — written, not completed. Needs your Angel One login; can't be done by me.

## What Stage 1 surfaced that wasn't in the original audit (F9)

`trading_backtests/utils/data_loader.py::get_nifty500_universe()` is not a data fetch. It's 96 hardcoded tickers, chosen with 2026 hindsight, including stocks that didn't exist before their 2021-2022 IPOs. Quality Factor and Factor Timing — 2 of the tournament's 4 live strategies — both select from this fabricated list. This is worse than the survivorship-bias risk originally flagged for AlgoTrader's own universe (which is at least a real, if not point-in-time, fetch). Full detail in the audit doc's F9.

This is the actual argument for doing P1's "point-in-time universe" work as **shared infrastructure** rather than fixing it twice: AlgoTrader needs point-in-time correction (F1), the sibling suite needs to stop being fabricated *and* become point-in-time (F9) — same fix, two codebases, currently zero shared code between them.

## Minimal architecture for P1 — nothing beyond this

**One shared module, not a package, not a repo restructure:** a single `universe_source.py` (or equivalent) that both codebases import, backed by whichever point-in-time data source gets chosen (this is a vendor/data question, not an architecture question — NSE doesn't publish historical constituent membership for free; likely candidates are a paid vendor or manual reconstruction from NSE circulars, both out of scope for this doc). Until that source is picked, there is nothing to build.

**Explicitly not doing yet:** config extraction, shared metrics module, shared cost model reuse in the sibling suite, testing harness, any of Phase 2+ from the original roadmap. Those remain roadmap entries, not current work. P1 stays scoped to: pick a point-in-time data source, replace both `fetch_universe.py`'s current-membership fetch and `get_nifty500_universe()`'s hardcoded list with it, re-run all affected backtests, and only then decide if a shared module is worth extracting versus just fixing both files independently.

## Next question

Is a paid point-in-time constituent-history vendor worth it for a solo, pre-live-capital project, or is manual reconstruction from NSE's historical index-change circulars (free but slow) the better first move? That's the actual decision blocking P1, not architecture.
