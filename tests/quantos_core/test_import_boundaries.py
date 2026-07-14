"""Architectural import-boundary gate (WP-005, ADR-029/ADR-032).

Mechanically enforces the Constitution's dependency rules: the ADR-032
matrix of allowed internal imports between quantos_core modules, and
the ban on quantos_core importing outer layers (services, api,
dashboard, experiments, tools, research, tests) or the six frozen root
scripts. Runs in the default CI-blocking suite; a violation is a hard
failure, never a warning (ADR-018).
"""

import ast
from pathlib import Path

QUANTOS_CORE = Path(__file__).resolve().parents[2] / "quantos_core"

# ADR-032 matrix — widening any cell requires citing an ADR in the same
# change. Keys: quantos_core submodule; values: allowed internal imports.
ALLOWED_INTERNAL: dict[str, frozenset[str]] = {
    "utils": frozenset(),
    "monitoring": frozenset({"utils"}),
    "config": frozenset({"utils", "monitoring"}),
    "storage": frozenset({"utils", "monitoring"}),
    "brokers": frozenset({"utils"}),
    "data": frozenset({"utils", "monitoring"}),
    "factors": frozenset({"utils", "monitoring"}),
    "strategies": frozenset({"factors", "data", "utils", "monitoring"}),
    "portfolio": frozenset({"strategies", "risk", "storage", "utils", "monitoring"}),
    "risk": frozenset({"storage", "utils", "monitoring"}),
    "execution": frozenset({"brokers", "storage", "utils", "monitoring"}),
    "paper": frozenset({"strategies", "portfolio", "risk", "execution", "brokers", "utils", "monitoring"}),
    "live": frozenset({"strategies", "portfolio", "risk", "execution", "brokers", "utils", "monitoring"}),
    "analytics": frozenset({"storage", "factors", "utils", "monitoring"}),
    "validation": frozenset({"strategies", "data", "analytics", "utils", "monitoring"}),
}

# Never importable from anywhere inside quantos_core, in any form.
FORBIDDEN_TOP_LEVEL = frozenset(
    {
        "services",
        "api",
        "dashboard",
        "experiments",
        "tools",
        "research",
        "tests",
        # the six frozen root scripts (ADR-003)
        "momentum_backtest",
        "paper_trader",
        "transaction_costs",
        "fetch_universe",
        "download_data",
        "factor_attribution",
    }
)


def resolve_relative(file_module_parts: list[str], level: int, module: str | None) -> str:
    """Resolve a relative import to its absolute dotted name.

    file_module_parts are the dotted parts of the module CONTAINING the
    import (e.g. ["quantos_core", "storage", "sqlite"]).
    """
    base = file_module_parts[:-level] if level else file_module_parts
    return ".".join(base + ([module] if module else []))


def imported_names(path: Path, file_module_parts: list[str]) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                names.add(resolve_relative(file_module_parts, node.level, node.module))
            elif node.module:
                names.add(node.module)
    return names


def violations_in(path: Path) -> list[str]:
    relative = path.relative_to(QUANTOS_CORE.parent)
    file_module_parts = list(relative.with_suffix("").parts)
    if file_module_parts[-1] == "__init__":
        file_module_parts.pop()
    own_submodule = file_module_parts[1] if len(file_module_parts) > 1 else None

    found: list[str] = []
    for name in imported_names(path, file_module_parts):
        top = name.split(".")[0]
        if top in FORBIDDEN_TOP_LEVEL:
            found.append(f"{relative}: imports forbidden layer {name!r}")
            continue
        if top != "quantos_core":
            continue  # stdlib / third-party — not this gate's concern
        parts = name.split(".")
        target = parts[1] if len(parts) > 1 else None
        if target is None or target == own_submodule:
            continue  # bare package / own-module imports are fine
        if own_submodule is None:
            continue  # quantos_core/__init__.py may not exist yet as importer
        if target not in ALLOWED_INTERNAL.get(own_submodule, frozenset()):
            found.append(f"{relative}: {own_submodule!r} may not import quantos_core.{target} (ADR-032)")
    return found


def test_quantos_core_import_boundaries() -> None:
    all_violations: list[str] = []
    for path in sorted(QUANTOS_CORE.rglob("*.py")):
        all_violations.extend(violations_in(path))
    assert all_violations == [], "\n".join(all_violations)


def test_matrix_covers_every_package() -> None:
    packages = {p.name for p in QUANTOS_CORE.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    assert packages == set(ALLOWED_INTERNAL), (
        "quantos_core packages and the ADR-032 matrix have drifted apart; "
        "update tests/quantos_core/test_import_boundaries.py and file an ADR."
    )


def test_scanner_catches_forbidden_layer_import(tmp_path: Path) -> None:
    # Self-test (ADR-018 mutation spirit): a synthetic violating module
    # placed at a quantos_core-shaped path must be detected.
    bad = tmp_path / "quantos_core" / "factors" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("import tools\nfrom quantos_core.brokers import x\n", encoding="utf-8")
    parts = ["quantos_core", "factors", "bad"]
    names = imported_names(bad, parts)
    assert "tools" in names
    hits_forbidden = any(n.split(".")[0] in FORBIDDEN_TOP_LEVEL for n in names)
    hits_matrix = "brokers" not in ALLOWED_INTERNAL["factors"]
    assert hits_forbidden and hits_matrix


def test_scanner_resolves_relative_imports() -> None:
    assert resolve_relative(["quantos_core", "storage", "sqlite"], 1, "errors") == "quantos_core.storage.errors"
    assert resolve_relative(["quantos_core", "storage", "sqlite"], 2, "config") == "quantos_core.config"
