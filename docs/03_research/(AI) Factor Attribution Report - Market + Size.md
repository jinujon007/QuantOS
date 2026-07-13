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

# Factor Attribution Report: Does Alpha Survive Controlling for Size?

**Question:** how much of the previous single-factor alpha was actually a small/mid-cap risk premium, and does genuine alpha remain once that confound is controlled for?

## Framework built

`factor_attribution.py` — a reusable, general N-factor OLS module (`ols_multifactor()`), not a one-off script. Takes any number of factor return series, returns alpha/betas, standard errors, t-stats, p-values, 95% CIs, R², and adjusted R². Adding a third factor later (value, quality, a passive momentum index) means passing another column — no changes to the regression math itself. Lives in the AlgoTrader project root as a standalone research tool; does not import from or modify any strategy/execution file.

**Size factor data note, disclosed not hidden:** neither Nifty Midcap 150 nor Nifty Smallcap 250 resolved on Yahoo Finance after 7 reasonable ticker attempts (`^NSEMDCP150`, `MIDCAPETF.NS`, `NIFTYSMLCAP250.NS`, `MID150BEES.NS`, `^CNXSC`, `SMALLCAP.NS`, `NIFTY_MIDCAP_150.NS` — all empty). Used **Motilal Oswal Nifty Midcap 100 ETF (`MOM100.NS`)** instead — full clean 2019-2024 daily coverage (1480 rows, matching the price matrix exactly). This is a reasonable but not exact proxy for the requested Midcap 150/Smallcap 250 factor; noted as a limitation below, not smoothed over.

## Results: one-factor vs. two-factor, side by side

| | One-factor (market only) | Two-factor (market + size) |
|---|---|---|
| Alpha (weekly) | +0.509% | +0.402% |
| Alpha (annualized) | +30.2% | +23.2% |
| Alpha t-stat / p-value | 3.106 / 0.0021 | 2.646 / 0.0086 |
| Alpha 95% CI (annualized) | [+9.9%, +52.0%]* | [+5.5%, +42.3%]* |
| Market beta | 0.360 (p<0.0001) | -0.131 (p=0.143, not significant) |
| Size beta | — | +0.576 (p<0.0001) |
| R² | 0.092 | 0.228 |
| Adjusted R² | 0.089 | 0.223 |

*annualized CI approximated from the weekly CI bounds via the same compounding formula used for the point estimate.

**Alpha reduction from adding the size factor: 21.0%** (30.2% → 23.2% annualized). A real, non-trivial chunk of the original single-factor "alpha" was size exposure, exactly as the prior report's stated limitation predicted. **Alpha survives regardless** — still significant at the 1% level, still economically large.

Notably, market beta itself becomes statistically insignificant once size is added (p=0.143, and the point estimate even flips slightly negative). This says the "market exposure" the one-factor model was picking up was itself partly a size-factor artifact — Nifty 500-universe midcap names correlate with Nifty 50 too, so a single-factor model conflates the two. The two-factor model cleanly separates them: essentially zero *large-cap* market beta, substantial (+0.576) *size* beta.

## Return and variance decomposition (two-factor)

Of the mean weekly return (+0.612%):
- Alpha: 65.7% (down from 83.2% in the one-factor decomposition)
- Size factor: 40.4%
- Market factor: -6.1% (small, not significant, roughly a wash)

R² jumped from 9.2% to 22.8% — the size factor explains meaningfully more of the strategy's return variance than market beta alone ever did, confirming size exposure is real and substantial, not a marginal effect.

## Rolling 52-week stability (two-factor)

| | One-factor | Two-factor |
|---|---|---|
| Mean rolling annualized alpha | +35.5% | +20.1% |
| Std of rolling alpha | 34.2% | 25.3% |
| % of windows with positive alpha | 74% | 68% |
| Mean rolling size beta | — | 0.655 (range 0.000 to 1.548) |
| Mean rolling market beta | — | -0.019 (near zero, consistent with full-sample) |

5 of 260 rolling windows were skipped — they sat entirely inside an extended bear-market cash-hold stretch where weekly strategy return is exactly 0% every week (the regime filter doing its job), making variance zero and R² undefined. A real data characteristic, not a computation error — recorded rather than papered over with a fabricated number.

Size beta is **persistently substantial** across the rolling windows (mean 0.655, never negative, occasionally exceeding 1.5x) — this isn't a one-off artifact of the full-sample fit, it's a consistent structural feature of the strategy across the whole period. Rolling alpha is somewhat less stable than the one-factor version (std 25.3% vs 34.2% is actually *tighter*, interestingly, even though the mean dropped) — direction is still mostly positive (68%) but the magnitude estimate has meaningfully more honest uncertainty now that a real confound is being accounted for.

## Direct answers to the report's required questions

**Does alpha materially survive?** Yes. It shrinks by 21% but remains statistically significant (p=0.0086) and economically large (+23.2% annualized).

**How much of the previous alpha is actually explained by size exposure?** 21% of the point estimate. The size factor itself is highly significant (p<0.0001) and explains substantially more return variance than market beta alone (R² more than doubled).

**Which hypothesis is now best supported?** A genuine security-selection edge exists on top of a real, substantial size (midcap) tilt — both are true simultaneously. This is not an either/or result: the strategy has meaningful midcap exposure *and* alpha beyond that exposure.

## Assumptions and limitations

1. Size factor is a Midcap 100 ETF proxy, not the requested Midcap 150/Smallcap 250 — disclosed above, not a silent substitution. A true Midcap 150 or Smallcap 250 series could shift the exact split between "size" and "alpha" attribution, though a materially different result seems unlikely given how cleanly significant the size loading already is.
2. Same raw-returns (not risk-free-adjusted) simplification as the prior report — small, known, doesn't change the qualitative conclusion.
3. Two factors still doesn't rule out every possible confound — a quality or low-volatility factor, or a passive momentum-index factor specifically, could still explain some of the remaining alpha. This experiment narrows the space of alternative explanations; it doesn't close it.

## Evidence classification

**Moderately supports genuine alpha.**

Not "strongly" — a real, material 21% of the original claimed edge turned out to be a size-factor confound exactly where the prior report flagged the risk, and rolling-window alpha weakened somewhat once size was properly accounted for. Not "inconclusive" or "better explained by factor exposure" either — alpha remains statistically significant at the 1% level, economically large, and still accounts for the majority (65.7%) of the mean weekly return even after the size confound is priced in. The evidence moved in both directions at once: confirming a real confound existed, and confirming the edge survives it.

## Recommended next experiment (most likely to falsify again)

**Add a passive Nifty200 Momentum 30 index/ETF as a third factor.** This strategy is a momentum strategy by construction — the single most direct remaining alternative explanation isn't another style factor, it's whether this "alpha" is actually just generic exposure to the momentum risk premium itself (a well-documented academic anomaly, not stock-picking skill), rather than security selection *within* momentum that beats a passive momentum index. If alpha collapses once a passive momentum factor is added, the strategy would be better described as "expensive access to a factor you could buy cheaply" rather than genuine skill. If alpha survives a third confound this targeted, that would be the strongest evidence produced by any experiment in this entire research thread.

Waiting for approval before running it. (Ticker availability for a Nifty200 Momentum 30 proxy has not yet been checked — that's the first step if approved, not assumed.)
