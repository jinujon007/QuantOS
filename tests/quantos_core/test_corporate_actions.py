"""Corporate-action records, factors, and back-adjustment (WP-019, ADR-045).

The Bc fixture lines mirror the real PR-bundle Bc files verbatim
(2025-era DD/MM/YYYY dates and 2026-era ISO dates, series-duplicated
rows, trailing purpose padding) — verified against the live archive
2026-07-22, the session that also *disproved* the earlier
UDiFF-prev-close detection idea (HDFCBANK bonus ex 2025-08-26
published with a raw, unadjusted PrvsClsgPric).
"""

from datetime import date

import pandas as pd
import pytest

from quantos_core.data import (
    AdjustmentEvent,
    CorporateActionRecord,
    DataFetchError,
    adjustment_multipliers,
    events_from_records,
    factor_from_purpose,
    has_price_effect_risk,
    parse_bc_csv,
)

D1, D2, D3 = date(2026, 7, 13), date(2026, 7, 14), date(2026, 7, 15)

BC_HEADER = "SERIES,SYMBOL,SECURITY,RECORD_DT,BC_STRT_DT,BC_END_DT,EX_DT,ND_STRT_DT,ND_END_DT,PURPOSE"


def bc_bytes(*rows: str) -> bytes:
    return ("\n".join([BC_HEADER, *rows]) + "\n").encode()


# ── parsing ──────────────────────────────────────────────────────────────


def test_parses_2025_era_row_with_slash_dates() -> None:
    row = "BE,HDFCBANK,HDFC BANK LTD,27/08/2025, , ,26/08/2025, , ,BONUS 1:1                "
    records = parse_bc_csv(bc_bytes(row))
    assert records == [CorporateActionRecord(symbol="HDFCBANK", ex_date=date(2025, 8, 26), purpose="BONUS 1:1")]


def test_parses_2026_era_row_with_iso_dates() -> None:
    records = parse_bc_csv(bc_bytes("EQ,ACME,Acme Ltd,2026-07-15,,,2026-07-14,,,FVSPLT FRM RS 10 TO RS 2"))
    assert records == [CorporateActionRecord(symbol="ACME", ex_date=D2, purpose="FVSPLT FRM RS 10 TO RS 2")]


def test_series_duplicated_rows_dedup_to_one_record() -> None:
    records = parse_bc_csv(
        bc_bytes(
            "BE,HDFCBANK,HDFC BANK LTD,27/08/2025, , ,26/08/2025, , ,BONUS 1:1",
            "EQ,HDFCBANK,HDFC Bank Ltd.,27/08/2025, , ,26/08/2025, , ,BONUS 1:1",
        )
    )
    assert len(records) == 1


def test_rows_without_ex_date_are_skipped() -> None:
    assert parse_bc_csv(bc_bytes("EQ,ACME,Acme Ltd,2026-07-15,,, ,,,BONUS 1:1")) == []


def test_missing_required_column_fails_closed() -> None:
    broken = bc_bytes().replace(b"EX_DT", b"RENAMED")
    with pytest.raises(DataFetchError, match="missing required columns"):
        parse_bc_csv(broken)


def test_unparseable_ex_date_fails_closed() -> None:
    with pytest.raises(DataFetchError, match="Unparseable EX_DT"):
        parse_bc_csv(bc_bytes("EQ,ACME,Acme Ltd,,,,15-Jul-2026,,,BONUS 1:1"))


# ── purpose -> factor ────────────────────────────────────────────────────


def test_bonus_factors() -> None:
    assert factor_from_purpose("BONUS 1:1") == pytest.approx(0.5)
    assert factor_from_purpose("BONUS 1:5") == pytest.approx(5 / 6)
    assert factor_from_purpose("BONUS 3:2") == pytest.approx(2 / 5)


def test_face_value_split_and_consolidation_factors() -> None:
    assert factor_from_purpose("FVSPLT FRM RS 5 TO RE 1") == pytest.approx(0.2)
    assert factor_from_purpose("FVSPLT FRM RS 10 TO RS 2") == pytest.approx(0.2)
    assert factor_from_purpose("FVCONS FRM RE 1 TO RS 10") == pytest.approx(10.0)


def test_face_value_split_wording_variants_from_live_archive() -> None:
    # Every variant below was observed verbatim in the real
    # 2025-06..2026-07 Bc files (720-purpose scan, 2026-07-22).
    assert factor_from_purpose("FV SPLT FRM RS 2 TO RE 1") == pytest.approx(0.5)
    assert factor_from_purpose("FV SPLT FRM RS 10 TO 1") == pytest.approx(0.1)
    assert factor_from_purpose("FV SPLT FRM RS 10 TO RE1") == pytest.approx(0.1)
    assert factor_from_purpose("FVSPLT FRMRS 100 TO RE 1") == pytest.approx(0.01)
    assert factor_from_purpose("FVSPLT FRM RS10 TO RE 1") == pytest.approx(0.1)


def test_paise_denominated_split_fails_closed() -> None:
    # A rupee-ratio parse of "TO 50 PAISE" would be off by 100x.
    with pytest.raises(DataFetchError, match="paise"):
        factor_from_purpose("FVSPLT FRM RE 1 TO 50 PAISE")


def test_compound_purpose_multiplies_parts() -> None:
    assert factor_from_purpose("BONUS 1:1 / FVSPLT FRM RS 10 TO RS 5") == pytest.approx(0.25)


