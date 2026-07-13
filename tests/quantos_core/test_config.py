"""Tests for quantos_core.config (WP-002).

Covers environment resolution (explicit arg / QUANTOS_ENV), fail-closed
behavior, schema validation, immutability, and determinism. No file I/O
is exercised -- this WP constructs AppConfig directly.
"""

import pytest
from pydantic import ValidationError

from quantos_core.config import AppConfig, ConfigError, load_config


@pytest.mark.parametrize("env", ["dev", "paper", "live"])
def test_explicit_env_constructs_valid_config(env: str) -> None:
    config = load_config(env=env)
    assert config.environment == env


def test_quantos_env_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTOS_ENV", "paper")
    config = load_config()
    assert config.environment == "paper"


def test_explicit_env_overrides_quantos_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTOS_ENV", "live")
    config = load_config(env="dev")
    assert config.environment == "dev"


def test_missing_environment_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUANTOS_ENV", raising=False)
    with pytest.raises(ConfigError):
        load_config()


def test_invalid_environment_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        load_config(env="staging")


def test_unknown_field_rejected_on_direct_construction() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"environment": "dev", "unexpected": "value"})


def test_config_is_immutable() -> None:
    config = load_config(env="dev")
    with pytest.raises(ValidationError):
        config.environment = "live"  # type: ignore[misc]


def test_determinism() -> None:
    first = load_config(env="paper")
    second = load_config(env="paper")
    assert first == second
    assert first is not second
