"""Inventory classifier (TD-012 fix).

Pins the per-file scaffold-vs-platform split: implemented files under the
module-skeleton prefixes must never again be labeled "empty scaffold" —
that mislabeling recurred with every WP that added real quantos_core code.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.generate_inventory import classify  # noqa: E402


def test_real_module_code_is_platform_not_scaffold() -> None:
    assert classify("quantos_core/paper/cycle.py") == "platform"
    assert classify("quantos_core/config/schema.py") == "platform"
    assert classify("strategies_registry/momentum_v1.yaml") == "platform"


def test_stubs_remain_scaffold() -> None:
    assert classify("quantos_core/live/__init__.py") == "scaffold"
    assert classify("research/.gitkeep") == "scaffold"


def test_non_scaffold_paths_unaffected() -> None:
    assert classify("paper_trader.py") == "strategies"
    assert classify("tests/conftest.py") == "tests"
    assert classify("tools/paper_metrics.py") == "tooling"
    assert classify("pyproject.toml") == "configs"
