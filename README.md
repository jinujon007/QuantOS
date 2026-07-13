# QuantOS

Institutional-grade automated trading platform for the Indian equity market.

**Status**
- Current Phase: Phase 1
- Architecture: Frozen
- Constitution: Frozen
- Current Milestone: Engineering Foundation
- Documentation: See [docs/](docs/)
- Repository Status: Active Development

---

Engineering setup and day-to-day commands. For what this project *is* --
strategy, research findings, roadmap -- see `CONTEXT.md` and `PRD.md`.
This file is scoped to Phase 0: how to install, test, and verify this
repository, nothing else.

## Setup

```
python -m venv venv
venv\Scripts\pip install -r requirements-lock.txt
```

`requirements-lock.txt` is a fully-resolved dependency closure (39
packages) -- resolved from `pyproject.toml`'s pinned top-level
dependencies in a clean environment, not filtered from a larger one.
Regenerate it per the comment at the top of that file if `pyproject.toml`'s
dependencies change.

## Running the strategy

```
venv\Scripts\python momentum_backtest.py          # full backtest + walk-forward
venv\Scripts\python momentum_backtest.py --selftest # self-checks only (one makes a real network call)
venv\Scripts\python paper_trader.py               # daily live update (mutates data/paper_state.json -- do not run casually)
venv\Scripts\python paper_trader.py --status      # read-only status check
venv\Scripts\python paper_trader.py --selftest    # self-checks only (fully offline)
```

## Testing

```
venv\Scripts\python -m pytest                 # offline suite (default; excludes the one network-dependent selftest)
venv\Scripts\python -m pytest -m network -o addopts=""  # include the network selftest
venv\Scripts\python -m coverage run -m pytest -m "not network" && venv\Scripts\python -m coverage report -m
```

What's covered: `transaction_costs.py`'s cost model (golden-value tests),
`momentum_backtest.py`'s full backtest + walk-forward (golden-file
comparison against `tests/golden/`, captured by `tools/capture_golden.py`),
and both scripts' existing `--selftest` suites. `paper_trader.py`'s live
update path, and the network-fetch utilities (`fetch_universe.py`,
`download_data.py`, `factor_attribution.py`), are deliberately not
exercised by automated tests -- they mutate live state or hit the network
by design, not something a characterization test should do casually. See
the Phase 0 execution report for the full reasoning.

## Golden files (`tests/golden/`)

The single source of truth for "does this change alter Momentum's output."
Re-generate only when a change to `momentum_backtest.py` is deliberate and
you can state why the output should differ:

```
venv\Scripts\python tools/capture_golden.py
```

This overwrites `tests/golden/momentum_*`. Commit the change with the
reason in the message -- never silently.

## Determinism check

```
venv\Scripts\python tools/verify_determinism.py 10
```

Runs `momentum_backtest.py` as 10 independent subprocesses and confirms
byte-identical output (after normalizing the Windows CRLF/LF write-time
difference -- see the script's docstring). Baseline result as of
`baseline-v1` + formatting: `equity_curve.csv` sha256
`e3d29859aa0011d1e7ca92252452cba0495d6b154def12bdd7b20ce5c8d96020`.

## Inventory

```
venv\Scripts\python tools/generate_inventory.py
```

Regenerates `INVENTORY.md` from git-tracked files. CI fails if the
committed file is stale (`git diff --exit-code INVENTORY.md`).

## Linting / formatting

```
venv\Scripts\ruff check .
venv\Scripts\ruff format .
venv\Scripts\mypy download_data.py factor_attribution.py fetch_universe.py momentum_backtest.py paper_trader.py transaction_costs.py
```

`pyproject.toml`'s `[tool.ruff.lint.per-file-ignores]` documents exactly
which findings are known, tracked debt in the six original scripts (and
why) versus what's actually enforced.

Optional local pre-commit hooks (lint + format-check only, not the full
test suite -- that runs in CI):

```
pip install pre-commit
pre-commit install
```

## What Phase 0 is and isn't

This repository's engineering scaffolding (tests, golden files, CI,
formatting, dependency lock) was added without changing
`momentum_backtest.py`, `paper_trader.py`, `transaction_costs.py`,
`fetch_universe.py`, `download_data.py`, or `factor_attribution.py`'s
observable behavior -- proven, not asserted, by re-running the full test
suite and a fresh determinism check after every change and confirming
identical results. See `git log` for the exact sequence:
`baseline-v1` (verbatim snapshot) -> tests/golden files/determinism proof
-> formatting (zero behavioral change, verified) -> repo standards.

This is Phase 0 of the roadmap described in the project's audit and
architecture documents. No migration, no new modules, no strategy changes
happened here -- that's later phases, not this one.
