"""Rolling annual correlation between the CRNCY_LongTerm portfolio and ES (S&P 500) futures.

Two input series:
  * CRNCY_LongTerm_pnl_daily.csv  -- daily portfolio returns (already fractional returns, % of AUM)
  * ESAUSD_EOD.csv                -- ES futures end-of-day close *prices* (need converting to returns)

To correlate them on a like-for-like basis we turn the ES price series into daily
returns, align both series on their common trading days, and compute the Pearson
correlation over a rolling 252-trading-day window (the "annual" window used elsewhere
in this project, e.g. metrics.rolling_volatility).

Run:  python analysis/rolling_annual_correlation.py
Outputs (written next to this script):
  * rolling_annual_correlation.csv  -- date, portfolio_ret, es_ret, rolling_corr
  * rolling_annual_correlation.png  -- chart of the rolling correlation
"""

import os
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WINDOW = 252  # trading days ~ 1 year


def load_portfolio_returns(path: str) -> pd.Series:
    """Load the portfolio daily returns (Date, Portfolio). Already fractional returns."""
    df = pd.read_csv(path)
    s = pd.Series(
        pd.to_numeric(df["Portfolio"], errors="coerce").values,
        index=pd.to_datetime(df["Date"], format="%Y-%m-%d"),
        name="portfolio_ret",
    )
    return s.dropna().sort_index()


def load_es_returns(path: str) -> pd.Series:
    """Load ES EOD close prices (Date dd/mm/yyyy, Close) and convert to simple daily returns."""
    df = pd.read_csv(path)
    price = pd.Series(
        pd.to_numeric(df["Close"], errors="coerce").values,
        index=pd.to_datetime(df["Date"], dayfirst=True),
        name="es_close",
    ).dropna().sort_index()
    price = price[~price.index.duplicated(keep="first")]
    ret = price.pct_change().rename("es_ret")
    return ret.dropna()


def main() -> None:
    port = load_portfolio_returns(os.path.join(DATA, "CRNCY_LongTerm_pnl_daily.csv"))
    es = load_es_returns(os.path.join(DATA, "ESAUSD_EOD.csv"))

    # Align on common trading days (correlation needs paired same-day observations).
    df = pd.concat([port, es], axis=1, join="inner").dropna()

    rolling_corr = (
        df["portfolio_ret"].rolling(WINDOW).corr(df["es_ret"]).rename("rolling_corr")
    )
    out = pd.concat([df, rolling_corr], axis=1)

    csv_path = os.path.join(HERE, "rolling_annual_correlation.csv")
    out.to_csv(csv_path, index_label="Date", float_format="%.10g")

    valid = rolling_corr.dropna()

    # --- chart ---
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(valid.index, valid.values, color="#1f77b4", lw=1.2)
    ax.axhline(0.0, color="grey", lw=0.8, ls="--")
    full_corr = df["portfolio_ret"].corr(df["es_ret"])
    ax.axhline(full_corr, color="#d62728", lw=0.9, ls=":",
               label=f"full-sample corr = {full_corr:.3f}")
    ax.set_title(f"Rolling {WINDOW}-day (annual) correlation: CRNCY_LongTerm vs ES futures")
    ax.set_ylabel("Pearson correlation")
    ax.set_xlabel("Date")
    ax.set_ylim(-1, 1)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    png_path = os.path.join(HERE, "rolling_annual_correlation.png")
    fig.savefig(png_path, dpi=130)

    # --- summary to stdout ---
    print(f"Portfolio returns : {len(port):>5} rows  {port.index.min().date()} -> {port.index.max().date()}")
    print(f"ES returns        : {len(es):>5} rows  {es.index.min().date()} -> {es.index.max().date()}")
    print(f"Common (aligned)  : {len(df):>5} rows  {df.index.min().date()} -> {df.index.max().date()}")
    print(f"Window            : {WINDOW} trading days")
    print(f"Full-sample corr  : {full_corr:.4f}")
    if len(valid):
        print(f"Rolling corr      : mean={valid.mean():.4f}  min={valid.min():.4f}  max={valid.max():.4f}")
        print(f"Latest ({valid.index[-1].date()}) : {valid.iloc[-1]:.4f}")
    print(f"\nWrote: {csv_path}")
    print(f"Wrote: {png_path}")


if __name__ == "__main__":
    main()
