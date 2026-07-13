---
type: crystallization
date: 2026-07-12
area: self
project: AlgoTrader
status: active
confidence: 0.75
sources: 12
last_confirmed: 2026-07-12
ai_generated: true
---

# QuantOS Audit & Roadmap — Existing PRD as Phase 1

**Question:** does AlgoTrader-as-built justify calling it Phase 1 of a long-horizon "QuantOS," and what's the real gap to institutional standard?

**Method:** read every file in `AlgoTrader/` + sibling `My_terminal/trading_backtests/` + orphan `run_daily_traders.ps1` + both research docs. No code written yet — audit only, per instruction.

---

## 1. What Actually Exists (ground truth, not the PRD's summary of it)

Two sibling codebases, one orphan scheduler, zero shared library:

- **AlgoTrader/** — 1 strategy (momentum 12M-1M), own backtest engine, own paper trader, own cost model (`transaction_costs.py` — real Zerodha CNC charges: STT/stamp/exchange/GST/DP).
- **My_terminal/trading_backtests/** — 16 strategies, separate backtest engine (`run_all_backtests.py`), separate cost/metrics module (`utils/metrics.py`), separate paper traders per promoted strategy, own task-queue docs (`TASK_*.md`), own devlog.
- **run_daily_traders.ps1** — sits at `Projects/` root, calls into both codebases by hardcoded path, has no error surfacing beyond `Write-Log` (confirmed: PRD's P0-1 is still open, not fixed by the CWD patch).

No shared config, no shared metrics module, no shared cost model between the two codebases. Momentum's cost model (accurate DP+STT+GST) is *not* used by any of the 3 sibling paper traders — confirmed by reading `run_daily_traders.ps1` call signatures and `transaction_costs.py`'s import graph (only `momentum_backtest.py` imports it).

## 2. Findings the PRD Doesn't Surface

**F1 — Survivorship bias is not just a risk, it's confirmed present.**
`fetch_universe.py` scrapes NSE's *current* Nifty 500 list. `momentum_backtest.py` then backtests 2019-2024 against that same current-membership file. Any stock delisted, merged, or dropped from the index between 2019-2024 is invisible to the backtest — the 32.9% CAGR is measured against survivors only. This is the PRD's Open Question #2, but it's not actually an open question — the code confirms the bug exists. Fix requires point-in-time index membership history (NSE doesn't publish this cleanly; likely needs a paid data vendor or manual reconstruction).

**F2 — Look-ahead bias in both engines: signal and entry share a timestamp.**
In `momentum_backtest.py::run_backtest`, momentum score is computed `as_of=date` (today's close), and the same `today_prices` is used as the fill price for entries on that identical `date`. Live, you can't know today's close until after the market shuts — a live order can only fill at *tomorrow's* open or a delayed price. Same pattern in `paper_trader.py::run_daily_update` (computes and fills same session). This inflates every backtest and every paper P&L number in both codebases. Not flagged as fixed anywhere.

**F3 — CORRECTED 2026-07-12 (see also "Corrections" section below).** Original text claimed the live Quality Factor paper-trading P&L was look-ahead-biased. That was wrong — it conflated the *backtest* (`strategies/07_quality_factor.py`) with the *live paper trader* (`quality_paper_trader.py`), two different scripts. The backtest's look-ahead bug (T-006) was real and has since been fixed in code (confirmed via `results/07_quality_metrics.csv`, dated 2026-06-18: CAGR 40.3%→37.2%, Sharpe 2.34→2.13, MaxDD -12.6%→-11.8% after the fix — DEVLOG.md's "still pending" note was just stale, superseded by a later run it was never updated to reflect). The live paper trader correctly uses `yf.Ticker(...).info` (current fundamentals) for current-day decisions — that is not look-ahead bias, it's ordinary live operation. The real caveat on the live +43.8% figure is small-sample noise (~5 weeks of data), not a bias bug. See F9 for the actual serious problem this investigation surfaced.

**F9 — `get_nifty500_universe()` is not the Nifty 500. It's 96 hardcoded tickers, hand-picked with 2024 hindsight.**
`utils/data_loader.py` (sibling repo) defines this function as a literal Python list — not a fetch, not an API call, a name that promises index membership and delivers a curator's picks. The list includes Zomato, Paytm, LICI, Delhivery (all IPO'd 2021-2022) and IRCTC (2019), used as tradeable universe members across backtests that (per the T-006 problem description) run from 2010-2024. Whoever built this list knew in 2026 which ~96 names were worth including — that's survivorship bias by construction, not by accident, and it's worse than F1 (AlgoTrader's own universe is at least a real current fetch, just not point-in-time). **Both Quality Factor and Factor Timing — 2 of the tournament's 4 live strategies — call this same function.** Weekly Options doesn't (it trades index options, no stock universe needed). This affects all 16 strategies in `trading_backtests/`, not just the two promoted to live tournament capital. Not fixed in this pass — flagged as the highest-priority Phase 3 (Data Engine) item, ahead of even the point-in-time-membership work under F1, since F9 isn't a data-sourcing gap, it's actively wrong code masquerading as a real universe.

**F3-original (superseded, kept for the record):** Quality Factor, currently the tournament's best performer (+43.8% annualized per PRD), has a known, unresolved look-ahead bug.
`trading_backtests/DEVLOG.md` documents Strategy 07 (Quality Factor) pulling `yfinance.info` for fundamentals — which returns *current* ROE/fundamentals, not historical-as-of-date. Ticket T-006 to fix this via `get_income_stmt()`/`get_balance_sheet()` was still pending as of last DEVLOG update (2026-06-09), and the DEVLOG explicitly warns it may get BLOCKED on thin historical-financials coverage for Indian tickers. The PRD's tournament table presents Quality Factor's +43.8% as a real signal without this caveat. This is the single highest-priority correctness risk in the whole system — the tournament's apparent leader may be an artifact.

**F4 — Cost model inconsistency between backtest and paper trading, both codebases.**
`momentum_backtest.py` uses `BUY_RATE`/`SELL_RATE`/`DP_CHARGE_PER_SCRIP` (accurate, ~0.1-0.16% + flat DP). `paper_trader.py` uses `TRANSACTION_COST = 0.001` flat — a simplification that *understates* real cost by ignoring the flat DP charge entirely, the same DP charge the PRD/CONTEXT.md identifies as capital-critical (₹15.93/scrip dominates at small size). Paper P&L is therefore optimistic relative to what live capital would actually pay. No visibility into whether the sibling 3 paper traders use accurate or flat costs (not read in full — flag for next pass).

**F5 — Bug pattern across 16-strategy suite: no tests, only manual eyeballing catches errors, and errors get promoted to live paper trading before being caught.**
`TASK_FIX_BUGS.md` documents 4 confirmed bugs (decimal-threshold, index-vs-value lookup, wrong-signal-reused, monthly-treated-as-daily-annualization) that each silently produced dramatically wrong metrics (CAGR up to 1691%) for an unknown period before a manual audit caught them. Zero unit tests exist anywhere in either codebase. This is a structural gap, not a one-off — the same class of bug will recur.

**F6 — No portfolio-level risk engine.**
Each of the 4 tournament strategies runs isolated ₹1L virtual capital with its own stop-loss/regime logic. There is no cross-strategy exposure aggregation, no max-daily-loss circuit breaker, no correlation check between strategies, no kill switch. At go-live, if 2+ strategies simultaneously hold correlated positions (e.g., momentum and factor-timing both long the same sector), effective concentration risk is invisible to either system.

**F7 — Regulatory status genuinely unknown, deadlines already passed.**
SEBI's Algo-ID/static-IP/2FA framework hit full enforcement 1 Apr 2026 (per your own research doc) — today is 2026-07-12, three months past. PRD lists this as an open question with no owner-completed date. This blocks any live-capital deployment, not just automation — worth checking before anything else in this roadmap.

**F8 — No data lineage / experiment tracking.**
Strategy parameters (`TOP_N`, `STOP_LOSS_PCT`, etc.) are duplicated as module-level constants across `momentum_backtest.py` and `paper_trader.py` — if one gets tuned, the two files can silently diverge (already a latent risk: nothing enforces they match beyond a code comment). No run manifest ties a backtest result to a specific code commit + data snapshot — CAGR numbers in CONTEXT.md aren't reproducible against a git SHA.

## 3. What's Genuinely Good (preserve, don't rewrite)

- Cost model in `transaction_costs.py` — real Zerodha CNC rates, correctly composed (STT/stamp/exchange/SEBI/GST/DP). Reuse as the shared cost module.
- Regime filter engineering (MA100 vs MA200 choice, timezone bug fixes, NIFTYBEES fallback) — pragmatic, well-reasoned, documented in CONTEXT.md's decision log.
- Walk-forward validation already implemented and run (11.4% degradation, passed).
- The June bug-hunt audit on the 16-strategy suite (`TASK_FIX_BUGS.md`) — real root-cause debugging, well-documented, not hand-waved.
- Research discipline — `india_algo_landscape.md` and Tech Stack doc are properly source-cited, confidence-scored, and already surfaced the exact biases confirmed above before I re-derived them from code.

## 4. Gap Analysis

| Area | Current State | Target State (QuantOS) | Missing | Priority | Dependencies | Complexity | Risk if Skipped |
|---|---|---|---|---|---|---|---|
| Survivorship bias | Current-membership universe used for historical backtest (F1) | Point-in-time index membership | Historical constituent data source | P0 | None | High (data sourcing, likely paid vendor) | Every CAGR number is unreliable |
| Look-ahead bias | Signal + fill share timestamp (F2) | T+1 fill logic in both engines | Backtest engine rewrite (small, mechanical) | P0 | None | Low | Backtest/paper both overstate returns |
| Quality Factor fundamentals | Current-only `.info` fundamentals (F3) | Point-in-time financials or explicit "unreliable" flag | Historical fundamentals API/vendor, or gate strategy from live | P0 | F1 data-sourcing work can share vendor | Medium | Tournament "winner" may be fake signal |
| Cost model parity | Backtest accurate, paper trader flat 0.1% (F4) | Shared cost module, single source of truth | Import `transaction_costs.py` into all paper traders | P0 | None | Low | Paper P&L optimistic vs live reality |
| Testing | Zero unit tests, manual-eyeball bug discovery (F5) | Minimal regression tests on metrics/signal functions | Test harness (pytest) | P1 | None | Low-Medium | Next bug ships to live capital undetected |
| Risk engine | None — per-strategy isolated capital, no kill switch | Portfolio-level exposure/correlation/circuit-breaker | New module | P1 | Needs all 4 strategies stable first | Medium | Concentration risk invisible at go-live |
| Regulatory (SEBI) | Unknown/unchecked, deadline passed (F7) | Confirmed compliant or confirmed exempt | Direct Angel One portal check | P0 | None — pure verification task | Trivial | Illegal live trading if non-compliant |
| Scheduler reliability | Logs blindly, no error surfacing (per PRD) | Fails loudly, alerts on error | Exit-code/keyword check in `run_daily_traders.ps1` | P0 | None | Low | Silent month-long breakage (already happened once) |
| Data lineage | Params duplicated, no run manifest (F8) | Single config source, backtest run tagged to git SHA + data snapshot | Config module + manifest logging | P2 | None | Low | Irreproducible results, silent param drift |
| Shared architecture | 2 codebases, 0 shared library | Common `quantos-core` package (cost model, metrics, config) | Package extraction | P2 | After P0/P1 stabilize | Medium | Bugs get fixed once, recur in the other codebase |
| Broker abstraction | Not built, custom SmartAPI planned | OpenAlgo evaluation before build (already in PRD P1) | Evaluation spike | P1 | Regulatory clarity first | Low (spike) | Wasted glue-code effort if OpenAlgo fits |
| Observability | Plain-text logs only | Structured logs + alert (Telegram already mentioned in research) | Alerting hook | P2 | Scheduler fix first | Low | Failures found late, not in real time |
| Portfolio/allocation logic | Manual, per-PRD Track C at gate | Systematic capital allocation across strategies | Portfolio engine | P2 | Tournament gate result (2026-09-09) | Medium | Ad hoc capital split at go-live |

## 5. QuantOS Roadmap — PRD Becomes Phase 1

The existing PRD's 4 P0 items map directly onto this Phase 1, expanded with F1-F4/F7 findings above (which the PRD's own P0 items reference but don't yet resolve at the code level).

| Phase | Scope | Builds On | New Work | Defer Until |
|---|---|---|---|---|
| **1 — Stabilize existing PRD** | Fix F2 (look-ahead, both engines), F4 (cost parity), F7 (SEBI check), scheduler error-surfacing (PRD P0-1), F1 survivorship-check-or-caveat (PRD P0-2) | All 4 strategies, cost model, scheduler | T+1 fill logic, shared cost import, SEBI portal check | — now |
| **2 — Research Engine** | Single shared library (`quantos-core`): config, metrics, cost model, signal builder — extracted from both codebases without rewriting strategy logic | `transaction_costs.py`, `utils/metrics.py` | Package extraction, one config surface replacing duplicated constants | After Phase 1 P0s clear |
| **3 — Data Engine** | Point-in-time universe membership (fixes F1), corporate-action-adjusted OHLCV, point-in-time fundamentals (fixes F3) | `fetch_universe.py`, `download_data.py` | Historical constituent + fundamentals sourcing — likely requires a paid vendor evaluation (NSE doesn't offer this free) | After Phase 1; gates F1/F3 fixes properly rather than caveat-only |
| **4 — Backtesting Engine** | Testing harness (fixes F5's structural gap), reproducible runs (fixes F8) | `momentum_backtest.py`, `run_all_backtests.py` | pytest suite on signal/metrics functions, run-manifest logging | After Phase 2 (needs shared metrics module to test against) |
| **5 — AI Research Engine** | LLM signal layer — explicitly deferred in PRD's Non-Goals, correctly so per your own research (no verified Indian retail precedent) | — | Genuine R&D track, not adoption of a known pattern | After live capital is stable (per PRD) |
| **6 — Portfolio & Risk Engine** | Cross-strategy exposure/correlation, kill switch, daily loss limit (fixes F6) | Tournament results at 2026-09-09 gate | New module — needs real multi-strategy data to calibrate correlation limits | After Track C gate (PRD's own date) |
| **7 — Live Execution Engine** | Broker abstraction (OpenAlgo eval per PRD P1), order routing, retry logic | PRD's existing Phase 2 (₹1.6-3L live) | OpenAlgo adopt/reject decision, then integration | After Phase 1 + regulatory clearance |
| **8 — Monitoring & Observability** | Structured logs, Telegram/alert hook, dashboard | `run_daily_traders.ps1`, `trader_logs/` | Alerting layer only — logs already exist | Parallel with Phase 7, low cost to add early |
| **9 — Production Hardening** | Security review of API key storage, retry/failover, secrets management | `.env.example` | Move beyond plaintext `.env` before real capital scales past Phase 2's ₹3L | Before Phase 3 (PRD's scale-up) |
| **10 — Continuous Learning** | Systematic strategy retirement/promotion process, using the bench of 12 unpromoted strategies (PRD P2) as real optionality | `trading_backtests/` bench | Formal promotion criteria, not ad hoc | After 6+ months live track record |

**What this roadmap deliberately does NOT do:** rewrite either backtest engine, replace yfinance before a paid-vendor cost/benefit case exists, or start Phase 5's LLM layer before Phase 1-4 are solid. Every phase reuses existing code; new work is additive (shared library, new modules) except where a finding (F1-F4) requires a fix inside existing files.

## 6. Immediate Next Action

Phase 1 has 5 concrete items, all cheap, all P0, none requiring new infrastructure:
1. SEBI/Angel One compliance check (pure verification — do this first, it's a blocker for everything downstream)
2. Fix look-ahead bias (F2) in both `momentum_backtest.py` and `paper_trader.py` — T+1 fill
3. Import `transaction_costs.py` into `paper_trader.py` (kills F4)
4. Flag Quality Factor's live paper P&L as "unresolved look-ahead bias, do not treat +43.8% as reliable until T-006 closes" (F3) — one-line caveat in CONTEXT.md, unblocks nothing but prevents a bad go-live decision at the 2026-09-09 gate
5. Scheduler error-surfacing (PRD P0-1, still open)

None of these require the QuantOS package extraction (Phase 2) to start. Recommend approving Phase 1 scope now, holding Phase 2+ as roadmap-only until Phase 1 closes.
