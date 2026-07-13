---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.85
sources: 4
last_confirmed: 2026-07-13
ai_generated: true
---

# The QuantOS Constitution

**Status:** Ratified. Architecture frozen (per *QuantOS Target Architecture Blueprint*, 2026-07-13). Migration roadmap frozen (Phases 0–9). Prospective Validation freeze in effect (0/13 weekly rebalances). This document does not propose architecture — it codifies the architecture, roadmap, and risk design already decided, into permanent standards every future line of QuantOS code must obey.

**Inputs this document is grounded in, with nothing invented beyond them:**
- *QuantOS Independent Audit* (2026-07-13) — DRS 53/100, ground-truth subsystem inventory
- *QuantOS Target Architecture Blueprint* (2026-07-13) — hexagonal architecture, 21 modules, Phases 0–9
- *QuantOS OSS Adoption Review* (2026-07-13) — Qlib/TradingAgents evaluation
- *QuantOS External Repository Due Diligence* (2026-07-13) — 6-repo evaluation, zero ADOPTs, one ADOPT-adjacent

**How to read this document:** it is implementation-independent. It says what must be true, not which line of code makes it true. Where the source documents left a gap, this document closes it with an explicit decision, marked as such — never silently.

---

## PART I — Vision

### Mission

Close the one asymmetry the Independent Audit identified as QuantOS's entire story: research discipline that is genuinely ahead of retail-hobbyist standard, sitting inside software infrastructure that is pre-institutional (Risk 1/5, Execution 0%, Deployment 0/5, two disconnected codebases, zero shared architecture). QuantOS exists to make the software match the research, not to make the research more ambitious. Nothing in this Constitution asks for more strategy sophistication — it asks for the four things the audit found completely or almost completely absent: a real risk engine with a kill switch, a real execution engine with an order lifecycle, one shared library instead of two orphaned codebases, and a point-in-time data platform that makes fabricated or current-only universes structurally impossible.

### Engineering Philosophy

- **Functional core, imperative shell.** Signal math, sizing math, and risk math are pure — same input, same output, zero I/O, trivially unit-testable. All I/O lives in adapters at the edge, never in domain code.
- **Fail closed, never fail silent.** An ambiguous state — a broker that stops responding, storage that can't be read, a risk calculation that can't complete — defaults to blocking action, never to guessing and proceeding. The audit's worst-scoring finding (`download_data.py:64`, a silent `except Exception: return pd.DataFrame()`) is the anti-pattern this rule exists to permanently prohibit.
- **Determinism is a product requirement, not a nicety.** Every strategy replay must be byte-identical, every run, forever. This was proven once, by hand, for Momentum. The Constitution requires it be true, automatically, for every strategy, on every PR.
- **Boring and proven beats novel.** The current backtest engine is audited, look-ahead-free, and deterministic — it is retained, not replaced, by policy (ADR-021). New infrastructure is added only where the audit found a specific, cited gap, never to resemble a bigger platform.
- **One source of truth, everywhere.** One cost model. One metrics module. One universe provider. One config surface. The audit's recurring root cause — the same bug fixed once, then found again in a second codebase — is treated as the single most expensive failure mode in the system's history, and this Constitution's dependency rules exist specifically to make it structurally impossible going forward.

### Research Philosophy

- **Falsification, not confirmation.** The CAPM → two-factor → three-factor chain that found its own edge case (alpha loses significance on the only fair post-2021 window, p=0.23) is not a one-off audit exercise — it is the required standard of evidence for every strategy before live-eligibility, not just Momentum.
- **Report the failed test as the headline, not the footnote.** A strategy's own closure summary reporting its own weakest result, honestly, is the behavior this Constitution protects and requires — burying a null or marginal result is a Definition-of-Done violation (Part VII), not a style preference.
- **Point-in-time by default, current-data by exception.** Every data access answers "what was knowable as of this date," never "what do we know now," unless a caller explicitly and visibly asks for current state.
- **Survivorship bias is disclosed or it is fixed — never silently present.** F1 and F9 were both survivorship bias hiding behind code that looked like a real data fetch. The Constitution's data standards (Part IV) make that class of bug detectable by an automated check, not by a manual audit that has to happen to catch it.

### Product Philosophy

- **Institutional discipline, retail-appropriate infrastructure — never the reverse.** "Institutional-grade" describes correctness, reproducibility, and auditability. It does not describe Kubernetes, a distributed data warehouse, or multi-region deployment for a four-strategy, weekly-rebalance, ₹4L book. Every infrastructure decision in this Constitution states its own upgrade trigger in advance, so scaling up is a documented decision, never an unplanned rewrite.
- **Paper trading is a rehearsal of live, not a separate simulation.** The same execution pipeline, the same order lifecycle, the same risk gate runs in both — only the `BrokerAdapter` implementation differs. Going live is a config change and an adapter swap, never a second system.
- **The operator is one person.** "Code review" for a solo operator is a mandatory checklist (Part VIII), not a second human. Every process defined in this Constitution must be executable by one disciplined person, not a team.

### Long-Term Principles

1. Dependencies point inward, always. Adapters depend on ports; the domain never imports a concrete adapter. This is the single rule from which most of Part II follows.
2. A deviation from a default in this Constitution is not forbidden — it is required to be an ADR, so the decision is visible, dated, and reviewable, never silent.
3. Existing, proven logic is preserved verbatim through migration (strangler-fig, ADR-003), not rewritten for aesthetic reasons.
4. Complexity requires justification traceable to a cited gap. A module, a dependency, or an abstraction that does not close a specific finding does not belong in QuantOS.
5. Nothing is "done" without repository evidence — a test that runs in CI, a golden file, an ADR, a metric. Verbal or documentation-only claims of completeness are not evidence (Part VII).

### Explicit Non-Goals

These are permanent exclusions, not "not yet." Reversing any of them requires a new ADR with an explicit trigger condition met — not a preference change.

- **Kubernetes**, or any multi-host/multi-region deployment, until the stated trigger (multiple hosts needed for latency/redundancy, or >5 services needing independent scaling) is actually met. Docker Compose on one host is the permanent default until then.
- **Any multi-agent LLM decision-making core.** TradingAgents-style agentic debate frameworks are rejected outright (ADR-020, ADR-030) — they break the determinism guarantee this Constitution treats as non-negotiable, and no verified Indian-retail precedent exists to justify the risk.
- **LangGraph, or any general-purpose agent-orchestration framework**, as a runtime dependency. QuantOS's actual current "workflow" is a handful of scripts and a scheduler; adopting a framework built for graphs of autonomous agents is complexity years ahead of the real need.
- **Qlib, zipline, or backtrader as runtime dependencies.** Qlib's ML-infrastructure weight is roughly two orders of magnitude beyond what this codebase needs; the current backtest engine is audited, proven look-ahead-free, and deterministic — swapping it reopens a correctness risk that was just closed.
- **VaR/CVaR as the primary, hard risk gate** before the live track record has the return-history depth and regime stability such a statistic requires. Blunt, explainable limits (Part V) are the primary gate; VaR/CVaR are computed and reported, never load-bearing, until an ADR states otherwise with evidence.
- **A public-facing API or dashboard.** The `api` module binds local-only by default; public exposure is a separate, explicitly-reviewed ADR, not a default.
- **A dashboard before there is real telemetry to show.** Sequenced last (Phase 9) by design — building observability UI before `monitoring`/`risk`/`analytics` exist to feed it is the kind of premature complexity this Constitution exists to prevent.
- **Event-sourcing or a message bus.** State changes go through `storage` repositories with transactional guarantees; "events" in this system are structured log lines and metrics (Part II, Event Design), not a pub/sub architecture. No message broker is in scope.
- **Derivatives pricing math (Heston/Lévy/PIDE/Kalman/Bates) or any quant-desk-scope modeling** unconnected to the actual strategy set. Rejected per the Due Diligence review — no connection to a rules-based retail system.
- **Replacing the SEBI compliance checklist with an engineering workaround.** It is a pure verification task, has no engineering dependency, and no phase in this roadmap substitutes for it (Part IX).

---

## PART II — Architecture Principles

### Hexagonal Architecture Rules

QuantOS is built on Clean/Hexagonal architecture: a pure, deterministic **domain core** surrounded by **ports** (interfaces the core owns) implemented by **adapters** (all I/O and side effects).

