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

    def test_strat_dir_extracted(self, sample_trades_csv):
        df = load_ninja_trades(sample_trades_csv)
        meta = extract_metadata(df)
        # Column index 4 is "Exit.time" in our CSV
        assert meta["strat_dir"] != ""
