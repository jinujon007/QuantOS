"""Pytest configuration for characterization tests.

The strategy scripts under test live at the repo root as plain modules
(momentum_backtest.py, paper_trader.py, transaction_costs.py) — not an
installed package. Phase 0 does not restructure them into a package (that's
a Phase 1+ migration decision, out of scope here), so tests import them by
adding the repo root to sys.path, exactly how a developer running
`python momentum_backtest.py` from this directory already does today.
"""

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True, scope="session")
def _repo_root_cwd():
    """The scripts under test use paths like Path("data/cache") relative to
    the process CWD (the same assumption `python momentum_backtest.py` makes
    when run from this directory). Pin CWD to repo root for the whole test
    session so `pytest` behaves identically regardless of the shell's
    starting directory — a test-harness concern, not a change to the
    scripts' own behavior."""
    original = os.getcwd()
    os.chdir(REPO_ROOT)
    yield
    os.chdir(original)