1. Dependencies point inward only. Adapters depend on ports. Ports are owned by the domain. The domain never imports a concrete adapter class.
2. The domain core (`factors`, `strategies`, `portfolio`, `risk` math, `validation`, `analytics`) contains zero I/O. No network call, no file write, no broker call originates there.
3. All I/O — network, disk, broker, alert — lives in adapters, invoked only from `services`.
4. This rule is enforced mechanically, by a CI import-linter, not by convention or code review discipline alone.
5. A strategy may only obtain a universe, a price series, or a fundamental value through a `DataProvider` port call — it cannot define, hardcode, or fetch one itself. This structurally forecloses the exact failure mode that produced F9 (a fabricated 95-ticker "universe").

### Domain Ownership

Twenty-one modules, each with a fixed purpose, fixed dependency set, and fixed interface, specified in the Blueprint and not subject to informal renegotiation:

`research` · `data` · `factors` · `strategies` · `portfolio` · `risk` · `execution` · `brokers` · `paper` · `live` · `analytics` · `validation` · `monitoring` · `config` · `storage` · `services` · `api` · `dashboard` · `experiments` · `tests` · `tools`.

Each module owns its responsibilities exclusively. No other module reaches into its internals — only its published interface. A module's "why it exists" traces to a specific, cited audit finding (Blueprint §2/§5); a module that cannot make that trace does not get added.

### Module Independence

- `services` are thin. They wire config, storage, and concrete adapters via dependency injection at process start, and run one module's orchestration on a schedule or as a daemon. They contain **no business logic**.
- `experiments` and `tools` are dependency **leaves**. They may import `quantos_core` freely; nothing in `quantos_core` or `services` may import from them, ever. Enforced by the same CI import-linter as the hexagonal rule. This is what stops a research script or an ops one-off from silently becoming a production dependency — exactly what happened when 18 audit/research markdown files and production strategy code shared one flat folder.
- Each `service` fails and restarts independently. No service's crash blocks another's schedule — the permanent replacement for the single orphan PowerShell script that hardcoded paths into two unrelated codebases.

### Dependency Rules

```
services  →  quantos_core.*  →  quantos_core.utils
```

Within `quantos_core`:
- `risk` / `portfolio` / `execution` depend on `strategies` / `factors` / `data` ports — never the reverse.
- `brokers` depends on nothing else in the tree except `utils`.
- `monitoring` has **no upward dependency** — every other module depends on (emits to) `monitoring`; a monitoring outage can never block a trading decision.
- `config` and `storage` are near-leaves other modules depend on, not the reverse.
- `experiments` and `tools` are terminal leaves (see above).

### Interface Contracts

- `Strategy(Protocol)`: `generate_signals(ctx: StrategyContext) -> TargetWeights`, plus `metadata() -> StrategyMeta`. One strategy = one class implementing this protocol + one YAML entry in `strategies_registry`. Adding strategy 21 never touches an existing file.
- `BrokerAdapter`: **interface-segregated**, not one fat interface. Order placement, market data, and account/margin queries are separate protocols a given adapter composes — a data-only context is never forced to stub out order methods it cannot support.
- `Repository[T]`: `get(id) -> T · save(entity) · query(filter) -> list[T]`, one repository per aggregate (portfolio, orders, trades, kill-switch).
- Any `BrokerAdapter` implementation (Paper, Zerodha, Angel One, future IBKR) must be substitutable in the execution engine with zero caller-side branching (Liskov). This is the mechanism that makes paper trading a genuine rehearsal of live, not a lookalike.
- A new port requires an ADR. Ports are not added casually — each one is a permanent seam in the architecture.

### Event Design

QuantOS does not use event sourcing or a message bus (Part I, Non-Goals) — that is unjustified complexity at four-strategy, weekly-rebalance scale. "Events" in this system are:

- **Structured log lines** (JSON, one event per significant state transition — order submitted, fill received, kill switch engaged, risk gate rejection), emitted by the module where the transition occurred.
- **Metrics** (`monitoring.emit_metric(name, value, tags)`), pushed by every module that has something worth counting or timing.
- **Alerts** (`AlertSink.alert(severity, message)`), routed through `monitoring`, for anything that requires operator attention.

There is no in-process pub/sub, no event replay mechanism beyond the deterministic-replay test harness (Part IV), and no cross-service event bus. A module that needs another module's state reads it through that module's `Repository`, not by subscribing to its events.

### Configuration Standards

- Layered load order: `base.yaml` → environment overlay (`dev`/`paper`/`live`) → environment variables (secrets **references** only, never values) → schema validation (pydantic).
- Produces **one immutable config object**, once, at process start. Never re-read mid-run.
- Invalid or missing required config refuses to start the process — a loud failure at boot, never a silent surprise mid-rebalance.
- Zero bare numeric literals inside `quantos_core/strategies/` — enforced by a CI lint rule. Every threshold, window, or constant is sourced from `config` or `strategies_registry`.
- A config change to a risk threshold or strategy parameter is a reviewable diff in a YAML file, never a code edit.

### Versioning Strategy

- **Platform versioning:** SemVer tags on `quantos_core`, one version for the whole repository (single package, Part III — Packaging). Not independently versioned per service.
- **Strategy versioning:** a separate axis entirely. Each strategy's params/logic version lives in `strategies_registry`, git-diffable. This is what the Prospective Validation freeze actually gates — "restart the validation clock" has a precise, git-diffable trigger, never a judgment call.
- A strategy's registry entry changing is, by definition, a new strategy version and (per the currently active freeze rule) restarts its observation clock unless an ADR explicitly states otherwise for that change.

---

## PART III — Engineering Standards

### Python

- One interpreter version pinned exactly in the lockfile; a minimum of Python 3.11 across the whole repository (typed generics, exception groups, and `tomllib` all assumed available). Reviewed annually, bumped deliberately, never silently by a fresh `pip install`.
- No per-service Python version drift. One interpreter version, one repository.

### Typing

- `mypy --strict` on all of `quantos_core`. Not advisory — a CI-blocking gate (Part III, CI/CD).
- Every public function and class in `quantos_core` carries type hints. `Any` is permitted only at the outermost adapter boundary where untyped external data (a JSON API response, a CSV row) first enters the system, and must be converted to a typed domain object before crossing into `quantos_core` proper.
- Interfaces are `Protocol`s (`Strategy`, `BrokerAdapter`, `DataProvider`), not ABCs with inheritance — matches the composition-over-inheritance shape already established by the module specs.

### Dependency Injection

- No DI framework or container library. Composition is manual and explicit: `config = load_config(env); container = wire(config); container.run()` — one composition root per service, readable top to bottom without a framework's indirection.
- Concrete adapters are chosen once, at process start, by the composition root — never constructed inside domain code.

### Logging

- Structured (JSON lines), not plain text. Fields: timestamp, level, module, event, correlation/run-id, plus event-specific data.
- Every unattended process emits at least one log line and one metric per significant action (Definition of Done, Part VII).
- Never log secrets, credentials, or full order/account payloads containing sensitive account identifiers beyond what's needed for the audit trail.

### Error Handling

- Typed exceptions only (`DataFetchError`, `BrokerConnectionError`, `RiskLimitBreach`, `StorageError`, `OrderRejectedError`, etc.). `except Exception:` with no re-raise and no log is a permanently banned pattern — the single most-cited engineering defect in the Independent Audit.
- Every catch either re-raises or logs at the appropriate level **and** routes through `AlertSink` if it's operator-actionable. Never both silent and swallowed.
- Ambiguous state on anything touching capital or orders defaults to the safest, most restrictive action (fail-closed, Part V) — never to an optimistic guess.

### Testing

Full pyramid, detailed in Part IV/VII; CI-blocking subset: lint (ruff) + type-check (mypy strict) + unit + property + integration + bias-detector suites. Chaos and stress run on a schedule, not per-PR, and page the operator on regression — never silent.

- ≥90% coverage target on `factors`/`strategies`/`portfolio`/`risk` pure math.
- Every sizing/risk function gets property tests for its numeric invariants (e.g., "position sizes never exceed 100% deployed capital," "no size is ever negative").
- A flaky test is a bug in the test or the code's determinism — never silenced with a retry loop.

### Documentation

