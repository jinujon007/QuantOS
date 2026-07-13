---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.75
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Research Evidence Report: Does Momentum Have Genuine Alpha, or Just Beta?

**Question:** after controlling for market exposure, does the Momentum strategy generate statistically meaningful alpha, or does the "edge" collapse into repackaged Nifty 50 beta?

## Method

Weekly regime-filtered strategy returns (the live variant, 2019-2024, using the deterministic, verified backtest) regressed against Nifty 50 weekly returns over the exact same date intervals (not a generic calendar-week resample — each strategy observation's paired market return spans precisely the same two dates). OLS implemented by hand with numpy (no `statsmodels` in this environment) — standard errors, t-stats, and p-values computed from the standard OLS formulas and the exact t-distribution via `scipy.stats.t`, not approximated.

## Full-sample results (n=312 weeks)

| Statistic | Value |
|---|---|
| Alpha (weekly) | +0.509% |
| Alpha (annualized) | +30.2% |
| Beta | 0.360 |
| R² | 0.092 |
| t-stat (alpha) | 3.106 |
| p-value (alpha) | 0.0021 |
| t-stat (beta) | 5.601 |
| p-value (beta) | <0.000001 |

**Alpha is statistically significant at the 1% level.** Beta of 0.36 is low for a long-only equity strategy — expected, since the regime filter holds 100% cash during bear-classified periods, reducing average market correlation. R² of 0.092 means Nifty 50 beta explains only ~9% of the strategy's return *variance* — the other ~91% is idiosyncratic.

## Return decomposition

Of the strategy's mean weekly return (+0.612%):
- **16.8%** attributable to beta × mean market return (+0.103%)
- **83.2%** attributable to alpha (+0.509%)

By this decomposition, market beta is a minor contributor to average return — most of it is the regression's idiosyncratic term.

## Bull vs. bear subsample

| | Bull (n=224) | Bear (n=88) |
|---|---|---|
| Alpha (annualized) | +35.4% | -14.6% |
| Beta | 0.635 | 0.117 |
| t-stat (alpha) | 2.657 | -1.609 |
| p-value (alpha) | 0.0084 (significant) | 0.111 (not significant) |

Bull-period alpha remains significant. Bear-period alpha is negative and *not* statistically significant.

**This bear-period number needs a careful reading, not a face-value one.** During regime-classified bear weeks, the strategy is sitting in ~100% cash by design — it isn't making bad stock picks, it's holding nothing. A near-zero strategy return regressed against Nifty 50's often-negative bear-period returns, with beta correctly estimated near zero (0.117, matching "mostly in cash"), can produce a slightly negative intercept as a regression artifact rather than evidence of stock-picking failure. Combined with low power (n=88, t=-1.6), this isn't evidence of a *problem* during bear markets — it's evidence that "alpha" as a construct doesn't mean the same thing when the strategy isn't holding any stocks to have skill about.

## Temporal stability (rolling 52-week regression)

Annualized alpha across rolling 52-week windows: min -12.6%, max +102.2%, mean +35.5%, std 34.2%. **74% of rolling windows show positive alpha.**

Classification: **persistent in direction, not stable in magnitude.** This isn't "episodic" (a brief spike that vanishes) — three-quarters of all rolling windows across the 6-year sample stay positive. But it isn't "stable" either — a standard deviation nearly as large as the mean means the *size* of the edge varies substantially by period, and any given 52-week window could plausibly show a negative result even if the long-run average is real.

## Statistical interpretation

Alpha is significant at the full-sample level (p=0.0021) and the bull-subsample level (p=0.0084), using a standard two-tailed t-test against the null of zero alpha. This is a real, non-trivial statistical result — it isn't a rounding-error significance level, and it holds up under the bull-market split where most of the sample's activity actually occurs (224 of 312 weeks).

## Practical interpretation

The strategy is not simply a leveraged or unlevered bet on Nifty 50 — beta of 0.36 is too low and R² of 0.092 is too small for that story to hold. Most of the average return comes from something the single-factor Nifty 50 model doesn't explain.

**What this does NOT yet establish: that the unexplained return is genuine security-selection skill specifically**, as opposed to a different, non-skill-based factor this single-factor model can't see. This is the most important limitation of this experiment.

## Assumptions and limitations

1. **Raw returns, not excess-of-risk-free-rate.** A textbook CAPM regression subtracts the risk-free rate from both strategy and market returns before regressing. This analysis used raw weekly returns. India's risk-free rate (~6-7% annualized, ~0.12%/week) would shave a small, roughly-known amount off both sides — given alpha here is +30% annualized, this wouldn't change the qualitative conclusion, but it means the reported alpha is very slightly overstated relative to a formally correct CAPM figure. Not corrected for here; flagged, not silently absorbed into the number.

2. **Single-factor model, one real and significant confound not ruled out: size/style premium.** The strategy trades the Nifty 500 universe (including mid/small-cap names); the benchmark is Nifty 50 (large-cap only). Momentum strategies are well known in the broader literature to correlate with small-cap exposure. A stock-picking-blind small-cap tilt would show up as "alpha" in this single-factor model, because Nifty 50 beta can't capture size-factor returns at all. **This experiment cannot distinguish "genuine security-selection skill" from "small/mid-cap risk premium."** That distinction requires a second factor (a small or mid-cap index) in the regression, which this experiment didn't include.

3. **Weekly alignment uses `asof`-matched Nifty 50 prices to the strategy's exact (T+1-shifted, per the Stage-1 fix) rebalance dates**, not a generic calendar-week resample — internally consistent, but a different convention than some standard benchmarking approaches use.

4. **Regime classification for the bull/bear split uses the strategy's own regime filter**, not an independent market-condition definition — appropriate for explaining the strategy's own behavior, but means the "bear" bucket is defined by the same mechanism being evaluated.

## Is the hypothesis of genuine alpha supported, contradicted, or inconclusive?

**Partially supported, with an important, explicitly unresolved gap — not a clean "yes."**

Supported: the strategy generates statistically significant excess return beyond simple Nifty 50 market exposure (low beta, low R², significant alpha, majority of average return unexplained by beta, positive in 74% of rolling windows). The "this is just leveraged market beta" hypothesis is contradicted by this evidence — beta is too low and R² too small to sustain that story.

Not yet resolved: whether that excess return is genuine stock-picking skill or a small/mid-cap style premium this single-factor test cannot see. Calling this "genuine security-selection edge, confirmed" would overclaim what a one-factor regression against a large-cap-only index can actually show.

## Recommended next research experiment

**Add a second factor: regress strategy returns against both Nifty 50 (large-cap market beta) and a small/mid-cap index (Nifty Smallcap 250 or Nifty Midcap 150) simultaneously, and test whether alpha survives once both betas are controlled for.** This directly targets the one confound identified above as unresolved. If alpha collapses toward zero once size exposure is accounted for, the "edge" would be better described as a small-cap risk premium than a genuine security-selection skill — a materially different (and less differentiated) claim about what this strategy actually is. If alpha survives a two-factor model, that would be substantially stronger evidence for genuine skill than anything produced so far, since it would have survived the most obvious available confound.

Waiting for approval before running it.
