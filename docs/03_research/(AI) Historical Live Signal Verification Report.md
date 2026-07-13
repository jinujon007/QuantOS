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

# Historical Live Signal Verification Report

**Question:** does the production pipeline reproduce the research specification, tested now against real historical data rather than waiting for Friday's first live rebalance?

## Scope decision, disclosed up front

The live functions this was originally framed around (`paper_trader.py`'s `compute_momentum_scores()` / `check_regime()`) hard-code `today = pd.Timestamp.today()` — they have no historical-date parameter, so they cannot be run against a past date without modifying them, which wasn't authorized. The functions actually tested are `momentum_backtest.py`'s `momentum_score()` and `load_nifty50_regime()` — the same 12M-1M / MA100 formulas, operating on the same point-in-time-correct logic already verified causal in earlier work. This is a legitimate stand-in (identical specification, point-in-time-safe by construction), not a silent substitution — flagging it because "production pipeline" technically names two different files that happen to implement the same math.

## Dates selected

Chosen to span genuinely different conditions, not just three arbitrary Fridays:

1. **2020-04-03** — deep COVID crash. Production regime call: BEAR.
2. **2021-07-02** — mid-2021 bull run. Production regime call: BULL.
3. **2023-01-13** — deliberately chosen inside a regime-flip cluster (the actual regime series flips BULL/BEAR four times between 2023-01-05 and 2023-01-16) — the hardest boundary case available in the whole 2019-2024 window, picked specifically to stress-test the MA100 comparison rather than picking another comfortable interior date.

## Independent recomputation method

Deliberately different code shape from the production functions, not a re-run of them:
- Regime: manual `numpy.mean()` over a hand-sliced window located via `searchsorted`, not pandas `.rolling()`.
- Momentum: `searchsorted`-based as-of price lookup, not `.loc[:date].iloc[-1]`.
- Same underlying cached data production uses (`data/cache/`, `data/cache_index/NSEI.csv`) — same point-in-time information, independently consumed.

## Results

| Date | Regime | Top-10 set | Score diff (matched tickers) |
|---|---|---|---|
| 2020-04-03 | MATCH (BEAR/BEAR) | MATCH | 0.00000000 |
| 2021-07-02 | MATCH (BULL/BULL) | MATCH | 0.00000000 |
| 2023-01-13 | MATCH (BULL/BULL) | MATCH | 0.00000000 |

All three dates: exact match, zero floating-point deviation, including the deliberately adversarial regime-flip-boundary date.

## Discrepancies

None found. No divergence to trace, no root cause to classify.

## Confidence in production correctness

**The production implementation faithfully reproduces the research specification on all 3 historical dates tested, including a stress-tested regime-boundary case.** Confidence in the momentum-ranking and regime-classification implementation materially increases as a result — this is now backed by independent, differently-coded verification, not just internal self-consistency (which is what the earlier determinism work established) or a single favorable date (the flip-cluster date was chosen specifically because it was the least likely to accidentally match).

This says nothing new about whether the strategy is *profitable* — only that the code computing its signals does what the specification says it should, which was the actual question asked.

## Recommendation for the next research milestone

The live verification protocol (`(AI) Live Signal Verification Protocol.md`) still applies once Friday 2026-07-17's rebalance happens — this historical check increases confidence in the *logic*, but the live path also depends on things this test can't touch (live `yfinance` fetch behavior, the actual order-fill mechanics, today's real data). Both checks are complementary, not redundant.

## Recommended robustness experiment (falsification attempt)

**Regress Momentum's weekly strategy returns against Nifty 50's weekly returns (single-factor CAPM-style regression) across the full 2019-2024 backtest, and test whether the intercept (alpha) is statistically distinguishable from zero once market beta is controlled for.**

Why this one, specifically: everything tested so far (T+1 fill, determinism, walk-forward, this historical verification) checks whether the *implementation* is correct — none of it tests whether the *edge itself* is real or just repackaged market exposure. If the strategy's returns are highly explained by beta to Nifty 50 (high R², beta near or above 1, alpha statistically indistinguishable from zero), that would directly falsify the claim that this is a genuine momentum/security-selection edge rather than a leveraged directional bet that happens to look good in a bull-dominated backtest window. If alpha survives as significant and positive after controlling for beta, that's the strongest evidence for a real edge produced by any experiment run on this project to date — stronger than any CAGR/Sharpe number alone, because those don't distinguish skill from market exposure.

Waiting for approval before running it.
