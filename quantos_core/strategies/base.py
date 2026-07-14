"""The Strategy port and its domain types (WP-009).

Constitution Part II (Interface Contracts): ``Strategy(Protocol):
generate_signals(ctx: StrategyContext) -> TargetWeights`` plus
``metadata() -> StrategyMeta``. One strategy = one class implementing
this protocol + one YAML entry in strategies_registry.

TargetWeights carries an explicit stance because the frozen strategy
has three distinct behaviors, and collapsing them would lose signal:
"rebalance" (trade to these weights), "cash" (liquidate everything --
bear regime), "hold" (do nothing -- insufficient history to rank).
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Mapping, Protocol

import pandas as pd


@dataclass(frozen=True)
class StrategyContext:
    """Everything a strategy may look at. Supplied by the caller --
    a strategy cannot fetch, define, or guess its own data
    (Constitution Part II item 5)."""

    as_of: pd.Timestamp
    prices: pd.DataFrame  # Date-indexed closes, one column per ticker
    market_uptrend: bool


@dataclass(frozen=True)
class TargetWeights:
    stance: Literal["rebalance", "cash", "hold"]
    weights: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stance in ("cash", "hold") and self.weights:
            raise ValueError(f"stance {self.stance!r} must carry no weights")
        if self.stance == "rebalance":
            if not self.weights:
                raise ValueError("stance 'rebalance' requires weights")
            if any(w <= 0 for w in self.weights.values()):
                raise ValueError("weights must be positive")
            if sum(self.weights.values()) > 1.0 + 1e-9:
                raise ValueError("weights must not sum above 1.0")
        object.__setattr__(self, "weights", MappingProxyType(dict(self.weights)))


@dataclass(frozen=True)
class StrategyMeta:
    name: str
    version: str
    params: Mapping[str, object]


class Strategy(Protocol):
    def generate_signals(self, ctx: StrategyContext) -> TargetWeights: ...

    def metadata(self) -> StrategyMeta: ...
