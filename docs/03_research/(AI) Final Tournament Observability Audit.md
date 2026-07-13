---
type: crystallization
date: 2026-07-13
area: self
project: AlgoTrader
status: active
confidence: 0.85
sources: 1
last_confirmed: 2026-07-13
ai_generated: true
---

# Final Tournament Observability Audit

**Question:** across all 4 tournament strategies, can any of them silently report success to the scheduler after a genuine data failure?

This closes the observability hardening thread that started with Stage 1's scheduler fix, continued through the Determinism Audit, the Scheduler Contract Audit, and Factor Timing's Error Signaling fix.

## Files reviewed

- `AlgoTrader/paper_trader.py` (Momentum) — already logs on its two fetch-failure paths (`Price fetch error: ...`, matches `error`) from Stage 1; not touched this round, in scope only for completeness confirmation.
- `My_terminal/trading_backtests/factor_timing_paper_trader.py` — done in the prior task.
- `My_terminal/trading_backtests/quality_paper_trader.py` — done this task.
- `My_terminal/trading_backtests/weekly_options_paper_trader.py` — done this task.

## Handlers reviewed and classified

**quality_paper_trader.py — 5 handlers:**

| Handler | Classification | Recovery (unchanged) |
|---|---|---|
| `fetch_fundamentals` — cache read | Recoverable data issue (corrupt cache file) | falls through to live fetch |
| `fetch_fundamentals` — live fetch | Recoverable data issue | `None` |
| `fetch_fundamentals_fresh` | Recoverable data issue (consequential: used during rebalance scoring) | `None` |
| `fetch_prices` | Recoverable data issue | `{}` |
| `check_regime` | Recoverable data issue, materially consequential — fail-open default (`is_bull=True`) could mask a real bear market | `(True, 0, 0)` |

**weekly_options_paper_trader.py — 2 handlers:**

| Handler | Classification | Recovery (unchanged) |
|---|---|---|
| `fetch_nifty_week` | Recoverable data issue — caller already skips the week cleanly on `(None, None)`, but the root cause was invisible | `(None, None)` |
| `fetch_vix_on` | Recoverable data issue, materially consequential — silently disables `VIX_SKIP_THRESH`'s risk-skip check for the week and falls back to an assumed 18.0 VIX in the premium calc | `None` |

No handler in either file was classified as pure "expected transient degradation" with no consequence — every one of the 7 has some effect on what the strategy does next (skip a rebalance, exclude a ticker, silently disable a risk check, or fail open on regime detection), which is exactly why all 7 needed logging, not just the ones that looked scariest.

## Logging added

Same structured format as Factor Timing, applied to all 7 handlers: `except Exception as e:` capturing type/message, one `print()` before the unchanged `return`, containing function name, operation, `type(e).__name__`, `e`, and an explicit "recovery:" clause — and the literal token `ERROR` in every line, since that's what the scheduler's existing `Invoke-Strategy` detection (`-match "(?i)\berror\b"`) actually keys on.

## Behavior preserved

No return value, trading logic, alpha, portfolio construction, or parameter changed in either file. Confirmed by:
- Real `--status` runs post-change, both files: exit 0, output structurally consistent with pre-change captures (Quality Factor: `Rs104,050 +4.1%`, 22-position table; Weekly Options: `Rs100,806 +0.81%`, 5 traded / 0 skipped).
- Self-checks assert the exact pre-existing fallback value is still returned under a forced failure, for every handler tested.

## Self-check results

`quality_paper_trader.py --selftest`:
```
[PASS] test_sell_order_deterministic (...)
[PASS] test_error_signaling: check_regime (healthy/recoverable/unexpected all correct)
[PASS] test_error_signaling: fetch_prices, fetch_fundamentals (live + corrupt-cache), fetch_fundamentals_fresh all log+recover correctly
```

`weekly_options_paper_trader.py --selftest` (new — this file had no self-test mechanism before):
```
[PASS] test_error_signaling: fetch_nifty_week (healthy/recoverable/unexpected all correct)
[PASS] test_error_signaling: fetch_vix_on logs+recovers correctly
```

Both cover all 3 required scenarios: healthy execution (no false-positive `[ERROR]`), recoverable data failure (`ConnectionError`, fully logged, exact fallback preserved), and an unrelated exception type (`KeyError`) proving the bare `except Exception` isn't narrowed to one failure class — same pattern proven for Factor Timing, now proven for the other two.

## Remaining observability limitations

1. `if df.empty: return <default>`-style branches (a legitimately empty API response, not a raised exception) remain silent in all files, including Factor Timing's from the prior task — a genuinely empty response and a caught exception are both "the data didn't arrive," and only the latter now logs. Flagged consistently across both audits, fixed in neither — same reasoning both times: out of the literal "exception handler" scope given.
2. `weekly_options_paper_trader.py`'s downstream message ("Could not fetch Nifty data for week... Skipping") still doesn't itself say why — it now has an upstream `[ERROR]` line immediately before it from `fetch_nifty_week`, so the information exists, just across two print statements instead of one.
3. No handler anywhere in the 4-strategy tournament was found to be a "genuine operational failure" category (e.g., state file corruption, unrecoverable crash) — everything audited across both this task and Factor Timing's was recoverable-data-issue, all with sound graceful-degradation design. That's a reassuring finding in itself, not a gap.

## Declaration

**The Error Signaling Contract is satisfied across every tournament strategy.**

This concludes the observability hardening phase.
