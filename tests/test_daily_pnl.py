"""Tests for app.processing.daily_pnl — the core trade splitting and PnL calculation."""

import os

import numpy as np
import pandas as pd
import pytest

from app.processing.daily_pnl import make_daily_pnl, process_backtest
from app.processing.trades import load_ninja_trades
from app.processing.eod import load_eod_prices, load_usd_conversion


@pytest.fixture
def backtest_inputs(sample_trades_csv, eod_dir):
    """Load all inputs needed for make_daily_pnl."""
    trades = load_ninja_trades(sample_trades_csv)
    eod = load_eod_prices("EURUSD", eod_dir)
    conv = load_usd_conversion("EURUSD", eod_dir, pnl_ccy="USD")
    return trades, eod, conv


class TestMakeDailyPnl:
    def test_returns_all_keys(self, backtest_inputs):
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        assert "trades" in result
        assert "pnl_daily" in result
        assert "pnl_raw" in result
        assert "discrepancies" in result

    def test_same_day_trade_not_split(self, backtest_inputs):
        """Trade 1 and Trade 3 are same-day — should have SplitID=0 (unsplit)."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        all_trades = result["trades"]

        # Trade 1 (same-day long)
        t1 = all_trades[all_trades["TradeID"] == 1]
        assert len(t1) == 1
        assert t1.iloc[0]["SplitID"] == 0

    def test_multi_day_trade_is_split(self, backtest_inputs):
        """Trade 2 spans 2 days — should be split into 2 sub-trades."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        all_trades = result["trades"]

        t2 = all_trades[all_trades["TradeID"] == 2]
        assert len(t2) >= 2, f"Expected trade 2 split into >=2 parts, got {len(t2)}"

    def test_three_day_trade_split_into_three(self, backtest_inputs):
        """Trade 4 spans Mon-Wed (3 days) — should produce 3 sub-trades."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        all_trades = result["trades"]

        t4 = all_trades[all_trades["TradeID"] == 4]
        # Mon entry → Mon EOD, Mon EOD → Tue EOD, Tue EOD → Wed exit = 3 parts
        assert len(t4) >= 3, f"Expected trade 4 split into >=3 parts, got {len(t4)}"

    def test_split_pnl_sums_match_raw(self, backtest_inputs):
        """Core invariant: sum of split PnL per trade must equal raw trade PnL."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        assert result["discrepancies"] == [], f"Discrepancies found: {result['discrepancies']}"

    def test_pnl_daily_has_values(self, backtest_inputs):
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        assert len(result["pnl_daily"]) > 0

    def test_pnl_raw_matches_trade_count(self, backtest_inputs):
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        assert len(result["pnl_raw"]) == len(trades)

    def test_long_trade_positive_pnl(self, backtest_inputs):
        """Trade 1: Long, entry=1.10, exit=1.105 → positive PnL."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        # Raw PnL for first trade
        assert result["pnl_raw"].iloc[0] > 0

    def test_short_trade_positive_pnl_on_price_drop(self, backtest_inputs):
        """Trade 3: Short, entry=1.11, exit=1.106 → positive PnL (price dropped)."""
        trades, eod, conv = backtest_inputs
        result = make_daily_pnl(trades, eod, conv, trade_tz="Europe/London")
        assert result["pnl_raw"].iloc[2] > 0

    def test_different_timezone_processing(self, sample_trades_csv, eod_dir):
        """Trades in Chicago timezone should still process correctly."""
        trades = load_ninja_trades(sample_trades_csv)
        eod = load_eod_prices("EURUSD", eod_dir)
        conv = load_usd_conversion("EURUSD", eod_dir, pnl_ccy="USD")
        # Should not raise — timezone conversion handles the offset
        result = make_daily_pnl(trades, eod, conv, trade_tz="America/Chicago")
        assert len(result["pnl_daily"]) > 0


class TestProcessBacktest:
    def test_full_pipeline(self, sample_trades_csv, eod_dir, tmp_dir):
        result = process_backtest(
            filepath=sample_trades_csv,
            eod_path=eod_dir,
            aum=1e8,
            strategy="CIT1",
            timeframe="240 min",
            is_future=False,
            pt_value=1.0,
            timezone="Europe/London",
            output_path=tmp_dir,
        )
        assert result["ccy_pair"] == "EURUSD"
        assert len(result["pnl_daily"]) > 0
        assert os.path.exists(result["files"]["daily"])
        assert os.path.exists(result["files"]["trades"])
        assert os.path.exists(result["files"]["raw"])

    def test_futures_multiplier(self, sample_trades_csv, eod_dir, tmp_dir):
        result_no_fut = process_backtest(
            filepath=sample_trades_csv, eod_path=eod_dir, aum=1e8,
            strategy="CIT1", timeframe="240 min", is_future=False,
            pt_value=1.0, timezone="Europe/London", output_path=tmp_dir,
        )
        result_fut = process_backtest(
            filepath=sample_trades_csv, eod_path=eod_dir, aum=1e8,
            strategy="CIT1", timeframe="240 min", is_future=True,
            pt_value=10.0, timezone="Europe/London", output_path=tmp_dir,
        )
        # Futures PnL should be 10x the non-futures PnL
        ratio = result_fut["pnl_daily"].sum() / result_no_fut["pnl_daily"].sum()
        assert abs(ratio - 10.0) < 0.01

    def test_daily_pnl_csv_has_metadata_header(self, sample_trades_csv, eod_dir, tmp_dir):
        result = process_backtest(
            filepath=sample_trades_csv, eod_path=eod_dir, aum=1e8,
            strategy="TEST", timeframe="60 min", is_future=False,
            pt_value=1.0, timezone="Europe/London", output_path=tmp_dir,
        )
        with open(result["files"]["daily"]) as f:
            header = f.readline()
        assert "DailyPnl(USD)" in header
        assert "EURUSD" in header
        assert "TEST" in header
