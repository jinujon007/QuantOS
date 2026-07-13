"""Configuration loader (WP-002).

Resolves the active environment from an explicit argument or the
QUANTOS_ENV environment variable, and constructs AppConfig directly
from it. No file I/O, no layering, no persistence format -- reserved
for WP-006 (Layered Configuration).
"""

import os

from pydantic import ValidationError

from quantos_core.config.schema import AppConfig, ConfigError


def load_config(env: str | None = None) -> AppConfig:
    """Construct AppConfig for the resolved environment.

    Raises ConfigError if no environment can be resolved, or if the
    resolved value fails schema validation.
    """
    resolved = env or os.environ.get("QUANTOS_ENV")
    if not resolved:
        raise ConfigError("No environment resolved: pass env explicitly or set the QUANTOS_ENV environment variable.")

    try:
        return AppConfig.model_validate({"environment": resolved})
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration for environment {resolved!r}: {exc}") from exc
