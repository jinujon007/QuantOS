"""
Download historical OHLCV data for all Nifty 500 stocks.
Run after fetch_universe.py. Takes ~10-20 minutes for 500 stocks.
Data is cached in data/cache/ — re-running skips already-downloaded tickers.

For recent IPOs that don't have 2018 data, we retry with progressively
later start dates to capture whatever history exists.
"""

import time
import pandas as pd
import yfinance as yf
from pathlib import Path

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PRIMARY_START = "2018-01-01"
END = "2024-12-31"
# Retry start dates for recently listed companies
FALLBACK_STARTS = ["2020-01-01", "2022-01-01", "2023-01-01"]
MIN_ROWS = 50       # Accept any ticker with at least 50 days of data
BATCH_SIZE = 20


def cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker.replace('.', '_')}.csv"


def already_cached(ticker: str) -> bool:
    return cache_path(ticker).exists()


def save_ticker(ticker: str, close_series: pd.Series):
    close_series.to_frame(name="Close").to_csv(cache_path(ticker))


def load_ticker(ticker: str) -> pd.Series | None:
    p = cache_path(ticker)
    if not p.exists():
        return None
    return pd.read_csv(p, index_col=0, parse_dates=True)["Close"]


def _download_raw(tickers: list[str], start: str) -> pd.DataFrame:
    """Download a batch and return a Close price DataFrame. Empty on failure."""
    try:
        raw = yf.download(
            tickers,
            start=start,
            end=END,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            return raw["Close"]
        # Single ticker
        if "Close" in raw.columns:
            return raw[["Close"]].rename(columns={"Close": tickers[0]})
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def download_batch(tickers: list[str]) -> tuple[dict[str, pd.Series], list[str]]:
    """
    Download tickers not yet cached.
    Returns (results_dict, still_failed_list).
    Retries with later start dates for recent IPOs.
    """
    results = {}
    # Load cached
    for t in tickers:
        if already_cached(t):
            s = load_ticker(t)
            if s is not None:
                results[t] = s

    remaining = [t for t in tickers if t not in results]
    if not remaining:
        return results, []

    # Try primary start date first
    close = _download_raw(remaining, PRIMARY_START)
    saved = set()
    if not close.empty:
        for ticker in remaining:
            if ticker in close.columns:
                s = close[ticker].dropna()
                if len(s) >= MIN_ROWS:
                    save_ticker(ticker, s)
                    results[ticker] = s
                    saved.add(ticker)

    still_missing = [t for t in remaining if t not in saved]

    # Retry each fallback start date individually (avoids one bad ticker poisoning batch)
    for fallback_start in FALLBACK_STARTS:
        if not still_missing:
            break
        retry_batch = still_missing[:]
        close2 = _download_raw(retry_batch, fallback_start)
        if close2.empty:
            continue
        newly_saved = []
        for ticker in retry_batch:
            if ticker in close2.columns:
                s = close2[ticker].dropna()
                if len(s) >= MIN_ROWS:
                    save_ticker(ticker, s)
                    results[ticker] = s
                    newly_saved.append(ticker)
        for t in newly_saved:
            still_missing.remove(t)

    return results, still_missing


def main():
    if not Path("nifty500_universe.csv").exists():
        print("ERROR: nifty500_universe.csv not found. Run fetch_universe.py first.")
        return

    universe = pd.read_csv("nifty500_universe.csv")
    tickers = universe["yf_ticker"].tolist()

    cached = sum(1 for t in tickers if already_cached(t))
    to_download = len(tickers) - cached

    print(f"Universe: {len(tickers)} tickers")
    print(f"Already cached: {cached}")
    print(f"To download: {to_download}")
    if to_download == 0:
        print("All tickers already cached.")
        return
    print(f"Primary period: {PRIMARY_START} to {END}")
    print(f"Fallback periods: {FALLBACK_STARTS} (for recent IPOs)")
    print("Starting download...\n")

    success = cached
    truly_failed = []

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        results, still_failed = download_batch(batch)

        newly_ok = [t for t in batch if t in results]
        success = sum(1 for t in tickers[: i + BATCH_SIZE] if already_cached(t) or t in results)
        truly_failed.extend(still_failed)

        done = min(i + BATCH_SIZE, len(tickers))
        pct = done / len(tickers) * 100
        print(f"[{pct:5.1f}%] {done}/{len(tickers)} — {success} OK, {len(truly_failed)} failed")

        time.sleep(0.3)

    print(f"\nDownload complete.")
    print(f"  Success : {success}")
    print(f"  Failed  : {len(truly_failed)}")
    print(f"  Cached in: {CACHE_DIR.resolve()}")

    if truly_failed:
        pd.DataFrame({"ticker": truly_failed}).to_csv("data/failed_tickers.csv", index=False)
        print(f"\n  Truly unavailable (no data on Yahoo Finance at any start date):")
        for t in truly_failed:
            print(f"    {t}")
        print(f"\n  These are likely: not-yet-listed IPOs, placeholder tickers (DUMMYVEDL*),")
        print(f"  or companies whose Yahoo ticker differs from NSE symbol.")


if __name__ == "__main__":
    main()
