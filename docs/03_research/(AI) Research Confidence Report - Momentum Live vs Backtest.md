---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.9
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Research Confidence Report: Does the Corrected Backtest Predict Live Behavior?

**Question:** does the corrected backtest provide a credible expectation for current live paper-trading behavior?

**Short answer, stated plainly rather than hedged: there is no live track record to compare against. Zero trades have ever executed.** This isn't a small-sample problem, it's a no-sample problem, and the two should not be conflated.

## Evidence gathered

`data/paper_state.json`: `cash: 100000.0`, `holdings: {}`, `portfolio_value: 100000.0`, unchanged since `start_date: 2026-06-09`. No `data/paper_trades.csv` file exists at all — not one BUY or SELL has ever been logged.

Root cause, confirmed directly from `trader_logs/2026-07-10.log` (the last Friday — the only rebalance day — before the scheduler fix):

```
REBALANCE DAY -- computing signals...
ERROR: nifty500_universe.csv not found. Run fetch_universe.py first.
Could not compute signals. Check data.
```

Regime that same day: `Nifty 24207 vs MA100 24020 -> BULL`. The market was investable — the strategy wanted to buy — and the working-directory bug (fixed 2026-07-12) silently ate the signal computation instead. Same pattern confirmed on 2026-07-03. Every weekly rebalance window since inception (2026-06-09) has been consumed by this bug, not by the strategy legitimately choosing to hold cash.

2026-07-12 (the fix date) was an NSE holiday — no rebalance triggered. Today, 2026-07-13 (Monday), is the first successful post-fix run: regime reads BULL again (`Nifty 24207 vs MA100 24020`), still zero holdings, because Monday isn't a rebalance day (weekly, Friday-only). The next real opportunity is Friday 2026-07-17 — has not happened yet as of this report.

## Evaluation against the requested dimensions

- **Live return vs. expected trajectory:** undefined. 0.0% P&L reflects zero activity, not zero edge.
- **Trade frequency:** 0 trades in ~5 elapsed calendar weeks, against an intended weekly cadence. Entirely explained by the bug, not by strategy behavior.
- **Position turnover:** undefined, no positions ever held.
- **Regime behavior:** the one real, usable data point. The regime-detection mechanism itself (Nifty vs. MA100, independent of the broken signal-generation half) has read correctly and consistently BULL on three separate checked dates (07-03, 07-10, 07-13), matching what the raw index levels support. This says the regime filter's mechanics work; it says nothing about the momentum-ranking/trade-execution side, which never ran.
- **Drawdown behavior:** undefined, no positions ever held, no drawdown possible.
- **Market environment during the live period:** consistently BULL. If the strategy had been executing, it would have been fully invested (10 stocks), not defensively in cash — so the flat P&L cannot be attributed to correct regime-driven risk avoidance either.
- **Sample size:** zero rebalance events, zero trades. Not "small" — zero.

## Statistical significance

None to discuss. A significance test requires observations. There are none. Stating a confidence interval, a t-stat, or even an informal "looks consistent/inconsistent" judgment on zero trades would be fabricating precision that doesn't exist. The honest statement is: **no conclusion is possible yet, and none is being forced here.**

## Survivorship-bias re-check (per instruction: only answer "does new evidence change the prior assessment")

Nothing in this investigation touches historical universe membership, delisted constituents, or backtest construction — it's entirely about the live paper-trading record, a different axis. **No newly discovered evidence materially changes the prior assessment. The existing Decision Record (`(AI) Decision Record - Point-in-Time Universe.md`) stands unchanged, not revisited beyond this confirmation.**

## Research Confidence Summary

- **Current confidence in the Momentum edge:** unchanged from the last backtest-based assessment (walk-forward degradation 45.6% unfiltered / 47.0% filtered, both marginal against the 50% threshold). This exercise neither adds nor removes evidence about the edge itself — it had no live data to contribute either way.
- **Evidence supporting confidence:** none new from this pass.
- **Evidence reducing confidence about the edge itself:** none new from this pass.
- **A separate, honest operational finding (not about the edge):** the tournament's implicit assumption that Momentum has "~5 weeks of live paper-trading history" is false. It has zero executed weeks. This matters for the 2026-09-09 gate, which requires "3 months documented track record" — that clock has not actually started for Momentum in any meaningful sense, regardless of the calendar date since `start_date`.
- **Unknowns:** everything about live execution — real slippage vs. the assumed cost model, whether live signal computation matches an independent recomputation, live turnover, live drawdown behavior, all of it. Total unknown, not partially known.
- **Behaving consistently with expectations?** Cannot be evaluated. Consistency requires a comparison, and there is nothing yet to compare.
- **Is additional live history required before drawing conclusions?** Yes, unambiguously. At minimum, the first successful rebalance (2026-07-17) needs to occur. Given weekly rebalancing, the PRD's own "3 months documented track record" gate criterion implies roughly 13 rebalance cycles before a meaningful comparison is possible — not the 1 that will exist after this Friday.

## Recommended next research experiment

After Friday 2026-07-17's rebalance executes (the first real opportunity since the fix), independently recompute the top-10 12M-1M momentum ranking for that exact date from the same point-in-time price data `compute_momentum_scores()` used, and confirm the live-logged trades match. This is the first chance to verify signal-generation correctness under live conditions rather than backtest conditions — a distinct question from anything tested so far, since every prior verification (T+1 fill, determinism, walk-forward) ran against historical, cached data, never against a real live signal computation. Not engineering, not a parameter check — a direct evidence check on whether the live code path actually produces what the strategy specification says it should, the first time it gets the chance to run for real.

Waiting for approval before acting on this once Friday's data exists.
