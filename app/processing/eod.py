"""EOD price loading and currency conversion — port of daily_PnL_v5.R utility functions."""

import os
import pandas as pd
import numpy as np


def load_eod_prices(ccy_pair: str, path: str, tz: str = "Europe/London") -> pd.Series:
    """Load end-of-day prices from CSV. Returns Series indexed by tz-aware datetime at midnight.

    Handles multiple CSV formats:
      - Header + skip row + [Date, Price] (legacy R format)
      - Header + [Date, Close/Price/...] (standard export)
    Date parsing is flexible (d/mm/yyyy, dd/mm/yyyy, yyyy-mm-dd, etc.).
    """
    filename = os.path.join(path, f"{ccy_pair}_EOD.csv")
    # Peek at file to detect format
    df_peek = pd.read_csv(filename, nrows=2, header=0, skipinitialspace=True)
    first_col = df_peek.columns[0].strip().lower()

    # If the header looks like a date (not "date"), the file has no real header
    if first_col in ("date", "date%"):
        df = pd.read_csv(filename, header=0, skipinitialspace=True)
    else:
        # Legacy format: header row is data, or there's a skip row
        df = pd.read_csv(filename, skiprows=1, header=0, skipinitialspace=True)

    prices = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    dates = pd.to_datetime(df.iloc[:, 0], dayfirst=True, format="mixed")
    eod = pd.Series(prices.values, index=dates, name=ccy_pair)
    eod = eod.dropna()
    # Remove duplicate dates
    eod = eod[~eod.index.duplicated(keep="first")]
    eod.index = eod.index.tz_localize(tz)
    return eod


def add_time_to_date(eod: pd.Series, eod_hour: int = 17, tz: str = "Europe/London") -> pd.Series:
    """Convert date-only index to datetime at specified EOD hour."""
    new_index = eod.index.normalize() + pd.Timedelta(hours=eod_hour)
    if new_index.tz is None:
        new_index = new_index.tz_localize(tz)
    return pd.Series(eod.values, index=new_index, name=eod.name)


def load_usd_conversion(ccy_pair: str, path: str, pnl_ccy: str = "USD") -> pd.Series:
    """Load currency conversion rates to convert PnL into pnl_ccy.

    Logic mirrors R load.USD.conv():
      - If pnl_ccy == quote ccy (ccy2) → conversion rate = 1.0
      - If pnl_ccy == base ccy (ccy1) → find ccy2→pnl_ccy pair
      - Otherwise → find ccy2→pnl_ccy pair
    """
    ccy1 = ccy_pair[:3]
    ccy2 = ccy_pair[3:6]
    eod_files = [f for f in os.listdir(path) if f.endswith("_EOD.csv")]

    if pnl_ccy == ccy2:
        eod = load_eod_prices(ccy_pair, path)
        conv = pd.Series(np.ones(len(eod)), index=eod.index, name=ccy_pair)
    else:
        # Try ccy2+pnl_ccy, then pnl_ccy+ccy2 (inverted)
        conv_pair = f"{ccy2}{pnl_ccy}"
        conv_pair_inv = f"{pnl_ccy}{ccy2}"
        if f"{conv_pair}_EOD.csv" in eod_files:
            conv = load_eod_prices(conv_pair, path)
        elif f"{conv_pair_inv}_EOD.csv" in eod_files:
            conv = 1.0 / load_eod_prices(conv_pair_inv, path)
            conv.name = conv_pair
        else:
            raise FileNotFoundError(
                f"Cannot find end-of-day reval file for: {conv_pair} or {conv_pair_inv}"
            )

    return add_time_to_date(conv)


def get_nearest_eod(dt: pd.Timestamp, eod_times: pd.DatetimeIndex, direction: int = 1) -> pd.Timestamp:
    """Find nearest official EOD time to datetime dt.

    direction=1: next EOD (or exact match), direction=-1: previous EOD.
    """
    if dt in eod_times:
        return dt
    if direction == 1:
        valid = eod_times[eod_times > dt]
        if len(valid) == 0:
            return eod_times[-1]
        return valid[0]
    else:
        valid = eod_times[eod_times < dt]
        if len(valid) == 0:
            return eod_times[0]
        return valid[-1]


def get_nearest_eod_vectorized(dts: pd.DatetimeIndex, eod_times: pd.DatetimeIndex,
                                direction: int = 1) -> pd.DatetimeIndex:
    """Vectorized version of get_nearest_eod for an array of datetimes.

    Uses searchsorted for O(n log m) instead of O(n*m).
    direction=1: next EOD (or exact match), direction=-1: previous EOD.
    """
    eod_sorted = eod_times.sort_values()
    eod_vals = eod_sorted.values
    dt_vals = dts.values

    if direction == 1:
        idx = np.searchsorted(eod_vals, dt_vals, side="left")
        idx = np.clip(idx, 0, len(eod_vals) - 1)
        result = eod_vals[idx]
    else:
        idx = np.searchsorted(eod_vals, dt_vals, side="left") - 1
        idx = np.clip(idx, 0, len(eod_vals) - 1)
        result = eod_vals[idx]

    result_idx = pd.DatetimeIndex(result)
    if eod_sorted.tz is not None:
        # numpy .values strips tz and stores as UTC nanos, so localize as UTC first
        result_idx = result_idx.tz_localize("UTC").tz_convert(eod_sorted.tz)
    return result_idx
