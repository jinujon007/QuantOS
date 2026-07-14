"""Shared low-level utilities with no domain dependencies.

WP-004 implements structured logging (Constitution Part III/Logging):
JSON-lines output where every record carries timestamp, level, module,
event, and run id. Calendar and determinism helpers arrive with the
phases that need them (Clock port: Part V, Market Holiday Handling).
The six frozen scripts are untouched (ADR-003, strangler-fig).
"""

from quantos_core.utils.logging import JsonLineFormatter, get_logger

__all__ = [
    "JsonLineFormatter",
    "get_logger",
]