- Every module's spec follows the fixed template already established for the 21 canonical modules: purpose, why it exists (traced to a finding), responsibilities, inputs/outputs, dependencies, interface, configuration, error handling, failure & recovery, testing. A new module proposal without all nine fields is incomplete.
- An ADR is mandatory for any decision that overrides a default in this Constitution (a risk threshold change, a new dependency, a new port).
- Docstrings are required on every public interface in `quantos_core`; internal/private functions are documented only where the *why*, not the *what*, is non-obvious.

### Profiling

- No APM or distributed tracing platform (non-goal — matches the infrastructure-minimalism principle; a single-process, single-host system doesn't need distributed tracing).
- Performance-sensitive paths (pre-trade risk gate at full-universe scoring, backtest engine on the full historical window) are profiled as part of the stress-test suite (Part III, Testing), not continuously in production.
- Timing is captured via `monitoring.emit_metric`, not a separate profiling stack.

### Performance

- No numeric SLA has been measured yet on any path — the Independent Audit found none, and this Constitution does not fabricate one as fact. It sets a **default target, explicitly tunable via config/ADR, in the same style as the Part V risk thresholds**: the pre-trade risk gate should complete in under 200ms at full 500-name universe scale. This is a stated policy default, not a benchmarked measurement — the stress-test suite (Part III, Testing) is the mechanism that turns it into a verified number before Phase 4 (Risk Engine) is marked done.
- Backtests and walk-forward runs have no hard latency requirement (offline, batch); they are expected to complete within a single operator session (same-day), a soft target reviewed if it stops holding.

### Security

- No secret is ever committed to git, in any form, in any file — including `.env`, YAML, or a code comment.
- Every credential is referenced from the OS-level secret store (Windows Credential Manager locally, the hosting provider's secret manager if deployed) and injected at process start.
- Least privilege on every broker/API credential — scoped to only the operations the adapter actually performs.
- The `api` module binds local-only by default; any public exposure is a separate, explicitly-reviewed ADR, never a default flip.
- Auth failure, rate-limit breach, and session expiry are distinct typed exceptions so `risk`/`execution` can react differently (Part V).

### Configuration

(Coding-level practice; system-level design is Part II.) No magic numbers in `quantos_core/strategies/` — CI-enforced. Config schema-validated at boot; invalid config is a boot-time failure, never a runtime surprise.

### Secrets

Rotation runbook lives in `docs/`, not tribal knowledge. Broker keys rotate at minimum on every SEBI-mandated interval. `.env.example`'s current dead-code status (nothing loads it — audit-confirmed) is retired entirely in favor of a real secret-store loader; template `.env` files are never treated as a secrets mechanism.

### Packaging

- One `pyproject.toml`, one lockfile, for the whole repository. Not one per service.
- One repository (`quantos/`), not a multi-repo split. `services` import `quantos_core` as an internal package; they are not independently published.
- A clean checkout must be reproducible from the lockfile alone, on a clean machine, with no undocumented manual step — the specific gap the audit found in AlgoTrader's original `requirements.txt`-less state.

### Repository Structure

Fixed, per the Blueprint, not subject to ad hoc reorganization without an ADR:

```
quantos/
├── pyproject.toml
├── quantos_core/        # config, data, factors, strategies, portfolio, risk,
│                         # execution, brokers, paper, live, analytics,
│                         # validation, monitoring, storage, utils
├── services/             # thin deployable entry points
├── dashboard/             # read-only UI over api — built last (Phase 9)
├── experiments/            # dated research output — leaf, never imported
├── strategies_registry/     # versioned YAML params — single source of truth
├── tests/                    # unit / integration / regression / property / chaos
├── tools/                     # one-off ops scripts — leaf, never imported
├── infra/                      # Dockerfiles, compose, CI config
└── docs/adr/                    # Architecture Decision Records
```

### Naming

- Modules and functions: `snake_case`. Classes and `Protocol`s: `PascalCase`.
- Typed exceptions: suffixed `Error` (`DataFetchError`, `RiskLimitBreach` is the one deliberate departure — name for what happened, not the class hierarchy, when it reads clearer to an operator scanning a log).
- Ports/adapters follow the established suffix convention: `*Provider` (data source), `*Adapter` (broker/external system), `*Sink` (outbound alert/event channel), `Repository[T]` (persistence). A new port that doesn't fit one of these suffixes is a signal to reconsider whether it's really a new port.

### Code Complexity

- No god-modules. One strategy = one class implementing `Strategy`. The audit's confirmed anti-pattern — 16 independent, copy-pasted scripts, zero shared class — is permanently prohibited by the Open/Closed rule (Part III, engineering standards) and the `strategies` module's registry design.
- Cyclomatic complexity is linted (ruff/mccabe); a function tripping the threshold is refactored or explicitly justified in review, not silently merged.
- A pure function in `factors`/`portfolio`/`risk` math that needs more than a page to read is a signal the abstraction is wrong, not that it needs more comments.

### CI/CD

Push → lint + typecheck + test (CI-blocking subset, Part III/Testing) → build Docker image, tag with commit SHA → (main only) manual approval → deploy by pulling the tagged image. Rollback = redeploy the previous SHA-tagged image; image immutability makes this a one-command action, never a re-debug session.

Trunk-based development. Protected `main`. Short-lived feature branches, one concern each. "Review" for a solo operator is a mandatory PR-template checklist (Part VIII), not a second human.

### Release Process

1. Tag `quantos_core` with the next SemVer per its own change (Part II, Versioning).
2. CI builds and tags the image with the commit SHA.
3. Manual approval gate on `main` (the solo operator's own deliberate go/no-go, not a rubber stamp).
4. Deploy by pulling the tagged image; no other deploy path exists.
5. Post-deploy smoke test (Part VII, Production Release DoD) before the release is considered live.
6. Rollback plan (previous SHA tag) is confirmed available *before* deploying, not discovered during an incident.
7. Strategy releases are independent of platform releases — a `strategies_registry` version bump does not require a `quantos_core` release, and vice versa.

---

## PART IV — Quant Research Standards

### Point-in-Time Data

Every data access is `as_of`-parameterized by default. `get_universe(as_of) -> list[Ticker]`, `get_fundamentals(ticker, as_of) -> Fundamentals` — there is no "current" overload without an explicit, visible parameter naming it as such. This is the structural fix for F1 and F9: a strategy cannot accidentally receive today's constituent list when it asked for 2019's.

### Universe Construction

Universe membership comes from one point-in-time index-membership store, owned by `data`, used by every strategy in the platform. No strategy — none of the current 20, none added later — may define, hardcode, or independently fetch its own universe. `data_loader.py`'s 95-ticker hardcoded list is the permanently prohibited pattern this rule exists to prevent from recurring in any form.

### Survivorship Bias

Detected automatically, not manually. The `validation` module's bias-detector suite includes a survivorship-bias check that runs on every backtest in CI, not as a one-off audit pass. A bias-detector failure is a **hard error** for that backtest run, never a warning buried in a report — this is the check that would have caught F9 automatically instead of requiring the manual audit that eventually did.

### Look-ahead Bias

The `assert fill_date > signal_date` invariant, currently hand-written in `momentum_backtest.py`, is generalized into a bias detector that runs on every strategy, every backtest, in CI, on every PR — not once, manually, per strategy. Mutation-tested: CI deliberately reintroduces the pre-fix same-day-fill logic periodically and asserts the detector still catches it.

### Purged Cross Validation

Purged/embargoed k-fold cross-validation, reimplemented natively in `validation` (per the Due Diligence review's ADAPT verdict on the purged-CV pattern) — not imported as a framework dependency. Replaces the current single 3yr/3yr train/test split, which the audit correctly flagged as thin.

### Walk-forward Analysis

k-fold/rolling walk-forward, extending the existing single-split design (reference pattern: Qlib's rolling-window walk-forward task-generator, reimplemented, not imported — Due Diligence REFERENCE verdict). Every strategy that reaches live-eligibility review must pass walk-forward validation on the multi-fold design, not the single split.

### Statistical Validation

The falsification chain applied to Momentum — one-factor CAPM → multi-factor with confound control → out-of-sample/regime-restricted window — is the **mandatory minimum standard of evidence** for any strategy before it is eligible for live capital, not a one-off audit exercise applied to a single strategy. A strategy that has not survived this chain, or whose survival is undocumented, is not live-eligible regardless of its backtested Sharpe.

### Benchmarking

Primary benchmarks: Nifty 50 (broad market) and Nifty 500 (universe-matched). Any strategy whose universe includes mid/small-caps must also be tested against a size-matched benchmark (e.g., Nifty Smallcap 250) to rule out a risk-premium confound before its alpha is reported as "genuine skill" — directly required by Momentum's own still-open size-factor question.

### Cost Modeling

One `CostModel` port, one implementation (the audited, accurate Zerodha CNC model: STT/stamp/exchange/SEBI/GST/DP), used by every strategy — paper and live alike. A second, independent cost implementation anywhere in the codebase is a review-blocking finding, not a style preference; this is the direct fix for F4 (3 of 4 live strategies previously used flat, inaccurate cost constants).

### Slippage

The `execution` module models explicit slippage assumptions in paper mode (sourced from `config`, never hardcoded) and computes realized execution-quality metrics (slippage vs. expected) on every fill, in both paper and live modes, so paper-mode cost realism is measured against reality, not assumed.

### Corporate Actions

`data` applies corporate-action adjustments (splits, bonuses, dividends) before any price series reaches a strategy or the backtest engine. This is a `data`-module responsibility exclusively — no strategy or backtest script performs its own ad hoc adjustment.

### Experiment Tracking

MLflow, adopted **directly** as a dependency at Phase 5 (Due Diligence ADAPT verdict — Qlib's `Recorder` is a thin wrapper around MLflow that adds indirection with no benefit at this scale). Every backtest and walk-forward run is tracked: params, code SHA, data snapshot, results.

### Reproducibility

Byte-identical deterministic replay of every strategy's full historical run is a **CI gate on every PR**, not a one-off manual proof. This generalizes the audit's own verified method (hash-seed-varying determinism checks, 3 consecutive byte-identical runs) from 5 hand-written scripts to the entire strategy set, automatically, forever.

### Dataset Versioning

Every experiment produces a dated, immutable folder under `experiments/YYYY-MM-DD-slug/` with a `manifest.yaml` recording the question, method, findings, and the git SHA of the code that produced it. `experiments/` is a dependency leaf (Part II) — nothing in `quantos_core` or `services` may ever depend on a specific experiment's output; a finding only enters production logic through a reviewed, ADR-logged change to `strategies_registry` or `quantos_core` itself.

---

## PART V — Risk Engineering Standards

All thresholds below are **config-tunable policy defaults**, not fixed constants — but changing any of them requires an ADR, per ADR-025. They are deliberately blunt: VaR/CVaR need return-history depth and regime stability a sub-one-year live track record does not yet have, so a false-precision statistical gate on immature data is explicitly rejected as the primary control (Part I, Non-Goals; ADR-027).

| Control | Default Threshold | Action on Breach |
|---|---|---|
| **Position Limits** — single-name | 15% of book NAV | Pre-trade gate rejects the order; no partial override without config change + ADR |
| **Exposure Limits** — sector | 30% of book NAV | Pre-trade gate rejects new same-sector orders past limit |
| **Portfolio Constraints** — cross-strategy correlated exposure, single name | 20% of book NAV, aggregated across all live strategies | Portfolio risk monitor blocks a new order from **any** strategy that would breach the aggregate, not just its own book (this is the direct closure of F6) |
| **Drawdown Controls** — from high-water mark | −20% (matches the existing backtest MaxDD threshold) | Strategy flagged for mandatory human review; does **not** auto-liquidate — logged, human-decided |
| **Circuit Breakers** — daily loss, soft | −3% NAV intraday | Halt new order generation, alert operator; existing positions untouched |
| **Circuit Breakers** — daily loss, hard | −5% NAV intraday | Global kill switch engages |
| **Liquidity Checks** — single order vs. average daily volume | No order exceeds 5% of the name's 20-day ADV *(placeholder default — not yet calibrated against real liquidity data; confirm via ADR before Phase 8 live rollout)* | Pre-trade gate rejects or truncates the order |
| **Broker Failure Recovery** — health check | 3 consecutive failed heartbeats within 60s | SAFE_MODE: block new orders, alert; existing positions deliberately left alone (auto-flattening into a disconnect-induced bad quote is its own failure mode) |
| **Broker Failure Recovery** — session expiry | Any auth/session failure | Automatic re-auth attempt; repeated failure → SAFE_MODE + immediate alert, never a silent stop |
| **Broker Failure Recovery** — ambiguous fill state | Broker unresponsive mid-order | Order marked `UNKNOWN` (never assumed filled or cancelled); reconciliation required before that ticker trades again |
| **SEBI Compliance Gate** | Algo-ID tag required per current registration status | Pre-trade gate rejects any order missing a valid Algo-ID once registration is required |

### Kill Switches

One global, **persisted** boolean (survives process restart — a flag in `storage`, never in memory), checked by the pre-trade risk gate before every single order, in every service, with **no bypass path**. Settable automatically (daily-loss hard breach, data-quality failure, broker health failure) or manually via an operator CLI runnable from anywhere. This is the single control the Independent Audit found most conspicuously absent (F6, 0/5 subsystem score) and the highest-leverage piece of infrastructure in the entire platform.

### Market Holiday Handling

Not explicitly specified in the source audit trail — resolved here explicitly: the `Clock` port is the single, NSE-trading-calendar-aware source of truth (holidays, half-days) for every module that needs "is today a trading day." No strategy or service maintains its own calendar logic. This closes a class of bug adjacent to the "timezone bug fixes" the audit already found and praised as a preserved good pattern — the calendar problem is the same shape and deserves the same one-source-of-truth treatment before it recurs.

### Audit Logging

The `live` module writes every action to an **immutable, append-only** compliance audit trail — never mutated, never deleted. Retention period is confirmed against current SEBI record-keeping requirements as part of the Phase 8 compliance checklist (Part IX) before Phase 8 is considered closed; this Constitution does not assert a specific retention number it has not verified against the actual regulation. Every kill-switch engagement, every risk-gate rejection, and every live order is logged to this trail, independent of the operational log stream in Part III.

### Fail-Closed Is Non-Negotiable in `risk`

Ambiguous risk state (exposure can't be computed, storage can't be read, kill-switch state is unreadable) **always** defaults to reject/block. This is the one place in the entire system where "fail closed" has zero exceptions, zero override path, and zero config flag to disable it.

---

## PART VI — Architecture Decision Records

Thirty ADRs, each documenting a decision already made across the Audit, Blueprint, and Due Diligence review — formalized here as the permanent record. Future ADRs are numbered sequentially from ADR-031 and filed in `docs/adr/`.

**ADR-001 — Hexagonal (Ports & Adapters) Architecture for `quantos_core`**
*Decision:* Domain core is pure/I/O-free; ports are domain-owned interfaces; adapters implement ports; dependencies point inward only.
*Context:* Every major audit finding (F1, F4, F8, F9) traced to the same root cause — no boundary existed between logic and data/broker/config access.
*Alternatives:* Layered MVC-style architecture; no formal architecture (status quo).
*Rationale:* A hexagonal boundary makes "a strategy defines its own universe/cost/params" structurally impossible, not just discouraged.
*Consequences:* Every new capability must be expressed as a port + adapter pair; short-term velocity cost for permanent correctness guarantee.

**ADR-002 — Single Repository, Single Shared Package**
*Decision:* One `quantos/` repo, one `quantos_core` package, replacing two disconnected codebases.
*Context:* Zero shared library between AlgoTrader and the 16-strategy sibling suite; the same bug (F4, cost model) required two separate fix passes.
*Alternatives:* Keep two repos with a shared internal package published separately; monorepo of independently-versioned packages.
*Rationale:* Solo operator, retail scale — multi-repo/multi-package overhead has no offsetting benefit here.
*Consequences:* One lockfile, one CI pipeline, one version number for the platform; strategy versioning kept as a deliberately separate axis (ADR see Part II).

**ADR-003 — Strangler-Fig Migration Over Rewrite**
*Decision:* Existing, validated strategy logic is preserved verbatim and relocated behind new interfaces, never rewritten wholesale.
*Context:* Momentum's signal math is audit-proven look-ahead-free and deterministic — the problem is everything around it, not the logic itself.
*Alternatives:* Full rewrite from a clean slate.
*Rationale:* Rewriting proven-correct logic reintroduces exactly the correctness risk the audit spent its effort closing.
*Consequences:* Every extraction step is gated by a golden-file regression test (ADR-005); migration is slower than a rewrite but never regresses correctness silently.

**ADR-004 — Git Baseline as Mandatory Phase 0 Precondition**
*Decision:* `git init` and a baseline tag of the current, verbatim codebase is the first action of the entire roadmap.
*Context:* No git repository exists anywhere in the audited tree; zero commit-SHA-to-result traceability.
*Alternatives:* Defer version control until after initial refactoring.
*Rationale:* Every subsequent step needs to be a reviewable diff against a known baseline; this is the audit's most basic unmet precondition and the single highest-leverage, lowest-risk first move available.
*Consequences:* All Phase 1+ work is blocked until this completes; it is intentionally trivial to unblock immediately.

**ADR-005 — Golden-File Regression as the Migration Safety Net**
*Decision:* Before any extraction, pin the current scripts' exact output (equity curve, trade log) as golden files; every extraction step must reproduce them exactly, or the change is explicit and separately justified.
*Context:* "Pure refactor" changes have historically hidden behavior changes (the audit's own bug-hunt found 4 metric-breaking bugs caught only by manual eyeballing).
*Alternatives:* Trust code review alone to catch behavior drift during migration.
*Rationale:* An automated, exact-match check is strictly stronger than human review for this specific risk.
*Consequences:* Golden files are deleted/superseded only once the real test suite (Part III) covers equivalent ground.

**ADR-006 — Functional Core, Imperative Shell**
*Decision:* `factors`, `strategies` (signal logic), `portfolio` (sizing math), and `risk` (limit math) are pure functions; all I/O lives in adapters called only from `services`.
*Context:* The audit's `--selftest` pattern (assert-based, hash-seed-varying) already worked because the underlying logic was close to pure; this generalizes that accidental property into an enforced one.
*Alternatives:* Object-oriented domain model with internal state and I/O intermixed.
*Rationale:* Pure functions are the cheapest thing in software to test exhaustively and the only thing that can be proven deterministic by property test.
*Consequences:* Any I/O creeping into `quantos_core/factors|strategies|portfolio|risk` is a code-review-blocking finding.

**ADR-007 — Typed Exceptions Only — Ban Blanket `except Exception`**
*Decision:* All error handling uses typed, specific exceptions; a caught exception either re-raises or logs+alerts, never both silent and swallowed.
*Context:* `download_data.py:64`'s fully silent `except Exception: return pd.DataFrame()` was the single most concrete engineering defect the audit cited.
*Alternatives:* Broad exception handling with mandatory logging (still permits swallowing without failure surfacing).
*Rationale:* A typed exception forces the caller to decide what "failure" means for that specific case, rather than papering over it with an empty default.
*Consequences:* More exception classes to define and maintain; zero silent-failure classes of bug remain possible by construction.

**ADR-008 — Fail-Closed Default on Risk/Capital Ambiguity**
*Decision:* Any ambiguous state on a path touching capital, orders, or risk limits defaults to the safest, most restrictive action.
*Context:* The pre-audit regime-check fallback defaulted to "bull market" on exception — a risk-increasing failure mode, silently.
*Alternatives:* Fail-open with alerting (act on best guess, notify operator).
*Rationale:* On a path that can lose real capital, an unnoticed alert is a worse outcome than a blocked trade.
*Consequences:* Some false-positive blocks are accepted as the cost of eliminating false-negative risk exposure.

**ADR-009 — Persisted, Not In-Memory, Global Kill Switch**
*Decision:* Kill-switch state is a flag in `storage`, checked before every order in every service, with no bypass.
*Context:* F6 — zero kill switch existed anywhere; the closest analog (per-strategy stop-loss) resets on process restart.
*Alternatives:* In-memory flag per service.
*Rationale:* An in-memory flag doesn't survive the exact crash-and-restart scenario the audit found evidence of (the 2026-06-09 double-run incident).
*Consequences:* Every order path takes a dependency on `storage` being readable; storage unavailability itself fails closed (ADR-008).

**ADR-010 — Paper Trading as Live Trading Against a Fake Broker**
*Decision:* `paper` and `live` share an identical dependency graph and `run_cycle(as_of)` signature; only the injected `BrokerAdapter` differs.
*Context:* Today's paper trader is a bespoke dict-mutation loop with no relationship to any future live pipeline.
*Alternatives:* Keep paper trading as a separate, simpler simulation distinct from the live pipeline.
*Rationale:* This is the specific design choice that turns "go live" into a config change and an adapter swap, not a second system to build and separately validate.
*Consequences:* Paper mode inherits the full error-handling and testing rigor of live mode — it is not a lower bar.

**ADR-011 — `BrokerAdapter` Interface Built Before Any Real Adapter**
*Decision:* The `brokers` module's interface is specified and the `PaperBrokerAdapter` implemented first; real broker adapters (Zerodha, Angel One) are implementation #2 and #3 of the same interface.
*Context:* Zero broker integration exists anywhere today; the interface has never been forced to prove itself against a real constraint.
*Alternatives:* Build directly against one real broker's API first, extract an interface later.
*Rationale:* Interface-first avoids designing an interface shaped by one broker's quirks; Paper is a full stress-test of the interface with zero external-account risk.
*Consequences:* Some interface rework is possible once a real broker is integrated; accepted as cheaper than the alternative.

**ADR-012 — Interface-Segregated `BrokerAdapter` Protocols**
*Decision:* Order placement, market data, and account/margin queries are separate protocols a concrete adapter composes, not one fat interface.
*Context:* Some future contexts (e.g., a data-only integration) have no need for order-placement methods.
*Alternatives:* One unified `BrokerAdapter` interface covering all capabilities.
*Rationale:* Interface Segregation Principle — a caller should never be forced to depend on methods it doesn't use or can't support.
*Consequences:* Slightly more interface surface to define upfront; adapters that genuinely only do one thing (e.g., a market-data-only feed) can implement only the relevant protocol.

**ADR-013 — Layered, Schema-Validated Configuration**
*Decision:* `base.yaml` → environment overlay → env vars (secret references only) → pydantic schema validation → one immutable config object per process.
*Context:* F8 — strategy params duplicated as module-level constants across files with nothing enforcing parity.
*Alternatives:* Environment variables only; a single flat config file with no environment layering.
*Rationale:* Layering supports `dev`/`paper`/`live` environments cleanly; schema validation turns a typo'd config key into a boot-time failure instead of a runtime surprise mid-rebalance.
*Consequences:* Config changes require updating a schema when adding new keys — a small deliberate friction in exchange for fail-fast behavior.

**ADR-014 — Secrets in OS-Level Secret Store Only**
*Decision:* Broker/API credentials live in the OS-level or hosting-provider secret manager, injected at process start; never in `.env`, never in a committed YAML.
*Context:* `.env.example` is confirmed dead code — nothing in either codebase ever loaded it; no secrets-handling path has ever been exercised end to end.
*Alternatives:* Encrypted `.env` file committed to a private repo; a dedicated secrets-management service (Vault, etc.).
*Rationale:* OS-level stores are zero-additional-infrastructure at this scale; a dedicated secrets service is out of scope per the infrastructure-minimalism principle (Part I).
*Consequences:* Revisit only if/when the deployment trigger for multi-host infrastructure (Part I, Non-Goals) is actually met.

**ADR-015 — `strategies_registry` as Single Source of Truth for Params**
*Decision:* All strategy parameters live in versioned YAML under `strategies_registry/`, never as module-level constants in code.
*Context:* F8 — `TOP_N`, `STOP_LOSS_PCT`, etc. duplicated across files with nothing enforcing they match; a real, live risk (params can silently diverge).
*Alternatives:* A shared Python constants module imported by all strategies.
*Rationale:* A YAML registry is git-diffable, versioned independently of code, and is what precisely gates the Prospective Validation freeze clock.
*Consequences:* Every strategy migration (Blueprint Phase 3) must externalize its params as part of the port, with no exceptions.

**ADR-016 — One Shared `CostModel` Port**
*Decision:* A single, accurate cost model (the audited Zerodha CNC model) is the only cost implementation in the platform.
*Context:* F4 — 3 of 4 live strategies used flat, inaccurate cost constants instead of the accurate model AlgoTrader already had.
*Alternatives:* Allow each strategy to define its own cost approximation for simplicity.
*Rationale:* A second cost implementation is strictly worse information with no offsetting benefit; the audit already validated the correct model exists and should be reused, not reinvented.
*Consequences:* A second cost implementation appearing anywhere in a future PR is a review-blocking finding, not a matter of style preference.

**ADR-017 — Point-in-Time-by-Default Data Access**
*Decision:* `data` module functions are `as_of`-parameterized by default; there is no bare "current" call.
*Context:* F1 and F9 are both instances of "current data used where point-in-time data was required," one by accident (F1) and one by construction (F9).
*Alternatives:* Keep a "current" convenience method alongside PIT methods.
*Rationale:* A convenience "current" method is exactly the shape of API that produced F1/F9 in the first place — removing it removes the footgun, not just discourages its use.
*Consequences:* Any caller genuinely needing "today's" data must pass today's date explicitly and visibly — no silent default.

**ADR-018 — Bias Detectors as Hard CI Failures**
*Decision:* Look-ahead, PIT-universe-violation, and survivorship-bias detectors run on every backtest in CI; a failure is a hard error for that run, never a warning.
*Context:* F9 (fabricated universe) and the Quality Factor PE-filter no-op were both found by manual audit, not by any automated check — and could have persisted indefinitely otherwise.
*Alternatives:* Advisory warnings surfaced in a report, reviewed periodically by the operator.
*Rationale:* A warning that can be ignored eventually is ignored; F9 sat in production-adjacent code for an unknown period specifically because nothing forced attention to it.
*Consequences:* A legitimate edge case that trips a detector requires either a code fix or an explicit, ADR-logged detector exception — never a silently-ignored red CI run.

**ADR-019 — Deterministic Replay as a Per-PR CI Gate**
*Decision:* Every strategy's full historical backtest must produce byte-identical output across repeated runs, checked on every PR.
*Context:* The audit's own determinism proof (hash-seed-varying, 3 consecutive byte-identical runs) was manual and one-off, covering only the 4 tournament strategies.
*Alternatives:* Manual determinism spot-checks, periodically, as the audit did.
*Rationale:* A determinism regression is exactly the kind of subtle bug that survives casual review; automating the check that already proved valuable once makes it valuable forever.
*Consequences:* Non-deterministic dependencies (unseeded randomness, wall-clock reads, unordered set iteration) are permanently prohibited in the domain core.

**ADR-020 — Reject Qlib, TradingAgents, LangGraph as Runtime Dependencies**
*Decision:* None of the three evaluated external repositories are adopted as a code dependency; useful patterns are reimplemented natively where cited.
*Context:* Due Diligence review scored all three REJECT or REFERENCE-ONLY on every subsystem that matters to QuantOS's actual scale and risk profile.
*Alternatives:* Adopt Qlib as the research/backtesting platform; adopt LangGraph for pipeline orchestration once LLM work begins.
*Rationale:* Qlib's ML-infra weight is ~2 orders of magnitude beyond this codebase's needs; TradingAgents' core is agentic and non-deterministic; LangGraph solves an orchestration problem QuantOS's current four-script pipeline doesn't have.
*Consequences:* Specific patterns (PIT schema shape, purged-CV method, YAML DI triple, CI test-matrix structure, SQLite checkpointing) are studied and reimplemented in 50–200 lines of native code rather than imported as a framework.

**ADR-021 — Retain the Existing Backtest Engine — Reject zipline/backtrader Replacement**
*Decision:* `momentum_backtest.py`'s engine logic is ported, not replaced, by any general-purpose backtesting framework.
*Context:* The current engine is audit-proven look-ahead-free (a hand-written invariant runs on every buy) and deterministic (byte-identical proof).
*Alternatives:* Adopt zipline-reloaded or backtrader for a more "standard" backtesting framework.
*Rationale:* Swapping a proven-correct engine for an unaudited one reopens exactly the correctness risk the audit spent its effort closing, for no cited benefit.
*Consequences:* The engine is extracted into `validation` per the migration plan (ADR-003), not rewritten against a third-party API.

**ADR-022 — Adopt `empyrical`/`pyfolio` for Standardized Metrics**
*Decision:* Performance metrics (CAGR, Sharpe, Sortino, MaxDD, Calmar) are computed via the `empyrical`/`pyfolio` libraries, not hand-rolled per strategy.
*Context:* `TASK_FIX_BUGS.md` documents a confirmed bug where a monthly return series was annualized as if daily, producing a 1691% CAGR — a hand-rolled metrics bug class.
*Alternatives:* Continue with the existing hand-rolled `utils/metrics.py`.
*Rationale:* Well-trodden, widely-used libraries close this exact bug class by construction; Due Diligence review scored this ADOPT with high confidence.
*Consequences:* `analytics` module wraps these libraries rather than reimplementing metric math; any QuantOS-specific metric not covered by the library is added natively, reviewed with the same rigor as any other domain-core function.

**ADR-023 — Adopt MLflow Directly at Phase 5 (Reject Qlib's Recorder Wrapper)**
*Decision:* Experiment tracking uses MLflow directly, not Qlib's `Recorder` abstraction over it.
*Context:* Due Diligence review found Qlib's `Recorder` is a thin wrapper adding indirection with no functional benefit over calling MLflow directly.
*Alternatives:* Build a custom lightweight run-manifest system from scratch (git SHA + data snapshot logging only, no MLflow).
*Rationale:* MLflow is the mature, standard tool for this exact problem; a custom system would be reinventing well-solved infrastructure, and Qlib's wrapper adds a dependency with no offsetting value.
*Consequences:* MLflow becomes a Phase 5 dependency; its scope is bounded to experiment tracking only, not extended into orchestration or serving.

**ADR-024 — Port Alpha158 Factor Formulas Natively, No ML-Infra Dependency**
*Decision:* Momentum/quality-relevant formulas from Qlib's Alpha158 factor set are ported into native pandas functions in `factors`, not imported as a Qlib dependency.
*Context:* Due Diligence review found these formulas are expression strings, cleanly separable from Qlib's framework — real time saved with none of Qlib's weight.
*Alternatives:* Reject Alpha158 entirely and derive all factors from scratch; import Qlib solely for this feature.
*Rationale:* The formulas themselves are the valuable artifact, not the framework delivering them; porting captures the value without the dependency cost.
*Consequences:* Applies to non-frozen strategies (Quality Factor specifically) — Momentum's frozen logic under the Prospective Validation rule is not touched by this or any other factor-library change without separately restarting its validation clock.

**ADR-025 — Risk Thresholds Are Config Defaults, Changes Gated by ADR**
*Decision:* Every numeric threshold in Part V is stored in config, changeable without a code deploy, but any change requires a filed ADR.
*Context:* The Blueprint's own risk table is explicitly framed as "proposed, tunable via config" — this ADR makes that framing permanent policy, not a one-time note.
*Alternatives:* Hardcode thresholds; allow config changes with no review requirement.
*Rationale:* A risk threshold change is a capital-risk decision, not a routine config tweak — it deserves the same dated, reviewable trail as any other architectural decision.
*Consequences:* Threshold changes are slower than a raw config edit by design; this friction is intentional.

**ADR-026 — Docker Compose on One Host — Kubernetes Explicitly Out of Scope**
*Decision:* Deployment is Docker Compose, one host, one container per service, until a stated trigger is met.
*Context:* Four strategies, weekly rebalance, ₹4L paper book scaling toward ₹1.6–10L live — nowhere near the scale that justifies orchestration overhead.
*Alternatives:* Kubernetes from day one, for "future-proofing."
*Rationale:* Building institutional-scale infrastructure for retail-scale capital violates the Constitution's own complexity-requires-justification principle (Part I).
*Consequences:* Upgrade trigger stated explicitly in advance (multiple hosts needed for latency/redundancy, or >5 services needing independent scaling) so scale-up is a documented decision, not scope creep.

**ADR-027 — Blunt Limits, Not VaR/CVaR, as the Primary Risk Gate Pre-Track-Record**
*Decision:* Position/sector/correlation/drawdown limits (Part V table) are the hard, primary gates; VaR/CVaR are computed and reported but never load-bearing at current capital/history scale.
*Context:* VaR/CVaR need return-history depth and regime stability a sub-one-year live track record does not have.
*Alternatives:* Compute and enforce VaR/CVaR from day one of live trading.
*Rationale:* A false-precision statistical gate on immature data is a worse failure mode than a simple, robust, explainable limit.
*Consequences:* Revisit only once live track record has sufficient depth — an explicit future ADR, not an automatic transition.

**ADR-028 — Dashboard Built Last, Read-Only, Minimal Write Surface**
*Decision:* `dashboard` is Phase 9 (last), strictly read-only over `api`, with exactly one write surface (the kill-switch control, itself authenticated and alerting on use).
*Context:* No dashboard exists today; building one before `monitoring`/`risk`/`analytics` produce real telemetry would have nothing meaningful to display.
*Alternatives:* Build a dashboard early for operator visibility during migration.
*Rationale:* Premature dashboard work is exactly the kind of complexity-without-justification this Constitution exists to prevent; operator visibility during migration comes from structured logs and alerts (Part II, Event Design), not a UI.
*Consequences:* Operator has no visual UI until Phase 9; accepted tradeoff given the CLI/log-based visibility available throughout.

**ADR-029 — `experiments/` and `tools/` as Enforced Dependency Leaves**
*Decision:* Nothing in `quantos_core` or `services` may import from `experiments/` or `tools/`, enforced by the CI import-linter.
*Context:* 18 dated research/audit markdown docs previously sat in the same flat folder as production strategy scripts, with no structural separation.
*Alternatives:* Rely on convention/documentation alone to keep research separate from production.
*Rationale:* Convention alone is exactly what failed to prevent the original flat-folder mixing; a mechanical CI check cannot be casually bypassed under deadline pressure.
*Consequences:* A genuinely valuable research finding must go through a reviewed change to `strategies_registry` or `quantos_core` to affect production — never a direct import.

**ADR-030 — LLM/Agentic Signal or Decision Layer Deferred Indefinitely**
*Decision:* No LLM-based signal generation or agentic decision-making is adopted from any external framework or built internally, until an independent ADR states a specific, evidenced justification.
*Context:* Two independent reasons converge: the project's own PRD already deferred this for lack of verified Indian-retail precedent, and the Due Diligence review adds that agentic frameworks would break the audited reproducibility/determinism guarantee the Prospective Validation freeze depends on.
*Alternatives:* Adopt TradingAgents-style multi-agent debate as a signal layer; build a custom LLM-assisted research copilot now.
*Rationale:* Determinism (ADR-019) and this non-goal are in direct tension for any agentic system — the Constitution resolves that tension by keeping determinism non-negotiable and the LLM layer out of scope.
*Consequences:* `.env.example`'s placeholder LLM keys remain unused scaffolding until this ADR is formally superseded with cited justification, not casually revisited.

---

## PART VII — Definition of Done

Nothing is "complete" without repository evidence — matching the audit's own standard of never marking anything complete without it.

### Modules
- Code lives in `quantos_core` or a `service`, imported through its public interface only.
- Unit/property tests exist, wired into CI (not gated behind a manual flag).
- Typed exceptions only; every catch re-raises or logs+alerts, never both silent and swallowed.
- Config-sourced values only; zero magic numbers in the diff.
- Module spec (Part III, Documentation template) complete — all nine fields.
- An ADR exists for any decision overriding a Constitution default.
- Structured log line + at least one metric emitted for anything that runs unattended.
- Documented failure mode + recovery path for anything touching network, broker, or capital.

### Strategies
- All Modules criteria, plus:
- Implements `Strategy(Protocol)`; params fully externalized to `strategies_registry`, zero module-level constants.
- Golden-file regression passes (post-migration) or is intentionally re-pinned with an ADR explaining why.
- Property test confirms weights are non-negative and sum to ≤100% deployed capital.
- Has survived the full statistical-validation falsification chain (Part IV) before being marked live-eligible — not merely backtested.
- Deterministic-replay CI gate passes.

### Data Providers
- Implements `DataProvider` port fully; every method is `as_of`-parameterized (ADR-017).
- PIT-correctness unit test: a ticker delisted mid-window is excluded from later-date queries.
- Integration test against recorded fixtures/cassettes — no live network call required in CI.
- Quality validation (gaps, stale prices, delisting flags) runs before any downstream consumer reads the data.
- Failure mode documented: provider outage serves last-known-good cache with an explicit staleness flag, never a silent empty result.

### Brokers
- Implements the full `BrokerAdapter` protocol set (order/market-data/account, segregated per ADR-012).
- Contract test asserts protocol conformance identically across every adapter (Paper, Zerodha, Angel One).
- Integration test against provider sandbox/cassette where available.
- Chaos test: simulated disconnect mid-order, simulated session expiry — both produce the documented recovery behavior (Part V).
- Typed exceptions for auth failure, rate-limit breach, session expiry — each independently testable.

### Research Experiments
- Runs against a frozen, dated data snapshot; produces a `manifest.yaml` with question, method, findings, and code SHA.
- Reproducibility test: same snapshot + same spec ⇒ byte-identical result.
- Findings that report a null or marginal result are retained and reported as prominently as a positive result (Part I, Research Philosophy).
- Never imported by `quantos_core` or `services` (enforced, ADR-029).

### Risk Modules
- Pre-trade gate demonstrably blocks a constructed breach scenario in an integration test.
- Kill switch: integration test confirms persisted state, confirms no bypass path exists.
- Fail-closed behavior verified: a simulated storage/data unavailability provably rejects, never silently approves.
- Cross-strategy aggregation returns a real, tested number for a constructed multi-strategy scenario — never "not implemented."

### Validation
- Bias detectors (look-ahead, PIT-universe, survivorship) run in CI on every backtest, hard-fail on violation.
- Mutation test: a deliberately reintroduced known bug (e.g., the pre-fix same-day-fill logic) is caught by the relevant detector.
- k-fold/purged walk-forward runs in CI, not just a single manual split.

### Production Releases
- Full chaos suite (broker disconnect, data outage, process kill mid-cycle) passes without manual intervention.
- For a **live** release specifically: all 7 SEBI checklist items closed with documented evidence; first live order round-trips through the identical interface paper trading already validated.
- Rollback plan (previous SHA-tagged image) confirmed deployable before the release ships.
- Post-deploy smoke test passes; monitoring confirms health endpoints green.

---

## PART VIII — Engineering Review Checklists

### Pull Request Checklist
- [ ] Does this touch a strategy on the current Prospective Validation freeze list? If yes — is that intentional, and does it correctly restart the observation clock?
- [ ] Does this change a golden-file output? If yes — is the new expected output re-pinned with an ADR explaining why?
- [ ] Is there a test? (Unit/property for domain-core changes; integration for adapter changes; contract test for a new `BrokerAdapter`.)
- [ ] Any new bare numeric literal inside `quantos_core/strategies/`? (CI-blocking if yes.)
- [ ] Any new `except Exception` without re-raise or log+alert? (CI-blocking if yes.)
- [ ] Any new dependency added? Is it justified against a cited need, and does it respect the Non-Goals (Part I)?
- [ ] Does this cross a module boundary improperly (reach into another module's internals instead of its public interface)?
- [ ] Lint, type-check (`mypy --strict` on `quantos_core`), and CI-blocking test subset all green.

### Code Review Checklist (solo-operator cooling-off pass)
- [ ] Re-read the diff after a break, not immediately after writing it.
- [ ] Does every new port follow the naming convention (Part III)?
- [ ] Does every new module have a complete spec (Part III, Documentation)?
- [ ] Is there an ADR for every Constitution-default override in this diff?
- [ ] Would this diff pass if reviewed a week from now with no memory of writing it?

### Strategy Review Checklist
- [ ] Params fully externalized to `strategies_registry`; zero embedded constants.
- [ ] Has it passed the full falsification chain (CAPM/factor → confound-controlled → out-of-sample), and is the result — positive, negative, or marginal — reported honestly?
- [ ] Universe sourced exclusively via `DataProvider.get_universe(as_of)` — no hardcoded or self-fetched list.
- [ ] Cost accounting via the shared `CostModel` — no independent cost constant.
- [ ] Deterministic-replay CI gate green.
- [ ] Golden-file regression clean (or explicitly re-pinned with rationale).

### Risk Review Checklist
- [ ] Every threshold change traces to a filed ADR (ADR-025).
- [ ] Kill-switch bypass path: confirmed none exists, anywhere, for any reason.
- [ ] Fail-closed behavior re-verified after any change to `risk` or `storage`.
- [ ] Cross-strategy aggregate exposure recalculated and tested against the new/changed threshold.
- [ ] SEBI Algo-ID gate still enforced correctly if this change touches order construction.

### Production Readiness Review
- [ ] Full chaos suite passes (broker disconnect, data outage, process kill mid-cycle).
- [ ] Monitoring/alerting confirmed live: a simulated failure produces an alert within SLA.
- [ ] Rollback path tested, not just documented.
- [ ] For live-capital readiness specifically: SEBI checklist 7/7 closed with evidence attached, not asserted.
- [ ] Staged capital rollout plan exists (smallest tranche, one strategy, kill switch armed) before any broader rollout.

### Release Approval
- [ ] SemVer tag matches the actual scope of change (platform) or registry version bump (strategy) — correct axis used.
- [ ] CI green on the exact commit being tagged, not a later or earlier one.
- [ ] Manual approval gate exercised by the operator deliberately — not a rubber-stamp click.
- [ ] Post-deploy smoke test plan ready to execute immediately after deploy.
- [ ] Previous SHA-tagged image confirmed pullable, as the rollback target, before deploying the new one.

---

## PART IX — Implementation Governance

### Phase Gates, Entry/Exit Criteria, Success Metrics

Ten phases (0–9), each independently deployable, each preserving the golden-file regression, each raising the measured DRS. No phase before Phase 8 adds live-capital risk. Entry criterion for each phase is the prior phase's exit criterion — strictly sequential except the two items explicitly parallelizable (below).

| Phase | Scope | Exit Criterion / Success Metric |
|---|---|---|
| **0 — Foundation & Safety** | git baseline, characterization tests, root-cause 3 confirmed scheduler gaps, stop-gap kill switch | Repo under git with baseline tag; zero unexplained scheduler log gaps for 2 consecutive weeks |
| **1 — quantos-core skeleton** | `config`, `storage`, `utils`(logging), CI stood up, AlgoTrader dependency manifest added | CI green on every push; installable from lockfile on a clean machine |
| **2 — Data Platform** | `data` module, PIT universe store, corp actions, quality validation — closes F1 + F9 | Zero hardcoded universe lists remain (grep-verifiable); PIT membership queryable for any historical date |
| **3 — Strategy Platform** | All 20 strategies ported to `Strategy` interface, unchanged logic, params externalized | All 20 pass golden-file regression; one `CostModel` import count across all live strategies |
| **4 — Risk Engine** | Pre-trade gate, portfolio risk monitor, real kill switch — closes F6 | Kill switch demonstrably blocks an order in integration test; cross-strategy exposure aggregation returns a real number |
| **5 — Validation Hardening** | k-fold/purged walk-forward, automated bias detectors in CI, MLflow experiment tracking | k-fold walk-forward runs in CI; bias-detector suite fails on a deliberately-reintroduced bug (mutation-tested) |
| **6 — Execution Engine + Paper Broker** | `execution` module, `PaperBrokerAdapter` as sole implementation, existing paper traders migrated | Paper trading runs entirely through the order-lifecycle pipeline; zero direct state-mutation remains |
| **7 — Observability + Automation** | Structured logs, metrics, health endpoints, Telegram `AlertSink`, supervised services | Killed service auto-restarts within 5 minutes; alert fires within 1 minute of simulated failure |
| **8 — Live Broker Integration** | SEBI checklist closed first; real `BrokerAdapter`; staged rollout, smallest tranche | All 7 SEBI items closed with documented evidence; first live order round-trips through the paper-proven interface |
| **9 — Institutional Hardening** | Chaos/failure-injection, secret-rotation runbook exercised, `dashboard` built last | Chaos suite passes without manual intervention |

Two items run in parallel at any point, blocking nothing: the SEBI compliance checklist (pure verification, no engineering dependency — starts immediately, alongside Phase 0) and the size-factor benchmark regression (pure research, gates no engineering phase).

### Rollback Criteria

- Any phase whose golden-file regression breaks **unexpectedly** (not via an explicit, ADR-logged re-pin) triggers rollback to the previous tagged state before proceeding.
- Any bias-detector mutation test that stops catching its target bug is treated as a Phase 5+ regression, blocking further work until fixed.
- Phase 8 (Live) specifically: any kill-switch failure, any SEBI checklist item found incorrectly marked closed, or any chaos-test regression triggers immediate rollback to paper-only — no partial live continuation under a known defect.
- A rollback is always to a previously tagged, known-good commit — never a forward "hotfix under pressure" on the live path.

### Technical Debt Policy

- An ADR-logged deviation from a Constitution default is **not** debt — it is a documented decision, reviewable and reversible.
- An **undocumented** deviation — a threshold changed without an ADR, a module boundary violated without review — is debt, and is treated as a bug, not a backlog item to defer indefinitely.
- Each phase gate (above) includes a check for undocumented deviations accumulated during that phase; found deviations are either retroactively ADR'd (if still justified) or reverted (if not) before the next phase begins.
- No phase is allowed to accumulate debt "to be cleaned up later" as a matter of course — the golden-file/DoD discipline (Part VII) exists specifically to make deferred cleanup the exception, not the plan.

### Documentation Requirements

- Every new module: full nine-field spec (Part III).
- Every Constitution-default override: an ADR, filed in `docs/adr/`, sequential from ADR-031.
- Every research experiment: a `manifest.yaml` (Part IV, Dataset Versioning).
- Every secret-rotation event: logged per the rotation runbook (Part III, Secrets).
- Every phase-gate transition: the success metric evidence attached to the closing PR or tag, not asserted in a commit message alone.

---

## PART X — The QuantOS Engineering Manifesto

QuantOS's research is already good. That was never the gap. The gap is that a genuinely rigorous falsification chain — the kind that finds its own edge case and reports it as the headline — was running inside two disconnected scripts with no shared cost model, no portfolio-level risk engine, no kill switch, and a universe file that, on inspection, turned out to be ninety-five tickers picked with hindsight, not fetched at all. Good research deserves infrastructure that doesn't undermine it by accident.

So the rule is simple: **nothing gets to define its own reality.** A strategy cannot invent its own universe, its own cost model, its own risk limit, or its own idea of "today's date." It asks a port, the port asks an adapter, and the adapter is the only place in the system allowed to touch the outside world. That one rule — dependencies point inward, always — is most of this Constitution. Everything else is what falls out of taking it seriously: typed exceptions instead of silent failure, fail-closed instead of a hopeful guess, one cost model instead of four, byte-identical replay on every PR instead of a proof done once by hand.

We do not build for the platform we wish we had. We build for the four-strategy, weekly-rebalance, ₹4L-book system that exists today, sized honestly, with every module tracing to a cited gap and every threshold stated as a tunable default, not a guess dressed up as certainty. Kubernetes is not coming. A multi-agent LLM is not deciding what to trade. VaR is not the primary gate before there's a track record long enough to trust it. Complexity is added when the evidence demands it, never before.

Paper trading is not a simulation of the real thing — it is the real thing, pointed at a fake broker. That is the whole point of building the interface first: going live should be a config change and an adapter swap, proven safe by the same chaos tests, the same kill switch, the same order lifecycle that already ran, unattended, for weeks, in paper. If it isn't safe in paper, it does not go live. There is no separate, lower bar for the dress rehearsal.

An ADR is not bureaucracy — it is memory. A solo operator has no second reviewer, no institutional hallway conversation to fall back on six months later. The ADR is that hallway conversation, written down, dated, and honest about the alternative not taken. Every deviation from this Constitution is welcome, on the condition that it is visible.

Determinism is not a feature. It is the precondition for everything else in this document being trustworthy — a backtest that isn't reproducible tells you nothing, a risk gate that behaves differently on retry cannot be certified safe, and a kill switch that might not fire the same way twice is not a kill switch. Every rule here ultimately serves one goal: when this system says something is true — this is the universe, this is the cost, this is the risk, this order is safe — it has to actually be true, every time, provably, without asking a human to trust it on faith.

Build the four things that were missing. Touch nothing that already works. Write the ADR. Ship the phase. Watch the thirteen weeks.

---

*This Constitution supersedes no prior document — it formalizes [[QuantOS Target Architecture Blueprint]], [[QuantOS Audit and Roadmap]], and [[QuantOS Foundation]] into permanent standards. Architecture, roadmap, and validation freeze remain exactly as those documents specify. Amendments require a filed ADR (Part VI/IX), never a silent edit to this file.*
