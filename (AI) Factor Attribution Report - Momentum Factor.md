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

# Factor Attribution Report: Does Alpha Survive Controlling for Passive Momentum Exposure?

**Question:** does the strategy generate alpha beyond what an investor could obtain by simply buying a passive momentum index — and does the earlier "moderately supports genuine alpha" verdict hold up under the sharpest remaining test?

**This is the most important finding of the whole research thread so far, and it isn't the one the framing of this task expected.** Not "momentum factor explains away alpha" — instead, the fair-comparison sample reveals **alpha was already not statistically significant before the momentum factor was even added**, once the test window is restricted to where all data actually overlaps. That's a materially different, more consequential finding than a clean "controlled for momentum, alpha survives/disappears" result, and it is reported plainly rather than reframed to fit the expected shape of the experiment.

## 1-3. Momentum proxy survey, evaluation, and selection

| Candidate | Availability | Historical coverage | Investability | Suitability | Limitation |
|---|---|---|---|---|---|
| Nifty200 Momentum 30 (index itself) | No direct index ticker resolves on Yahoo Finance | N/A | N/A (not directly investable, index only) | N/A | Index-only tickers (`^NIFTY200MOM30`, `NIFTY200MOM30.NS`) return empty |
| HDFC Nifty200 Momentum 30 ETF (`HDFCMOMENT.NS`) | **Real, resolves** | 2023-10-17 to present (~295 days, ~60 weeks) | Yes — exchange-traded, intraday liquid | High conceptually, but too short | Inception is recent; can't support a regression against the full 2019-2024 backtest window |
| UTI Nifty200 Momentum 30 Index Fund, Direct Growth (`0P0001LMOA.BO`) | **Real, resolves** | 2021-03-10 to present (~935 daily NAV points, ~198 overlapping weeks) | Yes — open-end index fund, direct plan (lowest-cost route to this benchmark), daily NAV, retail-accessible | **Selected** | Mutual fund NAV, not exchange-traded intraday; still doesn't cover 2019-2021 |
| Nifty500 Momentum 50 (index or fund) | No resolvable ticker found | — | — | — | Searched, nothing found — not a silent omission |
| Other momentum/quality ETFs (Motilal Oswal, ICICI-branded) | No resolvable ticker found | — | — | — | Same |

**Selected: UTI Nifty200 Momentum 30 Index Fund, Direct Growth.** Chosen for the longest available history among real candidates (essential — a 60-week sample would barely support a regression at all) and because it directly tracks Nifty200 Momentum 30, the primary candidate the task named. Not selected because it looked favorable to the strategy — it was the only candidate with enough history to be usable at all. The ETF (`HDFCMOMENT.NS`) was rejected specifically for insufficient history, not for any result-related reason.

## Framework extension

`factor_attribution.py`'s `ols_multifactor()` needed no changes — already N-factor generic. Added: a third factor series, and an **overlap-window methodology** — since the momentum factor's history (2021-03 onward) doesn't reach back to 2019, every comparison involving it recomputes the *two-factor* model on the identical restricted window before comparing to the *four-factor* model on that same window. This avoids confounding "added a factor" with "shrank the sample," which naively comparing the four-factor model against the earlier full-sample two-factor result would have done.

## Results

**Full sample (2019-2024, n=312) — unchanged from the prior report, shown for continuity:**
- One-factor alpha: +30.2% annualized, p=0.0021
- Two-factor (market+size) alpha: +23.2% annualized, p=0.0086

**Overlap sample (2021-03-22 to 2024-12-30, n=198) — the fair comparison:**

| | Two-factor (mkt+size) | Four-factor (mkt+size+mom) |
|---|---|---|
| Alpha (weekly) | +0.235% | +0.227% |
| Alpha (annualized) | +12.99% | +12.49% |
| t-stat (alpha) | 1.196 | 1.196 |
| p-value (alpha) | **0.2331 (not significant)** | **0.2332 (not significant)** |
| Market beta | +0.037 (p=0.787, n.s.) | -0.369 (p=0.027, significant) |
| Size beta | +0.727 (p<0.0001) | +0.379 (p=0.0049) |
| Momentum beta | — | +0.611 (p=0.0001) |
| R² | 0.327 | 0.379 |
| Adjusted R² | 0.321 | 0.369 |

