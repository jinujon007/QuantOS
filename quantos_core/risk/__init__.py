"""Risk engine: pre-trade gates, kill switch, composable limits.

WP-008 (ADR-034): persisted global kill switch (ADR-009 -- a storage
flag, checked before every order, no bypass, fail-closed on unreadable
state) behind the KillSwitchGate seam. WP-016 (ADR-041): Part V
controls land incrementally as composable gates -- PositionLimitGate
(single-name <= limit_pct of NAV) + CompositeGate (first breach
blocks); sector/aggregate/drawdown/circuit-breaker/liquidity/Algo-ID
gates follow as their data dependencies arrive. Depends only on
storage/utils/monitoring (ADR-032); books and orders arrive
structurally (BookView/OrderLike).
"""

from quantos_core.risk.gate import KillSwitchGate, RiskLimitBreach
from quantos_core.risk.kill_switch import KillSwitch, KillSwitchState
from quantos_core.risk.limits import (
    BookView,
    CompositeGate,
    PositionLimitGate,
    check_position_limit,
)

__all__ = [
    "BookView",
    "CompositeGate",
    "KillSwitch",
    "KillSwitchGate",
    "KillSwitchState",
    "PositionLimitGate",
    "RiskLimitBreach",
    "check_position_limit",
]
