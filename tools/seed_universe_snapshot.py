"""Seed / append a dated Nifty 500 membership snapshot into the PIT
universe store (WP-007, ADR-033).

Usage (venv):
    python tools/seed_universe_snapshot.py 2026-07-14
    python tools/seed_universe_snapshot.py 2026-07-14 --replace

Reads nifty500_universe.csv (the file fetch_universe.py maintains) and
records its tickers under the given snapshot date in
data/universe_pit.db. Refuses empty input and silent overwrites.
Pre-seeding history remains survivorship-biased by construction --
snapshots only accumulate real point-in-time value from first seeding
onward (Decision Record 2026-07-12).
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantos_core.data import SqliteUniverseStore, Ticker  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def load_universe_csv(path: Path) -> list[Ticker]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    column = "yf_ticker" if rows and "yf_ticker" in rows[0] else "ticker"
    tickers = sorted({row[column].strip() for row in rows if row.get(column, "").strip()})
    return [Ticker(t) for t in tickers]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_date", type=date.fromisoformat)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--csv", type=Path, default=REPO / "nifty500_universe.csv")
    parser.add_argument("--db", type=Path, default=REPO / "data" / "universe_pit.db")
    args = parser.parse_args()

    tickers = load_universe_csv(args.csv)
    store = SqliteUniverseStore(args.db)
    store.record_snapshot(args.snapshot_date, tickers, replace=args.replace)
    print(f"Recorded {len(tickers)} tickers as universe snapshot {args.snapshot_date.isoformat()} in {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
