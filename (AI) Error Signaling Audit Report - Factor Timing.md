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

# Error Signaling Audit Report — factor_timing_paper_trader.py

**Question:** can a genuine data outage in this strategy still look identical to a healthy run, after the Scheduler Contract Audit flagged this file's silent except blocks as the one remaining blind spot?

## Exception handlers reviewed

All 5 `except` blocks in the file — this is exhaustive, no others exist:

| Function | What it catches | Classification | Existing recovery (unchanged) |
|---|---|---|---|
| `get_vix()` | `^INDIAVIX` fetch failure | Recoverable data issue, but materially consequential — the 18.0 fallback sits inside `VIX_LOW=20`'s range, silently forcing regime determination toward LOWVOL_MOM rather than reflecting real market volatility | `return 18.0` |
| `get_nifty_momentum()` | bulk momentum fetch/compute failure | Recoverable data issue — cascades to LOWVOL_MOM selection being skipped | `return pd.Series(dtype=float)` |
| `get_nifty_volatility()` | bulk volatility fetch/compute failure | Same as above | `return pd.Series(dtype=float)` |
| `fetch_prices()` | batch price fetch failure | Recoverable data issue — affected buys/sells/valuations silently no-op via callers' existing `if not px: continue` guards | `return {}` |
| `fetch_gold_price()` | GOLDBEES.NS fetch failure | Recoverable data issue — GOLDBEES trades silently skipped via callers' existing `if gp > 0` guards | `return 0.0` |

None of these are "genuine catastrophic operational failure" in the sense of corrupting state or crashing the process — all 5 are intentional graceful-degradation-to-a-safe-default design, which is sound. The defect was never the recovery behavior; it was that the recovery carried zero signal, so a real data outage was indistinguishable from a quiet, uneventful day.

## Logging added

Each of the 5 except blocks: `except Exception:` → `except Exception as e:`, with one `print()` before the unchanged `return`. Every logged line includes all 5 required fields — function name, operation, exception type, exception message, recovery action — in one line, e.g.:

```
[ERROR] get_vix: fetch ^INDIAVIX failed (ConnectionError: simulated network failure) -- recovery: using fallback vix=18.0
```

The literal word "ERROR" is deliberate, not decorative — the scheduler's existing detection (`Invoke-Strategy`, audited and fixed in the prior task) matches `/(?i)\berror\b/` against captured output. Without that exact word, this task would add visibility to the log file but still leave the scheduler blind — which was the entire point of doing this.

## Behavior preserved

No return value changed. No trading logic, alpha, portfolio construction, or parameter touched. Confirmed by:
- A real `--status` run post-change produces byte-identical output to the pre-change run captured during the earlier determinism audit (`Rs101,513 +1.5% Regime: LOWVOL_MOM`, same 7-position table).
- The self-check asserts the exact fallback value (`18.0`, empty `Series`, `{}`, `0.0`) is still returned under a forced failure — recovery mechanics are untouched, only the silence is fixed.

## Self-check results

`factor_timing_paper_trader.py --selftest` (now runs both the pre-existing determinism check and this task's new one):

```
[PASS] test_lowvol_mom_selection_deterministic (...)
[PASS] test_error_signaling: get_vix (healthy/recoverable/unexpected all correct)
[PASS] test_error_signaling: get_nifty_momentum, get_nifty_volatility, fetch_prices, fetch_gold_price all log+recover correctly
```

`test_error_signaling` covers the 3 required scenarios:
1. **Successful execution** — healthy mocked data path produces no `[ERROR]` text (no false positives introduced).
2. **Recoverable data failure** — a `ConnectionError` produces a fully-populated log line and the unchanged fallback value.
3. **Unexpected exception** — a `KeyError` (a type with no relationship to network/data-fetch failures) is caught and logged identically, proving the bare `except Exception` isn't accidentally narrowed to one failure class.

`get_vix` gets the full 3-scenario treatment as the representative case (all 5 functions share an identical try/except-as-e/log/return-fallback shape); the other 4 get a lighter forced-failure check confirming the structured log line and correct fallback each.

## Remaining observability gaps

1. The `if df.empty: return 18.0`-style branches (a genuinely empty-but-not-exceptional API response, distinct from a caught exception) were left untouched — out of this task's stated scope ("audit every exception handler," not every silent fallback branch). Worth a future look: an empty response and a raised exception are both "the data didn't come through," and only one of them now logs.
2. `weekly_options_paper_trader.py` and `quality_paper_trader.py` have their own silent-except patterns (noted in the Scheduler Contract Audit) — not in this task's scope (factor_timing only).
3. No log rotation/aggregation — each `[ERROR]` line goes to stdout, captured by the scheduler's existing per-run log file. Fine for current volume, not something this task needed to address.

## Error Signaling Contract: satisfied

For `factor_timing_paper_trader.py`, within the scope of "exception handlers": **no exception that materially affects data quality or strategy execution fails silently.** All 5 handlers now emit a structured, scheduler-visible `[ERROR]` line with function name, operation, exception type, message, and recovery action, while every existing recovery behavior is provably unchanged.
