"""Strategy platform: the Strategy port, its domain types, the
registry loader, and the strategies themselves -- one class per
strategy, parameters only from strategies_registry (ADR-015).

WP-009 (Phase 3 opening) ports the validated Momentum v1.0 behind the
port with proven signal parity against the frozen script. Zero change
to the six frozen scripts; the Prospective Validation clock is
unaffected (port, not change).
"""

from quantos_core.strategies.base import Strategy, StrategyContext, StrategyMeta, TargetWeights
from quantos_core.strategies.momentum_v1 import MomentumV1
from quantos_core.strategies.registry import (
    MomentumParams,
    StrategyRegistryError,
    load_momentum_params,
)

__all__ = [
    "MomentumParams",
    "MomentumV1",
    "Strategy",
    "StrategyContext",
    "StrategyMeta",
    "StrategyRegistryError",
    "TargetWeights",
    "load_momentum_params",
]
