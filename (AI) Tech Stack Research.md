---
type: learning
date: 2026-07-12
area: self
project: AlgoTrader
status: active
confidence: 0.7
sources: 8
last_confirmed: 2026-07-12
ai_generated: true
---

# Automated Trading Infrastructure — India (NSE/BSE/MCX)

Web research pass, 8 domains: broker APIs, OSS frameworks, HF models, data vendors, backtesting, execution layer, SEBI rules, open repos.

**Bottom line:** no single vendor gives full stack. Closest: **OpenAlgo** (self-hosted, AGPL, unifies 30+ Indian brokers) + real backtest engine (NautilusTrader or vectorbt) + compliant broker. SEBI Apr 2026 rules killed "grab API key, run anywhere" — broker choice now compliance decision first, cost second.

**Relevant to this project:** already on Zerodha (manual) + Angel One SmartAPI (auto) per [[CONTEXT]]. Angel One confirmed free API, ~₹20/order F&O, transparent rate-limit docs. Worth checking Angel One's SEBI Algo-ID / static-IP compliance status before automation goes live (Apr 2026 deadline).

---

## 01 — Broker APIs

| Broker | Cost | Notes |
|---|---|---|
| Zerodha Kite Connect | orders free; data API ₹500/mo | best docs, biggest community, reference standard |
| Upstox | free API, ~₹10/order (promo, verify) | half Zerodha's per-order cost |
| **Angel One SmartAPI** | free API, ~₹20/order F&O | **current pick** — transparent docs |
| Fyers | free API + free data | stable SDKs, cited often |
| Dhan | free, 20k req/day cap | sub-second execution claims |
| Shoonya (Finvasia) | zero brokerage + free API + zero AMC | cheapest total cost, thinner docs |

Groww: **no public API found** — confirmed absent, don't assume.

## 02 — Open-Source Frameworks

- **OpenAlgo** (marketcalls/openalgo) — active, AGPL, 30+ Indian brokers unified, OMS + options Greeks/OI/max-pain. Strongest single find.
- **NautilusTrader** — active, ~23k★, production-grade, no native India adapter (build own).
- **vectorbt** — fast vectorized backtesting; community fork adds TA-Lib + QuantStats for India.
- **backtrader** — unmaintained. Backtest-only, not live-safe.
- **jugaad-data** — active, free NSE/RBI historical+live data, pairs with any engine above.
- QuantConnect Lean: no India/NSE support found. Skip.

## 03 — ML / Hugging Face

Thin. ProsusAI/finbert (general sentiment baseline). Small India fine-tunes (Vansh180/FinBERT-India-v1, kdave/FineTuned_Finbert) — low signal, unverified. No NSE-tuned price-forecasting model found.

## 04 — Data Vendors

- yfinance — free, `.NS` suffix, fine for EOD, unreliable intraday, unofficial.
- TrueData / Global Datafeeds — paid, authorized NSE/BSE/MCX, tick-level + Greeks.
- Kite historical API — ₹500/mo, best if already on Zerodha.

## 05 — Backtesting

No India-native standalone engine. Pattern: jugaad-data/Kite/TrueData → vectorbt or NautilusTrader as generic OHLCV feed. OpenAlgo bundles backtest layer wired to Indian instruments incl. options Greeks.

## 06 — Execution Layer

Retail colocation irrelevant at this scale. OpenAlgo only OSS project functioning as real OMS+risk layer across multiple Indian brokers. Rest (AlgoTest, Stratzy, uTrade Algos) commercial, not OSS.

## 07 — SEBI Regulatory Floor (load-bearing — check against project timeline)

- **5 Jan 2026** — non-compliant brokers barred from onboarding new API clients.
- **1 Apr 2026** — full framework mandatory. Every algo order needs exchange-assigned Algo-ID tag.
- **Open APIs disallowed** — client-specific keys + broker-whitelisted static IP only.
- Algo providers (incl. solo devs) must operate through registered broker, no direct exchange access.

Action: confirm Angel One's compliance status + static-IP whitelisting process before this project automates live execution.

## 08 — Open-Source Full-Stack Examples

- marketcalls/openalgo — best-in-class, only one with real ongoing maintenance.
- buzzsubash/algo_trading_strategies_india — option-selling strategies, Zerodha-only.
- srikar-kodakandla/fully-automated-nifty-options-trading — Selenium-based (ToS risk, illustrative only).
- yugeshk/Zerodha_Live_Automate_Trading — exploratory quality.

---

## Next question

Does OpenAlgo replace or wrap the current Angel One SmartAPI integration in this project? Worth a scoping pass before automation phase.

## Sources
AlgoTest broker guide · IndianBrokerTest API comparison · Pocketful free-API roundup · Sahi SEBI 2026 rules brief · AlgoBulls SEBI blog · FinSecLaw tracker
