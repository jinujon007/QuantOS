"""Tests for the operator console generator and kill-switch CLI (WP-010).

The console is presentation over real artifacts, so the load-bearing
checks are: the Indian-format helper is exact, the kill-switch CLI
round-trips state fail-closed, and the generated page contains every
section with real data markers. Offline; CLI exercised via subprocess
against a temp database.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.build_dashboard import build_page, inr, outcome_tag  # noqa: E402

KILL_SWITCH = REPO / "tools" / "kill_switch.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(KILL_SWITCH), *args], capture_output=True, text=True, cwd=REPO)


def test_inr_indian_grouping() -> None:
    assert inr(583819) == "₹5,83,819"
    assert inr(100000) == "₹1,00,000"
    assert inr(999) == "₹999"
    assert inr(1000) == "₹1,000"
    assert inr(10000000) == "₹1,00,00,000"
    assert inr(-4322.23) == "-₹4,322"


def test_outcome_tags_cover_all_outcomes() -> None:
    assert 'class="tag fill"' in outcome_tag("FILLED")
    assert 'class="tag block"' in outcome_tag("BLOCKED")
    assert 'class="tag block"' in outcome_tag("UNKNOWN")
    assert 'class="tag wait"' in outcome_tag("OPEN")


def test_kill_switch_cli_round_trip(tmp_path: Path) -> None:
    db = str(tmp_path / "risk.db")
    status = run_cli("status", "--db", db)
    assert status.returncode == 0 and "not engaged" in status.stdout

    assert run_cli("engage", "--db", db).returncode != 0  # reason required

    engaged = run_cli("engage", "halt for test", "--db", db)
    assert engaged.returncode == 0 and "ENGAGED" in engaged.stdout
    assert "ENGAGED" in run_cli("status", "--db", db).stdout

    released = run_cli("release", "resume", "--db", db)
    assert released.returncode == 0
    assert "not engaged" in run_cli("status", "--db", db).stdout


def test_console_builds_with_all_sections() -> None:
    page = build_page()
    for marker in (
        "Operator Console",
        "Paper mode",  # mode banner
        "paper portfolio (virtual)",
        "strategies_registry/momentum_v1.yaml",
        "const EQUITY",  # chart data embedded
        "kill_switch.py engage",  # runbook
        "Zerodha Kite",
        "Angel One SmartAPI",
        "data-age-of",  # freshness pills
        "₹",
    ):
        assert marker in page, f"console missing section marker: {marker!r}"
    assert "{{" not in page  # every template slot filled
