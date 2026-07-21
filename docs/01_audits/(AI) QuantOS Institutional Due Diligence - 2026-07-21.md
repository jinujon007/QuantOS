---
type: crystallization
date: 2026-07-21
area: self
project: AlgoTrader
status: active
confidence: 0.9
sources: 15
last_confirmed: 2026-07-21
ai_generated: true
---

# QuantOS — Institutional Technical Due Diligence & Strategic Assessment

**Date:** 2026-07-21 · **Auditor:** Claude (zero-assumption, repository-first protocol) · **Scope:** entire repository at commit `8bc915e` (WP-013), plus live operational state, plus current-web market/OSS research.

**Evidence tiers used throughout:** `[VF]` Verified Fact (executed/observed this session) · `[RE]` Repository Evidence (read in files) · `[ER]` External Research (web, 2026-07-21) · `[INF]` Inference · `[REC]` Recommendation.

---

## 1. Executive Summary

QuantOS is a **solo-operator algorithmic trading platform for Indian NSE equities**, built by a non-coder operator (Jinu Joshi) directing AI, currently running one validated momentum strategy in live paper trading with ₹1,00,000 virtual capital, targeting ₹3L real capital in October 2026 gated on a 13-week prospective validation window. `[RE: CONTEXT.md, EXECUTION_PLAN.md]`

**What makes it unusual is not the strategy — it's the governance.** The repository contains a 766-line engineering Constitution codifying 30+ architecture decision records, an enforced hexagonal architecture with a CI-blocking import-boundary matrix, byte-identical determinism verified 3× on every push, golden-file regression tests, a persisted fail-closed kill switch checked by every order path, and living risk/debt registers updated per work package. This is process discipline most funded quant startups do not have. `[VF: 233 tests pass in 24s; CI green on GitHub Actions; determinism gate in ci.yml]`

**What it is not, yet:** a system that has ever placed a real order, enforced a position limit, sent an alert, or survived a SEBI compliance review. The risk engine is one control (kill switch) out of a specified table of eleven. Observability is a static HTML console rebuilt daily, pull-only. Deployment is one Windows laptop with an interactive-logon scheduled task. The SEBI retail-algo checklist — a hard legal blocker for live trading, in enforcement since 1 Apr 2026 — stands at 0/7 items closed. `[RE: Risk Register R-001, R-006; quantos_core/risk/gate.py]`

**Verdict in one line:** an exceptionally well-governed pre-institutional platform, roughly 60/100 by its own honest scoring, whose binding constraints are now operational (SEBI, alerting, backup, risk limits) and evidential (13 clean weeks), not architectural.

Headline numbers: `[VF unless noted]`

| Metric | Value |
|---|---|
| Tests | 233 passing, 1 network-marked deselected, 24s wall |
| Python LOC | 8,615 total (incl. tests); ~2,000 in `quantos_core` |
| Commits / WP tags | 24 / 13 work packages + baseline |
| CI | GitHub Actions green (private repo `jinujon007/QuantOS`) — lint, format, mypy `--strict` (core), pytest, determinism ×3, inventory freshness |
| Paper account | ₹100,755 (+0.8%), 9 positions, live since 2026-06-09 `[RE: data/paper_state.json]` |
| First real weekly rebalance | 2026-07-17 signal → 2026-07-20 T+1 fills — validation clock ~1/13 |
| Shadow cutover harness | Running daily; "Books MATCH" both observed days `[VF: data/shadow/cycle_reports.jsonl]` |
| Self-scored Deployment Readiness | 61/100, "Research only" tier `[RE: CONTEXT.md DRS table]` |

---

## 2. Project Brief (Phase 1 — discovery)

- **Mission** `[RE: Constitution Part I]`: make the software match the research. The 2026-07-13 independent audit found research discipline "ahead of retail-hobbyist standard" inside pre-institutional infrastructure (Risk 1/5, Execution 0%, two disconnected codebases). QuantOS exists to close exactly four cited gaps: a real risk engine with kill switch, a real execution engine with order lifecycle, one shared library, and a point-in-time data platform.
- **Product philosophy**: "Institutional discipline, retail-appropriate infrastructure — never the reverse." Explicit non-goals are constitutional: no Kubernetes, no LLM decision core (ADR-030), no event bus, no VaR as primary gate pre-track-record, no public API, no dashboard before telemetry.
- **Strategy under management**: Nifty-500 weekly momentum (12M-1M), top-10 equal weight, 8% stop, 100-day-MA regime filter to cash. Pinned reproducible backtest: CAGR 34.3%, Sharpe 1.46, MaxDD −23.6% (2019-2024, accurate Zerodha delivery cost model incl. ₹15.93/scrip DP). All strategy parameters frozen under a Prospective Validation rule: 13 clean weekly rebalances before any re-evaluation; any frozen-list change restarts the clock. `[RE: CONTEXT.md]`
- **Business plan** `[RE: EXECUTION_PLAN.md]`: paper (Jun-Sep 2026, gate 2026-09-09: paper Sharpe > 1.0, no critical bugs) → live ₹1.6-3L manual execution (Oct-Dec 2026) → scale ₹5-10L + prop-firm track (2027). A 4-strategy tournament (Momentum, Quality Factor, Factor Timing, Weekly Options) exists in a sibling repo but that repo has no git/tests (TD-004) and two of its strategies carry a fabricated 96-ticker universe (F9) — the go-live pick must weigh this.
- **Users**: exactly one. Every process is designed to be executable by one disciplined person; "code review" is a mandatory checklist, not a second human.
- **Engineering philosophy**: functional core / imperative shell; fail closed, never silent; determinism as product requirement; boring-and-proven over novel; one source of truth per concept (cost model, universe, params).

---

## 3. Repository Map (Phase 2)

639 tracked files; 459 are cached EOD price CSVs. `[VF: git ls-files]`

