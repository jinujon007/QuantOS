"""The Repository[T] port and the Entity base model (WP-003).

Constitution Part II (Interface Contracts): ``Repository[T]: get(id) -> T
| save(entity) | query(filter) -> list[T]``, one repository per aggregate.
The port is a Protocol (Part III, Typing: composition over inheritance);
concrete adapters (SQLite here, Postgres only if the stated upgrade
trigger -- concurrent writers -- is ever met) implement it structurally.

``save(entity)`` takes only the entity, per the frozen contract -- so every
persisted aggregate carries its own identity. Entity is the minimal base
model providing that: an ``id`` plus the same frozen/extra-forbid rigor
AppConfig established in WP-002.
"""

from collections.abc import Mapping
from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict


class Entity(BaseModel):
    """Base for every persisted aggregate: immutable, strict, self-identifying."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str


T = TypeVar("T", bound=Entity)


class Repository(Protocol[T]):
    """Persistence port for one aggregate type. Owned by the domain;
    implemented by adapters in this module's concrete backends."""

    def get(self, entity_id: str) -> T:
        """Return the entity with this id.

        Raises EntityNotFoundError if absent, StorageError on any failure.
        """
        ...

    def save(self, entity: T) -> None:
        """Insert or overwrite the entity under its own id, transactionally.

        Raises StorageError on any failure -- never a partial write.
        """
        ...

    def query(self, filter: Mapping[str, object]) -> list[T]:
        """Return all entities whose fields equal every (key, value) in
        filter, ordered by id (deterministic). An empty filter returns the
        whole aggregate.

        Raises StorageError if a filter key is not a field of the entity
        type -- a typo'd key must fail loudly, never return [] silently.
        """
        ...
