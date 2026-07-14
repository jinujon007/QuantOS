"""Tests for quantos_core.utils.logging (WP-004).

Covers the JSON-line contract: required fields (timestamp, level,
module, event, run_id), event data pass-through, UTC timestamps, level
filtering, exception capture, key ordering stability, non-serializable
fallback, and no handler duplication on repeated get_logger calls.
"""

import io
import json
import logging
from datetime import datetime

from quantos_core.utils import get_logger


def emit_and_parse(stream: io.StringIO) -> list[dict[str, object]]:
    lines = [line for line in stream.getvalue().splitlines() if line]
    return [json.loads(line) for line in lines]


def test_one_json_line_with_required_fields() -> None:
    stream = io.StringIO()
    logger = get_logger("execution", run_id="run-42", stream=stream)
    logger.info("order_submitted")
    (record,) = emit_and_parse(stream)
    assert record["level"] == "INFO"
    assert record["module"] == "quantos.execution"
    assert record["event"] == "order_submitted"
    assert record["run_id"] == "run-42"
    assert "timestamp" in record


def test_timestamp_is_utc_iso8601() -> None:
    stream = io.StringIO()
    get_logger("risk", run_id="r", stream=stream).warning("limit_breach")
    (record,) = emit_and_parse(stream)
    parsed = datetime.fromisoformat(str(record["timestamp"]))
    assert parsed.utcoffset() is not None
    assert parsed.utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_event_data_rides_in_extra() -> None:
    stream = io.StringIO()
    logger = get_logger("paper", run_id="r", stream=stream)
    logger.info("fill_received", extra={"data": {"ticker": "TCS", "quantity": 10}})
    (record,) = emit_and_parse(stream)
    assert record["data"] == {"ticker": "TCS", "quantity": 10}


def test_no_data_key_when_no_data_passed() -> None:
    stream = io.StringIO()
    get_logger("paper", run_id="r", stream=stream).info("heartbeat")
    (record,) = emit_and_parse(stream)
    assert "data" not in record


def test_below_level_records_suppressed() -> None:
    stream = io.StringIO()
    logger = get_logger("data", run_id="r", stream=stream, level=logging.INFO)
    logger.debug("cache_probe")
    assert emit_and_parse(stream) == []


def test_exception_info_captured() -> None:
    stream = io.StringIO()
    logger = get_logger("brokers", run_id="r", stream=stream)
    try:
        raise ValueError("session expired")
    except ValueError:
        logger.error("broker_auth_failure", exc_info=True)
    (record,) = emit_and_parse(stream)
    assert "session expired" in str(record["exception"])


def test_repeat_get_logger_does_not_duplicate_lines() -> None:
    stream = io.StringIO()
    get_logger("monitoring", run_id="r1", stream=stream)
    logger = get_logger("monitoring", run_id="r2", stream=stream)
    logger.info("single_event")
    records = emit_and_parse(stream)
    assert len(records) == 1
    assert records[0]["run_id"] == "r2"


def test_keys_are_sorted_for_stable_output() -> None:
    stream = io.StringIO()
    get_logger("analytics", run_id="r", stream=stream).info("report_built")
    line = stream.getvalue().splitlines()[0]
    keys = list(json.loads(line).keys())
    assert keys == sorted(keys)


def test_non_serializable_data_falls_back_to_str() -> None:
    stream = io.StringIO()
    logger = get_logger("storage", run_id="r", stream=stream)
    logger.info("snapshot_saved", extra={"data": {"at": datetime(2026, 7, 14)}})
    (record,) = emit_and_parse(stream)
    assert "2026-07-14" in str(record["data"])
