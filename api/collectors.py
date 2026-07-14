"""Read models for the operator surfaces (WP-011).

One place that turns the system's real artifacts -- paper state,
registry, pinned equity curve, PIT universe store, order journal,
production kill switch -- into plain dicts. Consumed by both the
desktop app's API (api/server.py) and the static console generator
(tools/build_dashboard.py). Every collector degrades gracefully:
missing artifact -> explicit absence, never a guess.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
import yaml

from quantos_core.risk import KillSwitch, KillSwitchState
from quantos_core.storage import SqliteRepository, StorageError
from quantos_core.strategies import load_momentum_params

REPO = Path(__file__).resolve().parents[1]


def collect_paper_state() -> dict:
    path = REPO / "data" / "paper_state.json"
    if not path.exists():
        return {"available": False}
    state = json.loads(path.read_text(encoding="utf-8"))
    return {"available": True, **state}


def production_kill_switch() -> KillSwitch:
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(
        REPO / "data" / "risk.db", "kill_switch", KillSwitchState
    )
    return KillSwitch(repo)


def collect_kill_switch() -> dict:
    try:
        return {"engaged": production_kill_switch().is_engaged()}
    except StorageError:
        return {"engaged": True}  # unreadable = blocked; surfaces show the truth


def collect_strategy() -> dict:
    params = load_momentum_params(REPO / "strategies_registry" / "momentum_v1.yaml")
    return {
        "name": "nifty500-weekly-momentum",
        "version": params.version,
        "params": params.model_dump(),
    }


def collect_equity() -> dict:
    path = REPO / "data" / "results" / "equity_curve.csv"
    if not path.exists():
        return {"available": False}
    curve = pd.read_csv(path, parse_dates=["date"]).dropna()
    values = curve["value"].astype(float)
    dates = curve["date"]
    years = (dates.iloc[-1] - dates.iloc[0]).days / 365.25
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0
    running_max = values.cummax()
    drawdown = values / running_max - 1
    weekly_returns = values.pct_change().dropna()
    sharpe = 0.0
    if float(weekly_returns.std()) > 0:
        sharpe = float(weekly_returns.mean() / weekly_returns.std()) * (52**0.5)
    return {
        "available": True,
        "points": [(d.strftime("%Y-%m-%d"), round(float(v), 2)) for d, v in zip(dates, values)],
        "start": dates.iloc[0].strftime("%Y-%m-%d"),
        "end": dates.iloc[-1].strftime("%Y-%m-%d"),
        "final": float(values.iloc[-1]),
        "initial": float(values.iloc[0]),
        "cagr": cagr,
        "max_dd": float(drawdown.min()),
        "sharpe": sharpe,
    }


def collect_universe() -> list[dict]:
    db = REPO / "data" / "universe_pit.db"
    if not db.exists():
        return []
    with closing(sqlite3.connect(db)) as conn:
        rows = conn.execute(
            "SELECT snapshot_date, COUNT(*) FROM universe_membership GROUP BY snapshot_date ORDER BY snapshot_date DESC"
        ).fetchall()
    return [{"date": r[0], "count": r[1]} for r in rows]


def collect_journal(limit: int = 40) -> list[dict]:
    db = REPO / "data" / "demo" / "journal.db"
    if not db.exists():
        return []
    with closing(sqlite3.connect(db)) as conn:
        rows = conn.execute("SELECT id, document FROM order_journal ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(r[1]) for r in rows]


def collect_project_state() -> dict:
    path = REPO / ".ai" / "PROJECT_STATE.yaml"
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def collect_all() -> dict:
    """The desktop app's single state payload."""
    return {
        "paper": collect_paper_state(),
        "kill_switch": collect_kill_switch(),
        "strategy": collect_strategy(),
        "equity": collect_equity(),
        "universe": collect_universe(),
        "journal": collect_journal(),
        "project": collect_project_state(),
    }
