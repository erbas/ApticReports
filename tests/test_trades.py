"""Tests for app.processing.trades — NinjaTrader CSV loading and metadata extraction."""

import os

import pandas as pd
import pytest

from app.processing.trades import load_ninja_trades, extract_metadata


class TestLoadNinjaTrades:
    def test_loads_all_rows(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        assert len(df) == 4

    def test_has_required_columns(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        required = ["Instrument", "Market.pos.", "Entry.price", "Exit.price",
                     "Entry.time", "Exit.time", "Quantity", "Entry.name"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_prices_are_numeric(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        assert pd.to_numeric(df["Entry.price"], errors="coerce").notna().all()
        assert pd.to_numeric(df["Exit.price"], errors="coerce").notna().all()

    def test_space_separated_headers_normalised(self, tmp_dir):
        """Real NinjaTrader 8 exports use spaces, not dots."""
        path = os.path.join(tmp_dir, "nt8_export.csv")
        with open(path, "w") as f:
            f.write("Trade-#,Instrument,Account,Strategy,Market pos.,Quantity,Entry price,Exit price,Entry time,Exit time,Entry name,Exit name,Profit,Cum. profit,Commission,MAE,MFE,ETD,Bars,\n")
            f.write("1,$XAGUSD,Backtest,TestStrat,Long,100000,17.67,17.19,23/01/2020 12:15:00,28/02/2020 05:55:00,1_long,Sell,-0.027,0,0,0,0,0,156,\n")
        df = load_ninja_trades(path)
        assert "Entry.time" in df.columns
        assert "Exit.price" in df.columns
        assert "Market.pos." in df.columns
        assert len(df) == 1

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_ninja_trades("/nonexistent/path.csv")


class TestExtractMetadata:
    def test_strips_dollar_sign(self):
        df = pd.DataFrame({
            "Instrument": ["$XAUUSD"],
            "Market.pos.": ["Long"],
            "Entry.price": [1800],
            "Exit.price": [1810],
            "Entry.name": ["CIT1_L_01"],
        })
        meta = extract_metadata(df)
        assert meta["ccy_pair"] == "XAUUSD"

    def test_plain_instrument(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        meta = extract_metadata(df)
        assert meta["ccy_pair"] == "EURUSD"

    def test_strat_dir_from_market_pos(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        meta = extract_metadata(df)
        # 3 longs + 1 short → mode is "Long"
        assert meta["strat_dir"] == "Long"
