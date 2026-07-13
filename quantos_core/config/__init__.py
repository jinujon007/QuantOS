"""Typed, validated, immutable configuration -- one source of truth for
every parameter.

WP-002: environment resolution (QUANTOS_ENV or explicit argument) and
schema validation only -- AppConfig is constructed directly, no file I/O.
Layered, file-backed configuration (QuantOS Constitution, Part II /
ADR-013) is reserved for WP-006, not yet implemented.
"""

from quantos_core.config.loader import load_config
from quantos_core.config.schema import AppConfig, ConfigError

__all__ = ["AppConfig", "ConfigError", "load_config"]
