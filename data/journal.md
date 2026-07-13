# AlgoTrader — Trade Journal
> Log every Friday's signals here. This is your track record. It gets you into prop firms.

---

## How to use this

Every Friday after running `python paper_trader.py`:
1. Copy the "Top 10 momentum scores today" output here
2. Note the regime status
3. Note what changed from last week (new entries, exits, stop losses)
4. In Phase 2 (live): note actual Zerodha execution prices vs paper signals

---

## Monthly Performance Log

| Month | Paper Portfolio Value | Monthly Return | Nifty Return | Alpha | Regime Days Cash |
|-------|----------------------|----------------|--------------|-------|-----------------|
| Jun 2026 | — | — | — | — | — |
| Jul 2026 | — | — | — | — | — |
| Aug 2026 | — | — | — | — | — |
| Sep 2026 | — | — | — | — | — |

**Alpha** = monthly return minus Nifty return (positive = beating index)
**Regime Days Cash** = number of trading days held cash due to bear filter

---

## Weekly Logs

---

### Week of 2026-06-09 (Monday)

**Regime:** BEAR — Nifty 23,242 < MA100 24,364
**Portfolio:** ₹1,00,000 (100% cash)
**Positions:** 0
**Action:** None — bear market, holding cash

**Notes:**
- Paper trading initialized today
- System working correctly — regime filter active
- Nifty needs ~4.8% rally (to ~24,364) to re-enter market
- Next rebalance: Friday 2026-06-13 — will check regime again

---

<!-- TEMPLATE FOR EACH FRIDAY — copy and paste below -->
<!--
### Week of YYYY-MM-DD (Friday)

**Regime:** BULL / BEAR — Nifty XXXXX vs MA100 XXXXX
**Portfolio:** ₹X,XX,XXX (X% vs start)
**Positions:** X stocks + ₹X cash
**Action:** BUY X, SELL X, HOLD X

**Top 10 Signals:**
| Rank | Ticker | 12M-1M Return | Action |
|------|--------|---------------|--------|
| 1 | — | — | — |
...

**Changes from last week:**
- Added: —
- Removed: —
- Stop losses triggered: —

**Notes:**
- 
-->
