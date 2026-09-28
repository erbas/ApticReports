"""Instrument registry — point-value multipliers and USD conversion rules.

Instruments listed here get their PnL converted and scaled automatically.
Anything not listed falls back to the generic currency-pair logic in
``eod.load_usd_conversion`` (ccy2→USD or USD→ccy2 EOD file) with a
multiplier of 1.

Conversion rules are ``(eod_pair, op)`` where ``op`` is ``"mul"`` (multiply
PnL by the EOD rate) or ``"div"`` (divide PnL by the EOD rate).  ``None``
means PnL is already in USD.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: str
    description: str = ""
    multiplier: float = 1.0
    conversion: tuple[str, str] | None = None
    tick_size: float | None = None


_INSTRUMENTS = [
    # ── CCY ──
    Instrument("AUDNZD", "CCY", "AUD/NZD", conversion=("NZDUSD", "mul")),
    Instrument("NZDJPY", "CCY", "NZD/JPY", conversion=("USDJPY", "div")),
    Instrument("EURCHF", "CCY", "EUR/CHF", conversion=("USDCHF", "div")),
    Instrument("EURGBP", "CCY", "EUR/GBP", conversion=("GBPUSD", "mul")),
    # ── INDEX (US) ──
    Instrument("ESAUSD", "INDEX", "CME E-mini S&P 500", multiplier=50.0, tick_size=0.25),
    Instrument("RTYUSD", "INDEX", "CME E-mini Russell 2000", multiplier=50.0, tick_size=0.1),
    # ── CMDTY ──
    Instrument("XAGUSD", "CMDTY", "Silver"),
    Instrument("XAUXAG", "CMDTY", "Gold/Silver ratio", conversion=("XAGUSD", "mul")),
]

INSTRUMENTS: dict[str, Instrument] = {i.symbol: i for i in _INSTRUMENTS}


def normalise_symbol(instrument: str) -> str:
    """Strip NinjaTrader's ``$`` prefix and whitespace, upper-case."""
    return str(instrument).strip().lstrip("$").upper()


def get_instrument(symbol: str) -> Instrument | None:
    return INSTRUMENTS.get(normalise_symbol(symbol))


def get_multiplier(symbol: str) -> float:
    inst = get_instrument(symbol)
    return inst.multiplier if inst else 1.0
