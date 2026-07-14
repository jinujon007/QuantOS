"""Risk engine: pre-trade gate, portfolio risk monitor, kill switch.

WP-008 (ADR-034 demo vertical slice) implements the persisted global
kill switch (ADR-009: a storage flag, checked before every order, no
bypass, fail-closed on unreadable state) and the KillSwitchGate seam
where Phase 4 adds the full Part V control table (position/sector/
drawdown/circuit-breaker limits). Depends only on storage/utils/
monitoring (ADR-032).
"""

from quantos_core.risk.gate import KillSwitchGate, RiskLimitBreach
from quantos_core.risk.kill_switch import KillSwitch, KillSwitchState

__all__ = [
    "KillSwitch",
    "KillSwitchGate",
    "KillSwitchState",
    "RiskLimitBreach",
]
