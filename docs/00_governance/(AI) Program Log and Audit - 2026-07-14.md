---
type: register
date: 2026-07-14
status: active
area: self
project: AlgoTrader / QuantOS
ai_generated: true
---

# QuantOS — Program Log & Independent Audit — 2026-07-14

One document, three parts: **(1)** the complete chronological log of everything
built so far, **(2)** a four-track independent audit of it (docs/governance,
core correctness, operations reliability, desktop security), **(3)** the fixes
applied today with verification evidence, plus the ranked list of what remains.

---

## Part 1 — Program log (everything done so far)

### Pre-repo research era (2026-06-09 → 2026-07-12, recorded in CONTEXT.md only)

| Date | What happened |
|---|---|
| 2026-06-09 | Paper trading live (₹1L virtual). Accurate Zerodha cost model replaces 0.1% flat — DP charge (₹15.93/scrip/sell) shown to dominate at small capital; ₹10K live capital ruled unviable. |
| 2026-07-12 | **Look-ahead bias fixed** (signal and fill shared the same close; fills now T+1). **Reproducibility fixed** (regime-index cache + sort-before-set-iteration) — 3 consecutive byte-identical runs proven. Pinned: CAGR 34.3%, Sharpe 1.46, MaxDD −23.6%. PIT-universe survivorship decision: delisted-direction bias accepted, not fixed (NSE blocks automated access to historical constituents). |
| 2026-07-13 | Historical research phase **closed**. Prospective Validation freeze active: strategy frozen until 13 clean weekly rebalances (~2026-09-09 gate). DRS 61/100 → policy tier "Research only". Five governing docs authored: Independent Audit, Target Architecture Blueprint, OSS Adoption Review, External Due Diligence, and the **QuantOS Constitution**. |

### Engineering program (git history — all of WP-001→WP-011 in 2026-07-13/14)

| Commit | WP | What was built |
|---|---|---|
| ac908ca | Phase 0 + WP-000 | `git init` + `baseline-v1` tag (ADR-004). Characterization tests, golden files, determinism proof, dependency lock, CI (ADR-005). `docs/` hierarchy, empty `quantos_core/` skeleton (ADR-031), Risk + Tech-Debt Registers. |
| b8a9931 | WP-001 | Repository foundation: `mypy --strict` CI-blocking on `quantos_core`, import smoke test. |
| 18c554c | WP-002 | Typed, immutable, validated `AppConfig` (env-resolution slice of ADR-013). |
| cb117fb | WP-003 | Storage: `Repository[T]` port, `Entity` base, transactional fail-closed `SqliteRepository`. |
| f0c8dae | WP-004 | Structured logging: JSON-lines, run-id correlated, stdlib-only. Phase 1 scope complete. |
| 72f71a0 | docs | External repo addendum: ai-hedge-fund + Vibe-Trading NOT ALIGNED. |
| b79de08 | WP-005 | Import-boundary matrix (ADR-032) + stdlib-`ast` CI gate. TD-010 closed. **Phase 1 fully closed.** |
| 8d57c22 | WP-007 | Data platform: segregated `DataProvider` ports (ADR-033), PIT `SqliteUniverseStore`, fail-closed `CsvCachePriceProvider`. **Phase 2 opened.** |
| 13ab642 | research | India execution landscape verified: Zerodha Kite primary (free personal API since Apr 2025), Fyers backup, Angel One retired, OpenAlgo reference-only. |
| 6b1bf5c | WP-008 | Execution vertical slice (ADR-034, deliberately ahead of phase order): broker ports (ADR-011/012), Paper/Zerodha/Angel adapters, persisted kill switch (ADR-009), gated `ExecutionEngine` + order journal, end-to-end demo. |
| 1d04d2f | hardening | Adversarial review: UNKNOWN-state error taxonomy (Kite 5xx, SmartAPI AB1004), data:null guards, tick-grid limit prices, journal re-run collision fix, per-ticker price fail-closed. Backlog → TD-013. |
| 288161e | WP-009 | Strategy platform: Momentum v1.0 behind the `Strategy` port, **byte-equal parity** with the frozen script (ADR-003), params externalized to `strategies_registry/momentum_v1.yaml` (ADR-015). **Phase 3 opened.** |
| 313967c | WP-010 | Operator console (ADR-035): static read-only page (halt tint, freshness pills, equity chart) + `tools/kill_switch.py` CLI. |
| 9b084e5 | ops | Unattended daily runner (`tools/daily_run.ps1`) + Windows scheduled task "QuantOS Daily Paper Run" (weekdays 15:40). 4 operator-interview decisions recorded in CONTEXT.md. |
| 8502ce3 | WP-011 | QuantOS Desktop (ADR-036): local FastAPI on 127.0.0.1:8742 + Edge `--app` window. Broker connect flows, dashboard, orders view, kill-switch UI (the single write surface, ADR-028). |

