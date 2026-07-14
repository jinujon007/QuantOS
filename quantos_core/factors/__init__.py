"""Pure factor math: signal transforms with zero I/O, trivially
unit-testable (Blueprint module 03: "deliberately dependency-free").

WP-009 implements the two factors the validated strategy needs, both
VERBATIM ports from the frozen scripts (ADR-003) with parity pinned by
tests: 12M-1M momentum and the trend-regime filter.
"""

from quantos_core.factors.momentum import momentum_12m1m
from quantos_core.factors.regime import is_uptrend, uptrend_series

__all__ = [
    "is_uptrend",
    "momentum_12m1m",
    "uptrend_series",
]
