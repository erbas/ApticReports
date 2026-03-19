"""NinjaTrader trade file loader — port of get.ninja.trades() from daily_PnL_v5.R."""

import re
import pandas as pd


# Canonical column names used throughout the codebase
_REQUIRED = ["Instrument", "Market.pos.", "Entry.price", "Exit.price",
             "Entry.time", "Exit.time", "Quantity"]
_OPTIONAL = ["Entry.name", "Exit.name"]

# Patterns that map messy header variants to canonical names.
# Order matters — first match wins.  Patterns are case-insensitive.
_COLUMN_MAP = [
    (r"instrument",               "Instrument"),
    (r"market[\s._]*pos",         "Market.pos."),
    (r"entry[\s._]*price",        "Entry.price"),
    (r"exit[\s._]*price",         "Exit.price"),
    (r"entry[\s._]*time",         "Entry.time"),
    (r"exit[\s._]*time",          "Exit.time"),
    (r"^quantity$",               "Quantity"),
    (r"entry[\s._]*name",         "Entry.name"),
    (r"exit[\s._]*name",          "Exit.name"),
]


def _normalise_columns(columns: pd.Index) -> list[str]:
    """Map raw CSV header names to canonical names via fuzzy matching."""
    result = []
    for raw in columns:
        raw_clean = raw.strip()
        matched = False
        for pattern, canonical in _COLUMN_MAP:
            if re.search(pattern, raw_clean, re.IGNORECASE):
                result.append(canonical)
                matched = True
                break
        if not matched:
            # Keep original (strip + dots) for any extra columns
            result.append(raw_clean.replace(" ", "."))
    return result


def load_ninja_trades(filepath: str) -> pd.DataFrame:
    """Load a NinjaTrader CSV trade export file.

    Handles column naming differences across NinjaTrader versions
    (spaces, dots, varying capitalisation, trailing commas).
    Returned columns always use canonical dot-separated names.
    """
    df = pd.read_csv(filepath, header=0, sep=",", skipinitialspace=True)
    # Drop unnamed trailing columns (trailing comma in CSV)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = _normalise_columns(df.columns)

    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Found: {list(df.columns)}"
        )
    return df


def extract_metadata(trades: pd.DataFrame) -> dict:
    """Extract currency pair and strategy direction from loaded trades."""
    instrument = str(trades["Instrument"].iloc[0])
    ccy_pair = instrument.replace("$", "")

    # Determine predominant direction from the Market.pos. column
    if "Market.pos." in trades.columns and len(trades) > 0:
        strat_dir = trades["Market.pos."].mode().iloc[0]
    else:
        strat_dir = ""

    return {"ccy_pair": ccy_pair, "strat_dir": str(strat_dir)}
