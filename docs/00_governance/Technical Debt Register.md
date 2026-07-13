---
type: register
date: 2026-07-13
status: active
updated_by: WP-001 Repository Foundation
---

# Technical Debt Register

Living document. Updated at the end of every work package (never silently)
— items added when discovered, closed with the work package that resolved
them, never deleted from history (mark `Resolved`, keep the row).

| ID | Item | Severity | Impact | Discovered | Resolution phase | Est. effort |
|---|---|---|---|---|---|---|
| TD-001 | No per-trade log artifact anywhere in the codebase — `run_backtest()` returns only an equity curve, no trade-by-trade record | Medium | Can't audit individual trade decisions/fills after the fact; blocks any future forensic P&L attribution | Phase 0 (golden-file capture) | Phase 6 (Execution Engine) — `execution` module's order/trade journal closes this by design | Small once Phase 6 starts; not retrofittable into the frozen scripts without touching frozen logic |
| TD-002 | `paper_trader.py`'s live-update path (`run_daily_update`, `fetch_current_prices`, `check_regime`) has zero automated test coverage | Medium | A regression in the live daily path would only surface in production, not CI | Phase 0 | Phase 6 — `paper` module is designed to replace this loop entirely; testing the legacy loop directly isn't worth building | None now; superseded, not fixed |
| TD-003 | `fetch_universe.py`, `download_data.py`, `factor_attribution.py` — zero test coverage (0% each) | Low | Network-fetch/research tools; not on the live-trading critical path, but silent breakage wouldn't be caught | Phase 0 | Phase 2 (Data Platform) — `data` module replaces `fetch_universe.py`/`download_data.py`'s job entirely | None now; superseded, not fixed |
| TD-004 | `My_terminal/trading_backtests/` (16-strategy suite) has no git repository, no characterization tests, no golden files, no CI — zero Phase 0 safety net | High (for that codebase specifically) | Any future work touching that suite has no regression protection at all — it is *less* protected today than AlgoTrader/ was before Phase 0 | Phase 0 (scope decision — user confirmed AlgoTrader/-only git scope) | Requires its own Phase 0 pass, not yet scheduled | Medium — same shape of work as this repo's Phase 0, ~1 session |
| TD-005 | 29 pre-existing ruff findings in the 6 frozen scripts (E402 ×17 deliberate encoding-guard pattern, E501 ×12 wide print lines) | Low | Cosmetic/style only, no correctness risk; currently suppressed via disclosed `pyproject.toml` per-file-ignores | Phase 0 | Phase 1, only if/when those specific lines are touched during strangler-fig extraction — never a standalone fix | Trivial, but blocked on "don't touch frozen files" until Phase 1 |
| TD-006 | 7 pre-existing mypy errors in `momentum_backtest.py`/`paper_trader.py` (Optional-handling in `walk_forward_test`; `--selftest`'s monkeypatch pattern reads as `attr-defined` to the type checker) | Low | No runtime impact — code is correct, type checker just can't see it | Phase 0 | Phase 1 — resolved naturally once `strategies`/`paper` modules are typed from day one; not worth annotating legacy scripts for | Small, deferred |
| TD-007 | No GitHub remote configured — `.github/workflows/ci.yml` has never run in a real CI runner, only validated by running each step locally | Medium | CI config could have an environment-specific bug (e.g. `ubuntu-latest` path/line-ending differences vs this Windows dev machine) that local validation can't catch | Phase 0 | First push to a real remote — operator decision, not an engineering one | None (waiting on a decision, not effort) |
| TD-008 | Coverage is 25% overall — by design (TD-002/TD-003 explain the 0%-coverage files), no enforced floor yet | Low | Not a regression risk today; becomes one if new code is added without tests and coverage silently drifts lower | Phase 0 | Phase 1, once `quantos_core`'s real test pyramid exists and a floor makes sense to enforce | Policy decision, ~0 effort |
| TD-009 | Blueprint §3's literal repository tree omits two modules (`research`, `api`) that its own §5 module specs require | Low | Would have caused ambiguity again the next time someone scaffolds these modules from the Blueprint alone | WP-000, while resolving the chat-tree/Blueprint conflict | Resolved — placement decided in ADR-031 | Done |
| TD-010 | Import-boundary enforcement (Constitution Part II item 4; ADR-029 leaf enforcement for `experiments`/`tools`) is not mechanically enforced anywhere — no import-linter or equivalent exists | Low today (zero real code in `quantos_core` to violate a boundary) | Rises to Medium the moment WP-002+ lands real module code with nothing checking dependency direction | WP-001 (scoped out per Technical Review Board direction — Constitution/ADR requirement confirmed unmet, tooling explicitly deferred, not silently dropped) | Reserved as **WP-005 — Architectural Import Boundary Enforcement**, to be specified once `quantos_core` contains real implementation | Not yet estimated — WP-005 unspecified |

## Severity definitions

- **High** — affects an active live/paper-trading path, or leaves a whole codebase with no regression protection.
- **Medium** — affects correctness confidence or CI reliability, but not live capital or the currently-frozen strategies directly.
- **Low** — style/cosmetic, or fully superseded by a planned future module with no interim fix needed.
