"""The DataProvider ports (WP-007, ADR-033).

Segregated Protocols per ADR-012's precedent: a consumer depends only
on the capability it uses. Universe access is point-in-time only --
there is deliberately no argument-less "current universe" method
anywhere in this interface (ADR-017): the caller must always name the
date it is asking about.
"""

from datetime import date
from typing import NewType, Protocol

import pandas as pd

Ticker = NewType("Ticker", str)


class UniverseProvider(Protocol):
    """Point-in-time index membership."""

    def get_universe(self, as_of: date) -> list[Ticker]:
        """Return the index membership as of the given date, sorted.

        Raises DataFetchError if no membership is knowable for that
        date -- never an empty list as a failure disguise.
        """
        ...


class PriceProvider(Protocol):
    """Historical price series access."""

    def get_prices(self, tickers: list[Ticker], start: date, end: date) -> pd.DataFrame:
        """Return a Date-indexed close-price frame, one column per ticker.

        Raises DataFetchError if any requested ticker cannot be served
        -- never a silently narrower or empty frame.
        """
        ...