```
AlgoTrader/                        (repo = "QuantOS", private GitHub remote)
├── momentum_backtest.py  paper_trader.py  transaction_costs.py     ← 6 FROZEN legacy scripts —
│   fetch_universe.py  download_data.py  factor_attribution.py        system of record, char-tested
├── quantos_core/                  ← the new platform (hexagonal, mypy --strict, ~2k LOC)
│   ├── config/ storage/ utils/            WP-001..004: AppConfig, Repository[T]+SQLite, JSON-lines logging
│   ├── data/                              WP-007: UniverseProvider/PriceProvider ports, PIT SqliteUniverseStore,
│   │                                              fail-closed CsvCachePriceProvider
│   ├── factors/ strategies/               WP-009: momentum_12m1m verbatim port, Strategy Protocol,
│   │                                              MomentumV1, YAML registry loader
│   ├── portfolio/                         WP-012: immutable PortfolioState, pure T+1 accounting,
│   │                                              CostModel port (bit-identical to frozen cost script)
│   ├── risk/                              WP-008: persisted KillSwitch + KillSwitchGate (only control so far)
│   ├── execution/                         WP-008: gated ExecutionEngine + order journal (every path journals)
│   ├── brokers/                           WP-008: segregated ports; Paper / ZerodhaKite / AngelSmartAPI adapters
│   ├── paper/                             WP-013: run_cycle(as_of)->CycleReport, injected-I/O daily cycle
│   └── analytics/ live/ monitoring/ validation/   ← empty scaffolds (planned phases)
├── strategies_registry/momentum_v1.yaml   single source of truth for params (ADR-015)
├── tests/                          233 tests: unit, parity, characterization vs golden files, import-boundary gate
├── tools/                          daily_run.ps1 (Task Scheduler 15:40), run_paper_cycle.py (shadow),
│                                   kill_switch.py CLI, demo_pipeline, broker_connect_check, capture_golden,
│                                   verify_determinism, generate_inventory, build_dashboard, desktop shortcut
├── api/ + dashboard/               WP-011 desktop app: FastAPI on 127.0.0.1:8742 + Edge app window;
│                                   WP-010 static read-only console (dashboard/index.html, git-ignored)
├── data/                           cache/ (459 CSVs 2018-2024), cache_index/ (^NSEI), universe_pit.db,
│                                   paper_state.json + paper_trades.csv (LIVE validation account),
│                                   shadow/ (ADR-038 cutover evidence), risk.db (kill switch), daily_run.log
├── docs/00_governance/             Constitution (766 lines), Foundation, WP status reports ×14,
│                                   Risk Register (6), Technical Debt Register (16)
├── docs/adr/                       ADR-031..038 (constitution embeds 001-030)
├── docs/01_audits/ 02_architecture/ 03_research/   dated audits, blueprint, 17 research reports
├── .ai/                            PROJECT_STATE.yaml + AI context files (machine-readable state)
├── .github/workflows/ci.yml        the CI described in §1
└── pyproject.toml + requirements-lock.txt   pinned closure, 39 packages
```

Dead/noise: `experiments/`, `infra/`, `services/`, `research/` are `.gitkeep` scaffolds `[RE]`; untracked root `LOOP.md`, `STATE.md`, `loop-*.md` are unused loop-tooling boilerplate ("Last run: never") `[VF]` — candidates for deletion or gitignore.

**Dependency reality** `[RE: pyproject.toml]`: 9 runtime deps (pandas 3.0.3, numpy 2.4.6, yfinance 1.4.1, pydantic, fastapi/uvicorn, requests, scipy, pyyaml) + 4 dev. Lockfile = 39 packages. Known venv drift: ~145 extra packages incl. dead LLM stack (TD-015).

---

## 4. Development Status Matrix (Phase 3)

Roadmap = Constitution Part IX, Phases 0-9. Status `[RE: STATUS.md + code]`:

| Subsystem | Phase | Status | Evidence | Missing / debt |
|---|---|---|---|---|
| Foundation & safety net | 0 | ✅ Done | golden files, char tests, determinism proof, lockfile, CI | — |
| Core skeleton (config/storage/logging/typing) | 1 | ✅ Closed (WP-001..005) | mypy --strict blocking; AST import-boundary gate in CI | WP-006 layered config reserved, unbuilt — config is env-name-only today |
| Data platform | 2 | 🟡 Partial (WP-007) | PIT universe store live, weekly Friday snapshots since 2026-07-14; fail-closed CSV price provider | Corporate-actions module, quality validators, fetch adapter, PIT *history* (pre-2026 membership unavailable — accepted, documented); yfinance single-source |
| Strategy platform | 3 | 🟡 Opened (WP-009) | MomentumV1 behind Strategy port, byte-equal parity suite | Other 3 tournament strategies not ported (blocked on sibling-repo Phase 0, TD-004) |
| Risk engine | 4 | 🔴 Slice only | Persisted kill switch + gate, CLI + desktop UI, wired into legacy loop `[RE: paper_trader.py:239-248]` | Entire Part V control table: position/sector/aggregate limits, drawdown flag, circuit breakers, liquidity checks, SEBI Algo-ID gate |
| Validation hardening | 5 | 🔴 Not started | — | Purged k-fold CV, bias-detector CI suite, MLflow tracking (all constitution-specified) |
| Execution engine | 6 | 🟡 Slice | Gated engine + journal; UNKNOWN-state taxonomy; no-retry-on-POST discipline `[RE: zerodha.py]` | Order lifecycle states, reconciliation (incl. t1_quantity, TD-013d), write-ahead intent row (TD-013a), slippage metrics |
| Paper cycle (new core) | 6-pre | 🟢 Shadow | `run_cycle` live in shadow, books MATCH daily; cutover = 2 consecutive clean weekly rebalance matches | Cutover decision (first candidate week passed clean 2026-07-17→20) |
| Live broker | 8 | 🔴 Adapters only | Native Kite v3 + Angel adapters, connect-check tool; no credentials yet | SEBI checklist 0/7 (R-001, legal blocker); no real order ever placed |
| Observability | 7 | 🔴 Minimal | JSON-lines logging; daily-run status tile; static console; desktop app | No push alerting (Telegram AlertSink unbuilt), no health checks, no metrics store, monitoring/ package empty |
| Dashboard/UI | 9 (early slices exist) | 🟡 Ahead of sequence | WP-010 console + WP-011 desktop app (ADR-035/036 justify) | By design read-only; fine |
| Infra/deployment | — | 🔴 | One laptop, venv, Task Scheduler (interactive-logon, R-006) | Docker/compose described in Constitution but `infra/` empty — aspirational `[INF]` |

**Live operational state** `[VF, 2026-07-21]`: paper account ₹100,755, 9 positions (SYRMA.NS 10th buy dropped — insufficient cash after costs, see §6 finding E-2), 0 pending, regime BULL (Nifty 24,188 > MA100 23,912), scheduler firing daily 15:40 with log evidence, shadow cycle matching books both days since the rebalance.

---

## 5. Architecture Analysis (Phase 4)

**Style** `[RE]`: Hexagonal (ports & adapters) around a functional core, strangler-fig migration from 6 frozen scripts, single package + thin tool shells. Composition root pattern, no DI framework. Protocols (structural typing) over ABCs everywhere. Repository[T] persistence over stdlib SQLite. Immutability at boundaries (pydantic frozen models, `MappingProxyType` weights, dataclass frozen).

**Strengths, evidence-backed:**

1. **The import-boundary matrix is mechanically enforced, not aspirational.** `tests/quantos_core/test_import_boundaries.py` encodes the ADR-032 allowed-imports matrix, bans frozen-script imports from core, and self-tests its own scanner; runs in the CI-blocking suite. `[VF: test run]` This is rarer than it should be — most codebases document layering and enforce nothing.
2. **Determinism as CI gate.** Unordered-set iteration and live-fetch nondeterminism were found, fixed, and now regression-gated (`tools/verify_determinism.py` ×3 per push; hash-seed varying). `[RE: ci.yml:45-47; CONTEXT.md]`
3. **Fail-closed is structural.** Kill switch unreadable → engaged (`kill_switch.py:31-39`); regime UNKNOWN → no actions, degraded report, nonzero exit (`paper_trader.py:148-176,422-427`); PIT store refuses to guess membership (`universe_store.py:96-99`); broker 5xx → UNKNOWN state, never retried, never treated as rejection (`zerodha.py:94-99`). The one legacy fail-open (regime defaults bull in the frozen backtest, `momentum_backtest.py:263`) is inherited-and-pinned, superseded in the new core.
4. **Paper = live with a different adapter (ADR-010) is real, not slideware.** `paper.run_cycle` takes injected snapshot + store + strategy + kill switch; the live cycle is specified as a snapshot-builder/fill-path swap. The shadow harness proves the migration mechanism with daily book-level comparison. `[VF: cycle_reports.jsonl "diffs": []]`
5. **Right-sized.** No message bus, no microservices, no k8s, SQLite over Postgres — each with a stated upgrade trigger. Complexity budget is a governing rule ("complexity requires justification traceable to a cited gap").