**ADRs:** 001–030 catalogued in the Constitution Part VI; 031–036 in `docs/adr/`.
Load-bearing ones: 003 (strangler-fig, verbatim relocation), 008 (fail-closed on
capital ambiguity), 009 (persisted kill switch, no bypass), 010 (paper=live,
only the adapter differs), 018/019 (bias detectors + deterministic replay as CI
gates), 030 (LLM layer deferred indefinitely).

**Reserved / next:** WP-006 (layered config — reserved since WP-002, unbuilt),
WP-012 (portfolio module), WP-013 (`run_cycle`) per the 2026-07-14 operator
interview. `paper_trader.py` remains the running system of record until
WP-012/013 wire `MomentumV1` into the daily cycle.

---

## Part 2 — Audit (four independent tracks, 2026-07-14)

Method: four parallel reviews — docs/governance sweep, `quantos_core`
correctness (adversarial, code traced end to end, edge behavior verified by
execution), operations reliability (unattended-run failure modes, scheduled
task queried live), desktop-app security (exploit-scenario driven). Every
finding below states its disposition.

### Verdict in one paragraph

The engineering discipline is real: 188 tests (now 199), ruff + `mypy --strict`
clean, byte-parity contract enforced, fail-closed patterns genuinely applied in
`quantos_core`. The governance paperwork had drifted badly (STATUS.md was 11
work packages stale), and — the central finding — **the safety architecture was
built next to, not into, the system that actually trades**: the "production"
kill switch was consulted by nothing in the daily loop, and `paper_trader.py`
(the legacy script the validation record depends on) had five distinct paths
that could silently corrupt or miss weeks of the 13-week record. All of those
are fixed as of today; the remaining items are ranked at the end.

### Critical (fixed today)

| # | Finding | Where |
|---|---|---|
| C1 | **Kill switch never consulted by the daily loop.** Engaging the operator's one halt control stopped nothing — the scheduled 15:40 run filled orders, triggered stops, and rebalanced anyway while the console showed HALTED. | `paper_trader.py` (no check existed) |
| C2 | **Duplicate pending orders corrupt the books.** Friday queueing ignored orders already pending from prior sessions: a stuck order re-queued weekly; duplicate SELL double-credits cash, duplicate BUY double-debits and overwrites the holding. A stuck BUY was *guaranteed* by fee math on the first full rebalance (10 × allocation × 1.001187 > cash → 10th order pends forever). | `paper_trader.py` |
| C3 | **Missed-Friday rebalance silently skipped.** Laptop asleep/logged out at Friday 15:40 → catch-up run fires Saturday → `weekday()==4` false → no rebalance, no universe snapshot, log says "OK". Over 13 weeks, near-certain to hit at least once. | `paper_trader.py` + `tools/daily_run.ps1` + task config (`Interactive only`, `StartWhenAvailable` was off) |
| C4 | **Drive-by kill-switch release (DNS rebinding).** The desktop API had no Host validation: a malicious webpage re-binding its hostname to 127.0.0.1 gets same-origin JSON access — could flip the halt OFF, drop broker sessions, read state. | `api/server.py` |

### High (fixed today)

