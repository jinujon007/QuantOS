---
type: crystallization
date: 2026-07-12
area: self
project: AlgoTrader
status: active
confidence: 0.75
sources: 1
last_confirmed: 2026-07-12
ai_generated: true
---

# Decision Record: Point-in-Time Nifty 500 Universe

## What was investigated

Whether to source historical (point-in-time) Nifty 500 index membership via a
paid data vendor or manual reconstruction from NSE/niftyindices circulars, to
close the survivorship-bias gap (F1) in `momentum_backtest.py`'s 2019-2024
backtest. Decision memo recommended B (manual reconstruction) on the grounds
that the need is a one-time validation task, not ongoing infrastructure, and
no vendor was confirmed to sell this specific dataset. A time-boxed spike
followed to check actual data availability.

## What was confirmed

- The "stock didn't exist yet" direction of survivorship bias is **already
  handled correctly** by the existing code, with no fix needed. `momentum_score()`
  in both `momentum_backtest.py` and `paper_trader.py` computes returns from
  `prices.loc[:start_dt]` / `prices.loc[:end_dt]` — a ticker with no cached
  price history before its IPO date simply produces `NaN` there, and
  `.dropna()` already excludes it. Verified by reading the current code, not
  assumed.
- NSE's own ecosystem (niftyindices.com, nsearchives.nseindia.com) actively
  resists automated/headless access — 5 direct attempts (niftyindices.com x3,
  nsearchives.nseindia.com, Google, DuckDuckGo) were blocked or timed out.
  Bing returned only generic results, nothing pointing to a historical
  reconstitution circular archive. A GitHub search for an existing open
  point-in-time Nifty 500 constituents dataset returned zero repositories.
- No other look-ahead bias found in AlgoTrader's own pipeline beyond what
  Stage 1 already fixed. Re-verified `momentum_score()` (both files) and
  `check_regime()`/`load_nifty50_regime()`: all compute signals from strictly
  trailing data (`end_dt = as_of - 1 month`, rolling means), no same-day or
  future references remain.

## What remains unknown

Whether a stock that was a genuine Nifty 500 member historically and later
got delisted, merged, or renamed is missing from the backtest entirely — this
can't be checked without external membership history, and automated access to
NSE's own source for that history was blocked, not merely inconvenient. No
paid vendor was confirmed (or ruled out) to sell this specific dataset either.

## Expected direction of bias

Unquantified but directionally known: excluding historically-removed
constituents means the backtest only ever sees companies that survived to
today — this can only inflate reported returns, never deflate them. Magnitude
unknown. Given the 2019-2024 window is a bull run and the strategy is
momentum-on-smallcap-inclusive-universe (the segment most likely to have
delistings/mergers), the risk is not negligible, but it is bounded in
direction — there is no scenario where this bias makes the strategy look
worse than reality.

## Why the project proceeds anyway

1. The bias is one-directional (inflationary), not a correctness bug that
   could hide a broken strategy — it's a margin-of-safety question, not a
   go/no-go question on its own.
2. Stage 1 already fixed two bugs (look-ahead fill timing, cost-model
   mismatch) that were correctness bugs, not margin-of-safety questions —
   those were the higher-priority risks and are closed.
3. The tournament's actual purpose (per PRD) is a 3-month comparative
   evaluation against Nifty 50 and 3 other strategies, gated 2026-09-09 — not
   a final go-live decision. A single unquantified, one-directional bias is
   an acceptable known-unknown to carry into a comparative evaluation,
   provided it's written down and not silently forgotten.
4. Closing it fully would require either paying for an unconfirmed data
   product or a manual, human (non-automatable) NSE archive search — neither
   is worth blocking Stage 1's exit on, given the bias direction is already
   understood.

## Disposition

Documented research limitation, not an engineering blocker. Carried forward
as an explicit tournament assumption (see PRD.md, CONTEXT.md). Revisit only if
the 2026-09-09 gate result is close enough that this specific bias could flip
the go/no-go decision — at that point it becomes worth the manual effort.
