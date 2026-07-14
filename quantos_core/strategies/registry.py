"""strategies_registry loader (WP-009, ADR-015).

All strategy parameters live in versioned YAML under
strategies_registry/ -- never as constants in code. A registry entry
changing is, by definition, a new strategy version (Constitution
Part II, Versioning) and restarts that strategy's validation clock.

Loading happens once, at composition time (the root wires it in);
signal math never touches a file. Schema-validated, extra keys
forbidden, fail-closed on anything malformed.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrategyRegistryError(Exception):
    """Malformed, missing, or schema-violating registry entry."""


class MomentumParams(BaseModel):
    """Momentum v1.0 parameter set -- frozen values mirror the
    Prospective-Validation-frozen constants in momentum_backtest.py;
    the parity suite pins the correspondence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    top_n: int = Field(gt=0)
    lookback_months: int = Field(gt=0)
    skip_months: int = Field(ge=0)
    min_observations: int = Field(gt=0)
    stop_loss_pct: float = Field(gt=0, lt=1)
    trend_ma_days: int = Field(gt=0)


def load_momentum_params(path: Path) -> MomentumParams:
    """Parse and validate one registry entry. Raises
    StrategyRegistryError on every failure mode -- a strategy never
    starts with guessed or defaulted parameters."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StrategyRegistryError(f"Cannot read registry entry {path}: {exc}") from exc
    if not isinstance(raw, dict) or "params" not in raw or "version" not in raw:
        raise StrategyRegistryError(f"Registry entry {path} must be a mapping with 'version' and 'params'")
    try:
        return MomentumParams.model_validate({"version": str(raw["version"]), **raw["params"]})
    except (ValidationError, TypeError) as exc:
        raise StrategyRegistryError(f"Registry entry {path} failed schema validation: {exc}") from exc