def test_non_adjusting_purposes_have_no_factor() -> None:
    assert factor_from_purpose("DIV - RS 10 PER SH") is None
    assert factor_from_purpose("INTEREST PAYMENT") is None
    assert factor_from_purpose("AGM/DIV - RE 0.50 PER SH") is None
    assert factor_from_purpose("RGTS 1:5 @ PREMIUM RS 10") is None
    assert factor_from_purpose("SCHEME OF ARRANGEMENT") is None


def test_unparseable_computable_family_fails_closed() -> None:
    # ADV-1: a named bonus/split whose ratio defeats the exact patterns
    # must halt — silently returning None would misprice every pre-ex
    # close while a 1:2..1:9 bonus stays inside the quality band.
    for purpose in ("BONUS ISSUE 1:2", "BONUS DEBENTURES 5:1", "FVSPLT RS 10 TO 2", "CONSOLIDATION OF SHARES"):
        with pytest.raises(DataFetchError, match="unparseable"):
            factor_from_purpose(purpose)


def test_price_effect_risk_classification() -> None:
    def record(purpose: str) -> CorporateActionRecord:
        return CorporateActionRecord(symbol="X", ex_date=D2, purpose=purpose)

    assert has_price_effect_risk(record("SCHEME OF ARRANGEMENT")) is True
    assert has_price_effect_risk(record("RGTS 1:5 @ PREMIUM RS 10")) is True
    assert has_price_effect_risk(record("BONUS 1:1")) is False, "computable -> not risky"
    assert has_price_effect_risk(record("DIV - RS 10 PER SH")) is False, "price-neutral -> not risky"
    # ADV-4: compound computable + uncomputable stays risky.
    assert has_price_effect_risk(record("BONUS 1:1 AND SCHEME OF ARRANGEMENT")) is True
    # ADV-5: DEMERGER purposes never hide behind the DIV substring.
    assert has_price_effect_risk(record("DEMERGER CUM DIVIDEND")) is True
    # ADV-1: unparseable computable family is risky, not invisible.
    assert has_price_effect_risk(record("BONUS ISSUE 1:2")) is True
    # Unknown purpose with no neutral marker: conservative -> risky.
    assert has_price_effect_risk(record("CAPITAL REDUCTION")) is True


# ── records -> events ────────────────────────────────────────────────────


def test_events_from_records_skips_uncomputable_and_sorts() -> None:
    records = [
        CorporateActionRecord(symbol="ZZZ", ex_date=D2, purpose="BONUS 1:1"),
        CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="FVSPLT FRM RS 10 TO RS 2"),
        CorporateActionRecord(symbol="BBB", ex_date=D2, purpose="DIV - RS 3 PER SH"),
    ]
    events = events_from_records(records)
    assert events == [
        AdjustmentEvent(symbol="AAA", ex_date=D2, factor=0.2),
        AdjustmentEvent(symbol="ZZZ", ex_date=D2, factor=0.5),
    ]


def test_implausible_factor_fails_closed() -> None:
    records = [CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="FVSPLT FRM RS 1000 TO RE 1")]
    with pytest.raises(DataFetchError, match="Implausible adjustment factor"):
        events_from_records(records)


def test_reworded_duplicate_with_equal_factor_is_ambiguous_and_halts() -> None:
    # ADV-3: NSE re-wording one action across Bc files defeats a
    # purpose-keyed dedup; equal factor + different wording on one
    # (symbol, ex_date) must halt, never double-apply.
    records = [
        CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="BONUS 1:4"),
        CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="BONUS 1 : 4"),
    ]
    with pytest.raises(DataFetchError, match="Ambiguous corporate actions"):
        events_from_records(records)


def test_distinct_same_day_actions_with_different_factors_both_apply() -> None:
    records = [
        CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="BONUS 1:1"),
        CorporateActionRecord(symbol="AAA", ex_date=D2, purpose="FVSPLT FRM RS 10 TO RS 2"),
    ]
    events = events_from_records(records)
    assert sorted(e.factor for e in events) == pytest.approx([0.2, 0.5])


# ── multipliers ──────────────────────────────────────────────────────────


def test_multipliers_apply_strictly_before_ex_date() -> None:
    events = [AdjustmentEvent(symbol="AAA", ex_date=D2, factor=0.5)]
    frame = adjustment_multipliers(events, [D1, D2, D3], ["AAA", "BBB"])
    assert frame.loc[pd.Timestamp(D1), "AAA"] == pytest.approx(0.5)
    assert frame.loc[pd.Timestamp(D2), "AAA"] == pytest.approx(1.0)
    assert frame.loc[pd.Timestamp(D3), "AAA"] == pytest.approx(1.0)
    assert list(frame["BBB"]) == [1.0, 1.0, 1.0], "no events -> identity"


def test_multipliers_compound_across_events() -> None:
    events = [
        AdjustmentEvent(symbol="AAA", ex_date=D2, factor=0.5),
        AdjustmentEvent(symbol="AAA", ex_date=D3, factor=0.5),
    ]
    frame = adjustment_multipliers(events, [D1, D2, D3], ["AAA"])
    assert list(frame["AAA"]) == pytest.approx([0.25, 0.5, 1.0])


def test_multipliers_ignore_events_for_unrequested_symbols() -> None:
    events = [AdjustmentEvent(symbol="OTHER", ex_date=D2, factor=0.5)]
    frame = adjustment_multipliers(events, [D1, D2], ["AAA"])
    assert list(frame["AAA"]) == [1.0, 1.0]
