"""Tests for app.processing.portfolio — portfolio combination."""

import os

import numpy as np
import pandas as pd
import pytest

from app.processing.portfolio import (
    parse_pnl_column_name,
    load_daily_pnl_file,
    combine_portfolio,
)


class TestParsePnlColumnName:
    def test_pipe_separated(self):
        meta = parse_pnl_column_name("DailyPnl(USD)|EURUSD|CIT1|240 min|Long")
        assert meta["ccy_pair"] == "EURUSD"
        assert meta["strategy"] == "CIT1"
        assert meta["timeframe"] == "240 min"
        assert meta["direction"] == "Long"

    def test_dot_separated_from_csv_roundtrip(self):
        # When CSV is read/written, pandas may replace special chars with dots
        # "DailyPnl(USD)|GBPUSD|CIT2|60 min|Short" → dots replace pipes
        meta = parse_pnl_column_name("DailyPnl(USD)|GBPUSD|CIT2|60 min|Short")
        assert meta["ccy_pair"] == "GBPUSD"
        assert meta["strategy"] == "CIT2"

    def test_short_string_returns_empty_fields(self):
        meta = parse_pnl_column_name("short")
        assert meta["ccy_pair"] == ""


class TestLoadDailyPnlFile:
    def test_loads_series_and_meta(self, sample_pnl_daily_csvs):
        series, meta = load_daily_pnl_file(sample_pnl_daily_csvs[0])
        assert len(series) == 200
        assert meta["ccy_pair"] == "EURUSD"
        assert meta["strategy"] == "CIT1"

    def test_index_is_datetime(self, sample_pnl_daily_csvs):
        series, _ = load_daily_pnl_file(sample_pnl_daily_csvs[0])
        assert isinstance(series.index, pd.DatetimeIndex)

    def test_no_nans(self, sample_pnl_daily_csvs):
        series, _ = load_daily_pnl_file(sample_pnl_daily_csvs[0])
        assert not series.isna().any()


class TestCombinePortfolio:
    def test_sum_mode(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs,
            aum=1e8,
            report_name="TestPtf",
            rel_returns=False,
            output_path=tmp_dir,
        )
        # Portfolio should be sum of strategies
        expected_sum = result["strategy_returns"].sum(axis=1)
        pd.testing.assert_series_equal(result["portfolio"], expected_sum,
                                       check_names=False, atol=1e-10)

    def test_average_mode(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs,
            aum=1e8,
            report_name="TestPtf",
            rel_returns=True,
            output_path=tmp_dir,
        )
        expected_mean = result["strategy_returns"].mean(axis=1)
        pd.testing.assert_series_equal(result["portfolio"], expected_mean,
                                       check_names=False, atol=1e-10)

    def test_ptf_of_ptf_sets_aum_to_one(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs,
            aum=1e8,
            report_name="TestPtf",
            ptf_of_ptf=True,
            output_path=tmp_dir,
        )
        # With ptf_of_ptf, AUM is 1.0 so values should be large (raw PnL)
        assert abs(result["portfolio"].sum()) > 1

    def test_date_range_filter(self, sample_pnl_daily_csvs, tmp_dir):
        result_full = combine_portfolio(
            filepaths=sample_pnl_daily_csvs, aum=1e8,
            report_name="Full", output_path=tmp_dir,
        )
        result_trimmed = combine_portfolio(
            filepaths=sample_pnl_daily_csvs, aum=1e8,
            report_name="Trimmed",
            start_date="01/03/2020", end_date="30/06/2020",
            output_path=tmp_dir,
        )
        assert len(result_trimmed["portfolio"]) < len(result_full["portfolio"])

    def test_output_files_created(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs, aum=1e8,
            report_name="TestOut", output_path=tmp_dir,
        )
        assert os.path.exists(result["files"]["daily"])
        assert os.path.exists(result["files"]["monthly"])
        assert os.path.exists(result["files"]["only_daily"])

    def test_monthly_aggregation(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs, aum=1e8,
            report_name="TestMon", output_path=tmp_dir,
        )
        # Monthly should have fewer rows than daily
        assert len(result["ptf_monthly"]) < len(result["ptf_daily"])
        # Monthly sum should roughly equal daily sum
        np.testing.assert_almost_equal(
            result["ptf_monthly"]["Portfolio"].sum(),
            result["ptf_daily"]["Portfolio"].sum(),
            decimal=5,
        )

    def test_metadata_extracted(self, sample_pnl_daily_csvs, tmp_dir):
        result = combine_portfolio(
            filepaths=sample_pnl_daily_csvs, aum=1e8,
            report_name="MetaTest", output_path=tmp_dir,
        )
        assert len(result["metadata"]) == 2
        assert "EURUSD" in result["metadata"]["ccy_pair"].values
        assert "GBPUSD" in result["metadata"]["ccy_pair"].values
