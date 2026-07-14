---
type: audit-addendum
date: 2026-07-14
extends: "(AI) QuantOS External Repository Due Diligence - 2026-07-13.html"
ai_generated: true
---

# External Repository Addendum — virattt/ai-hedge-fund + HKUDS/Vibe-Trading

Requested by Jinu 2026-07-14 ("i believe these repos are inline with what
we are trying to build"). Neither repo appears in the 2026-07-13 Due
Diligence (verified by full read + grep). Both were cloned (shallow) and
analyzed against QuantOS requirements by independent agents, then
adversarially cross-checked against source. Method and criteria identical
to the 2026-07-13 review.

## Verdicts

| Repo | Verdict | One-line reason |
|---|---|---|
| virattt/ai-hedge-fund (61.6k★, MIT) | **NOT ALIGNED — REFERENCE ONLY** | US-only educational LLM-persona simulator; places zero real orders ("the system does not actually make any trades" — README), zero cost model, no CI, LLM is the decision core |
| HKUDS/Vibe-Trading v0.1.11 (MIT, Beta) | **NOT ALIGNED — pattern quarry, never a dependency** | LLM-codegen research agent, China/US/crypto focus; India support is 4-day-old backtest-only; no Zerodha/Angel One anywhere; its only Indian connectors (Dhan, Shoonya) hard-refuse live orders as the first line of `place_order` |

Both are exactly the architecture ADR-020/ADR-030 already reject: a
multi-agent LLM decision core, non-deterministic by construction. The
2026-07-13 standing rule holds unchanged: fragments only, no framework
ever owns domain logic.

## Key evidence (cross-checked, verbatim where quoted)

**ai-hedge-fund:** decisions emitted by an LLM portfolio-manager agent
(`src/agents/portfolio_manager.py`); LLM failure silently becomes a
"hold" (fail-soft — the exact anti-pattern ADR-007/008 ban); zero
broker/execution code repo-wide; zero transaction costs; ROADMAP marks
point-in-time correctness unfinished; README: "for educational and
research purposes only... Not intended for real trading." Cross-check
nuance: v2 contains a genuine non-LLM `QuantModel` path (PEAD, US-only,
WIP, no execution, empty validation module) — noted for the record,
verdict unaffected.

**Vibe-Trading:** live order placement exists only for
Robinhood/Tiger/Alpaca/OKX/Binance/Futu and is self-described as
"experimental and not verified by us against a real broker account";
Dhan/Shoonya are structurally paper+read-only; no
Zerodha/AngelOne/Upstox code at all; S&P 500 universe uses current
Wikipedia constituents with only a survivorship-bias warning flag; its
`walk_forward_analysis` is post-hoc equity-curve window-splitting, not
out-of-sample re-estimation; the installed `vibe-trading-ai 0.1.9` in
this repo's venv pollutes site-packages with a top-level `src/` package
and lags the repo by two versions.

## Fragments worth harvesting (ADAPT/REFERENCE, native reimplementation only)

1. **India cost-stack cross-check** (`agent/backtest/engines/india_equity.py`):
   STT 0.1% bilateral delivery, stamp 0.015% buy-only, GST 18% on
   (brokerage + exchange txn + SEBI fee), flat DP on sells — independent
   confirmation target for QuantOS's audited Zerodha CNC model (ADR-016).
2. **T+1 same-day-sell block + circuit-band execution refusal** in
   backtest fill logic — QuantOS's engine models neither today; candidate
   for the Phase 5 validation-hardening backlog (non-frozen paths only).
3. **Fail-closed pre-trade gate ordering** (`agent/src/live/order_guard.py`):
   mandate → expiry → kill switch → intent parse → fresh position read →
   limits, all before any broker call; unparseable = DENY. Mirrors
   Constitution Part V; worth copying the *ordering* at Phase 4.
4. **Structural paper/live capping** (`dhan/sdk.py`): a broker API with
   no paper/live discriminator gets hard-capped at paper as the first
   line of `place_order` — directly applicable to the Zerodha-manual
   phase.
5. **OHLC structural validation at the loader boundary** (drop bars with
   high < low, non-positive prices) — cheap addition to Phase 2 data
   platform.
6. **Survivorship bias surfaced as result metadata** — every QuantOS
   backtest over current Nifty 500 constituents should carry an explicit
   flag until the PIT universe store (Phase 2) exists; matches the
   accepted-not-fixed decision record of 2026-07-12.
7. **Never cache a date range ending today** (last bar still forming) —
   relevant to weekly data pulls.
8. (ai-hedge-fund v2) **DataClient protocol + shared contract test
   suite** — pattern for verifying any future NSE `DataProvider` adapter
   against one contract.
9. (ai-hedge-fund) **Negative example for design docs**: LLM failure
   silently mapped to "hold" — the concrete fail-soft anti-pattern the
   Constitution's fail-closed rule exists to prohibit.

## Standing conclusion

QuantOS is *ahead* of both repos on the axes that matter for its goal
(validated NSE strategy, accurate Indian cost model, byte-identical
determinism as a CI gate, frozen prospective validation). Neither repo
shortens the path to live Indian trading; the path remains the frozen
roadmap: Phase 2 data platform → risk engine → execution engine → paper
broker → SEBI checklist → Phase 8 staged live rollout.
