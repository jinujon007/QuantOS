---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.85
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Determinism Audit Report — All Tournament Strategies

Scope: eliminate the "iteration-order non-determinism" bug class (Python randomizes string-hash seed per process, so raw `set` iteration order differs run to run) from every strategy competing at the 2026-09-09 tournament gate. Momentum (`AlgoTrader/`) already fixed in the prior task; this covers the 3 sibling-repo strategies.

## Files audited

- `My_terminal/trading_backtests/quality_paper_trader.py`
- `My_terminal/trading_backtests/factor_timing_paper_trader.py`
- `My_terminal/trading_backtests/weekly_options_paper_trader.py`

## Issues found

**factor_timing_paper_trader.py — severe.** `get_target_portfolio()`'s `LOWVOL_MOM` branch: `combined = list(top_mom & low_vol)[:TOP_N_STOCKS]`, with a fallback `list(top_mom)[:TOP_N_STOCKS]`. Both truncate a `set` after casting away order. Unlike the momentum-backtest bug (which affected fill order under a cash constraint), this affects **which stocks get selected into the portfolio** — whenever the intersection has more than 15 members, a different random 15 get chosen each process run. This is the LOWVOL_MOM regime's actual stock-picking logic, and LOWVOL_MOM is the strategy's currently-active regime (confirmed live: `--status` shows `Regime: LOWVOL_MOM`).

**quality_paper_trader.py — minor.** `run_rebalance()`'s sell loop: `for t in to_sell:` iterates a raw set. No effect on final cash/holdings (set-difference into cash addition is commutative regardless of order) — only affects log/print order. Fixed for consistency; documented as lower severity in both the code comment and here, not oversold as equivalent to the factor-timing finding.

**weekly_options_paper_trader.py — none found.** Single-instrument (Nifty index options), settled sequentially via a plain list built by a chronological `while` loop, no set-based ranking or selection anywhere. `EVENT_SET` is a set but only ever used for membership testing (`in`), which is order-independent by definition — safe.

**Already correct, no fix needed:** both `quality_paper_trader.py`'s buy loop (`for t in sorted(to_buy):`) and `factor_timing_paper_trader.py`'s sell/buy loops in `run_rebalance()` (`for t in sorted(to_sell):` / `for t in sorted(to_buy):`) were already using `sorted()` — whoever wrote those got it right the first time.

## Issues fixed

1. `factor_timing_paper_trader.py::get_target_portfolio()` — `top_mom` kept as the already momentum-ranked `pd.Index` (not cast to a `set`); combined via `[t for t in top_mom_ranked if t in low_vol][:TOP_N_STOCKS]`, preserving the original "top momentum among the low-vol set" selection criteria — same criteria, deterministic order. Fallback similarly changed to slice the ranked index directly.
2. `quality_paper_trader.py::run_rebalance()` — sell loop now `for t in sorted(to_sell):`.

No changes to alpha logic, no new abstractions, no architecture changes. Both fixes are the minimum edit that removes set-order dependency while preserving exactly what each function already claimed to select.

## Self-check results

Both self-checks force **different `PYTHONHASHSEED` values across separate subprocess invocations** — same-process repeated calls share one hash seed and would pass even with the bug present, so this is the only test design that actually exercises the failure mode.

- `factor_timing_paper_trader.py --selftest`: `[PASS] test_lowvol_mom_selection_deterministic (15 stocks, identical across hash seeds 111/222)` — synthetic 30-ticker universe engineered so the intersection exceeds `TOP_N_STOCKS`, guaranteeing truncation would have triggered the bug if still present.
- `quality_paper_trader.py --selftest`: `[PASS] test_sell_order_deterministic (identical across hash seeds 111/222)`.
- `weekly_options_paper_trader.py`: no self-check added — no issue found, nothing to check.

## Three-run reproducibility evidence

Ran each strategy's `--status` mode (read-only, doesn't mutate live paper-trading state — chosen deliberately over forcing repeated real rebalances against production state, which would have churned real trade history for no evidentiary gain beyond what the isolated self-checks already prove more rigorously for the actual fixed code paths):

- Quality Factor: 3 runs, byte-identical (`Rs104,050 +4.1%`, 22-position table, identical order and values all 3 times).
- Factor Timing: 3 runs, byte-identical (`Rs101,513 +1.5%`, `LOWVOL_MOM`, 7-position table, identical all 3 times).
- Weekly Options: 3 runs, byte-identical (`Rs100,806 +0.81%`, 5 traded / 0 skipped).

**Caveat, stated plainly:** these 3 scripts fetch live current market data every run by design (unlike the momentum backtest, which runs over a fully cached historical window). Byte-identical `--status` output here mainly confirms no crash and stable display ordering within one check — it is not, by itself, proof that the *rebalance* logic is deterministic, because today isn't a rebalance trigger for any of these three. That proof comes from the hash-seed self-checks above, which directly exercise the fixed rebalance-selection code paths in isolation. Don't conflate the two forms of evidence.

## Remaining determinism risks

None from the iteration-order bug class within this audit's scope. Two things noted but explicitly out of scope (not fixed, not silently ignored):

- `quality_paper_trader.py`'s fundamentals refresh (`fetch_fundamentals_fresh`, called live on every rebalance) and these 3 scripts' live price/VIX fetches are not cached the way the momentum backtest's regime index now is — but that's a data-freshness question, correct behavior for a live trader (you want today's real data), not an iteration-order bug. Not conflating the two.
- Sibling repo's other 13 backtested-but-not-promoted strategies were not audited — out of scope (not part of the live tournament).

## Declaration

**All tournament strategies are reproducible under identical inputs.**
