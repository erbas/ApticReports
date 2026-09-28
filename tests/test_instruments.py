"""Tests for the instrument registry — USD conversion rules and point-value multipliers."""

import os

import numpy as np
import pandas as pd
import pytest

from app.processing.daily_pnl import process_backtest
from app.processing.eod import load_eod_prices, load_usd_conversion
from app.processing.instruments import INSTRUMENTS, get_multiplier, normalise_symbol

DATES = pd.bdate_range("2020-01-02", "2020-03-31")
PRICES = {
    "NZDUSD": 0.65, "USDJPY": 110.0, "USDCHF": 0.95, "GBPUSD": 1.30, "XAGUSD": 18.0,
    "AUDNZD": 1.05, "NZDJPY": 72.0, "EURCHF": 1.08, "EURGBP": 0.85, "XAUXAG": 85.0,
    "ESAUSD": 3200.0, "RTYUSD": 1600.0,
}


def _write_eod(path, pair, level):
    rng = np.random.default_rng(abs(hash(pair)) % 2**32)
    px = level * (1 + np.cumsum(rng.normal(0, 0.002, len(DATES))))
    with open(os.path.join(path, f"{pair}_EOD.csv"), "w") as f:
        f.write("Date,Price\n")
        for dt, p in zip(DATES, px):
            f.write(f"{dt.strftime('%d/%m/%Y')},{p:.6f}\n")


@pytest.fixture
def inst_eod_dir(tmp_dir):
    for pair, level in PRICES.items():
        _write_eod(tmp_dir, pair, level)
    return tmp_dir


def _write_trades(path, instrument, entry=100.0, exit_=101.0, qty=2):
    fpath = os.path.join(path, f"BT_{instrument.strip('$')}.csv")
    with open(fpath, "w") as f:
        f.write("Instrument,Market.pos.,Entry.price,Exit.price,Entry.time,Exit.time,Quantity\n")
        f.write(f"{instrument},Long,{entry},{exit_},06/01/2020 10:00,06/01/2020 15:00,{qty}\n")
    return fpath


@pytest.mark.parametrize("symbol, conv_pair, op", [
    ("AUDNZD", "NZDUSD", "mul"),
    ("NZDJPY", "USDJPY", "div"),
    ("EURCHF", "USDCHF", "div"),
    ("EURGBP", "GBPUSD", "mul"),
    ("XAUXAG", "XAGUSD", "mul"),
])
def test_conversion_rules(inst_eod_dir, symbol, conv_pair, op):
    conv = load_usd_conversion(symbol, inst_eod_dir)
    rate = load_eod_prices(conv_pair, inst_eod_dir)
    expected = rate.values if op == "mul" else 1.0 / rate.values
    np.testing.assert_allclose(conv.values, expected)
    assert (conv.index.hour == 17).all()


@pytest.mark.parametrize("symbol", ["ESAUSD", "RTYUSD", "XAGUSD"])
def test_usd_quoted_have_unit_conversion(inst_eod_dir, symbol):
    conv = load_usd_conversion(symbol, inst_eod_dir)
    assert (conv.values == 1.0).all()


def test_missing_conversion_file_names_required_pair(inst_eod_dir):
    os.remove(os.path.join(inst_eod_dir, "NZDUSD_EOD.csv"))
    with pytest.raises(FileNotFoundError, match="NZDUSD"):
        load_usd_conversion("AUDNZD", inst_eod_dir)


def test_multipliers():
    assert get_multiplier("$ESAUSD") == 50
    assert get_multiplier("RTYUSD") == 50
    assert get_multiplier("$XAGUSD") == 1
    assert get_multiplier("EURUSD") == 1  # unregistered


def test_normalise_symbol():
    assert normalise_symbol(" $esausd ") == "ESAUSD"


def test_registry_has_requested_instruments():
    for sym in ["AUDNZD", "NZDJPY", "EURCHF", "EURGBP", "ESAUSD", "RTYUSD", "XAGUSD", "XAUXAG"]:
        assert sym in INSTRUMENTS


def _run(path, eod, instrument, **kw):
    args = dict(aum=1e8, strategy="T", timeframe="60 min", is_future=False, pt_value=1.0,
                timezone="Europe/London", output_path=path)
    args.update(kw)
    return process_backtest(filepath=_write_trades(path, instrument), eod_path=eod, **args)


def test_esa_pnl_uses_point_value(inst_eod_dir, tmp_dir):
    res = _run(tmp_dir, inst_eod_dir, "$ESAUSD")
    # 1 point * 2 contracts * $50
    assert res["pnl_daily"].sum() == pytest.approx(100.0)
    assert res["multiplier"] == 50


def test_override_point_value_wins(inst_eod_dir, tmp_dir):
    res = _run(tmp_dir, inst_eod_dir, "$ESAUSD", is_future=True, pt_value=5.0)
    assert res["pnl_daily"].sum() == pytest.approx(10.0)


def test_nzdjpy_pnl_divided_by_usdjpy(inst_eod_dir, tmp_dir):
    res = _run(tmp_dir, inst_eod_dir, "$NZDJPY")
    usdjpy = load_eod_prices("USDJPY", inst_eod_dir)
    rate = usdjpy.loc[usdjpy.index.normalize() == pd.Timestamp("2020-01-06", tz="Europe/London")].iloc[0]
    assert res["pnl_daily"].sum() == pytest.approx(2.0 / rate)


def test_xauxag_pnl_multiplied_by_silver(inst_eod_dir, tmp_dir):
    res = _run(tmp_dir, inst_eod_dir, "$XAUXAG")
    xag = load_eod_prices("XAGUSD", inst_eod_dir)
    rate = xag.loc[xag.index.normalize() == pd.Timestamp("2020-01-06", tz="Europe/London")].iloc[0]
    assert res["pnl_daily"].sum() == pytest.approx(2.0 * rate)
