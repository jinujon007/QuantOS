"""Pre-trade gate (WP-008 slice of Phase 4).

The demo-era gate enforces exactly one control -- the persisted global
kill switch -- but owns the seam where Phase 4 adds position limits,
sector exposure, drawdown and circuit-breaker checks. Accepts any
order object (structural typing keeps risk free of a brokers
dependency, per the ADR-032 matrix).
"""

from quantos_core.risk.kill_switch import KillSwitch


class RiskLimitBreach(Exception):
    """An order violates an active risk control. Named for what
    happened, not the class hierarchy (Constitution Part III)."""


class KillSwitchGate:
    """Blocks every order while the global kill switch is engaged --
    or while its state is unreadable (fail-closed, zero exceptions)."""

    def __init__(self, kill_switch: KillSwitch) -> None:
        self._kill_switch = kill_switch

    def check(self, order: object) -> None:
        if self._kill_switch.is_engaged():
            raise RiskLimitBreach("Global kill switch engaged -- all trading blocked")
