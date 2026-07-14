"""Point-in-time universe store (WP-007, ADR-033).

Maintains dated index-membership snapshots; get_universe(as_of)
resolves the latest snapshot at or before the asked date. This is the
structural fix for F1/F9: a caller cannot receive today's constituent
list when it asked about 2019 -- if no snapshot existed by then, the
query fails loudly instead.

SQLite via stdlib (the data module's own adapter I/O -- ADR-032/033:
`data` does not depend on quantos_core.storage).
"""

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path

from quantos_core.data.errors import DataFetchError
from quantos_core.data.provider import Ticker


class SqliteUniverseStore:
    """UniverseProvider adapter over dated membership snapshots.

    Snapshots are immutable once recorded: re-recording an existing
    snapshot_date requires replace=True, never happens silently.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        try:
            with closing(sqlite3.connect(db_path)) as conn, conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS universe_membership ("
                    "snapshot_date TEXT NOT NULL, ticker TEXT NOT NULL, "
                    "PRIMARY KEY (snapshot_date, ticker))"
                )
        except sqlite3.Error as exc:
            raise DataFetchError(f"Universe store unavailable at {db_path}: {exc}") from exc

    def record_snapshot(self, snapshot_date: date, tickers: list[Ticker], replace: bool = False) -> None:
        """Record one dated membership snapshot, transactionally.

        Raises DataFetchError on an empty ticker list, on a duplicate
        snapshot_date without replace=True, or on any storage failure.
        """
        if not tickers:
            raise DataFetchError(f"Refusing to record an empty universe snapshot for {snapshot_date.isoformat()}")
        key = snapshot_date.isoformat()
        try:
            with closing(sqlite3.connect(self._db_path)) as conn, conn:
                existing = conn.execute(
                    "SELECT COUNT(*) FROM universe_membership WHERE snapshot_date = ?", (key,)
                ).fetchone()[0]
                if existing and not replace:
                    raise DataFetchError(
                        f"Snapshot {key} already recorded ({existing} tickers); pass replace=True to overwrite"
                    )
                if existing:
                    conn.execute("DELETE FROM universe_membership WHERE snapshot_date = ?", (key,))
                conn.executemany(
                    "INSERT INTO universe_membership (snapshot_date, ticker) VALUES (?, ?)",
                    [(key, str(t)) for t in tickers],
                )
        except sqlite3.Error as exc:
            raise DataFetchError(f"Failed to record universe snapshot {key}: {exc}") from exc

    def get_universe(self, as_of: date) -> list[Ticker]:
        """Membership from the latest snapshot at or before as_of, sorted."""
        snapshot = self.latest_snapshot_date(as_of)
        try:
            with closing(sqlite3.connect(self._db_path)) as conn, conn:
                rows = conn.execute(
                    "SELECT ticker FROM universe_membership WHERE snapshot_date = ? ORDER BY ticker",
                    (snapshot.isoformat(),),
                ).fetchall()
        except sqlite3.Error as exc:
            raise DataFetchError(f"Failed to read universe snapshot {snapshot.isoformat()}: {exc}") from exc
        return [Ticker(row[0]) for row in rows]

    def latest_snapshot_date(self, as_of: date) -> date:
        """The snapshot date that would serve a get_universe(as_of) call.

        Exposed so callers can see and log staleness explicitly (a
        2019 query served by a 2026 first-seeding snapshot is visibly
        survivorship-biased, per the 2026-07-12 decision record).
        """
        try:
            with closing(sqlite3.connect(self._db_path)) as conn, conn:
                row = conn.execute(
                    "SELECT MAX(snapshot_date) FROM universe_membership WHERE snapshot_date <= ?",
                    (as_of.isoformat(),),
                ).fetchone()
        except sqlite3.Error as exc:
            raise DataFetchError(f"Failed to resolve universe snapshot for {as_of.isoformat()}: {exc}") from exc
        if row is None or row[0] is None:
            raise DataFetchError(
                f"No universe snapshot exists at or before {as_of.isoformat()} -- refusing to guess membership"
            )
        return date.fromisoformat(row[0])
