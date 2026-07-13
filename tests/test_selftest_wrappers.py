"""Wires the strategy scripts' existing `--selftest` self-checks into pytest.

These self-checks already existed and were already audited as real (not
fake) before Phase 0 — the Independent Audit's specific finding was that
they were "real, gated behind manual --selftest flags, not wired to any
runner" (§9). This file is that wiring. It does not touch the self-check
logic itself, which lives entirely in momentum_backtest.py / paper_trader.py
and is frozen per the Phase 0 mandate.

Invoked as a subprocess (not imported), matching exactly how a human
operator runs them today (`python momentum_backtest.py --selftest`) — this
is the lowest-risk way to wire an existing script's behavior into CI
without touching a single line of the script itself.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def _run_selftest(script: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, script, "--selftest"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_paper_trader_selftest():
    """paper_trader.py --selftest → test_pending_order_fill(). Fully
    monkeypatched inside the script itself (no network, no disk, no state
    mutation) — safe to run in any environment, including CI with no
    internet access."""
    result = _run_selftest("paper_trader.py")
    assert result.returncode == 0, (
        f"paper_trader.py --selftest failed (exit {result.returncode}).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "[PASS] test_pending_order_fill" in result.stdout


@pytest.mark.network
def test_momentum_backtest_selftest():
    """momentum_backtest.py --selftest → test_no_lookahead_bias() (pure,
    offline), test_regime_cache_reproducibility() (ALWAYS clears its
    throwaway cache dir first, so it makes a real network call to Yahoo
    Finance every invocation — this is existing behavior, unmodified),
    test_walkforward_causal_and_deterministic() (offline, uses the real
    cache). Marked @pytest.mark.network and excluded from the default
    offline CI run (see pyproject.toml `-m "not network"` default) because
    one of the three checks genuinely requires internet — that's a property
    of the script as it exists today, not something Phase 0 papers over."""
    result = _run_selftest("momentum_backtest.py", timeout=60)
    assert result.returncode == 0, (
        f"momentum_backtest.py --selftest failed (exit {result.returncode}).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    for expected in (
        "[PASS] test_no_lookahead_bias",
        "[PASS] test_regime_cache_reproducibility",
        "[PASS] test_walkforward_causal_and_deterministic",
    ):
        assert expected in result.stdout, f"missing expected pass line: {expected}"
