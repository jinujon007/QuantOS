"""Shared low-level utilities with no domain dependencies.

WP-004 implements structured logging (Constitution Part III/Logging):
JSON-lines output where every record carries timestamp, level, module,
event, and run id. WP-018 adds the NSE trading-session helpers over
exchange-calendars (ADR-044; Part V, Market Holiday Handling).
The six frozen scripts are untouched (ADR-003, strangler-fig).
"""

from quantos_core.utils.logging import JsonLineFormatter, get_logger
from quantos_core.utils.trading_calendar import is_trading_session, most_recent_session

__all__ = [
    "JsonLineFormatter",
    "get_logger",
    "is_trading_session",
    "most_recent_session",
]
