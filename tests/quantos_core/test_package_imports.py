"""Import smoke test for quantos_core (WP-001).

Asserts the root package and every subpackage import cleanly and carry
a purpose docstring (per WP-000's scaffolding convention). Establishes
the quantos_core test-pyramid entry point; no module has logic yet.
"""

import importlib

import pytest

SUBPACKAGES = [
    "analytics",
    "brokers",
    "config",
    "data",
    "execution",
    "factors",
    "live",
    "monitoring",
    "paper",
    "portfolio",
    "risk",
    "storage",
    "strategies",
    "utils",
    "validation",
]


def test_root_package_imports() -> None:
    module = importlib.import_module("quantos_core")
    assert module.__doc__


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackage_imports(subpackage: str) -> None:
    module = importlib.import_module(f"quantos_core.{subpackage}")
    assert module.__doc__
