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

# Walk-Forward Extension: Does the Regime-Filtered Momentum Strategy Hold Out-of-Sample?

**Question:** does the regime-filtered Momentum strategy (the one actually running in paper trading) retain its performance when evaluated only on unseen data — or has walk-forward only ever validated a strategy variant nobody trades?

## 1. Audit finding

`walk_forward_test()` called `run_backtest(p_train, regime=None)` and `run_backtest(p_test, regime=None)` unconditionally. The `regime` Series was already computed in `__main__` (covering the full 2019-2024 range) but never passed into the function. Every walk-forward result on record validated the unfiltered baseline only — a strategy nobody has ever paper-traded. The live strategy (`paper_trader.py`, the tournament entry) has never had an out-of-sample check run against it, in the ~5 weeks since it went live.

## 2. Minimal fix

- `walk_forward_test(prices, regime=None)` — new optional parameter, defaults to `None` so any other caller keeps existing (unfiltered-only) behavior.
- Existing baseline computation left completely unchanged.
- Added a parallel regime-filtered computation, using the exact same train/test split, same `run_backtest()` function, same degradation formula — reported side by side via a small shared `report()` closure (extracted only to avoid duplicating the same 6 lines twice, not a new abstraction over any real complexity).
- Call site: `walk_forward_test(prices, regime=regime)` — the already-computed global `regime` Series now threaded through.

No changes to `run_backtest()`, `momentum_score()`, any strategy parameter, or any alpha logic.

## 3. Automated validation added

`test_walkforward_causal_and_deterministic()` — real cached data, no network needed once caches are populated. Proves two things about the train-window computation exactly as `walk_forward_test()` actually uses it (sliced `p_train`, never the full frame):

1. **Deterministic:** identical repeated calls produce byte-identical equity curves.
2. **Causal:** the train-window equity curve's last recorded date never exceeds the train window's end — no fill leaks into the test window.

**A real boundary nuance surfaced while writing this check, not fixed (out of scope):** if a future caller passed the *full* unsliced price history instead of a properly-sliced `p_train`, the T+1 fill mechanism (Stage 1's look-ahead fix) could execute the train window's final trade one trading day into the test window, because a "next available day" would exist in the wider frame. `walk_forward_test()` doesn't do this — it always slices — so this doesn't affect current results. Recorded as a fragility to watch if `walk_forward_test()` is ever refactored, not fixed now (fixing it means touching `run_backtest()`'s fill logic, out of this task's scope).

## 4. Comparison — the actual evidence

Same 2019-2021 train / 2022-2024 test split for both:

| | In-sample CAGR | Out-sample CAGR | Degradation |
|---|---|---|---|
| Unfiltered baseline (existing) | 74.1% | 40.3% | 45.6% |
| **Regime-filtered (live strategy)** | 49.6% | 26.3% | **47.0%** |

Both "pass" the pre-existing 50%-degradation threshold. Neither is close to comfortably passing — both sit within 5 points of the line.

## 5. Conclusion — evidence only, no editorializing beyond what the numbers show

**Does confidence in the strategy increase, decrease, or remain unchanged?**
Mixed, and the two halves of that answer shouldn't be collapsed into one:

- Confidence in the **validation process** increases — before this fix, there was zero out-of-sample evidence for the strategy actually being paper-traded. Now there is one real data point.
- Confidence in the **regime filter specifically improving robustness** does not increase. If anything, this single metric points the other way (47.0% vs 45.6% degradation) — but the gap is small enough (1.4 points, a 2-window comparison) that it isn't strong evidence of harm either. Call it a wash, not a win.

**Is the hypothesis ("the regime filter improves out-of-sample robustness") supported, contradicted, or inconclusive?**
**Inconclusive, leaning unsupported.** The CAGR-degradation metric doesn't favor the regime filter. But this metric was never designed to test what the regime filter is actually for — drawdown protection via bear-market cash exits — and no walk-forward comparison of MaxDD exists (before or after this fix) to test that directly. The honest statement is: this experiment answers a narrower question than the one that actually matters for the regime filter's design purpose, and answering the real question (does the regime filter reduce out-of-sample drawdown) would need a MaxDD/Sharpe walk-forward comparison, which doesn't exist yet.

## 6. What this doesn't settle

- Whether the regime filter reduces out-of-sample *drawdown* (its actual design goal) — untested here.
- Whether a 2-window (1 train, 1 test) split is enough to trust either degradation number — it isn't, statistically; this is evidence, not proof, in either direction.
