"""
Factor Attribution Framework — reusable multi-factor OLS regression for
testing whether a strategy's apparent alpha survives controlling for known
risk factors (market beta, size, and any factor added later).

Not part of the trading pipeline. Research tool only — reads cached backtest
output and factor price series, never touches strategy/execution code.

Usage:
    python factor_attribution.py
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import warnings

warnings.filterwarnings("ignore")

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

import momentum_backtest as m

FACTOR_CACHE_DIR = Path("data/cache_factors")
FACTOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Factor definitions: name -> (yfinance ticker, cache filename).
# MARKET uses the same ^NSEI/NIFTYBEES.NS series momentum_backtest.py already
# caches under data/cache_index/ -- reused directly, not refetched.
# SIZE: neither Nifty Midcap 150 nor Nifty Smallcap 250 resolved on Yahoo
# after a handful of reasonable ticker attempts (^NSEMDCP150, MIDCAPETF.NS,
# NIFTYSMLCAP250.NS, MID150BEES.NS, ^CNXSC, SMALLCAP.NS, NIFTY_MIDCAP_150.NS
# all empty). Motilal Oswal Nifty Midcap 100 ETF (MOM100.NS) is the closest
# available proxy with full 2019-2024 daily coverage -- disclosed here, not
# silently substituted. Add a real Midcap150/Smallcap250 series here later if
# a data source is found; nothing else in this module needs to change.
SIZE_FACTOR_TICKER = "MOM100.NS"
SIZE_FACTOR_CACHE = FACTOR_CACHE_DIR / "MOM100.csv"

# MOMENTUM: surveyed candidates --
#   HDFCMOMENT.NS (HDFC Nifty200 Momentum 30 ETF) -- real, exchange-traded,
#     but inception 2023-10-17, only ~295 days / ~60 weeks of history. Too
#     short for a meaningful regression against the full 2019-2024 sample.
#   0P0001LMOA.BO (UTI Nifty200 Momentum 30 Index Fund, Direct Growth) --
#     mutual fund NAV, not exchange-traded intraday, but directly tracks the
#     named Nifty200 Momentum 30 index, inception ~2021-03-10, ~935 daily NAV
#     points / ~198 overlapping weekly observations. Selected: longest
#     available history among real candidates, genuinely passive and
#     investable (index fund, direct plan = lowest available cost for this
#     benchmark), tracks an index explicitly named as a candidate.
#   Nifty500 Momentum 50, other momentum/quality ETFs, Motilal/ICICI-branded
#     momentum products: no resolvable Yahoo Finance ticker found.
# Limitation carried through the rest of this module: this factor's history
# does not cover 2019-2021 (COVID crash + initial bull run) -- every
# comparison involving this factor restricts ALL series to the overlapping
# window, so adding the factor is never confounded with shrinking the sample.
MOMENTUM_FACTOR_TICKER = "0P0001LMOA.BO"
MOMENTUM_FACTOR_CACHE = FACTOR_CACHE_DIR / "UTI_MOM30.csv"


def _load_or_fetch(ticker: str, cache_path: Path, start: str, end: str) -> pd.Series:
    if cache_path.exists():
        cached = pd.read_csv(cache_path, index_col=0, parse_dates=True)["Close"]
        if (
            not cached.empty
            and cached.index.min() <= pd.Timestamp(start)
            and cached.index.max() >= pd.Timestamp(end) - pd.Timedelta(days=5)
        ):
            return cached
    df = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    close = df["Close"].copy()
    if close.index.tz is not None:
        close.index = close.index.tz_convert(None)
    close.to_frame(name="Close").to_csv(cache_path)
    return close


def ols_multifactor(y: np.ndarray, X_factors: np.ndarray, factor_names: list[str]) -> dict:
    """OLS: y = alpha + sum(beta_i * factor_i) + residual.
    X_factors: (n, k) array, one column per factor (no intercept column -- added here).
    Returns alpha/beta point estimates, SEs, t-stats, p-values, 95% CIs, R^2, adj-R^2."""
    n, k = X_factors.shape
    X = np.column_stack([np.ones(n), X_factors])
    XtX_inv = np.linalg.inv(X.T @ X)
    coefs = XtX_inv @ X.T @ y

    y_hat = X @ coefs
    resid = y - y_hat
    dof = n - (k + 1)
    ssr = float(resid @ resid)
    sigma2 = ssr / dof
    se = np.sqrt(np.diag(sigma2 * XtX_inv))
    t_stats = coefs / se
    p_values = 2 * stats.t.sf(np.abs(t_stats), dof)
    t_crit = stats.t.ppf(0.975, dof)
    ci_low = coefs - t_crit * se
    ci_high = coefs + t_crit * se

    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ssr / sst
    adj_r2 = 1 - (1 - r2) * (n - 1) / dof

    names = ["alpha"] + factor_names
    return {
        "names": names,
        "coefs": coefs,
        "se": se,
        "t": t_stats,
        "p": p_values,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "r2": r2,
        "adj_r2": adj_r2,
        "n": n,
        "dof": dof,
        "resid": resid,
    }


def print_report(label: str, res: dict, factor_means: dict, mean_y: float):
    print(f"\n{'=' * 70}\n{label}  (n={res['n']}, dof={res['dof']})\n{'=' * 70}")
    for i, name in enumerate(res["names"]):
        ann = f"  annualized: {((1 + res['coefs'][i]) ** 52 - 1) * 100:+.2f}%" if name == "alpha" else ""
        sig = "***" if res["p"][i] < 0.01 else ("**" if res["p"][i] < 0.05 else ("*" if res["p"][i] < 0.10 else ""))
        print(
            f"  {name:10s}  coef={res['coefs'][i]:+.5f}  se={res['se'][i]:.5f}  "
            f"t={res['t'][i]:+.3f}  p={res['p'][i]:.4f} {sig}  "
            f"95% CI=[{res['ci_low'][i]:+.5f}, {res['ci_high'][i]:+.5f}]{ann}"
        )
    print(f"  R-squared: {res['r2']:.4f}   Adjusted R-squared: {res['adj_r2']:.4f}")

    print("\n  Return decomposition (mean weekly return):")
    total_explained = res["coefs"][0]  # alpha
    print(
        f"    alpha contribution:  {res['coefs'][0] * 100:+.4f}%  ({res['coefs'][0] / mean_y * 100:.1f}% of mean return)"
    )
    for i, name in enumerate(res["names"][1:], start=1):
        contrib = res["coefs"][i] * factor_means[name]
        total_explained += contrib
        print(f"    {name} contribution: {contrib * 100:+.4f}%  ({contrib / mean_y * 100:.1f}% of mean return)")
    print(f"    mean weekly return:  {mean_y * 100:+.4f}%  (sum check: {total_explained * 100:+.4f}%)")
    print(
        f"    variance explained (R2): {res['r2'] * 100:.1f}%   variance unexplained (residual): {(1 - res['r2']) * 100:.1f}%"
    )


def main():
    START_DATE, END_DATE = "2019-01-01", "2024-12-31"

    prices = m.load_price_matrix()
    regime = m.load_nifty50_regime(START_DATE, END_DATE)
    equity = m.run_backtest(prices, regime=regime)

    nsei = pd.read_csv("data/cache_index/NSEI.csv", index_col=0, parse_dates=True)["Close"]
    if nsei.index.tz is not None:
        nsei.index = nsei.index.tz_localize(None)
    nsei = nsei.sort_index()

    size_factor = _load_or_fetch(SIZE_FACTOR_TICKER, SIZE_FACTOR_CACHE, START_DATE, END_DATE)
    size_factor = size_factor.sort_index()
    if size_factor.index.tz is not None:
        size_factor.index = size_factor.index.tz_localize(None)

    mom_factor = _load_or_fetch(MOMENTUM_FACTOR_TICKER, MOMENTUM_FACTOR_CACHE, START_DATE, END_DATE)
    mom_factor = mom_factor.sort_index()
    if mom_factor.index.tz is not None:
        mom_factor.index = mom_factor.index.tz_localize(None)
    print(
        f"Momentum factor proxy: {MOMENTUM_FACTOR_TICKER} (UTI Nifty200 Momentum 30 Index Direct Growth), "
        f"coverage {mom_factor.index.min().date()} to {mom_factor.index.max().date()}"
    )

    strat_val = equity["value"]
    strat_ret = strat_val.pct_change().dropna()
    dates = strat_val.index

    mkt_ret, size_ret, mom_ret = [], [], []
    for i in range(1, len(dates)):
        d0, d1 = dates[i - 1], dates[i]
        mkt_ret.append(nsei.asof(d1) / nsei.asof(d0) - 1.0)
        size_ret.append(size_factor.asof(d1) / size_factor.asof(d0) - 1.0)
        mom_ret.append(mom_factor.asof(d1) / mom_factor.asof(d0) - 1.0 if d0 >= mom_factor.index.min() else np.nan)

    df = pd.DataFrame(
        {
            "strat": strat_ret.values,
            "mkt": mkt_ret,
            "size": size_ret,
            "mom": mom_ret,
        },
        index=strat_ret.index,
    )
    df_full = df[["strat", "mkt", "size"]].dropna()  # full 2019-2024 sample, no momentum factor
    df_overlap = df.dropna()  # restricted to where all 3 factors + strategy have data

    print(f"Full-sample aligned weekly observations (2019-2024): {len(df_full)}")
    print(
        f"Overlap-sample aligned weekly observations (momentum factor coverage): {len(df_overlap)}, "
        f"{df_overlap.index.min().date()} to {df_overlap.index.max().date()}"
    )
    print(f"Size factor proxy: {SIZE_FACTOR_TICKER} (Motilal Oswal Nifty Midcap 100 ETF)")

    mean_y_full = df_full["strat"].mean()
    factor_means_full = {"mkt": df_full["mkt"].mean(), "size": df_full["size"].mean()}

    # -- Full-sample: one-factor and two-factor, as before (context/continuity) --
    one_factor = ols_multifactor(df_full["strat"].values, df_full[["mkt"]].values, ["mkt"])
    print_report(
        "ONE-FACTOR MODEL, full sample 2019-2024 (market only) -- prior experiment",
        one_factor,
        factor_means_full,
        mean_y_full,
    )

    two_factor_full = ols_multifactor(df_full["strat"].values, df_full[["mkt", "size"]].values, ["mkt", "size"])
    print_report(
        "TWO-FACTOR MODEL, full sample 2019-2024 (market + size) -- prior experiment",
        two_factor_full,
        factor_means_full,
        mean_y_full,
    )

    # -- Overlap-sample: two-factor recomputed (fair baseline) and four-factor --
    # Recomputing two-factor on the SAME restricted window as the four-factor
    # model, not just reusing the full-sample two-factor result -- otherwise
    # any change in alpha would be confounded with the shorter sample period,
    # not attributable to adding the momentum factor specifically.
    mean_y_ov = df_overlap["strat"].mean()
    factor_means_ov = {
        "mkt": df_overlap["mkt"].mean(),
        "size": df_overlap["size"].mean(),
        "mom": df_overlap["mom"].mean(),
    }

    two_factor_ov = ols_multifactor(df_overlap["strat"].values, df_overlap[["mkt", "size"]].values, ["mkt", "size"])
    print_report(
        f"TWO-FACTOR MODEL, OVERLAP SAMPLE ({df_overlap.index.min().date()} to {df_overlap.index.max().date()}) -- fair baseline for the 4-factor comparison below",
        two_factor_ov,
        factor_means_ov,
        mean_y_ov,
    )

    four_factor = ols_multifactor(
        df_overlap["strat"].values, df_overlap[["mkt", "size", "mom"]].values, ["mkt", "size", "mom"]
    )
    print_report(
        "FOUR-FACTOR MODEL, same overlap sample (market + size + momentum)", four_factor, factor_means_ov, mean_y_ov
    )

    alpha_2f_ov = two_factor_ov["coefs"][0]
    alpha_4f = four_factor["coefs"][0]
    print(f"\n{'=' * 70}\nDIRECT COMPARISON (same overlap sample, isolating the momentum factor's effect)\n{'=' * 70}")
    print(
        f"  Alpha, two-factor (mkt+size):        {alpha_2f_ov * 100:+.4f}%/wk  ({(1 + alpha_2f_ov) ** 52 - 1:+.2%} ann.)  p={two_factor_ov['p'][0]:.4f}"
    )
    print(
        f"  Alpha, four-factor (mkt+size+mom):   {alpha_4f * 100:+.4f}%/wk  ({(1 + alpha_4f) ** 52 - 1:+.2%} ann.)  p={four_factor['p'][0]:.4f}"
    )
    reduction = (alpha_2f_ov - alpha_4f) / alpha_2f_ov * 100 if alpha_2f_ov != 0 else float("nan")
    print(f"  Alpha reduction from adding momentum factor: {reduction:.1f}%")
    print(
        f"  R2 two-factor: {two_factor_ov['r2']:.4f}   R2 four-factor: {four_factor['r2']:.4f}   (adj-R2: {two_factor_ov['adj_r2']:.4f} -> {four_factor['adj_r2']:.4f})"
    )
    print(f"  Incremental R2 from momentum factor: {four_factor['r2'] - two_factor_ov['r2']:.4f}")

    # -- Rolling 52-week four-factor coefficient stability (overlap sample) --
    print(f"\n{'=' * 70}\nROLLING 52-WEEK FOUR-FACTOR STABILITY (overlap sample, n={len(df_overlap)})\n{'=' * 70}")
    window = 52
    roll_alpha, roll_mkt_beta, roll_size_beta, roll_mom_beta, roll_idx = [], [], [], [], []
    skipped = 0
    for i in range(window, len(df_overlap)):
        sub = df_overlap.iloc[i - window : i]
        if sub["strat"].std() == 0:
            skipped += 1
            continue
        r = ols_multifactor(sub["strat"].values, sub[["mkt", "size", "mom"]].values, ["mkt", "size", "mom"])
        roll_alpha.append((1 + r["coefs"][0]) ** 52 - 1)
        roll_mkt_beta.append(r["coefs"][1])
        roll_size_beta.append(r["coefs"][2])
        roll_mom_beta.append(r["coefs"][3])
        roll_idx.append(df_overlap.index[i])
    roll_alpha = pd.Series(roll_alpha, index=roll_idx)
    roll_mkt_beta = pd.Series(roll_mkt_beta, index=roll_idx)
    roll_size_beta = pd.Series(roll_size_beta, index=roll_idx)
    roll_mom_beta = pd.Series(roll_mom_beta, index=roll_idx)
    if skipped:
        print(f"  ({skipped} of {len(df_overlap) - window} windows skipped -- zero-variance strategy return)")

    if len(roll_alpha) > 0:
        print(
            f"  Rolling annualized alpha: min={roll_alpha.min() * 100:+.1f}%  max={roll_alpha.max() * 100:+.1f}%  mean={roll_alpha.mean() * 100:+.1f}%  std={roll_alpha.std() * 100:.1f}%"
        )
        print(f"  Fraction of windows with positive alpha: {(roll_alpha > 0).mean() * 100:.0f}%")
        print(f"  Rolling market beta:   mean={roll_mkt_beta.mean():.3f}  std={roll_mkt_beta.std():.3f}")
        print(f"  Rolling size beta:     mean={roll_size_beta.mean():.3f}  std={roll_size_beta.std():.3f}")
        print(f"  Rolling momentum beta: mean={roll_mom_beta.mean():.3f}  std={roll_mom_beta.std():.3f}")
    else:
        print("  Overlap sample too short for a 52-week rolling window.")


if __name__ == "__main__":
    main()