| # | Finding | Where |
|---|---|---|
| H1 | Fills logged to CSV immediately but state saved only at run end; the task's 30-min kill window overlaps the Friday 500-ticker fetch → re-fills on next run. State writes were non-atomic; corrupt JSON then crashed trader + console daily. | `paper_trader.py` |
| H2 | Every network failure failed soft with exit 0 — "OK" logged for runs that computed nothing; regime check failed OPEN to BULL (an outage in a bear market would keep buying); stop-losses silently unmonitored on fetch failure. | `paper_trader.py` |
| H3 | Partial yfinance download → top-10 ranked from whatever subset downloaded → confidently wrong rebalance, undetectable afterwards. | `paper_trader.py` |
| H4 | Same-day rerun / market-holiday ffill filled queued orders at the very close that produced them — the look-ahead the T+1 queue exists to prevent. | `paper_trader.py` |
| H5 | A zero close in the price cache → `p_end/p_start` = +inf momentum → corrupt ticker ranked #1 and allocated 10% of capital. `dropna()` does not drop inf. | `quantos_core/data/prices.py` |
| H6 | Stale NSE tick constant (flat ₹0.05, pre-June-2024 reform): sub-₹250 buy limits floored below market rest unfilled forever — silently excluding exactly the low-price names momentum loves. | `quantos_core/brokers/orders.py` |
| H7 | Journal write failure AFTER successful broker placement discarded the receipt and raised — a placed live order becomes invisible, and a re-run re-places it (the duplicate-order bug the no-retry rule exists to prevent). | `quantos_core/execution/engine.py` |
| H8 | Regime MA warm-up read as BEAR, not "no data": `close > NaN` compares False and `.dropna()` on a bool series is a no-op — weeks of silent wrongful cash stance for any caller that doesn't pre-fetch extra history. | `quantos_core/factors/regime.py` |

### Medium / low (fixed today)

- `log_trade` rewrote the entire trades CSV per trade (one kill mid-write destroys the audit trail) → true append (`paper_trader.py`).
- Zerodha read paths lacked the data:null guards Angel got: `data: null` → raw TypeError; missing key → `{}` disguised as empty portfolio (`quantos_core/brokers/zerodha.py`).
- Angel login rejection (wrong PIN/TOTP, HTTP 200 + AB-code) surfaced as `OrderRejectedError` from a call that placed no order (`quantos_core/brokers/angel.py`).
- Journal failure on the BLOCKED path replaced `ExecutionBlockedError` with `StorageError` — kill-switch drill would crash instead of confirming the block (`engine.py`).
- Duplicate/unsorted cache dates leaked raw pandas exceptions instead of typed `DataFetchError` (`prices.py`).
- Runner log mojibake (PS 5.1 OEM decode of UTF-8), no HALTED/FAILED distinction, no venv-missing guard, no weekend snapshot catch-up (`tools/daily_run.ps1`, `tools/seed_universe_snapshot.py --skip-if-exists`).
- Scheduled task: `StartWhenAvailable` was off (missed trigger never fired late) → enabled live.

### Governance drift (fixed today)

- `STATUS.md` claimed "Phase 1 … last WP-000" — 11 work packages stale → rewritten.
- Risk/Tech-Debt registers claimed "no GitHub remote" — false since WP-001 era (`github.com/jinujon007/QuantOS` exists); actual gap is **12 unpushed commits** → R-005/TD-007 corrected, R-006 added (task logon mode).
- Register headers (`updated_by: WP-000/WP-002`) never maintained across 11 WPs → stamped.
- `AGENTS.md` said `npm test` / `npm run lint` in a Python repo → real commands + freeze-rule pointers.
- No `wp-011` tag (wp-001..010 all tagged) → tagged.

### Explicitly NOT changed (freeze discipline)

- **Strategy math, parameters, ranking, stop-loss, regime thresholds:** untouched. The momentum boundary quirk (last-row vs last-valid-price, one NaN can exclude a ticker) is **parity-pinned** — recorded as TD-014 for the Momentum v1.1 decision, not silently fixed.
- **Fill-allocation sizing:** not resized for fees. Dropping unaffordable buys (backtest semantics) chosen over a fee buffer, which would have been a sizing change on the frozen list.
- **Validation clock:** the paper_trader fixes alter behavior only in failure paths (duplicates, outages, missed runs) plus the holiday/same-day fill guard. Current clock stands at **0/13 rebalances** — nothing is lost regardless of how strictly the restart rule is read.

### Audit tracks that came back CLEAN