**Weaknesses / tensions:**

1. **Two systems of record during cutover.** The frozen `paper_trader.py` (dict-mutation, print-based, 0% test coverage on its live path — TD-002) is still what trades; the tested core shadows it. Correct migration strategy, but the risk window is real until cutover. `[RE: ADR-038]`
2. **`paper` module declares its own `StateStore` Protocol** because its ADR-032 cell excludes `storage` — structural typing papers over a matrix awkwardness. Defensible, slightly smelly. `[RE: cycle.py:36-43]`
3. **Config is a stub.** `AppConfig` = one `environment` field; the layered YAML→env→pydantic pipeline (ADR-013) is reserved as WP-006. Thresholds like `stop_loss_pct` flow from the strategy registry, but risk-engine config (Part V table) has nowhere to live yet. `[RE: config/loader.py]`
4. **`api/` imports `quantos_core` and legacy artifacts as an out-of-matrix consumer** — allowed (it's a shell), but `paper_trader.py` importing `api.collectors` for the kill switch inverts the intended direction (legacy script → api → core). Pragmatic wiring, documented, but a layering wrinkle to clean at cutover. `[RE: paper_trader.py:240]`
5. **Monitoring is a declared module with no implementation** — every module is supposed to "emit to monitoring," but today that means JSON logs to stderr/file only. The Constitution's Event Design (metrics, AlertSink) is unimplemented. `[RE: quantos_core/monitoring/__init__.py empty]`

**Verdict:** architecture is sound, unusually well-documented, and — the rare part — *enforced*. No fundamental redesign warranted. `[REC]` The only architecture-level action: finish the cutover, then collapse the legacy/api wiring wrinkles.

---

## 6. Engineering Audit (Phase 5)

**Code quality** `[RE, full read of quantos_core + both frozen scripts]`: consistently high in the core. Small files (largest 205 LOC), single-responsibility, typed exceptions everywhere (`DataFetchError`, `BrokerAuthError/ConnectionError`, `OrderRejectedError`, `StorageError`, `RiskLimitBreach`, `StrategyRegistryError`, `ConfigError`), comments explain *why* and cite ADRs/audit findings, docstrings carry failure-mode contracts. SQL identifier allow-listing in the repository adapter (`sqlite.py:28`), re-validation of documents on read, atomic JSON writes with corrupt-state quarantine in the legacy trader (`paper_trader.py:43-63`).

**Testing** `[VF]`: 233 passing. Real spread: golden-file characterization (backtest equity curves, metrics, walk-forward), byte-parity between frozen script and ported strategy, invariant tests on accounting (same-bar fill refusal, orphan-SELL drop, duplicate-BUY guard, unaffordable-BUY drop), broker adapter parsing incl. ambiguous-body guards, desktop-app security (foreign Host header rejected, content-type enforcement), import-boundary gate, logging determinism. Weaknesses: no property-based tests yet (constitution targets them), no chaos suite, coverage floor unenforced (27% overall — legacy scripts near-0% by explicit decision, core ~100% `[RE: PROJECT_STATE.yaml:87]`).

**Known debt is honestly ledgered** — 16 items, 5 resolved, none hidden `[RE: Technical Debt Register]`. Highest-signal open items: TD-013 (pre-live hardening: write-ahead intent row, logger run-id bleed, `t1_quantity` reconciliation), TD-014 (last-row NaN can silently drop a ticker from ranking — pinned frozen behavior), TD-015 (venv drift, dead LLM stack), TD-016 (live state git-tracked and mutated daily — the permanently dirty tree observed at session start `[VF]`), TD-004 (sibling repo unprotected — gates the tournament).

**New findings this audit** (not previously registered):

- **E-1 [RE]** `momentum_backtest.py:85-100` `_fetch_close` retains a broad `except Exception → empty Series` (prints, but proceeds); regime-empty then silently disables the filter for the run (`load_nifty50_regime` returns empty → `run_backtest` treats as no-filter). In the frozen, cached-input context the blast radius is small, but it is the constitution's named anti-pattern surviving inside the still-authoritative script. Superseded at cutover; until then it is live-path code.
- **E-2 [VF]** Equal-weight sizing guarantees the 10th entry drops on any full redeployment from cash: allocation = value/10 each, but buy cost = allocation × 1.001187, so after 9 buys the remaining cash (0.09893×value) < 10th cost (0.10012×value). Observed live: `dropped: BUY SYRMA.NS: insufficient cash (9893.13 < 10011.87)` `[data/shadow/cycle_reports.jsonl 2026-07-20]`. Same math in the backtest, so backtest/paper agree (no validity bug) — but "TOP_N=10" is effectively 9 + cash buffer on bear-recovery re-entries. Fold into the Momentum v1.1 decision with TD-014 (both need a version bump + clock restart).
- **E-3 [VF]** Untracked root clutter (`LOOP.md`, `STATE.md`, `loop-budget.md`, `loop-constraints.md`, `loop-run-log.md`) from an unused automation experiment — never run. Delete or ignore.
- **E-4 [INF]** `paper_trades.csv` timestamps (15:35) vs scheduler (15:40) imply a manual run preceded the scheduled one on 2026-07-20; idempotence guard handled it correctly ("Already ran today — skipping"). No defect — but worth noting the guard is date-granular: a manual morning run would consume the day before close. Mitigated by operator discipline only.
- **E-5 [RE]** `INITIAL_CAPITAL`-based P&L in `paper_trader.py:290-291` reads `peak_value` into `initial` but never uses it (dead F841-class line, disclosed lint debt) — cosmetic.

**Security posture**: no secrets in repo `[VF: .env.example is a template; grep clean]`; desktop API binds 127.0.0.1 with Host-header and content-type guards, tested; broker adapters refuse to construct without credentials; token exchange never persists the secret. Unexercised: OS credential store loading (no credentials exist yet — ADR-014 is still paper policy). License: proprietary, all-rights-reserved `[RE: LICENSE, PROJECT_STATE.yaml:98]`.

---

## 7. Product Maturity Scorecard (Phase 6)

Scored 0-10 against "what a solo-operator institutional-grade platform needs," not against a SaaS bar. Justifications inline.

| Area | Score | Why |
|---|---|---|
| Feature completeness (vs own Blueprint) | 4.5 | Phases 0-1 closed, 2/3/6 partial slices, 4/5/7/8/9 essentially unstarted |
| User workflows (operator UX) | 6.5 | Daily loop fully unattended + status tile + desktop app + kill-switch CLI; but alerting is pull-only — silence is invisible unless the operator looks |
| Operational maturity | 5.5 | Scheduler + idempotence + degraded-run exit codes + shadow diffing = strong for one machine; interactive-logon dependency (R-006), no off-machine backup cadence (R-005), no alert push |
| Developer experience | 8 | One-command test/lint/type/determinism; lockfile installs clean; INVENTORY auto-gated; AI-context files (.ai/) keep sessions warm |
| Deployment maturity | 3 | No container, no second environment, no restore drill; venv drift (TD-015) |
| Production readiness (live capital) | 3 | Blocked by SEBI 0/7, risk-engine absence, no reconciliation, no alerting — matches its own "Research only" DRS tier |
| Observability | 5 | Structured logs + daily tile + console; no metrics, no push alerts, no health endpoint |
| Reliability | 6.5 | Fail-closed defaults, idempotent runs, atomic writes, UNKNOWN-state taxonomy; unproven under chaos (no fault-injection suite yet) |
| Extensibility | 7.5 | Strategy port + registry means strategy #2 is additive; broker port proven ×3; but only 1 strategy ported so far |
| Documentation | 9.5 | Constitution + ADRs + WP reports + registers + PRD + research reports, all dated, cross-referenced, honest about failures — best-in-class for any size |

---

## 8. Market Research (Phase 7) `[ER — web research 2026-07-21; funding marked VERIFIED/UNVERIFIED; source URLs in the research annex conversation]`

### 8.1 India

| Company | Product | Funding | Pricing | Backtest | Live exec | Notes |
|---|---|---|---|---|---|---|
| **Tradetron** (tradetron.tech) | No-code strategy builder + marketplace, 70+ brokers | Bootstrapped [VERIFIED-unfunded] | ₹300–15,000/mo | Yes (weak fill modeling) | Yes | 30k+ marketplace strategies; cloud latency/slippage complaints |
| **Streak** (Zerodha) | No-code build/backtest/deploy in Kite | $1.35M (Rainmatter, 3one4) [VERIFIED] | Free for Zerodha users since Jan 2024 (5 live / 15 virtual cap) | Yes (shallow: ~4yr, 20 stocks/test) | Semi-auto (one-click confirm) | Distribution moat via ~8M Zerodha users; single-broker |
| **AlgoTest** (YC S22) | Options-first backtesting + execution | $500K pre-seed [VERIFIED] | 25 free backtests/wk; ₹1,299/28d signals | Best-in-class options-chain fidelity + slippage scenarios | Yes, multi-broker | Index-options DNA; weak for equity portfolios |
| **uTrade Algos** (Share India) | Broker-owned no-code algo + AI prompt layer | Acquired ~₹13.7Cr for 63.5% (2021) [VERIFIED] | From ₹999/mo | Yes | Yes, exchange-approved | Genuine NL-prompt strategy AI; empanelled vendor status |
| **QuantMan** | No-code F&O backtest + auto-exec | Bootstrapped [UNVERIFIED] | ~₹1,100–3,300/mo | Yes | Yes | Undifferentiated mid-market |
| **Quantiply** | Prebuilt F&O automation | Unfunded [VERIFIED] | ₹250–2,000/mo | Limited | Yes | Black-box prebuilts; sub-broker model conflict |
| **Stoxxo/Algobaba** | Windows-local signal bridge → broker APIs (<10ms) | Bootstrapped [UNVERIFIED] | ~₹1,500/mo class | None (bridge only) | Yes, multi-broker | Closest architectural cousin: local-first, strategy stays on user machine |
| **Symphony Presto** | Institutional algo infra, broker white-label (XTS APIs) | Private | Negotiated licenses | Yes (in ATS) | Yes, DMA | 15yr exchange empanelment; not self-serve retail |
| **AlgoBulls** | Coder IDE + no-code marketplace | $2.8M (Venture Catalysts) [VERIFIED] | Tiered + per-strategy | Yes | Yes | "AI" mostly branding |
| **Kuants** | Retail backtesting | ~$79K, acquired/dead 2021 [VERIFIED] | — | — | — | Cautionary: standalone backtest tools don't survive in India |
| **Wright Research** | Quant PMS/RA via smallcase (managed, not tooling) | ~$1M seed [UNVERIFIED] | smallcase subs + PMS fees | Closed | Managed | The *product-form* comp for Indian retail momentum |
| **smallcase** | Model-portfolio rails across brokers | $110M+ total; $50M Series D Mar 2025 [VERIFIED] | Manager subs | No | Click-to-rebalance | The distribution endgame for systematic equity in India |
| **OpenAlgo** (marketcalls) | AGPL self-hosted execution + options analytics, 33+ brokers | OSS | Free | Thin | Yes | Same local-first thesis, no research rigor; QuantOS already classifies REFERENCE-only `[RE: CONTEXT.md]` |
| Newer: **Stratzy** ($800K, acquired by Raise Nov 2025), **marketfeed** (YC S21, managed options), **TradeSteady** (static-IP compliance plumbing ₹499/mo) | | | | | | Tracxn: 209 India algo-platform startups, 117 funded, 36 Series A+ |

### 8.2 Global

| Company | Product | Funding/Scale | Relevance to QuantOS |
|---|---|---|---|
| **QuantConnect** | Cloud quant research + live on OSS LEAN engine | $4.6–8.6M over 14 yrs (deliberately capital-light) [VERIFIED range] | Category best; research→live parity is the same thesis; zero NSE/Kite support |
| **Composer** | No-code + AI "symphonies," own brokerage | ~$16.7M; **acquired by SoFi Jun 23, 2026** [VERIFIED] | Reference implementation of LLM→constrained-DSL strategy building |
| **Alpaca** | API-first brokerage infra | $150M Series D @ $1.15B, Jan 2026 [VERIFIED] | The US analog of Kite Connect as a business; first-class paper sandbox |
| **TradeStation/MultiCharts** | Legacy pro-retail desktop algo stack (integrated Aug 2025) | Monex-owned / private | Desktop determinism lineage; no India path |
| **Trade Ideas** | AI scanner + Holly signals | Private | Signals-not-systems; expensive |
| **Numerai** | Crowdsourced ML hedge fund (staked predictions) | $30M Series C @ $500M val Nov 2025; JPM AM committed up to $500M; AUM $550M [VERIFIED] | "Sell the signal, not the platform" pole for solo quants |
| **WorldQuant BRAIN** | Crowdsourced alpha expressions, paid consultants | — (WorldQuant) | Competes for solo-quant talent; IP stays with WorldQuant |
| **Blueshift** (QuantInsti) | Free Python backtest/live, India minute data | Education-funded | Only free platform with real India equity data; education-funnel priority |
| **Quantopian** | DEAD (Nov 2020) | — | Platform-economics failure; diaspora = QuantConnect, QuantRocket, zipline-reloaded |
| AI-native 2024-26: **Alphio AI** (agentic NL trading, Robinhood integration Jul 2026), **Surmount** (marketplace over user brokerages, Zerodha listed), **Tickeron** | | mostly small/undisclosed | LLM front-ends over rule engines; none improve alpha, all improve onboarding |

### 8.3 Where the market is heading (5 theses)

1. **AI-NL is the new front-end, not the new engine** — Composer→SoFi, Alphio×Robinhood, uTrade Intelligence all bolt LLM prompt→strategy onto rule engines. Nobody ships AI that improves alpha; differentiation shifts to execution fidelity and data integrity — QuantOS's exact chosen layer.
2. **Consolidation into distribution owners** — Streak/Sensibull free inside Zerodha, Composer→SoFi, Stratzy→Raise. Standalone ₹500-2,500/mo algo SaaS is a feature, not a company.
3. **SEBI's Apr-2026 regime inverts the market** — raises fixed costs for commercial vendors (empanelment, accountability), while the personal-API carve-out (self-coded, ≤10 orders/sec, static IP, broker-tagged generic Strategy-ID) legitimizes solo operators at near-zero incremental compliance cost.
4. **Two viable solo-quant monetization poles**: signals into crowdsourced funds (Numerai/BRAIN) or portfolios via distribution rails (smallcase). Platform-building between them is capital-intensive with weak moats.
5. **Local-first is a respectable counter-trend now** — OpenAlgo, QuantRocket, LEAN CLI, Stoxxo; static-IP compliance maps naturally onto one home machine/VPS.

### 8.4 Structural comparison

**QuantOS occupies an empty quadrant in India: self-directed + systematic equities + local-first + evidence-disciplined.** The commercial stack is index-options-intraday centric (that's where subscription value is); systematic equity rotation is served only as managed products (Wright/smallcase), never as tooling. No Indian offering combines PIT universe discipline + deterministic backtest→paper→live promotion + local execution. QuantOS's pipeline rigor exceeds what Tradetron/Streak/QuantMan sell — their backtests are marketing surfaces, not evidence chains. `[ER + RE]`

Honest disadvantages: no community error-correction on the backtest; single-person key risk; no execution redundancy; data-vendor dependency amortized across one person; and at ₹3L capital, infra effort per rupee deployed is orders of magnitude above any commercial comparable. The comparables justify QuantOS as capability-building and evidence discipline — not as cost-rational asset management at current AUM.

### 8.5 SEBI regulatory status (verified timeline)

Feb 4, 2025 circular (brokers accountable; Algo-ID for >10 orders/sec; white-box vs black-box tiers) → effective date extended Aug 1 → **Oct 1, 2025** → Jan 5, 2026 non-compliant brokers barred from new API clients → **Apr 1, 2026 full enforcement, in force now**: static-IP whitelisting mandatory (old keys expired), every algo order tagged with a Strategy-ID, mandatory pre-go-live simulation, 5-year broker logs; NSE algo-provider empanelment circular Apr 30, 2026. **Key carve-out for QuantOS:** self-coded strategies ≤10 orders/sec need no separate exchange registration — the broker tags a generic Strategy-ID; static IP + broker API compliance suffices. Zerodha personal Kite Connect API is now free (up to 2 whitelisted static IPs, order placement IP-locked). `[ER]`

**Implication for R-001:** the repo's 0/7 checklist is written against the retired Angel One route and pre-dates the Oct-2025 extension. It needs a Zerodha-specific rewrite: (1) create personal Kite key, (2) fix a static IP (home broadband static-IP add-on or VPS), (3) whitelist it, (4) confirm broker Strategy-ID tagging + simulation requirement, (5) confirm ≤10 orders/sec bucket in writing. Materially *simpler* than the register assumes — but still 0 items closed. `[REC]`

---

## 9. Open-Source Ecosystem (Phase 8) `[ER — GitHub API + PyPI verified 2026-07-21]`

Verdicts from QuantOS's stated perspective: deterministic byte-identical runs, stdlib-first, solo operator, EOD weekly, NSE, Windows, Python 3.13.

### 9.1 Verdict table

| Project | Stars / last push / license (verified) | Verdict | Why |
|---|---|---|---|
| **pykiteconnect** (Zerodha official) | 1.3k · 2026-04 · MIT | **Adopt** (see note) | The execution-port implementation for live cutover; ₹500/mo plan now bundles historical data — cheapest legitimate NSE feed. *Note: QuantOS already built a native ~150-line Kite adapter (WP-008) to avoid the SDK's Twisted/websocket weight; keep the native adapter, track the SDK repo for API-change signals — the adopt-value is the maintained API knowledge, not the import.* |
| **quantstats** | 7.5k · 2026-07 · Apache-2.0 | **Adopt** (report sidecar only) | Weekly HTML tearsheet from the paper equity curve; keep outside the decision path, version-pinned |
| **exchange-calendars** (zipline sibling) | — · active · Apache-2.0 | **Adopt** | Maintained XNSE trading calendar — closes the Constitution's Clock-port holiday problem without hand-maintaining a table |
| **DuckDB** | 39.6k · 2026-07 · MIT | **Adopt on trigger** | Pre-approved answer when full-history cross-sectional scans outgrow pandas; pin version, `threads=1` for byte-stability |
| **jugaad-data** | 542 · 2026-03 · **no license ("YOLO")** | **Adapt** | Vendor its bhavcopy URL/cookie/holiday logic into own fetch adapter; never depend on an unlicensed package |
| **yfinance** | 1.5.1 · active | **Adapt (quarantine)** | See 9.3 — keep behind the data port, cache-once-read-forever, never primary |
| **OpenAlgo** | 2.3k · 2026-07-21 · AGPL-3.0 | **Reference now, Adapt if multi-broker** | Confirms repo's existing verdict; best catalog of Indian broker API quirks; AGPL stays out of codebase by running as sidecar service if ever needed |
| **PyBroker** | 3.5k · 2026-07-20 · Apache-2.0+Commons | **Reference — top read** | Closest philosophical cousin (EOD, deterministic, cached); port its walk-forward splits + bootstrapped confidence intervals on Sharpe/MaxDD natively |
| **NautilusTrader** | 24.9k · 2026-07-21 · LGPL-3.0 | Reference | Best deterministic event-driven architecture in OSS; imitate patterns (clock abstraction, single-threaded loop), never import — Rust engine for 10 orders/week is a cannon for a mosquito |
| **Qlib** (Microsoft) | 46.5k · 2026-04 · MIT | Reference | Cleanest OSS PIT blueprint (`instruments/*.txt` date-ranges + two-date fundamentals schema); no NSE, no py3.13 wheel, gravity shifted to LLM RD-Agent — the direction ADR-030 rejects |
| **Zipline-reloaded** | 1.8k · 2026-01 · Apache-2.0 | Reference | Pipeline API = canonical cross-sectional ranking design; bus-factor-1 |
| **LEAN** (QuantConnect) | 20.6k · daily · Apache-2.0 | Reference | "Reality models" taxonomy (fee/slippage/fill plugins) maps to the CostModel port |
| **bt / ffn** | 2.9k/2.6k · 2026-07 · MIT | Reference | Algo-stack factoring (select→weigh→rebalance) mirrors the right decomposition |
| **pandera** | 4.4k · 2026-07 · MIT | Reference → Adopt on trigger | Schema-contract pattern for pipeline boundaries; the one data-quality dep worth taking if hand-rolled checks exceed ~200 lines |
| **empyrical/pyfolio-reloaded** | 116/599 · 2025-12 · Apache-2.0 | Reference | De-facto standard metric formulas — copy the math, cite the source, skip the dep. *Amends ADR-022's "adopt" — maintenance-mode status argues for formula-porting over dependency* |
| **VectorBT** | 8.4k · 2026-07 · fair-code | Reference | OSS tier is permanently the demo of PRO; read the vectorized-sweep pattern only |
| **Backtrader** | 22.5k · **last push 2024-08, dead ~3yr** · GPL-3 | **Reject** | Unmaintained core under live money is disqualifying — confirms ADR-021 |
| **Freqtrade / Hummingbot / VN.py / Lumibot** | 52.5k/19.2k/43.3k/1.8k · active | Reject | Crypto / China / US-broker ecosystems; zero NSE path |
| **OpenBB** | 70.8k · active · **AGPL-3.0 now** | Reject | 100-dependency detour to data already fetched directly |
| **MLflow** | 27.1k · active · Apache-2.0 | **Reject — amends ADR-023** | 3.x pivoted hard to GenAI/LLM tracing; experiment tracking for a deterministic system = run_id + config hash + git SHA + metrics table, ~50 lines native. Revisit ADR-023 before Phase 5 executes |
| **Dagster / Prefect / Ray / Feast / Great Expectations** | all active | Reject | Data-team orchestration/scale machinery; QuantOS's DAG is `run_cycle()` + Task Scheduler. GX also churned owners twice in 12 months (FICO shutdown of GX Cloud, Fivetran stewardship of core). Feast's PIT-join concept already implemented in `universe_pit.db` |
| India data: **eod2** (158★, bhavcopy incl. delisted), **nsepython** (GPL) | active | Reference | eod2 independently validates the bhavcopy-first architecture |

### 9.2 Point-in-time universe — state of the art vs QuantOS

**Norgate Data (the retail gold standard for survivorship-bias-free data) does not cover NSE.** The verified best practice for India is exactly what QuantOS does: DIY from official NSE bhavcopy (which includes later-delisted stocks), immutable raw store, membership table with as-of joins, symbol-change master, corp-actions applied at read. A 2026 arXiv study (Nifty Smallcap 250, 2016-2025) quantified the stakes: survivor-only backtests inflate returns **+4.94pp/yr**, universe churn 82.5%. `[ER: arXiv 2603.19380]` Implications: (a) `universe_pit.db`'s design is aligned with published best practice — not a compromise; (b) the accepted historical-membership gap (2019-2024 backtest on current constituents) is *material by that study's magnitude* — the pinned CAGR 34.3% should be mentally haircut several points, reinforcing the repo's own "weigh before trusting absolute CAGR" caveat; (c) EODHD (~NSE from 2006 incl. delisted) is the pragmatic paid one-time cross-check if historical re-validation is ever wanted.

### 9.3 yfinance reliability — verified status

Structurally unreliable, actively maintained: Nov 2024 per-IP rate-limiting broke bulk downloads (~950 tickers → 429s); Feb 2025 Yahoo redesign forced yfinance onto **curl_cffi browser-TLS impersonation** (the dependency now works by impersonating Chrome against a host trying to block it); documented NSE-specific defects (false "possibly delisted" on active `.NS` symbols, history mismatches, **silent historical revisions — fatal for byte-identical reruns**). `[ER: yfinance #2128/#2496/#2612/#1326]` QuantOS's cache-first pattern already blunts most of this; the correct end-state is bhavcopy primary + Kite historical (₹500/mo, now bundled) at live time + yfinance quarantined as cross-check. The CONTEXT.md decision "we don't need Kite's data tier — own EOD cache" `[RE]` deserves revisiting once live: it is now the cheapest *legitimate* NSE feed and removes the scraping dependency from the daily loop.

### 9.4 SEBI-compliant OSS execution besides OpenAlgo

Effectively none — OpenAlgo is the only maintained substantive OSS execution layer for India (its team's heavier "OpenBull" started building Apr 2026; watch-only). Everything else is official broker SDKs or dormant wrappers. Confirms the repo's REFERENCE-only stance and the native-adapter build choice. `[ER]`

---

## 10. Competitive Gap Analysis & SWOT (Phase 9)

### 10.1 Capability matrix — QuantOS vs the field

Scale: ● full · ◐ partial · ○ absent. QuantOS scored on *built and verified*, not planned. `[RE + ER]`

| Capability | QuantOS | Streak/Tradetron (India SaaS) | AlgoTest | QuantConnect/LEAN | OpenAlgo | Institutional desk |
|---|---|---|---|---|---|---|
| Research rigor (falsification chain, PIT discipline) | **●** (its differentiator) | ○ | ◐ (options data fidelity) | ◐ (tools exist, discipline is user's) | ○ | ● |
| Backtest determinism (byte-identical, CI-gated) | **●** | ○ | ○ | ◐ | ○ | ◐ (varies!) |
| Survivorship-bias control | ◐ (forward-accumulating PIT store; history gap documented) | ○ | ◐ | ● (US data) — ○ for India | ○ | ● |
| Backtest→live parity (same code path) | ● (by construction, shadow-verified) | ○ (separate engines) | ◐ | ● | n/a | ● |
| Multi-strategy portfolio & risk aggregation | ○ (Phase 4/5 unbuilt) | ◐ | ○ | ● | ○ | ● |
| Pre-trade risk controls | ◐ (kill switch only) | ◐ (broker-level) | ◐ | ● | ◐ | ● |
| Execution (live orders, lifecycle, reconciliation) | ○ (adapters exist, never fired) | ● | ● | ● | ● | ● |
| Broker abstraction | ● (3 adapters, one port, contract-tested) | ○/● | ◐ | ● | ● (33+) | n/a |
| Alerting/monitoring | ◐ (logs + tiles, no push) | ● | ● | ● | ◐ | ● |
| Paper trading realism | ● (T+1 fills, real cost model incl. DP) | ◐ | ◐ | ● | ◐ | ● |
| Compliance posture (India Apr-2026 regime) | ◐ (carve-out fits; 0 items executed) | ● (vendor-side) | ● | ○ (no India) | ◐ (docs) | ● |
| Cost of ownership | ~₹0 SW + operator time | ₹0–15k/mo | ₹1.3k/mo | $60+/mo | ₹0 + ops | ₹crores |
| AI/LLM layer | ○ (constitutional non-goal, ADR-030) | ◐/○ | ○ | ◐ (copilot) | ○ | ◐ |

### 10.2 SWOT

**Strengths** `[RE/VF]`
- Governance artifacts (Constitution, ADRs, registers, WP reports) + mechanical enforcement (import matrix, determinism gate, golden files) — rare at any scale, unique at solo scale.
- Honest evidence culture: the repo's own docs headline their weakest results (post-2021 alpha p=0.23; walk-forward caveats; survivorship acceptance). Audit-grade self-knowledge.
- Backtest→paper→live as one code path (ADR-010) with an operating shadow-cutover harness — the hard part of "go live safely" is designed-in, not bolted on.
- Regulatory tailwind: the Apr-2026 SEBI regime favors exactly this pattern (self-coded, personal API, low order rate).
- Cost model realism (DP charges, capital-viability floors) ahead of most retail practice.

**Weaknesses** `[RE/VF]`
- One strategy, one machine, one person, one data source (yfinance). Every one of those is a single point of failure; only the machine one has a partial mitigation (git remote).
- Risk engine = 1 of 11 specified controls. Execution never live-fired. Alerting absent (the system can fail silently for days if the operator doesn't look — the exact failure mode that cost a month once).
- Validation evidence: 1 of 13 clean weeks. Paper Sharpe unknown. The 2026-09-09 gate cannot be passed early no matter how good the code is.
- Sibling-repo tournament (per PRD, the go-live selection mechanism) is unprotected and partly built on a fabricated universe — the PRD's decision process and the repo's reality have diverged.
- Legacy scripts remain the trading system of record until cutover.

**Opportunities** `[ER/INF]`
- Cutover + Phase-4-minimum + alerting are all small, high-leverage, already-seamed work.
- India tooling white space (systematic equities, local-first) — if QuantOS ever productizes, the quadrant is empty; nearer-term, the discipline itself compounds into a prop-firm/track-record asset per EXECUTION_PLAN Phase 3.
- smallcase/Numerai/BRAIN routes exist to monetize the *signal* without building a business around the *platform*.
- Momentum-in-India is academically well-supported; the strategy choice itself was research-validated as defensible for small capital.

**Threats** `[ER/INF]`
- yfinance is unofficial scraping; NSE data access tightening or Yahoo breakage stalls the daily loop (mitigation: Kite's own quotes at live time, EODHD-class vendor later).
- SEBI regime is broker-mediated and still settling; broker policy shifts (API pricing, static-IP rules) can move the goalposts.
- Bull-regime dependence: strategy evidence is regime-concentrated (documented); a 2026-27 bear turns the validation window into mostly cash — clock passes but with thin signal evidence. `[INF]`
- Operator-life risk: solo discipline is the load-bearing wall; illness/attention drift = silent decay. Alerting (I-3) is the cheapest hedge.

### 10.3 Positioning statement

QuantOS is not competing with Tradetron or QuantConnect — it is a **one-person proprietary trading capability** whose nearest true peers are other disciplined solo quants (mostly invisible) and whose commercial comparables matter only as (a) pattern sources, (b) distribution endgames (smallcase), and (c) proof that the tooling middle-market is a bad business. Its defensible asset is the *evidence chain* (deterministic, PIT-clean, honestly-falsified, soon live-verified) — which is exactly the asset prop firms and allocators pay for. `[INF]`

---

## 11. Deployment Readiness (Phase 10)

| Target | Ready? | Evidence / blocker |
|---|---|---|
| Local development | ✅ | Lockfile-reproducible install verified (TD-011 closed); full suite 24s `[VF]` |
| Unattended daily operation | 🟡 | Works today with logged evidence; single machine, interactive-logon task (R-006), C-drive-full environment fragility `[RE: CONTEXT.md]` |
| Docker | ❌ | `infra/` empty; Constitution's CI/CD section (build image, SHA tags, rollback) is entirely aspirational today |
| Cloud/VPS | ❌ | Nothing exists; also constitutionally deferred until a trigger is met — correct for now |
| CI/CD | 🟡 | CI real and green; CD does not exist (no deploy target) |
| Paper trading | ✅ | Live 6+ weeks, first clean rebalance week complete, shadow harness matching |
| Live trading | ❌ | Hard blockers: SEBI checklist 0/7 (legal, R-001); risk engine Phase 4 unbuilt; no broker credentials/session flow exercised; no reconciliation; no alerting |
| Enterprise use | ❌ (non-goal) | Single-operator by constitutional design |

**Resilience gaps ranked** `[REC]`: (1) off-machine backup cadence — `main` has previously sat 12 commits ahead of origin (R-005); push-per-WP is now habit but state files (`paper_state.json`, journal CSVs, `universe_pit.db`) have no automated off-machine copy at all; (2) alert push on FAILED/HALTED/INCOMPLETE daily runs — currently only visible on the console tile if the operator opens it; (3) run-whether-logged-on scheduled task or missed-run alert; (4) restore drill: prove the lockfile+state backup actually reconstitutes on a second machine before Phase 8.

---

## 12. Strategic Improvement Opportunities (Phase 11)

Ordered; each sized against a solo operator + AI executor. No architectural rework is on this list because none is needed.

**Immediate (this week, low risk):**

| # | Action | Impact | Effort | Deps |
|---|---|---|---|---|
| I-1 | **Start the SEBI checklist** (Zerodha variant — Kite personal API, Algo-ID/exemption status in writing) | Unblocks everything live; legal risk → known | Operator hours, zero code | None — parallelizable since Phase 0, still 0/7 |
| I-2 | **Automated off-machine backup**: push state snapshot (paper_state, trades CSV, universe_pit.db, risk.db, daily_run.log) nightly — private git branch, or cloud drive sync step in daily_run.ps1 | Removes single-disk loss of the validation record | ~30 LOC | None |
| I-3 | **Telegram/ntfy alert on non-OK daily run** (one webhook call in daily_run.ps1 on FAILED/HALTED/INCOMPLETE) | Closes the "silent dead run" hole that already bit once (silent month-long breakage pre-QuantOS) | ~20 LOC | None |
| I-4 | Resolve TD-016 (gitignore live state + dated snapshot commits) + delete loop-scaffolding clutter (E-3) | Clean tree, no rollback foot-gun | Trivial | One-line ADR |
| I-5 | Rebuild venv from lockfile (TD-015) | Supply-chain surface down, env = lockfile truth | One sitting | TD-011 done ✅ |

**Short-term (before the 2026-09-09 gate):**

| # | Action | Impact | Effort |
|---|---|---|---|
| S-1 | **Complete shadow cutover** after 2 clean rebalance matches (first is in; second candidate 2026-07-24) → retire `paper_trader.py` to reference | Tested core becomes system of record; TD-002 closes by supersession | Operator decision + CONTEXT entry (mechanism already built) |
| S-2 | **Phase 4 risk engine minimum**: position-limit + drawdown-flag + daily-loss checks as pure functions behind the existing gate seam, config-sourced | 1→4+ real controls before any live order | Small; seam exists (`KillSwitchGate` pattern) |
| S-3 | Weekly research log discipline (template exists, 0 entries so far) + DRS re-score per entry | The gate decision is only as good as this evidence | Operator habit |
| S-4 | Task Scheduler → run-whether-logged-on (stored credentials) or missed-run alert | R-006 closed | Config change |
| S-5 | Property tests on accounting invariants (weights ≤ 1, cash never negative, shares > 0) | Constitution Part III commitment; cheap now, priceless at live | Small |

**Medium-term (Phase 2 gate → live, Oct-Dec 2026):**

- M-1 Order-lifecycle hardening for live: write-ahead intent row (TD-013a), post-place order-book poll, reconciliation incl. `t1_quantity` (TD-013d), slippage capture vs assumed costs.
- M-2 Kite session flow end-to-end: request-token exchange exercised via `broker_connect_check.py` read-only, then one smallest-tranche real order behind the full gate stack (Phase 8's staged-rollout DoD).
- M-3 Momentum v1.1 decision bundle: TD-014 (last-row NaN) + E-2 (10th-buy sizing) + any gate-review findings → one ADR, one version bump, one clock restart — never piecemeal.
- M-4 Purged/embargoed walk-forward + bias-detector suite in CI (Phase 5) — before any *new* strategy is trusted, not necessarily before Momentum goes live (Momentum's evidence chain already ran manually).
- M-5 Sibling-repo Phase 0 (TD-004) *only if* the tournament actually informs the go-live pick; otherwise formally descope the tournament from the gate decision (PRD and Constitution currently disagree with the repo's single-strategy reality — resolve on paper either way).

- M-6 Data-source hardening (from §9.3): bhavcopy-based fetch adapter (vendor jugaad-data's logic) as primary; Kite historical API at live time; yfinance demoted to quarantined cross-check. Also adopt `exchange-calendars` XNSE for the Clock port.

**Long-term (2027, post-live):**

- L-1 Experiment tracking: ~50-line native run-manifest (run_id, config hash, git SHA, metrics) instead of MLflow — **revisit ADR-023 first** (MLflow 3.x GenAI pivot post-dates the Due Diligence review; see §9.1). `experiments/` manifests when strategy #2 development begins.
- L-2 Docker + restore-drill + chaos suite (Phase 9) before capital scales past ₹3L.
- L-3 Strategy #2 port through the full falsification chain — the platform's real test of its own extensibility claim.
- L-4 PIT universe history enrichment (paid vendor or manual reconstruction) if any historical re-validation is ever needed; forward-accumulating snapshots already de-bias all future backtests.

---

## 13. Scoring Framework (Phase 12)

| Category | /10 | Basis |
|---|---|---|
| Product Vision | 9 | Unusually crisp mission + constitutional non-goals; vision docs and code agree `[RE]` |
| Architecture | 8.5 | Hexagonal, enforced, right-sized; minor wrinkles (§5) |
| Engineering Quality | 8 | Typed, fail-closed, journaled; legacy scripts still authoritative until cutover |
| Code Quality | 8.5 | Small, single-purpose, why-commented, zero silent catches in core |
| Maintainability | 8 | Registers + ADRs + inventory gate; solo bus-factor is the ceiling |
| Scalability | 4 | One machine, one strategy live; *deliberately* — triggers documented; scored against need it's ~7 |
| Reliability | 6.5 | Fail-closed + idempotent + shadow-verified; no chaos testing, no alerting |
| Security | 6 | Clean secrets hygiene on paper; credential path unexercised; local-only surfaces tested |
| Testing | 7.5 | 233 real tests incl. parity/characterization/boundary; no property/chaos tiers yet |
| Documentation | 9.5 | Best-in-class for size; honest failure reporting is the differentiator |
| Deployment | 3 | Laptop + scheduler; no container/second-env/restore drill |
| Automation | 6.5 | Daily loop + CI fully automated; alerting + backup manual/absent |
| Observability | 5 | Logs + tiles, pull-only |
| Developer Experience | 8 | Reproducible env, fast suite, machine-readable state for AI sessions |
| AI Readiness | 3 | Constitutionally deferred (ADR-030) — low score is a *choice*, and the .ai/ scaffolding is actually ahead of most repos |
| Product Maturity | 4 | Pre-live, single-strategy, validation week 1/13 |
| Operational Readiness | 5 | Runs unattended with evidence; single-machine + no-alert ceilings |
| Market Differentiation | 3 as product / 8 as method | Not a product; the governance-first solo+AI method is the differentiated asset |
| Innovation | 6 | Not novel quant; novel *process* (AI-executed institutional governance at retail scale) |
| **Overall Institutional Readiness** | **5.5** | Consistent with its own DRS 61/100 "Research only" — the self-score is honest `[RE]` |

---

## 14. Final Assessment

**What has been built** is a small, correct, enforced core (~2,000 typed LOC + 233 tests) implementing the four things the founding audit found absent — kill switch, gated execution seam, shared accounting/cost model, PIT data discipline — wrapped around a frozen, characterization-locked legacy strategy that is now one clean shadow-week away from being replaced by the tested core. The engineering trajectory since 2026-07-12 (24 commits, 13 work packages, 9 days) is disciplined, evidence-gated, and rapid without being reckless.

**What the numbers say:** self-scored DRS 61/100 ("Research only") is consistent with this audit's independent 5.5/10 institutional-readiness score. Both are honest. The platform is roughly where its own documents say it is — which is itself the strongest finding: *this repository does not lie to itself*, and that property is worth more than any single subsystem.

**The three binding constraints, in order:**
1. **Evidence** — 13 clean weekly rebalances (currently ~1). Nothing engineering can compress this. The system's job until September is simply to not corrupt the record — which is what the shadow harness, idempotence guards, and degraded-run signaling are for.
2. **Legal** — the SEBI/Zerodha checklist (rewritten per §8.5 — simpler than the register assumes, still 0 executed). Pure operator hours; parallelizable since day one; still the only item that can make live trading *illegal* rather than merely unwise.
3. **Operational safety net** — alerting, off-machine state backup, run-when-logged-out. ~50 LOC + config total. The only class of gap that can silently destroy the validation record the whole plan depends on.

Architecture, code quality, and process need no rescue — they need *continuation*: cutover, Phase-4 minimum controls, reconciliation hardening, in that order, at the already-demonstrated work-package cadence.

**Institutional-grade?** As a codebase and process: closer than most seed-stage fintechs. As an operating trading system: not yet — by its own definition, and on its own schedule. The gap is no longer architectural or intellectual; it is 12 more clean weeks, 7 checklist items, and ~3 small work packages of safety plumbing.

**Recommended next milestones** (compressing §12):

| When | Milestone | Gate |
|---|---|---|
| This week | SEBI/Zerodha checklist started · backup + alert hooks in daily_run · TD-015/016/E-3 hygiene | I-1..I-5 done |
| By 2026-08-01 | Shadow cutover decision (2 clean rebalance matches) · legacy trader retired to reference | ADR + CONTEXT entry |
| By 2026-09-09 | Phase-4 minimum risk controls · weekly research log ≥6 entries · paper Sharpe computed | Phase 1 gate review, DRS re-score |
| Oct 2026 | If gate passes: Kite session E2E + smallest-tranche live order behind full gate stack | Phase 2 begins at ₹1.6-3L |
| Dec 2026 | Slippage-vs-model report · live vs paper divergence analysis | Phase 2 gate |

*Report ends. Full research annex (per-company sources, OSS verdict details) preserved in the session transcript; key claims carry inline evidence tags.*
