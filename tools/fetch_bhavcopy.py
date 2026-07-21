"""Fetch NSE bhavcopies + PR bundles into the immutable raw archive
(WP-018/019/021, ADR-044/045).

    python tools/fetch_bhavcopy.py [--date YYYY-MM-DD] [--out-dir PATH] [--pr-dir PATH]
    python tools/fetch_bhavcopy.py --start YYYY-MM-DD --end YYYY-MM-DD [...]

Per session, two official files from the cookie-free archives host:
the UDiFF bhavcopy zip (closes) into ``data/bhavcopy/`` and the PR
bundle zip (whose Bc member is NSE's corporate-action record) into
``data/nse_pr/`` — each stored as-published under its original
filename and never rewritten (DD 2026-07-21 §9.2). Files already
archived are not re-fetched (idempotent); archived copies are
re-parsed either way, so a corrupted archive file still fails loudly.

Range mode (``--start``/``--end``, WP-021 backfill) walks every NSE
session in the window with a politeness delay between real downloads,
keeps going past per-session failures (a mid-range special holiday the
calendar doesn't know about must not abort a 280-session backfill),
and reports every failure at the end. Exit 0 only when every session
in the range archived and parsed clean.

The raw stores are regenerable from NSE's public archive, so they are
gitignored and not part of the WP-014 backup set.

Exit codes: 0 = archived + parsed clean, 1 = any failure.
"""

import argparse
import sys
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantos_core.data import (  # noqa: E402
    DataFetchError,
    bhavcopy_url,
    extract_bc_csv,
    fetch_bhavcopy_zip,
    fetch_pr_zip,
    load_bhavcopy,
    parse_bc_csv,
    pr_url,
)
from quantos_core.utils import is_trading_session, most_recent_session, sessions_between  # noqa: E402

DEFAULT_OUT_DIR = REPO / "data" / "bhavcopy"
DEFAULT_PR_DIR = REPO / "data" / "nse_pr"
FETCH_DELAY_S = 0.8  # politeness gap between real downloads in range mode


def _ensure_archived(session: date, url: str, dest_dir: Path, fetch: Callable[[date], bytes]) -> tuple[bytes, bool]:
    """Return (payload, downloaded_now). Atomic write, never re-fetch."""
    dest = dest_dir / url.rsplit("/", 1)[-1]
    if dest.exists():
        print(f"Already archived: {dest.name}")
        return dest.read_bytes(), False
    payload: bytes = fetch(session)
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(dest)  # atomic: the archive never holds a truncated zip
    print(f"Archived {len(payload):,} bytes -> {dest.name}")
    return payload, True


def archive_one(session: date, out_dir: Path, pr_dir: Path, *, verbose: bool = True) -> bool:
    """Archive + verify one session's bhavcopy and PR bundle. Returns
    True when at least one real download happened (range-mode delay)."""
    payload, fetched_bhav = _ensure_archived(session, bhavcopy_url(session), out_dir, fetch_bhavcopy_zip)
    bhav = load_bhavcopy(payload)
    if bhav.trade_date != session:
        raise DataFetchError(
            f"archive dated {bhav.trade_date.isoformat()} but session {session.isoformat()} was requested"
        )
    pr_payload, fetched_pr = _ensure_archived(session, pr_url(session), pr_dir, fetch_pr_zip)
    records = parse_bc_csv(extract_bc_csv(pr_payload))
    if verbose:
        print(
            f"Session {bhav.trade_date.isoformat()}: {len(bhav.equities)} equity rows (series EQ/BE), "
            f"{len(records)} corporate-action records."
        )
        for symbol, close in bhav.equities["close"].head(3).items():
            print(f"  {symbol:<12} close {close:,.2f}")
    return fetched_bhav or fetched_pr


def run_range(start: date, end: date, out_dir: Path, pr_dir: Path) -> int:
    sessions = sessions_between(start, end)
    if not sessions:
        print(f"No NSE sessions in {start.isoformat()}..{end.isoformat()} — nothing to fetch.")
        return 1
    print(f"Backfilling {len(sessions)} sessions {sessions[0].isoformat()}..{sessions[-1].isoformat()}")
    failures: list[tuple[date, str]] = []
    for session in sessions:
        try:
            fetched = archive_one(session, out_dir, pr_dir, verbose=False)
        except DataFetchError as exc:
            failures.append((session, str(exc)))
            print(f"FAILED {session.isoformat()}: {exc}")
            fetched = True  # a failed attempt still hit the host; keep the gap
        if fetched:
            time.sleep(FETCH_DELAY_S)
    print(f"Done: {len(sessions) - len(failures)}/{len(sessions)} sessions archived clean.")
    for session, reason in failures:
        print(f"  MISSING {session.isoformat()}: {reason}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive NSE bhavcopies + PR bundles (immutable raw store).")
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="session date (default: most recent)")
    parser.add_argument("--start", type=date.fromisoformat, default=None, help="range mode: first date (inclusive)")
    parser.add_argument("--end", type=date.fromisoformat, default=None, help="range mode: last date (inclusive)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="bhavcopy archive directory")
    parser.add_argument("--pr-dir", type=Path, default=DEFAULT_PR_DIR, help="PR bundle archive directory")
    args = parser.parse_args(argv)

    if (args.start is None) != (args.end is None):
        parser.error("--start and --end must be given together")
    if args.start is not None and args.date is not None:
        parser.error("--date and --start/--end are mutually exclusive")

    if args.start is not None and args.end is not None:
        return run_range(args.start, args.end, args.out_dir, args.pr_dir)

    session = args.date if args.date is not None else most_recent_session(date.today())
    if not is_trading_session(session):
        print(f"{session.isoformat()} is not an NSE trading session — nothing to fetch.")
        return 1
    try:
        archive_one(session, args.out_dir, args.pr_dir)
    except DataFetchError as exc:
        print(f"FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
