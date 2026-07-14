---
type: learning
date: 2026-07-12
area: self
project: AlgoTrader
status: active
confidence: 0.7
sources: 3
last_confirmed: 2026-07-12
ai_generated: true
---

# India Retail Algo Trading — Landscape Report

> **⚠ Partially superseded 2026-07-14.** Sections 1 (broker APIs), 4
> (platforms), and 5 (regulation) are superseded by the adversarially
> verified `(AI) India Execution Systems - Verified Landscape -
> 2026-07-14.md` — key flips: Angel One delivery no longer free (min
> ₹5/order since Nov 2025), Kite Personal order APIs free since Apr
> 2025, broker pick is now Zerodha primary / Fyers backup, OpenAlgo
> evaluated → REFERENCE only, SEBI registration-free tier confirmed
> from primary circulars (no Algo-ID needed at our order rate).

**Scope:** Tech/infra, regulation, community, education, strategy patterns — what's real vs hype in Indian retail algo trading right now (2026).

---

## TL;DR — 3 things that should change build/plan

1. **OpenAlgo already exists.** Self-hosted, 2.2k★, actively maintained, unifies 34 Indian broker APIs (incl. Angel One) behind one interface, paper-trading sandbox, options analytics, Telegram alerts. Evaluate before writing more Angel One SmartAPI glue code. `github.com/marketcalls/openalgo`
2. **SEBI's retail algo framework is live now, not future.** Feb 2025 circular, effective 1 Aug 2025, full enforcement 1 Apr 2026: Algo-ID tagging, static IP whitelisting, mandatory 2FA per API session. Broker (Angel One) is compliance gatekeeper. Check registration status before flipping paper → live.
3. **AlgoTrader's 32.9% CAGR backtest needs a re-test.** 2019-2024 spans a bull run; if Nifty500 universe uses *current* constituents rather than *point-in-time* membership, survivorship bias alone can inflate smallcap-heavy backtests ~20-25%.

---

## 1. Broker APIs

| Broker | Cost | Rate limit | Notes |
|---|---|---|---|
| Zerodha Kite Connect | Order/account APIs free (Mar 2025+); data APIs ₹500/mo | 10 req/sec/key; 3,000 instruments/websocket | Best docs, biggest community. Static IP mandatory since Apr 2025. |
| Angel One SmartAPI | Free | 10 orders/sec | Official Python SDK. AlgoTrader's planned path. |
| Upstox API v2 | Free; ₹10/order fee floated (contested) | 25 orders/sec | Reported lag vs Dhan/Fyers. |
| Fyers API v3 | Free | 10 orders/sec | TradingView-native. |
| Dhan (DhanHQ) | Trading free; data ₹499 | 25 orders/sec | Praised as fastest free-tier option. |
| AliceBlue / 5paisa / IIFL | — | — | Thin independent validation, second-tier. |

## 2. Open-source frameworks

- **OpenAlgo** — AGPL-3.0, self-hosted, 34-broker unified REST API, visual builder + Python hosting, options Greeks/Max Pain/IV, ₹1cr sandbox, MCP server. Check license terms for commercial intent.
- **vectorbt** (polakowo) — standard fast vectorized backtester. Prefer over `backtrader` (unmaintained since ~2021).
- **vectorbt-backtesting-skills** (marketcalls) — India-specific, bakes in SEBI Dec 2025 revised lot sizes.

## 3. Data vendors

- Kite historical API (₹500/mo, bundled with Connect)
- TrueData, Global Datafeeds — legitimate NSE/BSE/MCX-authorized, multi-year track record, no vaporware signal.
- Chartink — screener/webhook only, not backtest-grade data.

## 4. No-code/low-code platforms

| Platform | Price | Notes |
|---|---|---|
| AlgoTest | ~₹499/mo | Cheapest with live deployment |
| Zerodha Streak | ~₹500/mo | Largest user base |
| Tradetron | ₹300–1500+/mo | Strategy marketplace model |
| QuantMan | ₹1,300/mo | Markets SEBI-compliance |
| uTrade Algos | Free→₹999/mo | Newer, less proven |

## 5. Regulation — load-bearing

**SEBI circular, 4 Feb 2025**, effective 1 Aug 2025, full enforcement 1 Apr 2026:
- Every API-placed order is legally an "algo order." Below ~10 orders/sec may sit in lighter "regular API user" bucket — this is exactly where AlgoTrader's paper→live transition sits. Confirm classification before going live.
- Algo-ID tagging required per approved strategy.
- Static IP + mandatory 2FA per API session.
- Broker is gatekeeper — register strategy with Angel One, not exchange directly. Angel One had to register ≥1 retail algo strategy by 31 Oct 2025; mock trading mandatory by 3 Jan 2026; new API client onboarding barred from 5 Jan 2026 if non-compliant.
- **Action: check Angel One's retail algo registration portal status now** — dates above have already passed.

