"""Typed data-layer exceptions (WP-007).

DataFetchError is the structural replacement for the audit's
worst-scoring finding (download_data.py:64, a fully silent
``except Exception: return pd.DataFrame()``): a data failure is always
a typed, catchable event carrying the failing ticker/date context --
never a silently empty result (Constitution Part III, Error Handling;
ADR-007).
"""


class DataFetchError(Exception):
    """Any failure to obtain requested market data: missing ticker,
    absent point-in-time snapshot, unreadable cache, provider outage.
    Fail-closed: callers never receive an empty frame or list where a
    failure occurred."""
