"""Typed storage exceptions (WP-003).

Constitution Part III (Error Handling): typed exceptions only. A caller
never sees a raw sqlite3 error, a partial read, or a silently-empty
result where a failure occurred.
"""


class StorageError(Exception):
    """Any persistence failure: connection, write, read, or a stored
    document that no longer validates against its schema. Fail-closed:
    callers never receive a partial or guessed result."""


class EntityNotFoundError(StorageError):
    """A get() for an id that does not exist in the aggregate's table.

    Distinct from StorageError so callers can treat "absent" differently
    from "broken" -- but it still subclasses StorageError, so a caller
    that only handles the base type still fails closed."""
