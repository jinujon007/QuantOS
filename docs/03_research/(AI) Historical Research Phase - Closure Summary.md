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

# Historical Research Phase — Closure Summary

**Historical research on Momentum is now frozen.** No further retrospective slicing, optimization, or historical-data experiments unless a newly discovered defect or contradiction requires it. This note is the entry point for anyone (including a future session) picking this thread back up.

## What this phase established, in order

1. **Engineering foundation (Stage 1):** look-ahead bias fixed (T+1 fill), transaction-cost model unified, scheduler made to fail loudly, Quality Factor's live-vs-backtest confusion corrected, SEBI checklist handed off.
2. **Determinism:** regime-index caching + a Python hash-seed ordering bug both fixed and proven via 3 consecutive byte-identical production runs. Same bug class found and fixed across all 4 tournament strategies; scheduler's silent-failure gap (stale exit code) found and fixed; all 4 strategies' silent exception handlers converted to structured, scheduler-visible logging.
3. **Implementation correctness:** independently re-derived (different code path, not a re-run) regime and momentum-ranking logic against 3 historical dates including a deliberately adversarial regime-flip boundary — exact match, zero deviation.
4. **Statistical evidence chain, each step an honest attempt to falsify the last:**
   - One-factor (market) CAPM: alpha significant (+30.2% ann., p=0.002). Rules out "just leveraged market beta."
   - Two-factor (+size): alpha survives but shrinks 21% (+23.2% ann., p=0.009). Confirms a real size confound existed, alpha survives it anyway.
   - Three factors incl. momentum, restricted to the only fair overlap window (2021-2024): **alpha loses significance even before momentum is added** (p=0.23). The dominant open finding: the earlier significant result depends substantially on 2019-2021 (COVID crash + recovery) being in the sample.
   - Regime-based partition (not calendar-based): 54% of total return concentrated in TRENDING_BULL weeks (26% of the sample) — real concentration, but not total dependence; SIDEWAYS (62% of weeks, the most common regime) still contributes 32% with a positive Sharpe. Cross-checked against the period-dependency finding: RECOVERY is genuinely COVID-concentrated (87% of its weeks in 2019-2020), but TRENDING_BULL — the dominant contributor — recurs every year through 2024. The two findings partially converge, not fully.

## Current honest state of confidence

Momentum has a real, non-trivial statistical signal in the full 6-year sample that survives two independent falsification attempts (market beta, size exposure). It has NOT survived a third test cleanly (fair-window significance with 2019-2021 excluded) — the result there is a loss of statistical power on a shorter window, not a clean "alpha is zero," and regime analysis shows the dominant return driver (trending-bull episodes) keeps recurring past 2021, so "it was all COVID" is not the full explanation either. This is genuinely mixed evidence, not a clean verdict either way, and it should be represented as such going forward — not rounded up to "edge confirmed" or down to "edge disproven."

One flagged, not-yet-tested question carried into the next phase whenever historical work resumes: whether SIDEWAYS regime's positive Sharpe (0.84 on a 26.3% win rate) is broad-based or outlier-driven.

## What does NOT get revisited without new evidence

Every accepted decision from this phase (survivorship-bias limitation, size-factor proxy choice, momentum-factor proxy choice, regime thresholds, the T+1 fill design, the cost model) stands as-is. A future session should not re-litigate these without a specific, new, verified reason.
