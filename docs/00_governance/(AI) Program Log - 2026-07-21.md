---
type: report
date: 2026-07-21
area: self
project: AlgoTrader
status: active
ai_generated: true
---

# Program Log — 2026-07-21 (due-diligence audit + WP-014/015/016)

Session record, per the 2026-07-14 program-log convention. Everything
below is committed on branch `docs/institutional-dd-2026-07-21`
([PR #1](https://github.com/jinujon007/QuantOS/pull/1)), CI-gated.

## 1. Institutional due-diligence audit (morning)

Full 12-phase, evidence-tagged assessment written to
`docs/01_audits/(AI) QuantOS Institutional Due Diligence - 2026-07-21.md`
(commit `2104230`). Repository-first; market + OSS sections from
web research verified same day (GitHub/PyPI APIs, SEBI circulars).

**Verified state at audit time:** 233 tests green · CI green · paper
account ₹100,755, 9 positions from the **first real weekly rebalance**
(signal Fri 2026-07-17 → T+1 fills Mon 2026-07-20) · shadow harness
"Books MATCH" daily · validation clock ~1/13 · scores: 5.5/10
institutional readiness, concurring with the self-scored DRS 61/100.

**Findings new to the registers:**
- E-2 → now **TD-017**: equal-weight sizing always drops the 10th BUY
  on full redeployment (observed live: `SYRMA.NS 9893 < 10011`);
  backtest math identical, so no validity bug — bundle with TD-014
  into one Momentum v1.1 ADR at the version boundary.
- E-1 → now **TD-018**: frozen `_fetch_close` broad-except +
  regime-fail-open persists in the legacy script until cutover
  (superseded by the new core's UNKNOWN handling).
- **R-001 is simpler than registered:** SEBI regime fully enforced
  since 2026-04-01, but self-coded ≤10 orders/sec needs NO exchange
  registration — personal Kite key (free) + static-IP whitelisting
  (2 IPs) + broker Strategy-ID tag. Checklist needs a Zerodha rewrite;
  still 0 items executed. Effective date history: Aug→Oct 2025
  extensions, Jan 2026 broker onboarding bar, Apr 2026 full force.
- **ADR-023 (MLflow) and ADR-022 (empyrical) verified stale** against
  2026 upstream state (MLflow 3.x GenAI pivot; empyrical maintenance
  mode) — revisit both before Phase 5 executes; native ~50-line
  run-manifest recommended instead of MLflow.
- **yfinance:** structurally unreliable (curl_cffi TLS impersonation,
  silent history revisions — fatal for byte-identical reruns);
  cache-first pattern blunts it today; end-state = NSE bhavcopy
  primary + Kite historical (₹500/mo, now bundled) at live time.
  Bhavcopy-DIY confirmed as best-available India PIT method (Norgate
  has no NSE; arXiv 2603.19380 quantifies survivorship at ~4.9pp/yr).

## 2. Engineering loop (evening) — three work packages

| WP | ADR | Commit | Delivered |
|---|---|---|---|
| WP-014 | ADR-039 | `f39808a` | Operational safety net: `send_alert.ps1` (webhook on any non-clean daily run; `QUANTOS_ALERT_URL`, unset=SKIPPED), `backup_state.ps1` (dated daily backup of all non-git-protected state to `QUANTOS_BACKUP_DIR`, default `D:\QuantOS_Backups`, 30 kept; verified live ×2), `daily_watchdog.ps1` + registration script — **"QuantOS Daily Watchdog" task registered on this machine** (weekdays 16:30, boot-race-guarded). `daily_run.ps1`: PsStep helper, problem accumulation, backup step, alert dispatch. |
| WP-015 | ADR-040 | `4e25d22` | TD-016 decided + closed: `paper_state.json` untracked + gitignored (with `paper_trades.csv`, session scaffolding); WP-014 backups are the state history. 2026-07-17 PIT snapshot (504 tickers) committed as evidence; `equity_curve.csv` synced after verifying content = pinned sha `e3d29859…`. Working tree clean for the first time since the scheduler began mutating tracked files. |
| WP-016 | ADR-041 | `8dacd2c` | Phase 4 slice: `risk/limits.py` — `check_position_limit` (pure), `PositionLimitGate` (BUY ≤15% NAV/name; SELLs exempt; fail-closed on unreadable book), `CompositeGate` (first breach blocks; empty stack refused); structural `BookView`/`OrderLike` keep the ADR-032 cell clean. Demo runs the composed stack + new 7b drill: oversized order BLOCKED + journaled. 16 new tests incl. engine integration. |
| — | — | `20ebc7e` | `equity_comparison.csv` sync (determinism-run rewrite, content at pinned sha `6192c9d6…`). |

**Self-audit catches, fixed pre-commit:** Copy-Item nested
`shadow\shadow` on same-day backup re-runs (reproduced live);
watchdog boot-race false positive (3-min recheck); own docs briefly
claimed 20-new/253-total from an incremental pytest run — corrected to
16/249 from the full gate.

**Final gates:** 249 passed / ruff clean / format clean /
`mypy --strict` clean (44 files) / determinism 3× byte-identical /
import boundaries green / demo end-to-end verified.

**Register deltas:** R-005 → Low, R-006 → Low-Medium, TD-016 Resolved,
TD-017 + TD-018 added. `PROJECT_STATE.yaml` refreshed (was stale at
WP-010 / 178 tests).

## 3. Operator actions outstanding (nothing code can do)

1. **SEBI/Zerodha checklist** (rewritten scope per §1): personal Kite
   key, static IP + whitelisting, Strategy-ID/simulation confirmation
   in writing, ≤10 orders/sec bucket confirmation. Blocks live, not
   paper.
2. Set `QUANTOS_ALERT_URL` (ntfy topic) + subscribe — until then
   alerts log SKIPPED and the watchdog can detect but not notify.
3. Optionally point `QUANTOS_BACKUP_DIR` at a synced/second-disk
   folder (default is same-disk `D:\QuantOS_Backups`).
4. Cutover decision after Friday 2026-07-25's shadow match (2nd
   consecutive clean weekly candidate; first was 2026-07-17 week).
5. Merge PR #1 when reviewed (CI green on branch).

## 4. Next work package

**WP-017 — daily paper-equity history capture**: append
(date, portfolio value, cash, positions) per run from existing state —
freeze-safe, and converts the Sept-9 gate's "paper Sharpe > 1.0" from
uncomputable to computed (nothing in the repo can produce that number
today; gate is 7 weeks out). Then: TD-015 venv rebuild, TD-013 residue
at Phase 6, ADR-022/023 revisit before Phase 5.

## 5. Incident note (environment, not repo)

`~/.claude/skill-observations/` was deleted mid-session by an external
`.claude` junction migration; restored from session context. No repo
impact; noted here because the session-log trail briefly broke.
