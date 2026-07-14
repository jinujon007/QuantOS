"""Momentum v1.0 -- the validated Nifty 500 weekly momentum strategy,
behind the Strategy port (WP-009, Phase 3 opening).

Selection logic is the VERBATIM frozen behavior (ADR-003), proven
equal to `momentum_backtest.py` by the parity suite:
- bear regime -> everything to cash (stance "cash");
- fewer rankable tickers than top_n -> do nothing (stance "hold");
- otherwise long the top_n by 12M-1M momentum, equal weight
  (`nlargest` -- same tie behavior as the frozen script).

Parameters come only from strategies_registry/momentum_v1.yaml
(ADR-015). This class contains zero numeric literals.

The Prospective Validation clock is unaffected: this is a port with
proven signal parity, not a strategy change; `paper_trader.py` remains
the running system of record until Phase 6 swaps execution paths.
"""

from quantos_core.factors import momentum_12m1m
from quantos_core.strategies.base import StrategyContext, StrategyMeta, TargetWeights
from quantos_core.strategies.registry import MomentumParams


class MomentumV1:
    def __init__(self, params: MomentumParams) -> None:
        self._params = params

    def generate_signals(self, ctx: StrategyContext) -> TargetWeights:
        if not ctx.market_uptrend:
            return TargetWeights(stance="cash")

        scores = momentum_12m1m(
            ctx.prices,
            ctx.as_of,
            lookback_months=self._params.lookback_months,
            skip_months=self._params.skip_months,
            min_observations=self._params.min_observations,
        )
        if len(scores) < self._params.top_n:
            return TargetWeights(stance="hold")

        top = scores.nlargest(self._params.top_n).index
        weight = 1.0 / self._params.top_n
        return TargetWeights(stance="rebalance", weights={str(t): weight for t in top})

    def metadata(self) -> StrategyMeta:
        return StrategyMeta(
            name="nifty500-weekly-momentum",
            version=self._params.version,
            params=self._params.model_dump(),
        )
