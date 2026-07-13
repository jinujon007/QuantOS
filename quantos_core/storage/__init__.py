"""Persistence layer: repositories over SQLite/Postgres (state, orders, trades)
and Parquet (historical OHLCV).

Empty by design (QuantOS Constitution, Part IX / ADR-031). Phase 0 repository
organization only -- no implementation yet. Populated starting Phase 1, per the
frozen QuantOS Target Architecture Blueprint's module specification, strangler-
fig migration (ADR-003), never a rewrite of the frozen scripts at the repo
root.
"""
