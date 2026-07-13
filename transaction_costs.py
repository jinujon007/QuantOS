"""
NSE Equity Delivery Transaction Costs - Zerodha
Source: zerodha.com/charges (verified 2026-06-09)

All charges are for CNC (delivery) trades on NSE.
DP charges are flat per scrip per sell day - not percentage-based.
This makes capital size a critical variable in real-cost modelling.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# -- Percentage-based charges (as fractions, e.g. 0.001 = 0.1%) --------------

# STT: 0.1% on both buy and sell for delivery
STT_RATE = 0.001

# NSE Exchange Transaction Charges
NSE_EXCHANGE_RATE = 0.0000307  # 0.00307% per side

# SEBI Charges: Rs10 per crore = 1e-6 as a fraction
SEBI_RATE = 1e-6

# Stamp Duty: 0.015% on BUY only
STAMP_RATE = 0.00015

# GST: 18% on (brokerage + exchange + SEBI). Brokerage=0 for delivery.
GST_RATE = 0.18

# Brokerage: Rs0 for equity delivery at Zerodha
BROKERAGE_RATE = 0.0

# -- Flat charges -------------------------------------------------------------

# DP charges: Rs13.50 (Zerodha) + GST = Rs15.93 per scrip per sell day
# CDSL adds ~Rs0.70 more (Rs0.59 + GST). Using Rs15.93 conservative figure.
DP_CHARGE_PER_SCRIP = 15.93  # Rs per stock, charged on SELL only


# -- Functions ----------------------------------------------------------------


def buy_cost(buy_value: float) -> float:
    """Total rupee cost to buy equity delivery worth buy_value."""
    stt = STT_RATE * buy_value
    stamp = STAMP_RATE * buy_value
    exchange = NSE_EXCHANGE_RATE * buy_value
    sebi = SEBI_RATE * buy_value
    gst = GST_RATE * (exchange + sebi)
    return stt + stamp + exchange + sebi + gst


def sell_cost(sell_value: float, num_scrips: int = 1) -> float:
    """Total rupee cost to sell equity delivery across num_scrips stocks."""
    stt = STT_RATE * sell_value
    exchange = NSE_EXCHANGE_RATE * sell_value
    sebi = SEBI_RATE * sell_value
    gst = GST_RATE * (exchange + sebi)
    dp = DP_CHARGE_PER_SCRIP * num_scrips
    return stt + exchange + sebi + gst + dp


def round_trip_cost(trade_value: float, num_scrips: int = 1) -> float:
    """Total cost to buy then sell trade_value across num_scrips stocks."""
    return buy_cost(trade_value) + sell_cost(trade_value, num_scrips)


# -- Pre-computed percentage rates (no flat DP) -------------------------------
# Use these as multipliers in the backtest. Deduct DP_CHARGE_PER_SCRIP separately.

BUY_RATE = STT_RATE + STAMP_RATE + NSE_EXCHANGE_RATE + SEBI_RATE + GST_RATE * (NSE_EXCHANGE_RATE + SEBI_RATE)
# 0.001 + 0.00015 + 0.0000307 + 1e-6 + 0.18*(0.0000307+1e-6) = ~0.001187

SELL_RATE = STT_RATE + NSE_EXCHANGE_RATE + SEBI_RATE + GST_RATE * (NSE_EXCHANGE_RATE + SEBI_RATE)
# 0.001 + 0.0000307 + 1e-6 + 0.18*(0.0000307+1e-6) = ~0.001037


if __name__ == "__main__":
    print("=" * 60)
    print("  NSE Equity Delivery Cost Analysis - Zerodha (CNC)")
    print("=" * 60)
    print("\n  Percentage-based rates:")
    print(f"    STT:           {STT_RATE * 100:.4f}% per side (buy + sell)")
    print(f"    Stamp duty:    {STAMP_RATE * 100:.4f}% (buy only)")
    print(f"    Exchange txn:  {NSE_EXCHANGE_RATE * 100:.5f}% per side (NSE)")
    print(f"    SEBI:          Rs{SEBI_RATE * 1e7:.0f} per lakh = {SEBI_RATE * 100:.6f}%")
    print("    GST:           18% on exchange + SEBI")
    print("    Brokerage:     Rs0 (delivery = free)")
    print("\n  Flat charges:")
    print(f"    DP charges:    Rs{DP_CHARGE_PER_SCRIP:.2f} per scrip per sell day")
    print("\n  Effective rates (no DP):")
    print(f"    Buy rate:      {BUY_RATE * 100:.4f}%")
    print(f"    Sell rate:     {SELL_RATE * 100:.4f}% + DP (flat)")
    print(f"    Round-trip:    {(BUY_RATE + SELL_RATE) * 100:.4f}% + DP")

    print("\n  Round-trip cost at different capital levels (10 stocks, equal weight):")
    print(f"  {'Capital':>12}  {'Per stock':>10}  {'RT cost%':>9}  {'RT cost Rs':>10}  {'DP%':>7}")
    print(f"  {'-' * 57}")
    for capital in [10_000, 50_000, 1_00_000, 5_00_000, 10_00_000]:
        per_stock = capital / 10
        rt_pct = round_trip_cost(per_stock, num_scrips=1) / per_stock * 100
        rt_rs = round_trip_cost(per_stock, num_scrips=1)
        dp_pct = DP_CHARGE_PER_SCRIP / per_stock * 100
        print(f"  Rs{capital:>9,.0f}  Rs{per_stock:>8,.0f}  {rt_pct:>8.3f}%  Rs{rt_rs:>9.2f}  {dp_pct:>6.3f}%")

    print()
    print("  Previous backtest: 0.1% one-way (0.2% RT) -- no DP included")
    print(f"  Actual at Rs1L capital (Rs10K/stock): {round_trip_cost(10000, 1) / 10000 * 100:.3f}% RT")
    print(f"  Actual at Rs10K capital (Rs1K/stock): {round_trip_cost(1000, 1) / 1000 * 100:.3f}% RT")
    print(f"  -> DP alone is {DP_CHARGE_PER_SCRIP / 1000 * 100:.2f}% per sell at Rs1K/stock")
    print("=" * 60)
