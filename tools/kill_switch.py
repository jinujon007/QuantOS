"""Operator kill-switch CLI (WP-010).

Constitution Part V: the global kill switch is "settable ... manually
via an operator CLI runnable from anywhere." This is that CLI.

    python tools/kill_switch.py status
    python tools/kill_switch.py engage  "reason for halt"
    python tools/kill_switch.py release "reason for resume"

State lives in data/risk.db (the PRODUCTION switch -- the demo uses
its own db under data/demo/). Every engage/release is persisted and
survives restarts; every order path checks it with no bypass.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantos_core.risk import KillSwitch, KillSwitchState  # noqa: E402
from quantos_core.storage import SqliteRepository  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def build_switch(db: Path) -> KillSwitch:
    repo: SqliteRepository[KillSwitchState] = SqliteRepository(db, "kill_switch", KillSwitchState)
    return KillSwitch(repo)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["status", "engage", "release"])
    parser.add_argument("reason", nargs="?", default="")
    parser.add_argument("--db", type=Path, default=REPO / "data" / "risk.db")
    args = parser.parse_args()

    switch = build_switch(args.db)
    if args.command == "status":
        engaged = switch.is_engaged()
        print(f"kill switch: {'ENGAGED -- all trading blocked' if engaged else 'not engaged -- trading permitted'}")
        return 0
    if not args.reason:
        raise SystemExit(f"A reason is required to {args.command} the kill switch -- it goes in the audit record.")
    if args.command == "engage":
        switch.engage(args.reason)
        print(f"kill switch ENGAGED: {args.reason}")
    else:
        switch.release(args.reason)
        print(f"kill switch released: {args.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
