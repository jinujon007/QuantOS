---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.8
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Regime Stability Report: Is the Edge Concentrated in Favorable Regimes?

**Question:** does the apparent alpha hold across genuinely different market environments, or is it concentrated in a small number of favorable regimes — tested by economically meaningful regime classification, not another calendar split.

## Regime definitions (pre-specified before running the analysis, not fit to the result)

Computed from trailing Nifty 50 price action only, causal (each week classified using only data available at the start of that week):

- **BEAR:** drawdown from trailing 252-day peak ≤ -15%, OR trailing 60-day trend ≤ -8%
- **RECOVERY:** drawdown ≤ -8% (still meaningfully below peak) but trailing 60-day trend > 0
- **TRENDING_BULL:** trailing 60-day trend > +8%, drawdown > -8% (near highs, healthy uptrend)
- **SIDEWAYS:** everything else (low trend, shallow drawdown)
- **HIGH_VOL / LOW_VOL** (secondary, independent cross-cut): split at the full-sample median of trailing 60-day annualized realized volatility

## Per-regime performance (n=312 weeks total)

| Regime | n | Total compound return | Annualized (implied) | Sharpe | Max DD | Win rate |
|---|---|---|---|---|---|---|
| TRENDING_BULL | 80 (25.6%) | +159.5% | +91.8% | 2.56 | -13.7% | 57.5% |
| RECOVERY | 15 (4.8%) | +27.3% | +136.7% | 3.57 | -2.6% | 40.0% |
| SIDEWAYS | 194 (62.2%) | +76.1% | +18.8% | 0.84 | -21.9% | 26.3% |
| BEAR | 23 (7.4%) | +0.4% | +1.0% | 0.18 | -2.4% | 4.3% |

Whole-sample total compound return: +483.8%.

## Return contribution by regime

| Regime | Share of total log-return |
|---|---|
| TRENDING_BULL | 54.0% |
| SIDEWAYS | 32.1% |
| RECOVERY | 13.7% |
| BEAR | 0.2% |

**TRENDING_BULL — 26% of all weeks — generates 54% of total return.** That's real concentration, more than double its proportional share. But it is not the whole story: SIDEWAYS, the *most common* regime (62% of all weeks), still contributes a meaningful 32% with a positive (if modest) Sharpe of 0.84. BEAR correctly produces near-zero return (0.2% of total, Sharpe 0.18) — the regime filter is doing exactly what it's designed to do: not lose money in bear markets, not make money there either, since the strategy is sitting in cash.

## Statistical caveat on the per-regime alpha figures — read before trusting them

Per-regime alpha estimates all came back with p-values above 0.9 (e.g., TRENDING_BULL: +75.3% annualized, t=0.06, p=0.955). **These numbers are not evidence of anything and should not be quoted as if they were.** Splitting a sample by a variable correlated with the regressor (market return) mechanically restricts the regressor's variance *within* each group — inside a TRENDING_BULL bucket, Nifty's own weekly returns are almost by definition consistently positive with little spread, which inflates the standard error of any beta/alpha estimate on that subsample to the point of uselessness. This is a known statistical artifact (range restriction), not a finding about the strategy. The reliable evidence in this report is the CAGR/Sharpe/contribution figures, not the per-regime alpha column.

## Cross-check against the prior period-dependency finding

The previous experiment found alpha loses statistical significance when the sample is restricted to 2021-2024 (excluding 2019-2021, the COVID crash and V-shaped recovery). Checking whether that finding and this one describe the same underlying phenomenon, or two different things:

- **RECOVERY regime weeks: 13 of 15 (87%) occurred in 2019-2020.** This bucket genuinely is a COVID-recovery artifact — confirms and partially explains the earlier period-dependency finding.
- **TRENDING_BULL regime weeks, by year: 2019=11, 2020=11, 2021=27, 2022=6, 2023=8, 2024=17.** This is the *dominant* return contributor (54%), and it recurs throughout the entire sample, including 14 weeks in 2022-2023 (the heart of the "weak alpha" window) and 17 in 2024 alone. **TRENDING_BULL is not a COVID-only phenomenon.**

So the two findings partially converge, not fully. RECOVERY's concentration in 2019-2020 helps explain some of the earlier period-dependency result. But the largest single contributor to total return (TRENDING_BULL) keeps recurring well past 2021, which means the earlier finding of weak significance in 2021-2024 can't be fully attributed to "the favorable regime disappeared" — trending-bull episodes were still happening in that window. The weaker earlier significance is more likely a combination of smaller sample size (n=198 vs 312, real loss of statistical power) and the specific magnitude/timing of episodes in that shorter window, not the complete absence of the regime that drives most of the return.

## Which regime dominates?

No single regime accounts for "almost all" of the return — that would require something in the 80-90%+ range. TRENDING_BULL's 54% is a real, meaningful concentration (more than half the return from a quarter of the weeks), but SIDEWAYS' 32% from the plurality of the sample is not a rounding error — it's the second-largest contributor and the most common regime, with a still-positive (if unremarkable) Sharpe.

One thing worth flagging as a genuine open question, not resolved here: SIDEWAYS has a **26.3% win rate but a positive 0.84 Sharpe** — a classic signature of a right-skewed, few-large-winners-carry-many-small-losers return pattern (consistent with the strategy's 8% stop-loss capping downside per position while momentum winners run). Whether that skew is broad-based or driven by a handful of outlier weeks is not tested here.

## Classification

**Moderately regime-dependent.**

Not "robust across regimes" — the concentration in TRENDING_BULL is real and material, more than double its proportional share of return. Not "strongly regime-dependent" either — that would require near-total dependence on one favorable environment, and this data shows meaningful, positive contribution from the most common regime (SIDEWAYS) too, plus correct, non-value-destroying behavior in BEAR. Not "inconclusive" — the evidence is clear enough to support a specific, bounded claim (moderate concentration, not total dependence), even though the per-regime alpha statistics themselves are uninformative.

## Recommended next research question (before considering live capital)

**Is SIDEWAYS regime's positive Sharpe (0.84, on a 26.3% win rate) broad-based, or carried by a small number of outlier weeks?** This follows directly from what this experiment surfaced, not a generic next check. A low win rate with a positive Sharpe is exactly the profile that can look robust in aggregate while actually depending on a handful of large winning weeks — if removing the single best few weeks in the SIDEWAYS bucket collapses its Sharpe toward zero or negative, that would mean the "moderate" regime-dependence finding above understates the real concentration (adding a within-regime outlier dependency on top of the across-regime one already found). This is the most direct, evidence-driven next falsification attempt, more targeted than another factor or period test.

Waiting for approval before running it.
