---
type: learning
date: 2026-07-14
area: self
project: AlgoTrader
status: active
confidence: 0.9
sources: 20
last_confirmed: 2026-07-14
ai_generated: true
supersedes: "india_algo_landscape.md §1, §4, §5 (2026-07-12)"
---

# India Execution Systems — Verified Landscape (2026-07-14)

**Question (Jinu):** are there existing systems that can automatically
trade — algo trade or otherwise — that connect with Indian broker
accounts and execute trades?

**Method:** 4 parallel research agents on primary sources (SEBI/NSE
circulars, broker pricing pages, cloned repos), then 3 adversarial
fact-checkers re-deriving every load-bearing claim. Corrections from
the verify pass are already applied below.

---

## Direct answer: YES — three categories exist. None replaces QuantOS; one changes our broker decision.

### 1. Open-source self-hosted: OpenAlgo — real, works, stays OUT of our order path

github.com/marketcalls/openalgo, AGPL-3.0, v2.0.1.5 (2026-07-10),
daily commits. Verified against the cloned repo: **34 broker plugins
(33 Indian incl. Zerodha + Angel One), real live order code for both,
CNC delivery supported end-to-end**, unified REST API
(`/api/v1/placeorder`, `placesmartorder` with target position size),
genuine sandbox/analyzer mode. AGPL is a non-issue for us (proprietary
QuantOS calling a self-hosted instance over REST at arm's length, no
distribution — GNU FAQ mere-aggregation reading; sound judgment, not
court-tested).

**Verdict (verified SOUND): do not put it in the live order path.**
It's a 2,400-file Flask monolith releasing every 1–2 weeks, CI runs
only 5 of 69 test files, broker session needs a daily web-UI login,
and a global sandbox toggle sits in the money path — enormous surface
area for what is, for us, ~20 REST calls a week that a **~300-line
native adapter** behind our frozen `BrokerAdapter` port covers.
**Role: REFERENCE** — its `broker/zerodha/` and `broker/angel/` trees
are a living map of each API's undocumented quirks; reimplement,
never import. (Repo stays cloned in scratchpad; re-clone anytime.)

### 2. Hosted/no-code platforms: none can run our strategy

Tradetron, AlgoTest, Streak, QuantMan, uTrade Algos, SpeedBot,
Definedge ALGOSTRA — all no-code builders aimed at options/intraday;
**none runs arbitrary custom Python doing a weekly 459-stock momentum
rank**. The one full-code exception, AlgoBulls Python Build, wants our
proprietary strategy code on their cloud at ₹5,310+/month — IP
disclosure + cost for nothing we need. One bookmark: **AlgoTest Trade
Signals** (webhook → CNC delivery orders across 45+ brokers,
~₹100/month) as an emergency fallback execution route if a broker API
is down on a Friday — never the standing path.

### 3. Direct broker APIs: the correct path — and the 2026 facts flip our broker pick

| Broker | Order API | Delivery brokerage | Data | SDK state | Auth automation |
|---|---|---|---|---|---|
| **Zerodha Kite (Personal)** | **Free** (since 24 Apr 2025) | **₹0** | Not on free tier (₹500/mo Connect) | pykiteconnect 5.2.0, active (Apr 2026) | Daily browser request-token — manual step |
| **Fyers** | Free | ₹0 | **Free incl. historical** | fyers-apiv3 3.1.14, active (Jul 2026) | **TOTP fully programmatic, officially sanctioned** |
| Angel One SmartAPI | Free | **min ₹5/order since 17 Nov 2025** | Free but defect-ridden forums | smartapi-python 1.5.5 — **17 months stale** | TOTP programmatic |
| Dhan | Free | ₹0 | ₹499/mo (waived at 25+ trades/30d) | dhanhq 2.2.0, active | 24h token; browser step ambiguity in own docs |

**Decision (verified, adversarially checked): Zerodha PRIMARY, Fyers
BACKUP, Angel One RETIRED.** The old "Angel One because free" rationale
is dead: Angel now charges min ₹5/order on delivery while Zerodha and
Fyers charge ₹0, and Angel's SDK is the worst-maintained of the four.
Zerodha = the account our capital already sits in + free order APIs +
best SDK. Fyers = only fully-free orders+data combo with sanctioned
headless login; open the account at Phase 8 prep so `BrokerAdapter`
gets a tested second implementation. EOD data continues from our own
cache/yfinance (or NSE bhavcopy/Fyers) — nobody pays ₹500/mo for Kite
data.

