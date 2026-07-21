"""NSE trading-session helpers over exchange-calendars (WP-018, ADR-044).

ADR-044 adopted the maintained exchange calendar in place of a
hand-kept holiday table. exchange-calendars registers the Indian
equity calendar as ``XBOM`` — there is no ``XNSE`` calendar; NSE and
BSE share the trading-holiday calendar, and XBOM is the maintained
source (correction recorded in ADR-044's acceptance note).

Calendar bounds are finite (currently 2006 → end of next year);
queries outside them raise exchange-calendars' own errors — callers
asking about dates decades away get a loud failure, never a guess.
"""

from datetime import date
from functools import lru_cache
from typing import Any

import exchange_calendars

_CALENDAR_NAME = "XBOM"


@lru_cache(maxsize=1)
def _calendar() -> Any:
    return exchange_calendars.get_calendar(_CALENDAR_NAME)


def is_trading_session(day: date) -> bool:
    """True when the NSE held (or holds) a normal session on ``day``."""
    return bool(_calendar().is_session(day.isoformat()))


def most_recent_session(day: date) -> date:
    """``day`` itself when it is a session, else the nearest prior session."""
    ts = _calendar().date_to_session(day.isoformat(), direction="previous")
    return date(int(ts.year), int(ts.month), int(ts.day))
