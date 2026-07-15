"""The shared CostModel port and the one Zerodha CNC implementation
(WP-012, ADR-037; ADR-016: a second CostModel implementation anywhere
is a review-blocking finding).

Rates are built from the same primitive charges by the same expressions
as the frozen ``transaction_costs.py`` so the derived floats are
bit-identical -- pinned by a parity test that imports the frozen script
(tests may; this module may not, ADR-032/ADR-003).
"""

from typing import Protocol


class CostModel(Protocol):
    """Transaction-cost contract for fill accounting.

    ``buy_rate``/``sell_rate`` are fractional per-value charges;
    ``dp_per_scrip`` is the flat depository charge per stock per sell
    day (the term that dominates at small capital and killed the Rs10K
    live-capital plan).
    """

    @property
    def buy_rate(self) -> float: ...

    @property
    def sell_rate(self) -> float: ...

    @property
    def dp_per_scrip(self) -> float: ...

    def buy_cost(self, buy_value: float) -> float: ...

    def sell_cost(self, sell_value: float, num_scrips: int = 1) -> float: ...


class ZerodhaDeliveryCostModel:
    """NSE equity delivery (CNC) charges at Zerodha, zerodha.com/charges
    (verified 2026-06-09). Same primitives, same expressions as the
    frozen script -- do not 'simplify' the arithmetic; float identity
    with the validation record depends on the expression shape."""

    STT_RATE = 0.001  # both sides, delivery
    NSE_EXCHANGE_RATE = 0.0000307  # per side
    SEBI_RATE = 1e-6
    STAMP_RATE = 0.00015  # buy only
    GST_RATE = 0.18  # on brokerage + exchange + SEBI; brokerage = 0
    DP_CHARGE_PER_SCRIP = 15.93  # flat per stock, sell only

    @property
    def buy_rate(self) -> float:
        return (
            self.STT_RATE
            + self.STAMP_RATE
            + self.NSE_EXCHANGE_RATE
            + self.SEBI_RATE
            + self.GST_RATE * (self.NSE_EXCHANGE_RATE + self.SEBI_RATE)
        )

    @property
    def sell_rate(self) -> float:
        return (
            self.STT_RATE
            + self.NSE_EXCHANGE_RATE
            + self.SEBI_RATE
            + self.GST_RATE * (self.NSE_EXCHANGE_RATE + self.SEBI_RATE)
        )

    @property
    def dp_per_scrip(self) -> float:
        return self.DP_CHARGE_PER_SCRIP

    def buy_cost(self, buy_value: float) -> float:
        return buy_value * self.buy_rate

    def sell_cost(self, sell_value: float, num_scrips: int = 1) -> float:
        return sell_value * self.sell_rate + self.dp_per_scrip * num_scrips
