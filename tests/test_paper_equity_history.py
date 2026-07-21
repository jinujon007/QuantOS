"""Equity history capture + metrics (WP-017, ADR-042).

The capture side lives in the frozen script (paper_trader.log_equity_snapshot,
logging-only, permitted by the CONTEXT.md freeze rule); the read side is
tools/paper_metrics.py. Load-bearing properties: true append (header written
once, rows never rewritten), last-write-wins dedup on --force reruns, Sharpe
arithmetic pinned against a hand-computed series, zero-volatility handled as
undefined rather than a division crash, and the CLI's exit codes for the
missing/insufficient-history cases.
"""

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import paper_trader  # noqa: E402
from tools.paper_metrics import compute_metrics, load_history, main  # noqa: E402


@pytest.fixture
def equity_file(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "paper_equity_history.csv"
    monkeypatch.setattr(paper_trader, "EQUITY_FILE", path)
    return path


def test_snapshot_true_append_header_once(equity_file) -> None:
    paper_trader.log_equity_snapshot("2026-07-21", 101_234.567, 5_000.123, 9)
    paper_trader.log_equity_snapshot("2026-07-22", 102_000.0, 5_000.12, 9, degraded=True)

    text = equity_file.read_text()
    assert text.count("date,total_value,cash,positions,degraded") == 1, "header must be written exactly once"
    frame = pd.read_csv(equity_file)
    assert len(frame) == 2
    assert frame.loc[0, "total_value"] == 101_234.57  # rounded to paise
    assert bool(frame.loc[0, "degraded"]) is False
    assert bool(frame.loc[1, "degraded"]) is True


def test_force_rerun_appends_reader_keeps_last(equity_file) -> None:
    paper_trader.log_equity_snapshot("2026-07-21", 100.0, 100.0, 0)
    paper_trader.log_equity_snapshot("2026-07-21", 200.0, 200.0, 0)  # --force rerun same day

    assert len(pd.read_csv(equity_file)) == 2, "audit trail: both rows must survive on disk"
    history = load_history(equity_file)
    assert len(history) == 1, "readers must see one row per date"
    assert history.loc[0, "total_value"] == 200.0, "last write wins"


def test_load_history_sorts_by_date(tmp_path) -> None:
    path = tmp_path / "eq.csv"
    pd.DataFrame(
        {"date": ["2026-07-22", "2026-07-21"], "total_value": [110.0, 100.0], "cash": [0, 0], "positions": [1, 1]}
    ).to_csv(path, index=False)
    history = load_history(path)
    assert list(history["date"]) == ["2026-07-21", "2026-07-22"]


def test_sharpe_pinned_against_hand_computation() -> None:
    values = pd.Series([100.0, 102.0, 101.0, 104.0])
    returns = values.pct_change().dropna()
    expected = float(returns.mean()) / float(returns.std()) * math.sqrt(252)

    metrics = compute_metrics(values)
    assert metrics.sharpe == pytest.approx(expected)
    assert metrics.total_return == pytest.approx(0.04)
    # peak 102 -> trough 101 is the only drawdown
    assert metrics.max_drawdown == pytest.approx(101.0 / 102.0 - 1.0)


def test_zero_volatility_sharpe_is_undefined_not_a_crash() -> None:
    metrics = compute_metrics(pd.Series([100.0, 100.0, 100.0]))
    assert metrics.sharpe is None
    assert metrics.total_return == 0.0
    assert metrics.max_drawdown == 0.0


def test_monotonic_loss_has_negative_sharpe_and_full_series_drawdown() -> None:
    metrics = compute_metrics(pd.Series([100.0, 95.0, 90.0]))
    assert metrics.sharpe is not None and metrics.sharpe < 0
    assert metrics.max_drawdown == pytest.approx(0.90 - 1.0)


def test_cli_missing_file_exits_1(tmp_path, capsys) -> None:
    assert main(["--file", str(tmp_path / "nope.csv")]) == 1
    assert "No equity history" in capsys.readouterr().out


def test_cli_single_row_exits_1(tmp_path, capsys) -> None:
    path = tmp_path / "eq.csv"
    pd.DataFrame({"date": ["2026-07-21"], "total_value": [100.0], "cash": [100.0], "positions": [0]}).to_csv(
        path, index=False
    )
    assert main(["--file", str(path)]) == 1
    assert "Insufficient history" in capsys.readouterr().out


def test_cli_reports_metrics_and_degraded_warning(tmp_path, capsys) -> None:
    path = tmp_path / "eq.csv"
    pd.DataFrame(
        {
            "date": ["2026-07-21", "2026-07-22", "2026-07-23"],
            "total_value": [100_000.0, 101_000.0, 100_500.0],
            "cash": [100_000.0, 1_000.0, 500.0],
            "positions": [0, 9, 9],
            "degraded": [False, True, False],
        }
    ).to_csv(path, index=False)
    assert main(["--file", str(path)]) == 0
    out = capsys.readouterr().out
    assert "3 days" in out
    assert "Sharpe" in out
    assert "WARNING: 1/3 rows are degraded" in out


def test_cli_handles_history_without_degraded_column(tmp_path, capsys) -> None:
    """Backward/forward tolerance: a hand-seeded history without the
    degraded column must still compute, not KeyError."""
    path = tmp_path / "eq.csv"
    pd.DataFrame(
        {"date": ["2026-07-21", "2026-07-22"], "total_value": [100.0, 101.0], "cash": [0, 0], "positions": [1, 1]}
    ).to_csv(path, index=False)
    assert main(["--file", str(path)]) == 0
    assert "WARNING" not in capsys.readouterr().out
