"""Fetch one NSE bhavcopy into the immutable raw archive (WP-018, ADR-044).

    python tools/fetch_bhavcopy.py [--date YYYY-MM-DD] [--out-dir PATH]

Downloads the official UDiFF bhavcopy zip for the given session
(default: the most recent NSE session per the exchange calendar) into
``data/bhavcopy/``, stored as-published under its original filename and
never rewritten — the immutable raw store the point-in-time
architecture builds on (DD 2026-07-21 §9.2). A file already archived
is not re-fetched (idempotent); the archived copy is re-parsed and
summarized either way, so a corrupted archive file still fails loudly.

The raw store is regenerable from NSE's public archive, so it is
gitignored and not part of the WP-014 backup set.

Exit codes: 0 = archived + parsed clean, 1 = any failure.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantos_core.data import DataFetchError, bhavcopy_url, fetch_bhavcopy_zip, load_bhavcopy  # noqa: E402
from quantos_core.utils import is_trading_session, most_recent_session  # noqa: E402

DEFAULT_OUT_DIR = REPO / "data" / "bhavcopy"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive one session's NSE bhavcopy (immutable raw store).")
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="session date (default: most recent)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="archive directory (default: data/)")
    args = parser.parse_args(argv)

    session = args.date if args.date is not None else most_recent_session(date.today())
    if not is_trading_session(session):
        print(f"{session.isoformat()} is not an NSE trading session — nothing to fetch.")
        return 1

    dest = args.out_dir / bhavcopy_url(session).rsplit("/", 1)[-1]
    try:
        if dest.exists():
            print(f"Already archived: {dest}")
            payload = dest.read_bytes()
        else:
            payload = fetch_bhavcopy_zip(session)
            args.out_dir.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".tmp")
            tmp.write_bytes(payload)
            tmp.replace(dest)  # atomic: the archive never holds a truncated zip
            print(f"Archived {len(payload):,} bytes -> {dest}")

        bhav = load_bhavcopy(payload)
    except DataFetchError as exc:
        print(f"FAILED: {exc}")
        return 1

    if bhav.trade_date != session:
        print(f"FAILED: archive dated {bhav.trade_date.isoformat()} but session {session.isoformat()} was requested")
        return 1

    sample = bhav.equities["close"].head(3)
    print(f"Session {bhav.trade_date.isoformat()}: {len(bhav.equities)} equity rows (series EQ/BE).")
    for symbol, close in sample.items():
        print(f"  {symbol:<12} close {close:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
