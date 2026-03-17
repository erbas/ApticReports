"""Daily PnL calculation with trade splitting — port of make.daily.pnl() from daily_PnL_v5.R.

This is the core algorithm that splits multi-day trades at EOD boundaries
to produce accurate daily PnL attribution.
"""

import pandas as pd
import numpy as np

from .eod import add_time_to_date, get_nearest_eod


def make_daily_pnl(
    trades_csv: pd.DataFrame,
    eod_prices: pd.Series,
    ref_ccy_conv: pd.Series,
    trade_tz: str,
    ref_tz: str = "Europe/London",
    eod_hour: int = 17,
) -> dict:
    """Split trades at EOD boundaries and compute daily PnL.

    Parameters
    ----------
    trades_csv : DataFrame from NinjaTrader CSV
    eod_prices : EOD price Series (tz-aware index)
    ref_ccy_conv : Currency conversion Series (tz-aware index at eod_hour)
    trade_tz : Timezone of trade timestamps in the CSV
    ref_tz : Reference timezone for reporting
    eod_hour : Hour of official end-of-day

    Returns
    -------
    dict with keys: trades, pnl_daily, pnl_raw, discrepancies
    """
    # Parse entry/exit times in trade timezone, then convert to ref timezone
    entries = pd.to_datetime(trades_csv["Entry.time"], format="%d/%m/%Y %H:%M:%S", dayfirst=True)
    # Try with seconds first, fall back to without
    if entries.isna().any():
        entries = pd.to_datetime(trades_csv["Entry.time"], format="%d/%m/%Y %H:%M", dayfirst=True)
    exits = pd.to_datetime(trades_csv["Exit.time"], format="%d/%m/%Y %H:%M:%S", dayfirst=True)
    if exits.isna().any():
        exits = pd.to_datetime(trades_csv["Exit.time"], format="%d/%m/%Y %H:%M", dayfirst=True)

    entries = entries.dt.tz_localize(trade_tz).dt.tz_convert(ref_tz)
    exits = exits.dt.tz_localize(trade_tz).dt.tz_convert(ref_tz)

    # EOD times with hour
    eod_hms = add_time_to_date(eod_prices, eod_hour, ref_tz)
    trading_days = eod_hms.index

    # Skip trades closing after last EOD price
    last_eod = eod_prices.index[-1]
    mask_skip = exits > last_eod
    if mask_skip.any():
        trades_csv = trades_csv[~mask_skip].reset_index(drop=True)
        entries = entries[~mask_skip].reset_index(drop=True)
        exits = exits[~mask_skip].reset_index(drop=True)

    # Encode direction: Long=+1, Short=-1
    direction = trades_csv["Market.pos."].map({"Long": 1, "Short": -1}).fillna(0).astype(int)

    # Build raw trades table
    n = len(trades_csv)
    trades_raw = pd.DataFrame({
        "TradeID": range(1, n + 1),
        "SplitID": 0,
        "Market.pos.": direction.values,
        "Entry.price": trades_csv["Entry.price"].values.astype(float),
        "Exit.price": trades_csv["Exit.price"].values.astype(float),
        "Entry.time": entries.values,
        "Exit.time": exits.values,
        "Quantity": trades_csv["Quantity"].values.astype(float),
    })

    # Find synthetic trade dates for each trade (EOD times strictly between entry and exit)
    synthetic_dates = []
    for i in range(n):
        td = trading_days[(trading_days > entries.iloc[i]) & (trading_days < exits.iloc[i])]
        synthetic_dates.append(td)

    # Identify trades that need splitting (have at least one intermediate EOD)
    idx_split = [i for i, td in enumerate(synthetic_dates) if len(td) > 0]

    # Build modified entries, modified exits, and new synthetic trades
    new_rows = []

    # Unsplit trades (same-day) go straight through
    idx_unsplit = [i for i in range(n) if i not in idx_split]
    unsplit = trades_raw.iloc[idx_unsplit].copy()

    modified_entries = []
    modified_exits = []

    for i in idx_split:
        row = trades_raw.iloc[i]
        ref_eod = synthetic_dates[i]

        # Modified entry: original entry → first EOD
        entry_row = row.copy()
        entry_row["Exit.time"] = ref_eod[0]
        entry_row["Exit.price"] = eod_hms.loc[ref_eod[0]]
        entry_row["SplitID"] = 1
        modified_entries.append(entry_row)

        # Modified exit: last EOD → original exit
        exit_row = row.copy()
        exit_row["Entry.time"] = ref_eod[-1] + pd.Timedelta(seconds=1)
        exit_row["Entry.price"] = eod_hms.loc[ref_eod[-1]]
        exit_row["SplitID"] = len(ref_eod) + 1
        modified_exits.append(exit_row)

        # Synthetic middle trades (EOD[j-1] → EOD[j])
        if len(ref_eod) >= 2:
            for j in range(1, len(ref_eod)):
                new_row = {
                    "TradeID": row["TradeID"],
                    "SplitID": j + 1,
                    "Market.pos.": row["Market.pos."],
                    "Entry.price": eod_hms.loc[ref_eod[j - 1]],
                    "Exit.price": eod_hms.loc[ref_eod[j]],
                    "Entry.time": ref_eod[j - 1] + pd.Timedelta(seconds=1),
                    "Exit.time": ref_eod[j],
                    "Quantity": row["Quantity"],
                }
                new_rows.append(new_row)

    # Combine all trades
    parts = [unsplit]
    if modified_entries:
        parts.append(pd.DataFrame(modified_entries))
    if modified_exits:
        parts.append(pd.DataFrame(modified_exits))
    if new_rows:
        parts.append(pd.DataFrame(new_rows))

    all_trades = pd.concat(parts, ignore_index=True)
    all_trades = all_trades.sort_values(["TradeID", "SplitID"]).reset_index(drop=True)

    # Calculate PnL per trade (in original currency)
    price_change = all_trades["Exit.price"] - all_trades["Entry.price"]
    all_trades["pnl"] = price_change * all_trades["Market.pos."] * all_trades["Quantity"]

    # Raw PnL from original unsplit trades
    raw_dir = trades_csv["Market.pos."].map({"Long": 1, "Short": -1}).fillna(0).astype(int)
    pnl_raw_vals = (
        raw_dir.values
        * (trades_csv["Exit.price"].values.astype(float) - trades_csv["Entry.price"].values.astype(float))
        * trades_csv["Quantity"].values.astype(float)
    )
    pnl_raw = pd.Series(pnl_raw_vals, index=entries.values, name="pnl_raw")

    # Convert raw PnL to USD using nearest EOD conversion rate
    conv_times = ref_ccy_conv.index
    pnl_raw_usd = pnl_raw.copy()
    for i in range(len(pnl_raw)):
        nearest = get_nearest_eod(pnl_raw.index[i], conv_times, direction=1)
        pnl_raw_usd.iloc[i] = pnl_raw.iloc[i] * ref_ccy_conv.loc[nearest]

    # Align exit times to official EOD for daily aggregation
    all_exit_times = pd.to_datetime(all_trades["Exit.time"])
    if all_exit_times.dt.tz is None:
        all_exit_times = all_exit_times.dt.tz_localize(ref_tz)
    eod_exit_times = all_exit_times.map(lambda x: get_nearest_eod(x, trading_days, direction=1))
    all_trades["Exit.time.official"] = eod_exit_times

    # Create PnL series indexed by official EOD exit
    pnl_series = pd.Series(all_trades["pnl"].values, index=eod_exit_times.values)

    # Aggregate to daily
    pnl_daily = pnl_series.groupby(pnl_series.index.date).sum()
    pnl_daily.index = pd.to_datetime(pnl_daily.index).tz_localize(ref_tz)

    # Convert daily PnL to USD
    pnl_daily_usd = pnl_daily.copy()
    for dt in pnl_daily.index:
        nearest = get_nearest_eod(dt, conv_times, direction=1)
        conv_rate = ref_ccy_conv.loc[nearest]
        pnl_daily_usd.loc[dt] = pnl_daily.loc[dt] * conv_rate
    pnl_daily_usd.name = "pnl_daily_usd"

    # Sanity check: sum of split PnL per TradeID should equal raw PnL
    sum_by_trade = all_trades.groupby("TradeID")["pnl"].sum()
    discrepancies = []
    for tid in sum_by_trade.index:
        raw_val = pnl_raw_vals[tid - 1] if tid - 1 < len(pnl_raw_vals) else 0
        if abs(sum_by_trade[tid] - raw_val) > 1e-8:
            discrepancies.append(tid)

    return {
        "trades": all_trades,
        "pnl_daily": pnl_daily_usd,
        "pnl_raw": pnl_raw_usd,
        "discrepancies": discrepancies,
    }


