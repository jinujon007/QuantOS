"""Tests for quantos_core.storage (WP-003).

Covers the Repository[T] contract through the SqliteRepository adapter:
round-trip persistence, upsert, typed not-found/failure behavior,
fail-closed reads of corrupt or schema-drifted documents, filter
validation, deterministic ordering, cross-instance persistence, and the
aggregate-name injection guard. All I/O goes to pytest tmp_path -- no
shared state between tests.
"""

import sqlite3
from pathlib import Path

import pytest

from quantos_core.storage import (
    Entity,
    EntityNotFoundError,
    Repository,
    SqliteRepository,
    StorageError,
)


class Order(Entity):
    """Minimal test aggregate -- not a domain model, just a schema to persist."""

    ticker: str
    quantity: int


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "quantos_test.db"


@pytest.fixture
def repo(db_path: Path) -> SqliteRepository[Order]:
    return SqliteRepository(db_path, "orders", Order)


def test_save_then_get_round_trips(repo: SqliteRepository[Order]) -> None:
    order = Order(id="ord-1", ticker="RELIANCE", quantity=10)
    repo.save(order)
    assert repo.get("ord-1") == order


def test_save_is_upsert(repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="ord-1", ticker="RELIANCE", quantity=10))
    repo.save(Order(id="ord-1", ticker="RELIANCE", quantity=25))
    assert repo.get("ord-1").quantity == 25


def test_get_missing_raises_entity_not_found(repo: SqliteRepository[Order]) -> None:
    with pytest.raises(EntityNotFoundError):
        repo.get("absent")


def test_entity_not_found_is_a_storage_error() -> None:
    assert issubclass(EntityNotFoundError, StorageError)


def test_query_empty_filter_returns_all_ordered_by_id(repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="b", ticker="TCS", quantity=1))
    repo.save(Order(id="a", ticker="INFY", quantity=2))
    repo.save(Order(id="c", ticker="TCS", quantity=3))
    assert [o.id for o in repo.query({})] == ["a", "b", "c"]


def test_query_equality_filter(repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="a", ticker="INFY", quantity=2))
    repo.save(Order(id="b", ticker="TCS", quantity=1))
    repo.save(Order(id="c", ticker="TCS", quantity=3))
    result = repo.query({"ticker": "TCS"})
    assert [o.id for o in result] == ["b", "c"]


def test_query_multiple_conditions(repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="a", ticker="TCS", quantity=1))
    repo.save(Order(id="b", ticker="TCS", quantity=3))
    assert [o.id for o in repo.query({"ticker": "TCS", "quantity": 3})] == ["b"]


def test_query_unknown_field_fails_loudly(repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="a", ticker="TCS", quantity=1))
    with pytest.raises(StorageError, match="tikcer"):
        repo.query({"tikcer": "TCS"})


def test_query_is_deterministic(repo: SqliteRepository[Order]) -> None:
    for i in range(5):
        repo.save(Order(id=f"ord-{i}", ticker="TCS", quantity=i))
    assert repo.query({"ticker": "TCS"}) == repo.query({"ticker": "TCS"})


def test_persistence_across_instances(db_path: Path) -> None:
    SqliteRepository(db_path, "orders", Order).save(Order(id="x", ticker="HDFC", quantity=7))
    reopened: SqliteRepository[Order] = SqliteRepository(db_path, "orders", Order)
    assert reopened.get("x").ticker == "HDFC"


def test_corrupt_document_raises_storage_error(db_path: Path, repo: SqliteRepository[Order]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO orders (id, document) VALUES (?, ?)", ("bad", "not json at all"))
    with pytest.raises(StorageError):
        repo.get("bad")


def test_schema_drifted_document_raises_storage_error(db_path: Path, repo: SqliteRepository[Order]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO orders (id, document) VALUES (?, ?)", ("drift", '{"id": "drift"}'))
    with pytest.raises(StorageError):
        repo.get("drift")


def test_corrupt_document_fails_query_closed(db_path: Path, repo: SqliteRepository[Order]) -> None:
    repo.save(Order(id="good", ticker="TCS", quantity=1))
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO orders (id, document) VALUES (?, ?)", ("bad", "{}"))
    with pytest.raises(StorageError):
        repo.query({})


@pytest.mark.parametrize("name", ["Orders", "orders; DROP TABLE x", "1orders", "", "or ders"])
def test_invalid_aggregate_name_rejected(db_path: Path, name: str) -> None:
    with pytest.raises(StorageError):
        SqliteRepository(db_path, name, Order)


def test_unreachable_database_raises_storage_error(tmp_path: Path) -> None:
    with pytest.raises(StorageError):
        SqliteRepository(tmp_path, "orders", Order)  # a directory, not a db file


def test_two_aggregates_share_one_database(db_path: Path) -> None:
    orders: SqliteRepository[Order] = SqliteRepository(db_path, "orders", Order)
    fills: SqliteRepository[Order] = SqliteRepository(db_path, "fills", Order)
    orders.save(Order(id="only-in-orders", ticker="TCS", quantity=1))
    with pytest.raises(EntityNotFoundError):
        fills.get("only-in-orders")


def test_sqlite_repository_satisfies_the_port() -> None:
    # Structural check: assignment below is verified by mypy --strict;
    # at runtime it simply must not raise.
    def _accepts_port(repository: Repository[Order]) -> Repository[Order]:
        return repository

    repo: SqliteRepository[Order] = SqliteRepository(Path(":memory:"), "orders", Order)
    assert _accepts_port(repo) is repo


def test_entity_is_immutable() -> None:
    order = Order(id="a", ticker="TCS", quantity=1)
    with pytest.raises(Exception, match="frozen"):
        order.quantity = 2  # type: ignore[misc]
