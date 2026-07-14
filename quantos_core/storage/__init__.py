"""Persistence layer: repositories over SQLite (state, orders, trades);
Parquet (historical OHLCV) arrives with the data platform in Phase 2.

WP-003 implements the storage core slice: the Repository[T] port
(Constitution Part II, Interface Contracts), the Entity base model every
persisted aggregate extends, typed StorageError/EntityNotFoundError, and
the first concrete adapter, SqliteRepository (stdlib sqlite3, one table
per aggregate, transactional, fail-closed). No consumer is wired up yet;
the six frozen scripts are untouched (ADR-003, strangler-fig).
"""

from quantos_core.storage.errors import EntityNotFoundError, StorageError
from quantos_core.storage.repository import Entity, Repository
from quantos_core.storage.sqlite import SqliteRepository

__all__ = [
    "Entity",
    "EntityNotFoundError",
    "Repository",
    "SqliteRepository",
    "StorageError",
]