---

## SEBI compliance — now fully in force, and QuantOS's case is clean

Framework: SEBI circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013
(4 Feb 2025) + extension circular /2025/132 (30 Sep 2025) + NSE
INVG/67858 (5 May 2025) + NSE FAQ (Nov 2025). **Binding on all brokers
since 1 Apr 2026.** Every claim below verified verbatim against those
primary documents.

**The load-bearing fact:** self-developed ("tech-savvy") retail algos
at or below the Threshold Orders Per Second — **10 orders/second per
exchange** — need **NO exchange registration and no Algo-ID
application**. Orders are auto-tagged by the broker as
"registration-free algo" with a generic exchange ID. QuantOS at ~20
delivery orders **per week** is five orders of magnitude below the
threshold. No mock-session participation required for individuals.

**Phase 8 compliance checklist (all broker-side config + order
discipline, zero exchange paperwork):**
1. Static IP, whitelisted with the broker (Zerodha dev console: 1
   primary + 1 optional secondary; ISP add-on or small Indian VPS —
   VPS doubles as always-on runner).
2. OAuth/2FA login per SEBI rule; sessions force-logged-out daily —
   Zerodha needs a browser request-token each trading day (acceptable
   at weekly cadence; Fyers TOTP path is fully headless).
3. **Limit orders only** — plain market orders are prohibited for algo
   flow (NSE MSD/67753 8.1.1.12; Zerodha rejects market-protection=0,
   Angel prohibits market/IOC outright). Execution engine (Phase 6)
   must be designed limit-order-first.
4. Single API key for unregistered-algo flow (only one key may carry
   it), client-side rate cap well under 10 OPS.
5. Immutable local audit trail of every order — already a Constitution
   Part V requirement (`live` module append-only trail).
6. Own/family account only; no third-party money.

**Consequences already encoded in QuantOS docs:** ADR-016's cost model
gets a limit-order execution assumption at Phase 6; the risk table's
"SEBI Compliance Gate" row resolves to "generic algo-ID tagging,
broker-side" for our order rate.

---

## What this changes in the plan

| Item | Old | New |
|---|---|---|
| Automation broker | Angel One SmartAPI ("free") | **Zerodha Kite Personal (free orders, ₹0 delivery, capital already there); Fyers backup** |
| Kite Connect | "Skip — ₹2,000/mo" | Stale: order APIs free since Apr 2025; only the data tier costs ₹500/mo, which we don't need |
| OpenAlgo | "Evaluate before writing SmartAPI glue" (open item) | Evaluated + verified: REFERENCE only, never in the order path |
| Hosted platforms | Unexamined | Ruled out for the strategy; AlgoTest Trade Signals bookmarked as emergency fallback |
| SEBI status | "Check registration status" (open item) | Resolved: registration-free tier confirmed from primary circulars; checklist above is the whole surface |
| Execution engine design | Unconstrained | **Limit-order-first** (market orders prohibited for algo flow) |

## Sources (primary, load-bearing)

- SEBI 4 Feb 2025: sebi.gov.in/legal/circulars/feb-2025/safer-participation-of-retail-investors-in-algorithmic-trading_91614.html
- SEBI 30 Sep 2025 extension: sebi.gov.in/legal/circulars/sep-2025/...-_96979.html
- NSE INVG/67858 (TOPS=10 OPS): nsearchives.nseindia.com/content/circulars/INVG67858.pdf
- NSE Retail Algo FAQ (Nov 2025): nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQ_Retail%20Algo_03112025_NSE.pdf
- Kite pricing: support.zerodha.com/.../what-are-the-charges-for-kite-apis; zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect
- Zerodha algo compliance thread: kite.trade/forum/discussion/15912
- Angel One Nov-2025 pricing: angelone.in/news/product-updates/pricing-update-nov-2025; Apr-2026 API changes: angelone.in/news/market-updates/what-s-changing-in-angel-one-s-smartapi-access-from-april-1-2026
- Fyers free API: support.fyers.in/.../does-fyers-charge-any-subscription-fees-for-trading-api
- OpenAlgo: github.com/marketcalls/openalgo (cloned @ 60db329, v2.0.1.5)

Full agent outputs + fact-check transcripts: workflow `wf_9937e591-a81`
(session archive).
