"""
Fetch Nifty 500 constituent list and save with yfinance-compatible tickers.
Run this first before any other script.
"""

import time

import pandas as pd
import requests


def fetch_from_nse():
    """Fetch Nifty 500 list directly from NSE India."""
    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.nseindia.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    session = requests.Session()
    # Warm up session — NSE blocks cold requests
    session.get("https://www.nseindia.com", headers=headers, timeout=15)
    time.sleep(2)
    resp = session.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    df = pd.read_csv(pd.io.common.StringIO(resp.text))
    return df


def fetch_from_nsepython():
    """Fallback: use nsepython library."""
    from nsepython import nifty500_symbols

    symbols = nifty500_symbols()
    return pd.DataFrame({"Symbol": symbols})


NIFTY50_FALLBACK = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
    "ASIANPAINT",
    "MARUTI",
    "TITAN",
    "WIPRO",
    "HCLTECH",
    "SUNPHARMA",
    "ULTRACEMCO",
    "BAJFINANCE",
    "NESTLEIND",
    "POWERGRID",
    "NTPC",
    "ONGC",
    "JSWSTEEL",
    "TATAMOTORS",
    "BAJAJFINSV",
    "TATASTEEL",
    "TECHM",
    "M&M",
    "ADANIENT",
    "ADANIPORTS",
    "COALINDIA",
    "CIPLA",
    "DRREDDY",
    "DIVISLAB",
    "EICHERMOT",
    "HEROMOTOCO",
    "HINDALCO",
    "BRITANNIA",
    "GRASIM",
    "BPCL",
    "IOC",
    "TATACONSUM",
    "SBILIFE",
    "HDFCLIFE",
    "UPL",
    "INDUSINDBK",
    "APOLLOHOSP",
    "BAJAJ-AUTO",
]


def main():
    df = None

    print("Attempting NSE direct fetch...")
    try:
        df = fetch_from_nse()
        print(f"NSE fetch successful — {len(df)} stocks")
    except Exception as e:
        print(f"NSE fetch failed: {e}")

    if df is None:
        print("Attempting nsepython fallback...")
        try:
            df = fetch_from_nsepython()
            print(f"nsepython fetch successful — {len(df)} stocks")
        except Exception as e:
            print(f"nsepython failed: {e}")

    if df is None:
        print("WARNING: Using Nifty 50 fallback (50 stocks only)")
        df = pd.DataFrame({"Symbol": NIFTY50_FALLBACK})

    # Normalize symbol column name
    if "Symbol" not in df.columns:
        symbol_col = [c for c in df.columns if "symbol" in c.lower() or "ticker" in c.lower()]
        if symbol_col:
            df = df.rename(columns={symbol_col[0]: "Symbol"})
        else:
            df.columns = ["Symbol"] + list(df.columns[1:])

    df["Symbol"] = df["Symbol"].str.strip().str.upper()
    df["yf_ticker"] = df["Symbol"] + ".NS"

    # Keep relevant columns
    keep = ["Symbol", "yf_ticker"]
    for col in ["Company Name", "Industry"]:
        if col in df.columns:
            keep.append(col)
    df = df[keep]

    df.to_csv("nifty500_universe.csv", index=False)
    print("\nSaved to nifty500_universe.csv")
    print(f"Total tickers: {len(df)}")
    print("\nSample:")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
