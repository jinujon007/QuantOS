"""Characterization tests for transaction_costs.py — pins the current,
audited-correct Zerodha CNC cost model's exact output. Per the QuantOS
Constitution (Part IV, Cost Modeling): this is the single source of truth
for cost accounting across the platform, so a silent change here is one of
the highest-leverage regressions Phase 0 exists to catch.

These are golden VALUES, not golden FILES — the function is pure and the
inputs are few enough that pinning exact numbers inline is clearer than a
separate fixture file (matches the Constitution's own "golden-value tests"
pattern for pure domain-core functions).
"""

import math

from transaction_costs import (
    BUY_RATE,
    DP_CHARGE_PER_SCRIP,
    SELL_RATE,
    buy_cost,
    round_trip_cost,
    sell_cost,
)

# Golden values below were captured by direct execution against the current
# source (2026-07-13, baseline-v1) — not hand-derived — per the Constitution's
# reproducibility standard: a golden value must come from running the code,
# never from independently recomputing what it "should" be.


def test_rate_constants_unchanged():
    """These constants feed every strategy's cost accounting. A change here
    is a cost-model change, not a refactor — it must be deliberate."""
    assert math.isclose(BUY_RATE, 0.001187406, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(SELL_RATE, 0.001037406, rel_tol=0, abs_tol=1e-12)
    assert DP_CHARGE_PER_SCRIP == 15.93


def test_buy_cost_golden_values():
    assert math.isclose(buy_cost(10_000), 11.87406, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(buy_cost(100_000), 118.74059999999999, rel_tol=0, abs_tol=1e-9)


def test_sell_cost_golden_values():
    # num_scrips=1 (default): percentage cost + one flat DP charge
    assert math.isclose(sell_cost(10_000), 26.30406, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(sell_cost(100_000, num_scrips=1), 119.67059999999998, rel_tol=0, abs_tol=1e-9)


def test_sell_cost_scales_dp_charge_with_num_scrips():
    """DP charge is flat PER SCRIP, not per trade value — this is the exact
    behavior F4 (cost-model inconsistency, per the QuantOS Audit) depends on
    every paper trader eventually adopting correctly."""
    one_scrip = sell_cost(10_000, num_scrips=1)
    three_scrips = sell_cost(10_000, num_scrips=3)
    assert math.isclose(three_scrips - one_scrip, 2 * DP_CHARGE_PER_SCRIP, rel_tol=0, abs_tol=1e-9)


def test_round_trip_cost_golden_value_at_10k_per_stock():
    """₹10,000/stock is the per-stock allocation at ₹1L capital / 10 positions
    — the exact scale momentum_backtest.py and paper_trader.py both run at."""
    rt = round_trip_cost(10_000, num_scrips=1)
    expected = buy_cost(10_000) + sell_cost(10_000, num_scrips=1)
    assert math.isclose(rt, expected, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(rt, 38.17812, rel_tol=0, abs_tol=1e-9)
