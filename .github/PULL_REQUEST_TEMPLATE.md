## What changed and why

<!-- One or two sentences. -->

## Solo-operator cooling-off checklist

- [ ] Does this touch a strategy currently under the Prospective Validation
      freeze (`CONTEXT.md`)? If yes, is restarting its observation clock
      intentional?
- [ ] Does this change any golden-file output (`tests/golden/`)? If yes,
      was it re-pinned deliberately (`python tools/capture_golden.py`) with
      the reason stated in this PR, not silently?
- [ ] Is there a test covering this change?
- [ ] Re-read this diff after a break, not immediately after writing it.

## Verification

- [ ] `pytest` passes locally (offline subset: `pytest -m "not network"`)
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] If this touches `momentum_backtest.py` or `paper_trader.py`: ran
      `python tools/verify_determinism.py` and confirmed no unexpected hash
      change
