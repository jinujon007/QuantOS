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

# Scheduler Contract Audit Report

**Question:** can `run_daily_traders.ps1` ever incorrectly report success when a strategy has actually failed, for any of the 4 tournament strategies (Momentum, Quality Factor, Factor Timing, Weekly Options)?

## Scope confirmed

All 4 strategies route through the identical `Invoke-Strategy` function — one contract, structurally shared, not 4 separate implementations to reconcile. Momentum uses `$AlgoVenv`, the other 3 share `$PyExe`; both paths converge on the same function.

## Tests performed

**1. Normal successful execution (real strategies, not synthetic).** Ran all 4 real scripts in their actual default/scheduled mode (safe on a non-rebalance Monday — no forced trades). All 4: exit code 0, zero false-positive matches for `/error/i` or `/traceback/i` in real healthy output. No strategy's normal output accidentally contains error-like text that would trip a false failure.

**2. Simulated failures**, against the real `Invoke-Strategy` function (extracted from the actual file, not retyped, to avoid drift between test and production code):

| Failure mode | Detected? | How |
|---|---|---|
| Uncaught exception / Python traceback | Yes | non-zero exit code |
| Non-zero exit, clean-looking text | Yes | exit code check (this is the exact original bug — text alone wouldn't have caught it) |
| Missing dependency (bad executable path) | **No, initially** | see finding below |
| Silent malformed output (exit 0, no error text, empty/wrong result) | No (expected) | documented limit, not a bug — see below |

## Finding: stale-exit-code gap (fixed)

A nonexistent `$Exe` path throws a PowerShell `CommandNotFoundException` that (a) never updates `$LASTEXITCODE` and (b) never flows into the `2>&1`-redirected output. Isolated proof: after `$LASTEXITCODE = 0`, invoking a bad path left `$LASTEXITCODE` at `0` and `$out` empty. Concretely: **if a strategy's Python executable silently breaks mid-run, and the previous strategy in the sequence exited cleanly, `Invoke-Strategy` would report success** — neither the exit-code check nor the text-match check would ever see the failure. Confirmed by a regression test ordered specifically to expose it (clean success immediately followed by a bad path) — before the fix, this read as success; not the two other failure tests, which happen to leave a non-zero exit code lying around that would have masked the same gap.

**Fix:** wrapped the `& $Exe @ScriptArgs` invocation in `try/catch` — any invocation-level exception (bad path, access denied, etc.) is now caught and explicitly reported as `[FAILURE] ... invocation error: ...`. Smallest possible change: one try/catch, no other logic touched.

**Also fixed while in this code:** the `$reason` failure message used an em-dash that rendered as mojibake (`â€`) in the actual log output (confirmed by running the real script — encoding mismatch between how the file was saved and how the console/log renders it). Cosmetic, doesn't affect detection, but a failure message you can't read defeats the point of "fail loudly." Replaced with plain ASCII `--`.

## Finding: silent malformed output — known, undetectable limit (not fixed)

If a script exits 0 and prints no error/traceback-matching text, but produced empty/wrong results (e.g. every fetch silently failing and returning defaults), the current keyword-based contract cannot and will not catch it. Verified this is the actual behavior (expected to read as success, and it does). This isn't a bug in the scheduler — keyword matching was never going to catch a failure with zero textual signal — but it's a real boundary of what "fails loudly" currently means. Two concrete instances of this exact pattern exist in the strategy scripts themselves (found while auditing, not fixed — would be a strategy-file change, out of this task's scope):

- `factor_timing_paper_trader.py`: `get_vix()`, `get_nifty_momentum()`, `get_nifty_volatility()`, `fetch_prices()`, `fetch_gold_price()` all have bare `except Exception: return <empty/default>` with **no print statement at all** — a total data outage would produce a completely clean, silent, "successful" run that did nothing useful.
- `weekly_options_paper_trader.py`: a failed fetch prints "Could not fetch Nifty data... Skipping" — doesn't match `/error/i` or `/traceback/i`, so it wouldn't be flagged either, though arguably this one is closer to intentional graceful degradation (skip, retry next session, no corrupted state) than a real failure.

These are genuine operational risks worth a future task (adding explicit logging to those except blocks), not fixed here per this task's "no strategy logic changes" rule — logging a caught exception isn't alpha logic, but it touches strategy files, and I'm flagging rather than acting unprompted.

## Automated regression self-check added

`run_daily_traders.ps1 --selftest` — added directly to the real scheduler script (matches the existing `--selftest` convention already used in `momentum_backtest.py`/`paper_trader.py`), not left as a throwaway. Runs 4 checks against the real `Invoke-Strategy` function: normal success, uncaught exception, non-zero exit with clean text, and the stale-exit-code regression (clean success immediately followed by a bad path). Uses a disposable temp log directory, never touches `trader_logs/`. All 4 pass:

```
PASS : normal success reported as success
PASS : uncaught exception reported as failure
PASS : non-zero exit with clean text reported as failure
PASS : missing dependency after a clean exit code reported as failure
RESULT: PASS
```

## Remaining operational risks

1. Silent malformed output (zero textual signal, exit 0) is undetectable by design under the current keyword-based contract — would need output-schema validation (e.g., checking the strategy's own state file actually updated, or a sanity check on portfolio value) to close, which is a bigger change than this audit's scope.
2. `factor_timing_paper_trader.py`'s fully-silent except blocks (listed above) are a real gap specific to that strategy — flagged, not fixed.
3. Not audited: `portfolio_tracker.py` (runs through the same `Invoke-Strategy` contract but isn't one of the 4 named tournament strategies) — same structural protection applies since it uses the identical function, but its own script-level error handling wasn't reviewed.

## Declaration

**All tournament strategies satisfy the scheduler execution contract and cannot silently report success after failure under the tested conditions** (uncaught exceptions, non-zero exits, missing dependencies). The one exception — completely silent malformed output with zero textual signal — is a documented, inherent limit of keyword-based detection, not a violation of the contract as designed; closing it would require a different detection mechanism entirely.
