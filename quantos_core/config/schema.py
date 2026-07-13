"""Configuration schema and error type (WP-002).

AppConfig is deliberately minimal: one field, proven typed, validated,
and immutable. Future work packages extend it as real fields become
necessary -- this file does not anticipate them.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ConfigError(Exception):
    """Any configuration resolution or validation failure. Fail-closed:
    callers never receive a partially-built or defaulted config."""


class AppConfig(BaseModel):
    """The platform's validated, immutable configuration object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    environment: Literal["dev", "paper", "live"]