def process_backtest(
    filepath: str,
    eod_path: str,
    aum: float,
    strategy: str,
    timeframe: str,
    is_future: bool,
    pt_value: float,
    timezone: str,
    output_path: str,
) -> dict:
    """Full backtest processing pipeline — orchestrates loading, splitting, and output.

    Returns dict with results and file paths.
    """
    import os
    from .trades import load_ninja_trades, extract_metadata
    from .eod import load_eod_prices, load_usd_conversion

    trades_csv = load_ninja_trades(filepath)
    meta = extract_metadata(trades_csv)
    ccy_pair = meta["ccy_pair"]
    strat_dir = meta["strat_dir"]

    eod_prices = load_eod_prices(ccy_pair, eod_path)
    usd_conv = load_usd_conversion(ccy_pair, eod_path)

    result = make_daily_pnl(trades_csv, eod_prices, usd_conv, trade_tz=timezone)

    pnl_daily = result["pnl_daily"]
    pnl_raw = result["pnl_raw"]

    # Apply futures multiplier
    if is_future:
        pnl_daily = pnl_daily * pt_value
        pnl_raw = pnl_raw * pt_value

    # Scale daily PnL as returns (divide by AUM)
    pnl_daily_returns = pnl_daily / aum

    # Construct output filenames
    filestem = os.path.splitext(os.path.basename(filepath))[0]

    # Save processed trades
    trades_file = os.path.join(output_path, f"{filestem}_processed.csv")
    result["trades"].to_csv(trades_file, index=False)

    # Save raw PnL
    raw_file = os.path.join(output_path, f"{filestem}_pnl_raw.csv")
    pnl_raw.to_csv(raw_file, header=True)

    # Save daily PnL with metadata header (matching R format)
    daily_file = os.path.join(output_path, f"{filestem}_pnl_daily.csv")
    daily_out = pnl_daily.copy()
    daily_out.name = f"DailyPnl(USD)|{ccy_pair}|{strategy}|{timeframe}|{strat_dir}"
    daily_out.to_csv(daily_file, header=True)

    return {
        "pnl_daily": pnl_daily,
        "pnl_daily_returns": pnl_daily_returns,
        "pnl_raw": pnl_raw,
        "trades": result["trades"],
        "discrepancies": result["discrepancies"],
        "ccy_pair": ccy_pair,
        "strat_dir": strat_dir,
        "filestem": filestem,
        "files": {
            "trades": trades_file,
            "raw": raw_file,
            "daily": daily_file,
        },
    }
