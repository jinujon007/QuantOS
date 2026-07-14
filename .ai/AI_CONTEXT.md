# AI_CONTEXT — QuantOS

Executive summary. Grounded exclusively in the Constitution, the Target
Architecture Blueprint, the Independent Audit, the External Repository Due
Diligence review, the OSS Adoption Review, and the Phase 0 execution
history (all dated 2026-07-13, all in `docs/`). Nothing below is invented
beyond those sources.

## What QuantOS is

An institutional-grade automated trading platform for the Indian equity
market, built by a solo operator. QuantOS is not a rewrite of an existing
system — it is the ratified migration target for two disconnected
pre-existing codebases (`AlgoTrader/`, 1 strategy; a sibling 16-strategy
suite) plus one orphan PowerShell scheduler, with zero shared library
between them at audit time.

## Why it exists — the mission

The Independent Audit (2026-07-13) scored the combined system **53/100**
on its Digital Readiness Score, against an institutional bar. The story it
told: research discipline genuinely ahead of retail-hobbyist standard,
sitting inside software infrastructure that is pre-institutional —
portfolio-level Risk scored 10%, Execution 0%, Deployment 0%, Monitoring
0%. QuantOS exists to close that specific gap — a real risk engine with a
kill switch, a real execution engine with an order lifecycle, one shared
library instead of two orphaned codebases, and a point-in-time data
platform. It does not exist to make the research more ambitious.

Two concrete defects drove this: **F1** — the existing backtest evaluates
2019–2024 against a *current* Nifty 500 membership list (survivorship
bias). **F9** — the sibling suite's "universe" function is 96 hardcoded
tickers, hand-picked with hindsight, feeding 2 of its 4 live-tournament
strategies. Both are structural data-access bugs, not one-off code bugs.

## Architecture

Hexagonal (ports & adapters). A pure, deterministic **domain core**
(`factors`, `strategies`, `portfolio`, `risk` math, `validation`,
`analytics` — zero I/O) surrounded by **ports** the domain owns, implemented
by **adapters** that hold all I/O. Dependencies point inward only,
mechanically enforced by a CI import-linter, not convention.

Twenty-one fixed modules: `research · data · factors · strategies ·
portfolio · risk · execution · brokers · paper · live · analytics ·
validation · monitoring · config · storage · services · api · dashboard ·
experiments · tests · tools`. Each traces its existence to a specific,
cited audit finding.

Governing engineering rules: functional core / imperative shell; fail
closed, never fail silent (the audit's worst finding was a silent
`except Exception: return pd.DataFrame()`); determinism is a per-PR CI
gate, not a one-off proof; existing proven logic is migrated verbatim
(strangler-fig), never rewritten for aesthetics.

## External research grounding

- **OSS Adoption Review** (deep dive: Qlib, TradingAgents, and adjacent
  repos, pattern-level): 1 ADOPT (`empyrical`/`pyfolio` for metrics), 7
  ADAPT (reimplement natively — PIT fundamentals/universe, purged CV,
  walk-forward task generator, TopkDropout rebalancing, etc.), 5 REFERENCE
  ONLY. Qlib and TradingAgents are never imported as runtime dependencies.
- **External Repository Due Diligence** (6 repos, repo-level verdict):
  zero ADOPTs, one ADOPT-adjacent. Confirms the same conclusion from a
  different angle — reimplement the useful patterns in native code, don't
  import the frameworks.
- Both independently reject any multi-agent LLM decision core: it breaks
  the audited determinism guarantee the Prospective Validation freeze
  depends on, and no verified Indian-retail precedent exists.

## Roadmap — Phases 0–9 (frozen)

Each phase independently deployable; no phase adds live-capital risk
before Phase 8.

0. **Foundation & Safety** — git baseline, characterization tests, stop-gap
   kill switch. *(Complete.)*
1. **quantos-core skeleton** — extract `config`/`storage`/`utils`(logging)
   with zero strategy-logic change; CI; dependency lockfile.
2. **Data Platform** — `DataProvider` port, point-in-time universe store,
   corporate actions. Closes F1 + F9.
3. **Strategy Platform** — all 20 strategies onto the `Strategy` interface,
   logic unchanged, params externalized to `strategies_registry`.
4. **Risk Engine** — pre-trade gate, portfolio risk monitor, real
   persisted kill switch. Highest-leverage phase.
5. **Validation Hardening** — k-fold/purged walk-forward, automated bias
   detectors as CI gates, experiment tracking (MLflow).
6. **Execution Engine + Paper Broker** — real order lifecycle,
   `PaperBrokerAdapter` only.
7. **Observability + Automation** — structured logs, metrics,
   `AlertSink`, supervised `services`.
8. **Live Broker Integration** — gated on the SEBI/Angel One compliance
   checklist closing first. Staged rollout, smallest capital tranche.
9. **Institutional Hardening** — chaos testing, secret rotation runbook,
   read-only `dashboard`.

The SEBI compliance checklist and a size-factor research question run in
parallel throughout, blocking nothing before Phase 8.

## Status of governing documents

Constitution: **ratified, frozen**. Architecture: **frozen** (per the
Blueprint). Migration roadmap: **frozen** (Phases 0–9). Prospective
Validation: freeze in effect, 0/13 weekly rebalances observed.

## Current position

Phase 0 complete. WP-000 (pre-Phase-1 repository reorganization) complete,
2026-07-13. WP-001 (Repository Foundation — `mypy --strict` on
`quantos_core`, CI-blocking; import-smoke-test scaffold) complete,
2026-07-13. WP-002 (Configuration System) complete, 2026-07-13:
`quantos_core.config` — typed, immutable, strictly-validated `AppConfig`
(one field, `environment`); layering/persistence deferred, reserved as
**WP-006**. WP-003 (Storage Foundation) complete, 2026-07-14:
`quantos_core.storage` — the Constitution's frozen `Repository[T]` port,
`Entity` base model, typed `StorageError`/`EntityNotFoundError`, and
`SqliteRepository[T]` (stdlib sqlite3, transactional, fail-closed reads,
deterministic query ordering). No consumer wiring; no domain aggregates
yet (Phase 4/6). Architectural import-boundary enforcement (Constitution
Part II item 4, ADR-029) remains unmet, reserved as **WP-005**, Medium
priority (TD-010). WP-004 (Structured Logging) complete, 2026-07-14:
`quantos_core.utils` — JSON-lines logging (timestamp/level/module/
event/run-id, sorted keys, exception capture), stdlib-only. **Phase 1's
stated scope (config, storage, utils) is complete.** Next: WP-005,
WP-006, or Phase 2 (Data Platform). See `CURRENT_TASK.md` for exact
scope and `PROJECT_STATE.yaml` for current metrics.
