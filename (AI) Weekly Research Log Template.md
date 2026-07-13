---
type: review
date: YYYY-MM-DD
area: self
project: AlgoTrader
status: active
---

# Weekly Research Log — Momentum Prospective Validation — [Friday date]

Prospective Validation Phase. Purpose: measure whether historical expectations survive contact with future data. Not a performance-improvement exercise.

**Frozen until 13 weekly rebalances (~3 months) accumulate:** alpha model, ranking, universe, all parameters, stop-loss logic, regime filter, execution rules. Permitted without restarting the clock: verified bug fixes and operational/infra fixes that cannot alter historical or future signals. Any frozen-list change restarts the prospective clock to zero for this strategy version — see `CONTEXT.md`'s Prospective Validation Rule.

## 1. Live signal verification

Per `(AI) Live Signal Verification Protocol.md`: independently recompute regime + momentum ranking for this date from the same point-in-time data (different code path than `compute_momentum_scores()`/`check_regime()`), compare against what production actually generated.

- Regime: production = ___, independent = ___, match: Y/N
- Top-10 set match: Y/N (list any discrepancy)
- Score deviation (if any): ___
- Verdict: MATCH / MISMATCH (if mismatch — classify: implementation defect / data discrepancy / expected execution behavior / research assumption, per the protocol)

## 2. Trades recorded

From `trader_logs/YYYY-MM-DD.log` and `data/paper_trades.csv` (rows dated this week):

| Action | Ticker | Price | Shares | Reason |
|---|---|---|---|---|

## 3. Benchmark performance

Nifty 50 return this week: ___%
Strategy return this week: ___%

## 4. Realized slippage

Backtest assumes fill at T+1 close (Stage 1 fix). Live paper trading also fills at T+1 close via `fetch_current_prices()` — so "slippage" here means: does the live fill price match what an independent same-day price check would show, not a backtest-vs-live cost-model gap (already reconciled in Stage 1). Note any anomaly.

## 5. Turnover

Positions entered: ___  Positions exited: ___  (out of 10 target)

## 6. Drawdown

Current portfolio value vs. peak since `start_date`: ___%

## 7. Deviations from expected behavior

Anything that didn't match what the corrected backtest/walk-forward/factor work would predict for a week like this one (regime, ranking, turnover, or return magnitude). If nothing deviated, say so explicitly — "no deviation" is itself a data point, not a null result to skip.

## Running tally (update each week)

| Week | Rebalanced? | Regime | Verification match? | Strategy return | Nifty 50 return | Notes |
|---|---|---|---|---|---|---|
| 2026-07-17 | | | | | | first live rebalance since scheduler fix |

## Next log

Due the following Friday. If a Friday is skipped (holiday, no signal change), log that explicitly rather than leaving a silent gap — an unexplained missing week is exactly the kind of thing Stage 1 was built to catch.
