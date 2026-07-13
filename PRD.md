---
type: project
date: 2026-07-12
area: self
project: AlgoTrader
status: active
---

# Product Requirements Document: AlgoTrader — Multi-Strategy Tournament to Live Capital

**Author:** Jinu Joshi (with Claude)
**Date:** 2026-07-12
**Status:** Draft
**Stakeholders:** Jinu Joshi (solo operator)

---

## 1. Executive Summary

AlgoTrader has quietly grown into a 4-strategy paper-trading tournament (Momentum, Quality Factor, Factor Timing, Weekly Options) plus a 16-strategy backtest research suite, running daily and unmonitored via a scheduled task — but none of this is documented in one place, one strategy was silently broken for a month, and the original 3-phase plan (single momentum strategy → live ₹1.6L) doesn't reflect what's actually being tested. This PRD consolidates the real system into one plan: run the tournament properly, pick a winner (or blend) on evidence, close the regulatory/data-integrity gaps surfaced by research, then go live.

## 2. Background & Context

**What actually exists (discovered 2026-07-12, not previously documented together):**
- `AlgoTrader/` — original project. Nifty500 12M-1M momentum strategy. Backtested CAGR 32.9%, Sharpe 1.45, MaxDD -18.9% (2019-2024). Paper trading live since 2026-06-09.
- `My_terminal/trading_backtests/` — separate, undocumented sibling project: 16 backtested strategies (momentum, value, options, pairs, ML, IPO). 4 confirmed bugs found and fixed across strategies during a June 2026 audit (ROE threshold, dual-momentum index bug, trend-following signal bug, options CAGR annualization bug). 3 of these 16 were promoted to live paper trading.
- `run_daily_traders.ps1` — orphan scheduler script sitting at the Projects root (not inside either project folder), runs all 4 promoted strategies daily at 3:35pm, logs to `trader_logs/`.
- **Bug found and fixed this session:** the scheduler invoked AlgoTrader's `paper_trader.py` without setting working directory, so it silently crashed every day since 2026-06-09 looking for `nifty500_universe.csv`. It was reporting a fake flat 0.0% instead of erroring visibly. Fixed via `Push-Location`.

**Tournament standings, 2026-07-10** (₹1L paper capital each, ₹4L total deployed):

| Strategy | Value | P&L | Ann. Return | Status |
|---|---|---|---|---|
| Momentum (12M-1M) | ₹1,00,000 | +0.0% | +0.0% | was broken, now fixed |
| Quality Factor | ₹1,04,050 | +4.1% | +43.8% | 22 positions |
| Factor Timing | ₹1,01,513 | +1.5% | +19.2% | 7 positions, LOWVOL_MOM regime |
| Weekly Options | ₹1,00,806 | +0.8% | +10.3% | 5 weeks traded, 80% win rate |
| Nifty 50 (benchmark) | — | +1.0% | — | — |

