"""SQLite-backed Repository[T] adapter (WP-003).

Blueprint module 15 (storage): repositories over SQLite locally; Postgres
only if concurrent writers ever appear (explicit upgrade trigger, not
default). Documents are stored as the entity's own pydantic JSON, one
table per aggregate, and re-validated against the schema on every read --
a row that no longer validates is a StorageError, never a partially
constructed object.

stdlib sqlite3 only: no new dependency (Constitution Part I, complexity
requires justification traceable to a cited gap).
"""

import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Generic

from pydantic import ValidationError

from quantos_core.storage.errors import EntityNotFoundError, StorageError
from quantos_core.storage.repository import T

# Aggregate names become SQL identifiers; anything outside this alphabet is
# rejected at construction rather than interpolated into a statement.
_AGGREGATE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class SqliteRepository(Generic[T]):
    """One aggregate's repository over a local SQLite file.

    Generic over the concrete Entity subclass via the model_type argument;
    satisfies the Repository[T] Protocol structurally. One connection per
    operation, each inside a transaction that commits fully or rolls back
    fully.
    """

    def __init__(self, db_path: Path, aggregate: str, model_type: type[T]) -> None:
        if not _AGGREGATE_NAME.match(aggregate):
            raise StorageError(f"Invalid aggregate name {aggregate!r}: must match {_AGGREGATE_NAME.pattern}")
        self._db_path = db_path
        self._table = aggregate
        self._model_type = model_type
        with self._connection() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {self._table} (id TEXT PRIMARY KEY, document TEXT NOT NULL)")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        try:
            with closing(sqlite3.connect(self._db_path)) as conn:
                # sqlite3's connection context manager commits on success
                # and rolls back on exception; closing() then releases it.
                with conn:
                    yield conn
        except sqlite3.Error as exc:
            raise StorageError(f"SQLite failure on {self._db_path} [{self._table}]: {exc}") from exc

    def _validate(self, document: str) -> T:
        try:
            return self._model_type.model_validate_json(document)
        except ValidationError as exc:
            raise StorageError(
                f"Stored document in {self._table!r} no longer validates as {self._model_type.__name__}: {exc}"
            ) from exc

    def get(self, entity_id: str) -> T:
        with self._connection() as conn:
            row = conn.execute(f"SELECT document FROM {self._table} WHERE id = ?", (entity_id,)).fetchone()
        if row is None:
            raise EntityNotFoundError(f"No {self._table!r} entity with id {entity_id!r}")
        document: str = row[0]
        return self._validate(document)

    def save(self, entity: T) -> None:
        with self._connection() as conn:
            conn.execute(
                f"INSERT INTO {self._table} (id, document) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET document = excluded.document",
                (entity.id, entity.model_dump_json()),
            )

    def query(self, filter: Mapping[str, object]) -> list[T]:
        unknown = set(filter) - set(self._model_type.model_fields)
        if unknown:
            raise StorageError(f"Unknown filter field(s) for {self._model_type.__name__}: {sorted(unknown)}")
        with self._connection() as conn:
            rows = conn.execute(f"SELECT document FROM {self._table} ORDER BY id").fetchall()
        entities = [self._validate(row[0]) for row in rows]
        return [e for e in entities if all(getattr(e, key) == value for key, value in filter.items())]
