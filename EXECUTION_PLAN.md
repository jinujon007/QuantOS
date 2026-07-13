# AlgoTrader — Execution Plan
> The 12-month plan from paper trading to real income.
> Last updated: 2026-06-09

---

## Where We Are Right Now

| Item | Status |
|------|--------|
| Strategy | Validated (CAGR 32.9%, Sharpe 1.45, MaxDD -18.9%) |
| Paper trading | **LIVE** — started 2026-06-09 |
| Current regime | **BEAR** — Nifty 23,242 < MA100 24,364 → holding cash |
| Live trading | Not started |
| Capital deployed | ₹0 |

Bear market = no trades until Nifty closes above ~24,364. This is correct behavior. Use this time to master the daily routine.

---

## The 3-Phase Plan

### PHASE 1 — Paper Trading
**Duration:** June 9 → September 9, 2026 (3 months minimum)
**Goal:** Prove the strategy works in real-time, not just backtest. Build discipline.

**Daily action (every market day, after 3:30 PM IST):**
```powershell
cd "d:\Brain\JINU JOSHI\02 Self\Projects\AlgoTrader"
.\venv\Scripts\Activate.ps1
python paper_trader.py
```

**Friday action (rebalance day):**
- Run paper_trader.py — it auto-computes signals and logs trades
- Open `data/journal.md` and record the top 10 signals manually
- Note if any positions were added/removed and why

**Monthly review (1st of each month):**
1. Open `data/paper_trades.csv` — review all trades
2. Calculate month's return on ₹1,00,000 base
3. Compare to backtest expectations
4. Log in journal

**Phase 1 Gate Criteria (September 9, 2026):**
| Metric | Minimum to proceed | Notes |
|--------|-------------------|-------|
| Paper Sharpe (annualized) | > 1.0 | 30% below backtest 1.45 is acceptable |
| No critical bugs found | Required | Regime filter, stop loss, rebalance all work |
| Regime filter activated correctly | Required | Bear market → cash, bull → invest |
| Track record documented | Required | At least 3 months of trade logs |

If criteria met → Phase 2. If not → diagnose and fix before deploying capital.

---

### PHASE 2 — Go Live (Small)
**Duration:** October → December 2026 (3 months)
**Goal:** Real skin in the game. Learn execution. Build live track record.

**Capital:** ₹1.6L minimum, ₹3L recommended
- Why ₹1.6L: DP charge (₹15.93/scrip) = 0.1% per sell at ₹16K/stock. Below this, DP dominates costs and kills returns.
- Why not ₹10L immediately: prove system works live before committing full capital

**Broker:** Zerodha (manual execution — no API cost at this stage)
**Execution:** Every Friday, run paper_trader.py → copy the top 10 BUY signals → place manually on Zerodha app before 3:15 PM IST

**What to track:**
- Live trades vs paper trader signals (should match)
- Actual slippage vs assumed 0.1% cost
- Regime exits (if market goes bear → sell all, hold cash)
- Emotional responses — note any urge to override the system

**Phase 2 Gate Criteria (December 2026):**
| Metric | Minimum to proceed | Notes |
|--------|-------------------|-------|
| Live return > 0% | Required | Any positive return = system working |
| Live Sharpe > 0.8 | Strong signal | Lower bar — 3 months is short |
| Slippage within range | < 0.5% average | If higher, adjust cost model |
| No system overrides | Preferred | Overriding = strategy breakdown |

---

### PHASE 3 — Scale + Prop Firm
**Duration:** January 2027 onwards
**Goal:** Access institutional capital. Make real money.

**Track A — Own capital:**
- If Phase 2 passes → deploy ₹5-10L full capital
- At 3% monthly on ₹10L = ₹30,000/month
- At 5% monthly on ₹10L = ₹50,000/month

**Track B — Prop firm (the real lever):**
- 6 months live track record (Phase 2 + 3 months Phase 3) → apply to prop firm
- Target: funded account of ₹30-80L
- Profit split: 80-90% to you
- At 3% monthly on ₹50L funded = ₹1.5L gross → ₹1.2L to you/month
- That is real money.

**Prop firms to target (India-friendly, INR payouts):**
- FTMO (most reputable globally)
- Funded Engineer (India-focused)
- Goat Funded Trader (has India listings)
- Requirement: documented 6-month track record + consistent strategy

**Track C — Options layer (parallel, from Phase 2 onwards):**
- Add iron condor on Nifty monthly expiry alongside momentum system
- Separate ₹1-2L allocated to options selling
- Target: 2-3% monthly from premium collection
- This runs independent of regime filter — options selling works in range-bound markets too

---

## Income Projection

| Milestone | Timeline | Monthly Income |
|-----------|----------|----------------|
| Paper trading live | Now | ₹0 |
| Live ₹1.6-3L | Oct 2026 | ₹5-15K |
| Live ₹10L own capital | Jan 2027 | ₹25-50K |
| Prop firm funded ₹50L | Mid 2027 | ₹1-1.5L |

---

## Weekly Checklist

**Monday–Thursday:**
- [ ] Run `python paper_trader.py` after 3:30 PM
- [ ] Check regime status (BULL/BEAR)
- [ ] Note any stop loss triggers
- [ ] 5 minutes. No more.

**Friday (rebalance day):**
- [ ] Run `python paper_trader.py` after 3:30 PM
- [ ] Check the top 10 signals printed
- [ ] Open `data/journal.md` — log the signals + any position changes
- [ ] In Phase 2+: execute trades manually on Zerodha before 3:15 PM

**Monthly (1st of each month):**
- [ ] Review `data/paper_trades.csv`
- [ ] Calculate month return %
- [ ] Compare to backtest expectations
- [ ] Update Phase gate metrics

---

## Bear Market Protocol

Currently in bear market (Nifty 23,242 < MA100 24,364).

**What this means:**
- Paper trader holds 100% cash — correct
- No momentum trades until regime clears
- Watch Nifty weekly — needs to close above ~24,364 to re-enter

**Trigger to re-enter:** Nifty closes above MA100 on a Friday → paper trader auto-buys top 10 stocks next rebalance

**What to do during bear market:**
- Keep running daily to log the regime correctly
- Study the iron condor strategy (options don't care about trend direction)
- Review backtest code — understand the signals better
- Prepare Zerodha account for Phase 2

---

## Go/No-Go Decision Points

| Date | Decision | Criteria |
|------|----------|----------|
| 2026-09-09 | Paper → Live? | Phase 1 gate criteria above |
| 2026-12-01 | Scale live capital? | Phase 2 gate criteria above |
| 2027-01-01 | Apply to prop firm? | 6 months live track record |
| 2027-06-01 | Add options layer? | Momentum system stable, capacity to run 2 strategies |

---

## Emergency Rules (Non-Negotiable)

1. **Never override the system.** If the regime says cash, hold cash. Period.
2. **Never add to a losing position.** Stop loss exists for a reason.
3. **Never deploy more capital than you can afford to lose.** ₹1.6L live means ₹1.6L is expendable.
4. **Three months minimum before any assessment.** One bad month is noise. Three months is signal.
5. **Track record first, profit second.** A documented system that makes 20% beats an undocumented one that makes 40%.

---

*Run `python paper_trader.py --status` any time to check current portfolio.*
*Trade log: `data/paper_trades.csv`*
*Paper state: `data/paper_state.json`*
