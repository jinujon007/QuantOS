"""Corporate-action adjustment from NSE's official Bc records (WP-019, ADR-045).

The Bc member of each session's PR bundle (see ``nse_pr``) is NSE's
official corporate-action record. This module parses those records and
turns the purpose strings whose price effect is exactly computable —
``BONUS a:b`` (factor b/(a+b)), ``FVSPLT``/``FVCONS FRM RS x TO RS y``
(factor y/x) — into back-adjustment events. Dividend/interest/meeting
records carry no exchange price adjustment and yield no factor; any
other purpose (rights, schemes of arrangement, ...) is deliberately
left uncomputed: if such an action moves a price beyond the quality
band, the provider halts naming the record instead of guessing a
factor (fail closed, Constitution Part III).

An earlier same-session design derived factors from the UDiFF
bhavcopy's PrvsClsgPric and was disproven against the real archive
(HDFCBANK bonus ex 2025-08-26: prev-close published raw) — recorded in
ADR-045. Everything here is pure: bytes/records in, events out.

Ordinary dividends are not price-adjusted by the exchange, so adjusted
series are price-return, not total-return — an accepted, documented
divergence from the quarantined yfinance path (ADR-045).
"""

import io
import re
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from quantos_core.data.errors import DataFetchError

_REQUIRED_COLUMNS = ("SERIES", "SYMBOL", "EX_DT", "PURPOSE")
_BONUS = re.compile(r"BONUS\s+(\d+)\s*:\s*(\d+)")
# Live wording variants (scan of all 720 distinct purposes in the real
# 2025-06..2026-07 archive): "FVSPLT FRM RS 5 TO RE 1", "FV SPLT FRM
# RS 2 TO RE 1", "FVSPLT FRMRS 100 TO RE 1", "FV SPLT FRM RS 10 TO 1",
# "... TO RE1" — spacing and the RS/RE token are both optional.
_FV_CHANGE = re.compile(
    r"FV\s?(?:SPLT|CONS)\s+FRM\s*(?:R[SE]\.?)?\s*(\d+(?:\.\d+)?)\s*TO\s*(?:R[SE]\.?)?\s*(\d+(?:\.\d+)?)"
)
#: Keywords that mark a computable action *family* — a purpose that
#: names one of these but defeats the exact patterns above is a format
#: drift, and silently skipping it would misprice every earlier close
#: (adversarial review 2026-07-22, ADV-1).
_COMPUTABLE_FAMILY = re.compile(r"\bBONUS\b|FVSPLT|FVCONS|\bSPLIT\b|\bSPLT\b|\bCONSOL\w*")
#: Purposes with no exchange price adjustment — never events, never
#: worth surfacing when a quality check fails. Word-bounded so
#: DEMERGER/DIVESTMENT-style purposes never match via the DIV
#: substring (ADV-5).
_NO_PRICE_EFFECT = re.compile(
    r"\bDIV\b|\bDIVIDEND\b|\bINT\b|\bINTEREST\b|\bAGM\b|\bEGM\b|GENERAL MEETING|\bREDEMPTION\b"
)
#: Action families with a real price effect and no exactly-computable
#: factor — always named in diagnostics, even when they ride in a
#: compound purpose next to a computable part (ADV-4).
_RISKY_FAMILY = re.compile(
    r"\bRGTS\b|\bRIGHTS?\b|\bDEMERGER\b|\bMERGER\b|\bSCHEME\b|\bARRANGEMENT\b"
    r"|\bAMALGAMATION\b|\bCAPITAL\b|\bREDUCTION\b|\bBUY\s?-?\s?BACK\b|\bSPIN\s?-?\s?OFF\b"
)
# A factor outside this band is a data defect (or an action so extreme
# it deserves a human), never something to apply silently.
_FACTOR_MIN, _FACTOR_MAX = 0.01, 100.0


@dataclass(frozen=True)
class CorporateActionRecord:
    """One official Bc row: the action as NSE published it."""

    symbol: str
    ex_date: date
    purpose: str


@dataclass(frozen=True)
class AdjustmentEvent:
    """One computable price adjustment: multiply every close strictly
    before ``ex_date`` by ``factor`` to express it in post-action terms
    (a 1:1 bonus halves the basis, so factor = 0.5)."""

    symbol: str
    ex_date: date
    factor: float


def _parse_ex_date(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):  # 2025-era vs 2026-era Bc files
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise DataFetchError(
        f"Unparseable EX_DT {raw!r} in Bc corporate-actions file — NSE format change? Revisit ADR-045."
    )