Kill-switch internals (fail-closed on unreadable state, correct exception
ordering); paper broker fill/reject semantics; UNKNOWN-state order taxonomy on
both live adapters (no POST retries, pinned by tests); `SqliteRepository`
transactions and injection guards; PIT universe store date logic; momentum
signal look-ahead (verified none); determinism (no set-iteration order affects
trades in core); desktop app credential handling (secrets memory-only, never
disk/logs/URLs), SQL/command/path-injection surfaces, localhost binding.

---

## Part 3 — What changed today, verification, and what's next

### Changes applied (this commit)

**Safety wiring** — `paper_trader.py`: kill-switch interlock (exit 2, fail-closed
if unreadable); regime three-state (UNKNOWN → no liquidation, no rebalance,
exit 1); degraded-run exits (signals empty / prices missing / regime unknown →
FAILED in the log, never "OK").

**Book integrity** — `paper_trader.py`: pending-order dedup (seeded from
persisted queue); orphan-SELL and duplicate/unaffordable-BUY dropped with
reasons; fills persisted immediately; atomic state writes; corrupt state →
`.bad` + loud exit; append-only trade log; `queued_on` stamps + new-bar fill
guard (same-day rerun and holiday ffill can no longer fill on the signal bar);
same-day guard (`--force` to override); Sat/Sun rebalance catch-up via
`last_rebalance_date`.

**Core hardening** — `prices.py` (non-positive/duplicate/unsorted → typed
errors); `regime.py` (explicit warm-up drop, parity preserved and re-pinned);
`engine.py` (`_record_or_log`: journal failure can't mask placement or the
block signal); `zerodha.py` (read-path guards); `angel.py` (login taxonomy);
`orders.py` (band-aware `nse_tick_size` + `to_tick_up`; demo buys ceil).

**Security** — `api/server.py`: `TrustedHostMiddleware` (127.0.0.1 / localhost
/ testserver) closes the DNS-rebinding path; regression tests pin the foreign-
Host 400 and the text/plain-body rejection so a dependency change can't
silently reopen CSRF.

**Ops** — `daily_run.ps1`: UTF-8 log encoding, venv guard, HALTED vs FAILED,
Fri–Sun snapshot with idempotent `--skip-if-exists`. Scheduled task:
`StartWhenAvailable=True` set live.

### Verification evidence

- Full suite: **199 passed** (188 pre-existing + 11 new regression tests), ruff clean, `ruff format` clean, `mypy --strict` clean on all 39 core files.
- Parity suite (ADR-003 gate) passes against the frozen script after the regime change — warm-up exclusion pinned explicitly.
- `paper_trader.py --selftest`: 6 scenarios including same-bar refusal, orphan SELL, duplicate/unaffordable BUY.
- Live drill: engage → `paper_trader.py` exits 2 with halt message; release → same-day guard exits 0 without touching state.
- Scheduled task re-queried: `StartWhenAvailable=True`, battery restrictions off, next run 15-07-2026 15:40.

### Ranked remaining work

1. **Push to origin** (operator, 1 min): 12 commits + tags exist only on this disk; CI has never run on GitHub Actions (TD-007/R-005). One disk failure loses WP-003→WP-011.
2. **Task logon mode** (operator decision, R-006): "Interactive only" still skips runs while logged out; StartWhenAvailable only defers to next logon. Full fix = run-whether-logged-on (stored credential) or an explicit missed-run tile on the console.
3. **SEBI compliance checklist** (R-001): 0/7, blocks any live order regardless of engineering.
4. **WP-012/013** (portfolio + `run_cycle`): retire `paper_trader.py` as system of record — the audit's whole critical section exists because the validated core isn't wired into the daily loop yet.
5. **TD-011 + TD-015**: fix packaging config, rebuild venv from lockfile, drop the dead LLM stack (~145 unpinned packages).
6. **TD-016**: decide paper-state versioning policy (one-line ADR).
7. **TD-014**: momentum boundary NaN behavior — decide at Momentum v1.1 (version bump + clock restart).
8. **Console "last run" tile**: surface daily_run.log OK/FAILED/HALTED on the dashboard so a week of failures can't hide behind freshness pills (ops finding 9, unfixed).

*Author: Claude (program audit session, 2026-07-14). Sources: git history,
docs/00_governance/*, docs/adr/*, four independent review tracks with live
verification on this machine.*
