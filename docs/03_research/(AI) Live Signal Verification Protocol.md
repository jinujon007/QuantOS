---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.7
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Live Signal Verification Protocol — Momentum's First Real Rebalance

**Status: preparation only. Today is 2026-07-13 (Monday). Friday 2026-07-17 has not happened yet.** This document defines the protocol; it contains no results. Execution and the comparison report happen only after Friday's rebalance actually runs — nothing below should be read as having occurred.

## Research question

Does the production pipeline (`paper_trader.py`) generate exactly the portfolio the research specification (12M-1M momentum, top-10, regime-filtered) predicts from the same point-in-time data — the first time it gets a real chance to run since the scheduler fix?

## Evidence to collect (from the actual Friday run — no new code needed, all of this already gets logged)

| Evidence | Source |
|---|---|
| Market data snapshot | `nifty500_universe.csv` (note its mtime — confirm it wasn't re-fetched between now and Friday, which would change the universe out from under the comparison) |
| Regime determination inputs + result | `trader_logs/2026-07-17.log`, the `Regime: Nifty {price} vs MA100 {ma} -> {BULL/BEAR}` line from `check_regime()` |
| Eligible universe | Row count and ticker list of `nifty500_universe.csv` as of Friday |
| Momentum scores + ranked securities | `trader_logs/2026-07-17.log`'s "Top 10 momentum scores today" block (`compute_momentum_scores()`'s output, printed in full with a held/not-held marker per line) |
| Selected top-10 portfolio | Same block, the `[✓]` rows |
| Rejected candidates + reasons | Not explicitly logged by production today — this is where the independent recompute (below) adds detail production doesn't currently capture, not a defect in production, just a granularity gap |
| Generated orders / executed trades | `trader_logs/2026-07-17.log`'s `BUY`/`SELL` lines, cross-checked against new rows in `data/paper_trades.csv` dated 2026-07-17 |
| Resulting portfolio state | `data/paper_state.json` after Friday's run — `holdings`, `cash`, `portfolio_value` |

## Independent recomputation method

Deliberately NOT calling `compute_momentum_scores()` or `check_regime()` again — re-running the same function only proves reproducibility (already established separately for cached backtest data), not correctness of the implementation itself. A verification that reuses the code under test can't catch a bug in that code.

Instead, a freestanding script will:
1. Read the same `nifty500_universe.csv` (same file, same day).
2. Independently fetch each ticker's price history via a fresh `yfinance` call, spanning the same window `compute_momentum_scores()` uses (`today - 1mo` back to `today - 13mo`, `MIN_TRADING_DAYS=150`-equivalent validity floor).
3. Compute 12M-1M return (`p[end] / p[start] - 1`) from scratch, using pandas directly — same formula, hand-written, not imported from `paper_trader.py`.
4. Independently recompute the regime call: fetch `^NSEI`, compute a 100-day rolling mean, compare to the latest close — same formula, hand-written.
5. Rank, take top 10, and record which tickers were excluded and why (missing data / failed the minimum-history floor / simply outside top 10).

**Known limitation, disclosed up front, not something to fix:** Yahoo's historical data can be revised after the fact. Re-fetching after Friday isn't guaranteed byte-identical to what production fetched live on Friday itself — this is a data-provenance gap, not a code defect, and it's inherent to using yfinance as a live data source. If a mismatch shows up, this is the first thing to rule out before calling it an implementation defect.

## Comparison criteria

- **Regime call:** must match exactly (BULL/BEAR is binary).
- **Selected top-10 set:** must match as a set. Order matters less than membership, since `run_backtest`/`compute_momentum_scores` sorts by score and ties are not expected at 10 significant names out of ~450.
- **Individual momentum scores:** allow small floating-point tolerance (a few basis points) to account for intraday price timing differences between production's fetch and the independent re-fetch — anything beyond that tolerance is a genuine discrepancy to explain, not to wave off.
- **Orders/trades:** ticker, action (BUY/SELL), and share count (given the logged price) must match what the independent recompute's target allocation would produce.
- **Final holdings:** must match `data/paper_state.json` exactly.

## Root-cause classification (if any mismatch is found)

1. **Implementation defect** — the production code's logic doesn't match the documented specification (e.g., wrong date offset, wrong price column, off-by-one in the lookback window).
2. **Data discrepancy** — same formula, different underlying data (Yahoo revision, a ticker's data arriving late, a corporate action adjustment applied differently between the live fetch and the re-fetch).
3. **Expected execution behavior** — a documented, intentional filter or tie-break did its job (e.g., a ticker excluded for failing `MIN_TRADING_DAYS`, or a cash-constraint skip near the end of the buy loop).
4. **Research assumption** — the specification itself has an ambiguity the independent recompute exposed (e.g., "top 12 months" could mean calendar months or 365 days, and the two give different tickers at the margin).

Any divergence gets traced to the *first* point it appears (regime → universe → scores → ranking → selection → orders → final state), not just reported as "something differs."

## What this protocol will NOT do

Per the task's own rules: no strategy modification, no parameter tuning, no alpha change, and no engineering fix unless the verification actually finds a defect — a data-discrepancy or expected-behavior finding gets documented, not "fixed." Profitability of this single rebalance will not be evaluated — this is a correctness check, not a performance one (that question is explicitly parked per the prior Research Confidence Report, which already established there's nowhere near enough live history to evaluate performance).

## Next step

Nothing to execute until Friday 2026-07-17's rebalance actually completes. At that point: run the independent recompute script, pull the 4 evidence sources listed above, compare, and produce the Live Signal Verification Report this protocol is preparing for. This conversation (or a fresh one referencing this file) needs to be resumed after Friday — I have no way to act on a future calendar date on my own.