Alpha reduction from adding the momentum factor: **3.7%** — small, because there wasn't much statistically-distinguishable-from-zero alpha left to reduce once the sample was restricted fairly. **Incremental R² from the momentum factor: +0.0515** — the momentum factor itself is real and substantial (β=0.611, p=0.0001), it just doesn't have much more alpha left to eat into on this window.

## Rolling 52-week stability (four-factor, overlap sample, n=198)

Rolling annualized alpha: mean +12.8%, std 18.9% (std larger than mean), positive in 64% of windows (down from 68% in the two-factor full-sample rolling check, 74% in the one-factor). Rolling momentum beta: mean 0.384, std 0.443 — meaningfully volatile, sometimes near zero, sometimes substantial. The trend across every successive factor addition in this research thread has been the same direction: alpha's point estimate shrinks, its statistical confidence weakens, and rolling stability degrades a bit further each time.

## What this actually means — read carefully, don't force the expected conclusion

The full 2019-2024 sample showed significant alpha even after two factors. The overlap sample (2021-2024) — the *only* window where a fair three-factor comparison is possible — shows alpha that is **not statistically significant even in the two-factor baseline, before momentum is added at all.** This means the earlier significant full-sample result was substantially dependent on the 2019-2021 period specifically — which includes the COVID crash and the sharp V-shaped recovery that followed it. That period is unusual by any definition: a systemic, largely unforecastable shock followed by an unusually strong, broad-based rally. A strategy's apparent edge concentrated in that window is a materially weaker claim than an edge that holds up in more ordinary market conditions.

This is not the same finding as "the momentum factor explains the alpha away" (which is what this experiment was designed to test and would have been a clean falsification). It's a different, arguably more important finding: **the sample-period dependency itself is now the dominant open question**, more so than any single additional factor.

## Assumptions and limitations

1. The overlap window (2021-2024) is itself not a neutral, "normal markets" sample — it includes 2022's rate-hike volatility and a strong 2023-2024 rally, so this isn't simply "COVID period vs. everything else," it's a genuinely different, shorter slice of history with its own character.
2. n=198 weekly observations is a real, meaningful reduction in statistical power versus n=312 — non-significance here is consistent with either "no real edge in this period" or "a real, smaller edge that this sample is underpowered to detect at conventional significance." Both are legitimate readings; this experiment cannot distinguish them.
3. Momentum factor proxy is a mutual fund NAV (subject to fund-level cash drag, expense ratio, tracking error versus the index it targets) rather than the index itself — a small, known source of noise, not corrected for.
4. Same raw-returns (not risk-free-adjusted) simplification carried from prior reports.

## Evidence classification

**Inconclusive.**

Not "strongly supports" or "moderately supports" — alpha is not statistically significant on the only window where a fair comparison is possible. Not "better explained by passive momentum exposure" either — that would require alpha to have collapsed *because of* adding the momentum factor, and it didn't; it was already statistically indistinguishable from zero on this window before momentum was added. The honest reading is that this experiment's real contribution isn't "momentum explains it" — it's revealing that the strategy's statistical significance to date has been carried substantially by a period (2019-2021) that a fair three-factor test can't include, and that gap is the thing to resolve next, not another factor.

## Recommended next experiment (before considering real capital deployment)

**Test whether alpha holds on the 2022-2024 sub-period alone** — a window that excludes both the COVID-crash/recovery anomaly (2019-2021) *and* isn't artificially shortened by the momentum factor's data availability (this can be run as a one- or two-factor model over 2022-2024, without needing the momentum factor at all, since that's not the open question anymore). If alpha is significant on 2022-2024 specifically — a period with no dominant systemic shock, just ordinary bull/bear/sideways conditions — that would be the strongest evidence yet that the edge isn't just a COVID-era artifact. If it isn't significant there either, that would be a much more direct and honest falsification than anything found via factor decomposition, and the single most important thing to know before any real capital gets deployed.

Waiting for approval before running it.
