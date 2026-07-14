"""Persisted global kill switch (WP-008 slice of Phase 4, ADR-009).

One boolean that survives process restart, stored through the storage
Repository, checked before every order with no bypass path. The one
place fail-closed has zero exceptions (Constitution Part V): if the
switch state cannot be READ, trading is blocked.
"""

from quantos_core.storage import Entity, EntityNotFoundError, Repository, StorageError

_SWITCH_ID = "global"


class KillSwitchState(Entity):
    engaged: bool
    reason: str


class KillSwitch:
    """Operator- or system-settable global trading halt."""

    def __init__(self, repository: Repository[KillSwitchState]) -> None:
        self._repository = repository

    def engage(self, reason: str) -> None:
        self._repository.save(KillSwitchState(id=_SWITCH_ID, engaged=True, reason=reason))

    def release(self, reason: str) -> None:
        self._repository.save(KillSwitchState(id=_SWITCH_ID, engaged=False, reason=reason))

    def is_engaged(self) -> bool:
        """True blocks all trading. Unreadable state ALSO blocks --
        ambiguity is never permission (zero-exception fail-closed)."""
        try:
            return self._repository.get(_SWITCH_ID).engaged
        except EntityNotFoundError:
            return False  # never engaged yet -- the one well-defined absence
        except StorageError:
            return True
