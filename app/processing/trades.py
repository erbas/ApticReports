"""NinjaTrader trade file loader — port of get.ninja.trades() from daily_PnL_v5.R."""

import pandas as pd


def load_ninja_trades(filepath: str) -> pd.DataFrame:
    """Load a NinjaTrader CSV trade export file.

    Returns DataFrame with columns:
        Instrument, Market.pos., Entry.price, Exit.price,
        Entry.time, Exit.time, Quantity, Entry.name
    """
    df = pd.read_csv(filepath, header=0, sep=",", skipinitialspace=True)
    return df


def extract_metadata(trades: pd.DataFrame) -> dict:
    """Extract currency pair and strategy direction from loaded trades."""
    instrument = str(trades["Instrument"].iloc[0])
    ccy_pair = instrument.replace("$", "")

    # Strategy direction is in column index 4 (Entry.name or similar)
    strat_dir = str(trades.iloc[0, 4]) if trades.shape[1] > 4 else ""

    return {"ccy_pair": ccy_pair, "strat_dir": strat_dir}
