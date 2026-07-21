"""Bhavcopy-backed PriceProvider over the immutable raw archive (WP-021, ADR-045).

The Phase 2 capstone: serves corporate-action-adjusted, quality-validated
close series straight from the raw archives that ``tools/fetch_bhavcopy.py``
maintains — UDiFF bhavcopies (closes) plus PR bundles (official Bc
corporate-action records) — the bhavcopy-primary path of ADR-044, now
usable behind the ``PriceProvider`` port. Every session in the requested
window must be archived (a gap is a typed failure naming the fetch
command, never a narrower frame); adjustment events come from the
official records (WP-019) and every series is validated fail-closed
(WP-020) before it is returned. When validation fails and an
uncomputable corporate action (rights, scheme of arrangement, ...) sits
in the window for a requested symbol, the failure names that record —
the operator sees the *cause*, not just the symptom.

Returned prices are in the price basis of the window's last session
(standard back-adjustment): factors from actions with ex-dates inside
the window are applied to earlier closes; extending the window can
therefore rescale earlier values, exactly as any adjusted-price source
does. Future-dated records (Bc files list actions days ahead) are
never applied.
"""

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quantos_core.data.bhavcopy import Bhavcopy, bhavcopy_url, load_bhavcopy
from quantos_core.data.corporate_actions import (
    CorporateActionRecord,
    adjustment_multipliers,
    events_from_records,
    has_price_effect_risk,
    parse_bc_csv,
)
from quantos_core.data.errors import DataFetchError
from quantos_core.data.nse_pr import extract_bc_csv, pr_url
from quantos_core.data.provider import Ticker
from quantos_core.data.quality import DEFAULT_MAX_ABS_RETURN, DataQualityError, validate_close_frame
from quantos_core.utils import sessions_between

#: How many sessions before the window start to scan for corporate-action
#: records. NSE drops some records from the Bc file before their ex-date
#: (live scan 2026-07-22: 262 of 6,530 records, max gap 21 sessions —
#: including two real bonuses), so in-window files alone are not enough
#: (adversarial review ADV-2). 45 gives 2x headroom over the observed max.
_LOOKBACK_SESSIONS = 45


class BhavcopyPriceProvider:
    """PriceProvider adapter over the archived NSE bhavcopy + PR files."""

    def __init__(
        self,
        archive_dir: Path,
        pr_dir: Path,
        *,
        max_abs_return: float = DEFAULT_MAX_ABS_RETURN,
    ) -> None:
        if not archive_dir.is_dir():
            raise DataFetchError(f"Bhavcopy archive directory does not exist: {archive_dir}")
        if not pr_dir.is_dir():
            raise DataFetchError(f"PR bundle archive directory does not exist: {pr_dir}")
        self._archive_dir = archive_dir
        self._pr_dir = pr_dir
        self._max_abs_return = max_abs_return
        self._bhav_cache: dict[date, Bhavcopy] = {}
        self._records_cache: dict[date, list[CorporateActionRecord]] = {}

    def _archived(self, session: date, url: str, base_dir: Path, kind: str) -> bytes:
        name = url.rsplit("/", 1)[-1]
        path = base_dir / name
        if not path.is_file():
            raise DataFetchError(
                f"No archived {kind} for session {session.isoformat()} (expected {name}) — "
                f"run tools/fetch_bhavcopy.py to backfill the archive"
            )
        return path.read_bytes()

    def _load_session(self, session: date) -> Bhavcopy:
        cached = self._bhav_cache.get(session)
        if cached is not None:
            return cached
        bhav = load_bhavcopy(self._archived(session, bhavcopy_url(session), self._archive_dir, "bhavcopy"))
        if bhav.trade_date != session:
            raise DataFetchError(
                f"Archive file for {session.isoformat()} is dated {bhav.trade_date.isoformat()} — corrupt archive"
            )
        self._bhav_cache[session] = bhav
        return bhav

    def _load_records(self, session: date) -> list[CorporateActionRecord]:
        cached = self._records_cache.get(session)
        if cached is not None:
            return cached
        payload = self._archived(session, pr_url(session), self._pr_dir, "PR bundle")
        records = parse_bc_csv(extract_bc_csv(payload))
        self._records_cache[session] = records
        return records

    def _load_records_if_archived(self, session: date) -> list[CorporateActionRecord]:
        """Lookback loader: a missing file at the archive's left edge is
        tolerated (nothing to look back into before the backfill start);
        a present-but-corrupt file still fails loudly via _load_records."""
        if not (self._pr_dir / pr_url(session).rsplit("/", 1)[-1]).is_file():
            return []
        return self._load_records(session)

    def get_prices(self, tickers: list[Ticker], start: date, end: date) -> pd.DataFrame:
        if not tickers:
            raise DataFetchError("get_prices called with an empty ticker list")
        if end < start:
            raise DataFetchError(f"Invalid window: end {end.isoformat()} before start {start.isoformat()}")
        try:
            sessions = sessions_between(start, end)
        except Exception as exc:  # exchange-calendars raises its own types past its finite bounds (ADV-7)
            raise DataFetchError(f"Trading-calendar failure for {start.isoformat()}..{end.isoformat()}: {exc}") from exc
        if not sessions:
            raise DataFetchError(f"No NSE sessions in window {start.isoformat()}..{end.isoformat()}")

        symbols = sorted({str(t) for t in tickers})
        closes = pd.DataFrame({s: self._load_session(s).equities["close"].reindex(symbols) for s in sessions}).T
        closes.index = pd.DatetimeIndex([pd.Timestamp(d) for d in closes.index])

        # Union of official records from the window's sessions PLUS a
        # lookback buffer before it (NSE drops some records from the Bc
        # file before their ex-date — ADV-2), deduplicated the same way
        # parse_bc_csv dedups within one file (double-applying a bonus
        # would halve a series twice), restricted to requested symbols
        # and to ex-dates that actually occurred inside the window.
        try:
            earlier = sessions_between(sessions[0] - timedelta(days=120), sessions[0] - timedelta(days=1))
        except Exception:  # lookback past the calendar's lower bound: best-effort by design
            earlier = []
        lookback = earlier[-_LOOKBACK_SESSIONS:]

        in_window: dict[tuple[str, date, str], CorporateActionRecord] = {}
        for session_records in (
            *(self._load_records_if_archived(s) for s in lookback),
            *(self._load_records(s) for s in sessions),
        ):
            for record in session_records:
                if record.symbol in symbols and sessions[0] < record.ex_date <= sessions[-1]:
                    in_window.setdefault((record.symbol, record.ex_date, record.purpose.upper()), record)
        records = sorted(in_window.values(), key=lambda r: (r.ex_date, r.symbol, r.purpose))

        events = events_from_records(records)
        adjusted = closes * adjustment_multipliers(events, sessions, symbols)
        try:
            validate_close_frame(adjusted, expected_sessions=sessions, max_abs_return=self._max_abs_return)
        except DataQualityError as exc:
            risky = [r for r in records if has_price_effect_risk(r)]
            if risky:
                detail = "; ".join(f"{r.symbol} ex {r.ex_date.isoformat()} {r.purpose!r}" for r in risky[:5])
                raise DataQualityError(f"{exc} — uncomputable corporate-action records in window: {detail}") from exc
            raise
        return adjusted
