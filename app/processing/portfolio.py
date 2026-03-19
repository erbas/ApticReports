"""Portfolio combination — port of Unreactive_PortfolioMakeReport.R.

Loads multiple *_pnl_daily.csv files and combines them into a portfolio.
"""

import os
import pandas as pd
import numpy as np


def parse_pnl_column_name(col_name: str) -> dict:
    """Parse metadata from daily PnL column header.

    Format: DailyPnl(USD)|CCYPAIR|STRATEGY|TIMEFRAME|DIRECTION
    The column name from the R output has dots replacing pipes/parens in some cases.
    """
    # Handle both pipe-separated and dot-separated (from CSV round-trip)
    parts = col_name.replace(".", "|").split("|")
    # Find the relevant parts: ccy_pair, strategy, timeframe, direction
    meta = {"ccy_pair": "", "strategy": "", "timeframe": "", "direction": ""}
    if len(parts) >= 5:
        meta["ccy_pair"] = parts[1]
        meta["strategy"] = parts[2]
        meta["timeframe"] = parts[3]
        meta["direction"] = parts[4]
    return meta


def load_daily_pnl_file(filepath: str) -> tuple[pd.Series, dict]:
    """Load a single *_pnl_daily.csv file.

    Returns (Series indexed by date, metadata dict).
    """
    df = pd.read_csv(filepath, sep=",")
    col_name = df.columns[1]
    meta = parse_pnl_column_name(col_name)

    dates = pd.to_datetime(df.iloc[:, 0], utc=True).dt.tz_localize(None).dt.normalize()

    values = pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0)
    series = pd.Series(values.values, index=dates.values, name=meta.get("ccy_pair", col_name))
    return series, meta


def load_benchmark(index_path: str) -> pd.Series | None:
    """Load NewEdge CTA benchmark if available.

    CSV format: Date%, Value% (where Value% is like "0.05%" meaning 0.05%)
    """
    filepath = os.path.join(index_path, "NewEdge_CTA_Historical.csv")
    if not os.path.exists(filepath):
        return None

    df = pd.read_csv(filepath, header=None)
    values = df.iloc[:, 1].astype(str).str.replace("%", "").astype(float) / 100
    dates = pd.to_datetime(df.iloc[:, 0], dayfirst=True)
    benchmark = pd.Series(values.values, index=dates.values, name="NewEdge CTA Index")
    benchmark = benchmark.dropna()
    return benchmark


def combine_portfolio(
    filepaths: list[str],
    aum: float,
    report_name: str,
    start_date: str | None = None,
    end_date: str | None = None,
    rel_returns: bool = False,
    ptf_of_ptf: bool = False,
    index_path: str | None = None,
    output_path: str = ".",
) -> dict:
    """Combine multiple daily PnL files into a portfolio.

    Parameters
    ----------
    filepaths : list of paths to *_pnl_daily.csv files
    aum : assets under management (used to normalize PnL to returns)
    report_name : name for output files
    start_date, end_date : date range in dd/mm/yyyy format (optional)
    rel_returns : if True, average % returns; if False, sum cash PnLs
    ptf_of_ptf : if True, treat inputs as portfolio-level returns (AUM=1)
    index_path : path to benchmark index files (optional)
    output_path : directory for output files

    Returns
    -------
    dict with portfolio daily/monthly PnL, metadata, and file paths
    """
    if ptf_of_ptf:
        aum = 1.0

    # Load all PnL files
    all_series = []
    all_meta = []
    for fp in filepaths:
        series, meta = load_daily_pnl_file(fp)
        all_series.append(series / aum)
        all_meta.append(meta)

    # Combine into a single DataFrame, fill missing with 0
    combined = pd.concat(all_series, axis=1).fillna(0)

    # Find date range across all files
    first_date = combined.index.min()
    last_date = combined.index.max()

    # Load benchmark if available
    benchmark = None
    if index_path:
        benchmark = load_benchmark(index_path)
        if benchmark is not None:
            # Trim to strategy date range
            benchmark = benchmark[(benchmark.index >= first_date) & (benchmark.index <= last_date)]

    # Apply date range filter
    if start_date:
        sd = pd.to_datetime(start_date, format="%d/%m/%Y")
        combined = combined[combined.index >= sd]
        if benchmark is not None:
            benchmark = benchmark[benchmark.index >= sd]
    if end_date:
        ed = pd.to_datetime(end_date, format="%d/%m/%Y")
        combined = combined[combined.index <= ed]
        if benchmark is not None:
            benchmark = benchmark[benchmark.index <= ed]

    # Compute portfolio returns
    if rel_returns:
        portfolio = combined.mean(axis=1)
    else:
        portfolio = combined.sum(axis=1)
    portfolio.name = "Portfolio"

    # Build daily output with benchmark
    if benchmark is not None:
        ptf_daily = pd.DataFrame({"Portfolio": portfolio, "NewEdge.CTA": benchmark}).fillna(0)
    else:
        ptf_daily = pd.DataFrame({"Portfolio": portfolio})
    ptf_daily.index.name = "Date"

    # Monthly aggregation
    ptf_monthly = ptf_daily.resample("ME").sum()
    ptf_monthly.index.name = "Date"

    # Save outputs
    daily_file = os.path.join(output_path, f"{report_name}_pnl_daily.csv")
    ptf_daily.to_csv(daily_file)

    monthly_file = os.path.join(output_path, f"{report_name}_pnl_monthly.csv")
    ptf_monthly.to_csv(monthly_file)

    only_daily_file = os.path.join(output_path, f"{report_name}_only_pnl_daily.csv")
    portfolio.to_csv(only_daily_file, header=True)

    meta_df = pd.DataFrame(all_meta)

    return {
        "ptf_daily": ptf_daily,
        "ptf_monthly": ptf_monthly,
        "portfolio": portfolio,
        "benchmark": benchmark,
        "strategy_returns": combined,
        "metadata": meta_df,
        "files": {
            "daily": daily_file,
            "monthly": monthly_file,
            "only_daily": only_daily_file,
        },
    }