def parse_bc_csv(bc_bytes: bytes) -> list[CorporateActionRecord]:
    """Parse a Bc member into deduplicated corporate-action records.

    NSE lists the same action once per series (EQ + BE) and re-lists it
    across several sessions' files; records are deduplicated on
    (symbol, ex_date, normalized purpose). Rows without an ex-date are
    skipped (nothing to anchor an adjustment to); a missing column is a
    fail-closed format error.
    """
    try:
        frame = pd.read_csv(io.BytesIO(bc_bytes), dtype=str)
    except (ValueError, pd.errors.ParserError) as exc:
        raise DataFetchError(f"Unreadable Bc corporate-actions CSV: {exc}") from exc
    frame.columns = [str(c).strip() for c in frame.columns]
    missing = [c for c in _REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise DataFetchError(f"Bc file is missing required columns {missing} — NSE format change? Revisit ADR-045.")

    records: dict[tuple[str, date, str], CorporateActionRecord] = {}
    for _, row in frame.iterrows():
        ex_date = _parse_ex_date(str(row["EX_DT"]) if not pd.isna(row["EX_DT"]) else "")
        if ex_date is None:
            continue
        symbol = str(row["SYMBOL"]).strip()
        purpose = " ".join(str(row["PURPOSE"]).split()) if not pd.isna(row["PURPOSE"]) else ""
        if not symbol or not purpose:
            continue
        key = (symbol, ex_date, purpose.upper())
        records.setdefault(key, CorporateActionRecord(symbol=symbol, ex_date=ex_date, purpose=purpose))
    return sorted(records.values(), key=lambda r: (r.ex_date, r.symbol, r.purpose))


def factor_from_purpose(purpose: str) -> float | None:
    """The exact price-adjustment factor a purpose string implies, or
    None when the purpose carries no computable adjustment.

    Computable: BONUS a:b -> b/(a+b); FVSPLT/FVCONS FRM RS x TO RS y
    -> y/x (a compound purpose multiplies its parts). Dividends and
    other non-adjusting purposes return None. A purpose that *names* a
    computable family (BONUS/SPLIT/CONSOL...) but defeats the exact
    patterns is a fail-closed format error — silently returning None
    there would misprice every pre-ex close by the unapplied factor
    while staying inside the quality band (ADV-1).
    """
    text = purpose.upper()
    factor = 1.0
    matched = False
    for match in _BONUS.finditer(text):
        new_shares, held = int(match.group(1)), int(match.group(2))
        if new_shares + held == 0:
            raise DataFetchError(f"Degenerate bonus ratio in purpose {purpose!r}")
        factor *= held / (new_shares + held)
        matched = True
    for match in _FV_CHANGE.finditer(text):
        if "PAISE" in text:
            raise DataFetchError(
                f"Face-value change in {purpose!r} uses a paise denomination — "
                f"the rupee-ratio parse would be off by 100x; halting (ADR-045)."
            )
        old_fv, new_fv = float(match.group(1)), float(match.group(2))
        if old_fv <= 0 or new_fv <= 0:
            raise DataFetchError(f"Degenerate face-value change in purpose {purpose!r}")
        factor *= new_fv / old_fv
        matched = True
    if not matched and _COMPUTABLE_FAMILY.search(text):
        raise DataFetchError(
            f"Purpose {purpose!r} names a bonus/split/consolidation but its ratio is unparseable — "
            f"NSE wording drift? Halting rather than serving unadjusted prices (ADR-045)."
        )
    return factor if matched else None


def has_price_effect_risk(record: CorporateActionRecord) -> bool:
    """True for records that could move a price without an exactly
    computable factor — the ones worth naming when a quality check
    fails. A compound purpose stays risky when an uncomputable
    price-affecting part (rights, scheme, demerger...) rides next to a
    computable one (ADV-4); an unparseable computable-family purpose
    is always risky."""
    text = " ".join(record.purpose.upper().split())
    try:
        factor = factor_from_purpose(text)
    except DataFetchError:
        return True
    remainder = _FV_CHANGE.sub(" ", _BONUS.sub(" ", text))
    if _RISKY_FAMILY.search(remainder):
        return True
    if factor is not None:
        return False
    return _NO_PRICE_EFFECT.search(remainder) is None


def events_from_records(records: list[CorporateActionRecord]) -> list[AdjustmentEvent]:
    """Adjustment events for every computable record, fail-closed on
    factors outside the sanity band. Records are expected deduplicated
    (``parse_bc_csv`` output; union across files must dedup the same
    way — a double-applied bonus halves a series twice). Two records
    that share (symbol, ex_date) and parse to the *same* factor from
    different wording are ambiguous — one re-worded action applied
    twice, or two coincidentally-equal actions — and halt rather than
    guess (ADV-3); different factors on one day are a genuine compound
    and both apply.
    """
    events: list[AdjustmentEvent] = []
    seen: dict[tuple[str, date, float], CorporateActionRecord] = {}
    for record in records:
        factor = factor_from_purpose(record.purpose)
        if factor is None:
            continue
        if not (_FACTOR_MIN <= factor <= _FACTOR_MAX):
            raise DataFetchError(
                f"Implausible adjustment factor {factor:.6g} for {record.symbol} on "
                f"{record.ex_date.isoformat()} ({record.purpose!r}) — data defect, not a corporate action"
            )
        key = (record.symbol, record.ex_date, factor)
        earlier = seen.get(key)
        if earlier is not None:
            raise DataFetchError(
                f"Ambiguous corporate actions for {record.symbol} on {record.ex_date.isoformat()}: "
                f"{earlier.purpose!r} and {record.purpose!r} parse to the same factor {factor:.6g} — "
                f"re-worded duplicate or two equal actions? Halting rather than guessing (ADR-045)."
            )
        seen[key] = record
        events.append(AdjustmentEvent(symbol=record.symbol, ex_date=record.ex_date, factor=factor))
    return sorted(events, key=lambda e: (e.ex_date, e.symbol))


def adjustment_multipliers(events: list[AdjustmentEvent], sessions: list[date], symbols: list[str]) -> pd.DataFrame:
    """Per-session, per-symbol back-adjustment multipliers.

    Returns a DataFrame (index = ``sessions`` as Timestamps, columns =
    ``symbols``) of cumulative factors: raw close x multiplier = close
    in the latest session's price basis. Symbols without events stay at
    1.0; events for symbols outside ``symbols`` are ignored.
    """
    index = pd.DatetimeIndex([pd.Timestamp(s) for s in sessions])
    frame = pd.DataFrame(1.0, index=index, columns=list(symbols))
    wanted = set(symbols)
    for event in events:
        if event.symbol not in wanted:
            continue
        before_ex = index < pd.Timestamp(event.ex_date)
        frame.loc[before_ex, event.symbol] *= event.factor
    return frame
