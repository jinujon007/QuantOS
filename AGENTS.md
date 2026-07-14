# AGENTS.md

## Test commands

```powershell
.\venv\Scripts\python.exe -m pytest tests -q          # 190 tests, offline by default
.\venv\Scripts\python.exe -m ruff check .             # lint
.\venv\Scripts\python.exe -m ruff format --check .    # formatting
.\venv\Scripts\python.exe -m mypy quantos_core --strict
```

## Ground rules for agents

- Read `CONTEXT.md` first — Prospective Validation freeze is active:
  strategy logic/params are frozen until 13 weekly rebalances complete.
- `quantos_core/` is mypy --strict + ruff gated; the six root scripts are
  frozen legacy (per-file ignores in `pyproject.toml`).
- Import boundaries are CI-enforced (ADR-032) — check `docs/adr/` before
  adding cross-module imports.
- Kill switch and fail-closed semantics are non-negotiable (ADR-008/009).

## Loop conventions

- Report-only week one (L1) before enabling auto-fix (L2)
- See LOOP.md for cadence and human gates