**Tax**: momentum/swing profile (days-to-weeks holding) risks reclassification from flat STCG (20%) to business income once trade frequency climbs. Get CA read once volume is non-trivial.

## 6. Community / sentiment (weak signal — flagged)

Web search under-indexes Reddit/Telegram/YouTube retail chatter. Found:
- Recurring complaints: broker API downtime, backtest-vs-live gap, SEBI compliance confusion.
- **Prop firms**: mostly affiliate-marketing noise. Real risk found — **FEMA Section 13 penalty (up to 3x)** for undeclared foreign prop-firm payouts (FTMO etc.). Verify with CA before pursuing Phase 3 Track B.
- Needs manual browse pass on Reddit/Telegram for real signal — not done here.

## 7. Education

- **QuantInsti EPAT** — 6-month, ~₹2L+, most-cited "serious" credential. Reviews split: strong for people with a base already, weak on job-placement promises. No independent completion/outcome data exists industry-wide.
- For someone already building + paper trading a working strategy, a paid cert is optional signaling, not a knowledge gap-filler.

**Books:** Ernest P. Chan — *Quantitative Trading* (2nd ed.), *Algorithmic Trading: Winning Strategies and Their Rationale*.

## 8. Strategy archetypes — viability by capital

| Archetype | Viable at ₹1-10L? | Notes |
|---|---|---|
| Momentum/trend (AlgoTrader's strategy) | Yes | No infra edge needed, scales fine. Best-fit for small capital. |
| Mean reversion (VWAP, Bollinger) | Yes, crowded on liquid names | Better edge on lower-cap names. |
| ORB / MA crossover | Yes, commoditized | Starting template, not an edge. |
| Options selling (iron condor, 9:20 straddle) | Yes, most common retail archetype | Tail risk dominant — smooth backtest, gap/gamma blowup risk. Matches Phase 3 Track C. |
| Pairs trading / stat arb | No | Needs institutional-grade execution retail can't match. |
| VWAP intraday execution | No | Institutional tool, not retail alpha source. |

**Validates AlgoTrader's strategy choice**: momentum-on-Nifty500 is one of the more defensible small-capital archetypes — no institutional infra fight, no options gamma tail risk.

## 9. Backtesting pitfalls — check against own system

1. **Survivorship bias** — current vs point-in-time Nifty500 membership. **Action: verify `momentum_backtest.py` universe is point-in-time.** Highest-value check before trusting the 32.9% CAGR further.
2. **Corporate action errors** — unadjusted splits/bonuses create phantom moves. Verify yfinance cache handles all corporate actions.
3. **Look-ahead bias** — signal computed on close, entered same-day at that close (impossible live). Audit signal-to-entry lag.
4. **Expiry-day gamma** — relevant only for future options overlay.

**Cautionary data point**: a system backtested at 73% win rate, Sharpe >1.5, MaxDD <8% lost ₹80,000 live in six weeks. Generic failure pattern: great backtest, degraded live. AlgoTrader's system (CAGR 32.9%, Sharpe 1.45, MaxDD -18.9%) sits close to where sources flag overfitting suspicion, especially given the bull-run window and survivorship-bias risk.

## 10. LLM-assisted trading — mostly hype

Real current India usage is research-assistant level only (earnings-call summaries, sector Q&A). No credible source of a disclosed, working LLM-signal-generation retail system found. AlgoTrader's planned LLM signal layer (TradingAgents/Vibe-Trading) would be ahead of any verified public practice — genuine R&D, not adopting a proven pattern.

---

## Sources
- SEBI circular (4 Feb 2025): sebi.gov.in/legal/circulars/feb-2025/safer-participation-of-retail-investors-in-algorithmic-trading_91614.html
- github.com/marketcalls/openalgo
- Survivorship bias, Nifty Smallcap 250 (arXiv): arxiv.org/pdf/2603.19380
- QuantInsti EPAT: quantinsti.com/epat
- AlgoTest strategy taxonomy: algotest.in/blog/6-popular-algo-trading-strategies-for-retail-traders-in-india
- Ernest Chan books via QuantStart: quantstart.com/articles/Top-5-Essential-Beginner-Books-for-Algorithmic-Trading

**Gap:** community sentiment (Reddit/Telegram/YouTube) under-researched by web search — needs manual browse pass for real signal.