**⚠ Caveat added 2026-07-12 — Quality Factor and Factor Timing's stock universe is not the Nifty 500.**
Both strategies' live paper traders (and their backing sibling-repo backtests) select stocks from `trading_backtests/utils/data_loader.py::get_nifty500_universe()` — which is not a data fetch, it's 96 tickers hardcoded in source, hand-picked with the benefit of knowing which companies mattered by 2026 (includes Zomato, Paytm, LICI, Delhivery — all IPO'd 2021-2022). This is survivorship bias by construction. Their live P&L figures above (+4.1%, +1.5%) aren't wrong on their own terms (real prices, real trades against that 96-name list), but any conclusion that draws on the *backtests* behind these strategies inherits this bias, and the tournament is silently comparing 4 strategies against three different, unequal-quality universes (AlgoTrader's momentum: real current Nifty500 fetch; Quality Factor + Factor Timing: fabricated 96-name list; Weekly Options: index options, no universe). Do not use this table alone to pick a go-live winner at the 2026-09-09 gate — see `(AI) QuantOS Audit and Roadmap.md` F9. Momentum's own backtest look-ahead bias was separately found and fixed 2026-07-12 (see CONTEXT.md) — the 32.9%/36.6% CAGR figures on this page predate that fix and are stale; current numbers are in CONTEXT.md.

**Tournament assumption (added 2026-07-12):** Historical delisting-direction survivorship bias remains unquantified and may inflate reported returns. Investigated and accepted as a documented research limitation, not an engineering blocker — see `(AI) Decision Record - Point-in-Time Universe.md`. One-directional (inflationary only), doesn't invalidate the comparative tournament, but weigh it before treating any strategy's absolute CAGR/Sharpe as trustworthy at face value.

**Research findings** (`india_algo_landscape.md`, completed 2026-07-12, web research across broker APIs, regulation, community, education, strategy archetypes):
1. **OpenAlgo** (github.com/marketcalls/openalgo) — existing open-source, 2.2k★, self-hosted broker-abstraction layer covering 34 Indian brokers including Angel One, with paper-trading sandbox. Directly relevant to the planned Angel One SmartAPI integration — evaluate before writing more custom glue code.
2. **SEBI's retail algo regulation is already in its enforcement window**, not a future concern: Feb 2025 circular, effective 1 Aug 2025, full enforcement 1 Apr 2026. Requires Algo-ID tagging per strategy, static IP whitelisting, mandatory 2FA. Broker (Angel One) is the compliance gatekeeper — strategy must be registered with them before live API trading.
3. **Momentum strategy's 32.9% CAGR needs a survivorship-bias check** — backtest period (2019-2024) is a bull run, and if the Nifty500 universe uses current constituents rather than point-in-time historical membership, returns can be inflated ~20-25%.
4. Momentum-on-Nifty500 was validated by research as one of the more defensible small-capital retail strategies (vs. options-selling's tail risk or stat-arb's institutional infra requirement) — strategy choice itself is sound, execution/measurement is what needs tightening.

## 3. Objectives & Success Metrics

**Goals:**
1. One documented source of truth covering all 4 tournament strategies, replacing the stale single-strategy CONTEXT.md/EXECUTION_PLAN.md.
2. Resolve the 3 data-integrity/regulatory gaps from research before any strategy touches live capital.
3. Run a fair, bug-free tournament for a defined evaluation window, then select winner(s) by evidence, not by whichever wasn't broken.
4. Go live with the selected strategy(ies) within SEBI compliance, on the existing capital-scaling plan.

**Non-Goals:**
1. Not adding new strategies beyond the existing 4 in the tournament (the other 12 backtested-but-not-promoted strategies stay research-only unless a tournament strategy fails its gate).
2. Not building the LLM signal layer (TradingAgents/Vibe-Trading) yet — research confirmed this has no verified precedent in Indian retail practice; treat as a later R&D track, not part of this PRD's critical path.
3. Not pursuing prop-firm funding in this PRD's scope — that's Phase 3 of the existing plan, gated on 6 months of live track record that hasn't started yet.

**Success Metrics:**

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Strategies with verified, monitored daily execution | 1 of 4 (bug just fixed) | 4 of 4 | No silent failures in `trader_logs/` for 2 consecutive weeks |
| Momentum backtest survivorship-bias check | Not done | Done, CAGR re-validated point-in-time | Re-run `momentum_backtest.py` with historical universe |
| SEBI compliance status with Angel One | Unknown | Confirmed registered or confirmed exempt | Check Angel One's algo registration portal |
| Tournament evaluation window | Started informally 2026-06-09 | 3 full months of clean data (target gate: 2026-09-09, matching existing Phase 1 gate) | `tournament_history.csv` continuous, no gaps |
| Documentation consolidation | Scattered across 2 folders + orphan script | One CONTEXT.md / PRD covering all 4 | This PRD + updated CONTEXT.md |

## 4. Target Users & Segments

Solo user (Jinu Joshi) only. Not a coder — Claude executes; Jinu makes capital and go/no-go decisions. No external users, no multi-tenant concerns.

## 5. User Stories & Requirements

**P0 — Must Have:**

| # | User Story | Acceptance Criteria |
|---|-----------|-------------------|
| 1 | As the operator, I want the scheduler to fail loudly, not silently, so a broken strategy doesn't run undetected for a month again. | `run_daily_traders.ps1` checks each strategy's exit code / output for `ERROR` and surfaces a visible alert (console + log flag), not just a buried log line. |
| 2 | As the operator, I want to know if my momentum backtest is inflated by survivorship bias before trusting it further. | `momentum_backtest.py` re-run against point-in-time Nifty500 membership (or explicit confirmation current-membership approach is accepted with the known bias caveat documented). |
| 3 | As the operator, I want to know my current SEBI compliance status before going live. | Angel One's retail algo registration status checked and documented (registered / not required at current order-rate / blocked). |
| 4 | As the operator, I want one document that describes all 4 strategies, the tournament, and current standings — not scattered across 2 folders. | `CONTEXT.md` updated to reference all 4 strategies, tournament mechanics, and link to `trading_backtests/` sibling project. |

**P1 — Should Have:**

| # | User Story | Acceptance Criteria |
|---|-----------|-------------------|
| 5 | As the operator, I want to evaluate OpenAlgo as a broker-abstraction layer before writing custom Angel One SmartAPI code. | A short spike/evaluation note on OpenAlgo fit, decision recorded (adopt / reject + why). |
| 6 | As the operator, I want the weekly journal habit (currently abandoned since Jun 9) restored so I have a track record for future prop-firm applications. | `journal.md` backfilled or restarted with a lower-friction logging method (e.g. auto-appended from `tournament_history.csv` rather than manual copy-paste). |
| 7 | As the operator, I want clarity on tax treatment before trade frequency grows. | CA consultation logged, or explicit decision to defer until volume threshold is hit. |

**P2 — Nice to Have / Future:**

| # | User Story | Acceptance Criteria |
|---|-----------|-------------------|
| 8 | As the operator, I want the other 12 backtested-but-unpromoted strategies available as a bench if a tournament strategy fails its gate. | No action now — documented as existing optionality in `trading_backtests/`. |
| 9 | As the operator, I want an LLM signal layer eventually. | Deferred; revisit after live capital deployment is stable. |

## 6. Solution Overview

Three tracks, in priority order:

**Track A — Fix the foundation (this week):**
- Scheduler already patched (CWD fix applied 2026-07-12). Add error-surfacing so future breaks aren't silent.
- Re-run momentum backtest with point-in-time universe check.
- Check Angel One algo-registration status directly.

**Track B — Consolidate documentation (this week):**
- Rewrite `CONTEXT.md` to describe the 4-strategy tournament as the current reality, not the single-momentum-strategy history.
- Link `trading_backtests/` as a sibling research project in `CONTEXT.md`, not a hidden dependency.
- Restart `journal.md` logging, ideally automated from `tournament_history.csv`.

**Track C — Run the tournament to a real gate (through 2026-09-09):**
- Let all 4 strategies run clean, monitored, for the remaining ~2 months to the existing Phase 1 gate date.
- At gate: compare Sharpe/CAGR/MaxDD across all 4 + Nifty50 benchmark, apply existing Phase 1 gate criteria (Sharpe > 1.0, no critical bugs, regime filter correct, 3 months documented).
- Decide: single winner goes live per existing Phase 2 plan (₹1.6-3L capital), or a blend of top 2 if uncorrelated enough to diversify.

No new infrastructure decisions forced now beyond the OpenAlgo evaluation spike — everything else is fixing/consolidating what's already built.

## 6a. SEBI/Angel One Compliance Checklist (added 2026-07-12)

Can't complete this myself — needs your login to Angel One's portal. This is a
checklist for you to work through before any live order placement, not a
verification I can do. Per SEBI's 4 Feb 2025 circular (full enforcement
1 Apr 2026 — already passed):

- [ ] Log into Angel One SmartAPI developer portal. Check whether your API
      access is still active — non-compliant brokers were barred from
      onboarding new API clients from 5 Jan 2026.
- [ ] Check whether Angel One has registered you (or requires you to
      self-register) a retail Algo-ID for the momentum strategy specifically.
      Every API-placed order is legally an "algo order" now — there's no
      "just building/testing" exemption once you place real orders.
- [ ] Confirm whether your order rate qualifies for the lighter "regular API
      user" bucket (roughly <10 orders/sec) vs full algo registration — this
      determines which compliance path applies. Get this in writing/screenshot
      from Angel One, not inferred.
- [ ] Check static-IP whitelisting requirement — is your API key tied to a
      static IP? If not, this needs setting up before going live (may need a
      static IP from your ISP or a VPS).
- [ ] Confirm 2FA is enforced on your API session per the mandatory-2FA rule.
- [ ] Ask Angel One directly (support ticket or RM) whether mock trading /
      sandbox registration (mandatory by 3 Jan 2026 per broker-side rules) is
      something you need to do anything about, or if it's purely Angel One's
      internal obligation.
- [ ] If any of the above is unclear or Angel One's answer is ambiguous,
      don't self-interpret — this is a regulatory question, not a technical
      one, and the penalty side (FEMA-adjacent, SEBI enforcement) isn't
      something to guess on.

**This entire checklist blocks Phase 2 (go-live), not just automation.** Do it
before capital moves, not after.

## 7. Open Questions

| Question | Owner | Deadline |
|---|---|---|
| Is Angel One's retail algo registration required at current (near-zero, single-user) order rate, or does the "regular API user" exemption apply? | Jinu (check Angel One portal directly) | Before any live order placement |
| Does `momentum_backtest.py`'s Nifty500 universe use point-in-time or current constituents? | Claude (code check) | Next session |
| Is OpenAlgo worth adopting given AGPL-3.0 license, or does custom SmartAPI integration stay simpler for a single-user system? | Jinu + Claude | Before Angel One integration work starts |
| Should Quality Factor and Factor Timing's stronger paper returns (+43.8%, +19.2% annualized) shift the "which strategy goes live first" default away from Momentum, given Momentum was silently broken for a month and has less clean live data? | Jinu, at 2026-09-09 gate | 2026-09-09 |

## 8. Timeline & Phasing

| Phase | Window | Milestone |
|---|---|---|
| Track A + B (fix + consolidate) | This week (2026-07-12 onward) | Backtest re-validated, SEBI status known, docs unified |
| Track C (tournament to gate) | Now → 2026-09-09 | 3 months clean data on all 4 strategies |
| Existing Phase 2 (go live) | Oct-Dec 2026 | Winner(s) live at ₹1.6-3L, per existing EXECUTION_PLAN.md |
| Existing Phase 3 (scale + prop) | Jan 2027+ | Unchanged from EXECUTION_PLAN.md |

This PRD does not replace `EXECUTION_PLAN.md`'s Phase 2/3 structure — it fixes and expands Phase 1 to reflect the real 4-strategy tournament, then hands off to the existing plan unchanged.

**Phase update, 2026-07-13: Historical Research Phase declared complete for Momentum.** Engineering hardening (determinism, scheduler contract, error signaling) closed across all 4 strategies. Statistical research chain (CAPM, factor attribution, regime stability) produced genuinely mixed evidence — real alpha signal in the full sample, but it loses significance on a fair post-2021 window and is moderately concentrated in trending-bull regimes. See `(AI) Historical Research Phase - Closure Summary.md` for the full chain. No further historical retrospective work unless a new defect/contradiction surfaces. **Prospective Validation Phase begins now** — weekly research log per `(AI) Weekly Research Log Template.md`, starting with the first live rebalance since the scheduler fix (expected Friday 2026-07-17).
