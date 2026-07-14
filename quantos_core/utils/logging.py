"""Structured JSON-lines logging (WP-004).

Constitution Part III (Logging): structured, not plain text; every line
carries timestamp, level, module, event, and the correlation/run id,
plus event-specific data. Built on stdlib logging -- no new dependency.

Callers must never pass secrets, credentials, or full order/account
payloads in event data; this module serializes what it is given.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import IO


class JsonLineFormatter(logging.Formatter):
    """One JSON object per line, keys sorted (stable, diffable output)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "event": record.getMessage(),
            "run_id": getattr(record, "run_id", None),
        }
        data = getattr(record, "data", None)
        if data is not None:
            payload["data"] = data
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, default=str)


def get_logger(
    module: str,
    run_id: str,
    stream: IO[str] | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """Return the logger for one module in one run, emitting JSON lines.

    Event convention: the log message is the event name, event-specific
    data rides in ``extra={"data": {...}}``::

        logger.info("order_submitted", extra={"data": {"ticker": "TCS"}})

    Reconfigures (never duplicates) handlers on repeat calls for the
    same module -- one line per event, always.
    """
    logger = logging.getLogger(f"quantos.{module}")
    logger.setLevel(level)
    logger.propagate = False

    def _stamp_run_id(record: logging.LogRecord) -> bool:
        record.run_id = run_id
        return True

    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonLineFormatter())
    logger.handlers.clear()
    logger.filters.clear()
    logger.addHandler(handler)
    logger.addFilter(_stamp_run_id)
    return logger
