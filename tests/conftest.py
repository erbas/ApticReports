"""Shared test fixtures — synthetic data for all test modules."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def tmp_dir():
    """Temporary directory that gets cleaned up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def eod_dir(tmp_dir):
    """Temp directory populated with sample EOD price CSVs."""
    # EURUSD EOD — business days for 2 years
    dates = pd.bdate_range("2020-01-02", "2021-12-31")
    np.random.seed(42)
    prices = 1.10 + np.cumsum(np.random.normal(0, 0.002, len(dates)))

    # Format matching R output: header, skip row, dd/mm/yyyy
    path = os.path.join(tmp_dir, "EURUSD_EOD.csv")
    with open(path, "w") as f:
        f.write("Date,Price\n")  # real header
        f.write("ignore,ignore\n")  # row that gets skipped (skiprows=1 in loader)
        for dt, px in zip(dates, prices):
            f.write(f"{dt.strftime('%d/%m/%Y')},{px:.5f}\n")

    # GBPUSD EOD for currency conversion tests
    prices_gbp = 1.30 + np.cumsum(np.random.normal(0, 0.001, len(dates)))
    path_gbp = os.path.join(tmp_dir, "GBPUSD_EOD.csv")
    with open(path_gbp, "w") as f:
        f.write("Date,Price\n")
        f.write("ignore,ignore\n")
        for dt, px in zip(dates, prices_gbp):
            f.write(f"{dt.strftime('%d/%m/%Y')},{px:.5f}\n")

    # USDJPY EOD (for testing inverted conversion)
    prices_jpy = 110.0 + np.cumsum(np.random.normal(0, 0.1, len(dates)))
    path_jpy = os.path.join(tmp_dir, "USDJPY_EOD.csv")
    with open(path_jpy, "w") as f:
        f.write("Date,Price\n")
        f.write("ignore,ignore\n")
        for dt, px in zip(dates, prices_jpy):
            f.write(f"{dt.strftime('%d/%m/%Y')},{px:.5f}\n")

    return tmp_dir


@pytest.fixture
def sample_trades_csv(tmp_dir):
    """Create a sample NinjaTrader trade CSV file with known trades."""
    path = os.path.join(tmp_dir, "BT_EURUSD_240_Buys.csv")
    with open(path, "w") as f:
        f.write("Instrument,Market.pos.,Entry.price,Exit.price,Entry.time,Exit.time,Quantity,Entry.name\n")
        # Trade 1: same-day long (no splitting needed)
        f.write("EURUSD,Long,1.1000,1.1050,02/01/2020 10:00,02/01/2020 15:00,100000,CIT1_L_01\n")
        # Trade 2: multi-day long (spans 2 days, needs splitting)
        f.write("EURUSD,Long,1.1050,1.1100,02/01/2020 16:00,03/01/2020 12:00,100000,CIT1_L_02\n")
        # Trade 3: short trade, same day
        f.write("EURUSD,Short,1.1100,1.1060,06/01/2020 09:00,06/01/2020 14:00,50000,CIT1_S_03\n")
        # Trade 4: multi-day spanning 3 days (entry Mon, exit Wed)
        f.write("EURUSD,Long,1.1060,1.1120,06/01/2020 16:00,08/01/2020 11:00,100000,CIT1_L_04\n")
    return path


@pytest.fixture
def sample_daily_returns():
    """Synthetic daily returns for metric testing."""
    np.random.seed(123)
    dates = pd.bdate_range("2020-01-02", periods=500, tz="Europe/London")
    returns = pd.Series(np.random.normal(0.0003, 0.005, len(dates)), index=dates)
    return returns


@pytest.fixture
def sample_pnl_daily_csvs(tmp_dir):
    """Create two sample *_pnl_daily.csv files for portfolio testing."""
    np.random.seed(99)
    dates = pd.bdate_range("2020-01-02", periods=200)

    paths = []
    for i, (pair, strat) in enumerate([("EURUSD", "CIT1"), ("GBPUSD", "CIT2")]):
        pnl = np.random.normal(100, 500, len(dates))
        path = os.path.join(tmp_dir, f"BT_{pair}_240_{strat}_pnl_daily.csv")
        with open(path, "w") as f:
            col = f"DailyPnl(USD)|{pair}|{strat}|240 min|Long"
            f.write(f"Date,{col}\n")
            for dt, val in zip(dates, pnl):
                f.write(f"{dt.strftime('%Y-%m-%d')},{val:.2f}\n")
        paths.append(path)

    return paths
