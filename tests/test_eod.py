"""Tests for app.processing.eod — EOD price loading, currency conversion, nearest EOD."""

import pandas as pd
import numpy as np
import pytest

from app.processing.eod import load_eod_prices, add_time_to_date, load_usd_conversion, get_nearest_eod


class TestLoadEodPrices:
    def test_loads_correct_shape(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        assert len(eod) > 400  # ~2 years of business days
        assert eod.name == "EURUSD"

    def test_index_is_tz_aware(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        assert eod.index.tz is not None
        assert str(eod.index.tz) == "Europe/London"

    def test_no_duplicate_dates(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        assert not eod.index.duplicated().any()

    def test_no_nan_values(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        assert not eod.isna().any()

    def test_missing_file_raises(self, eod_dir):
        with pytest.raises(FileNotFoundError):
            load_eod_prices("NONEXIST", eod_dir)

    def test_prices_are_numeric(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        assert eod.dtype == np.float64


class TestAddTimeToDate:
    def test_adds_hour_to_index(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        eod_hms = add_time_to_date(eod, eod_hour=17)
        # All times should be at 17:00
        hours = eod_hms.index.hour
        assert (hours == 17).all()

    def test_preserves_values(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        eod_hms = add_time_to_date(eod, eod_hour=17)
        np.testing.assert_array_equal(eod.values, eod_hms.values)

    def test_custom_hour(self, eod_dir):
        eod = load_eod_prices("EURUSD", eod_dir)
        eod_hms = add_time_to_date(eod, eod_hour=22)
        assert (eod_hms.index.hour == 22).all()


class TestGetNearestEod:
    def test_exact_match(self):
        times = pd.DatetimeIndex([
            "2020-01-02 17:00", "2020-01-03 17:00", "2020-01-06 17:00"
        ], tz="Europe/London")
        dt = pd.Timestamp("2020-01-03 17:00", tz="Europe/London")
        assert get_nearest_eod(dt, times, direction=1) == dt

    def test_forward_finds_next(self):
        times = pd.DatetimeIndex([
            "2020-01-02 17:00", "2020-01-03 17:00", "2020-01-06 17:00"
        ], tz="Europe/London")
        dt = pd.Timestamp("2020-01-02 20:00", tz="Europe/London")
        result = get_nearest_eod(dt, times, direction=1)
        assert result == pd.Timestamp("2020-01-03 17:00", tz="Europe/London")

    def test_backward_finds_previous(self):
        times = pd.DatetimeIndex([
            "2020-01-02 17:00", "2020-01-03 17:00", "2020-01-06 17:00"
        ], tz="Europe/London")
        dt = pd.Timestamp("2020-01-04 10:00", tz="Europe/London")
        result = get_nearest_eod(dt, times, direction=-1)
        assert result == pd.Timestamp("2020-01-03 17:00", tz="Europe/London")

    def test_past_last_eod_returns_last(self):
        times = pd.DatetimeIndex([
            "2020-01-02 17:00", "2020-01-03 17:00"
        ], tz="Europe/London")
        dt = pd.Timestamp("2020-01-10 10:00", tz="Europe/London")
        result = get_nearest_eod(dt, times, direction=1)
        assert result == times[-1]

    def test_before_first_eod_returns_first(self):
        times = pd.DatetimeIndex([
            "2020-01-02 17:00", "2020-01-03 17:00"
        ], tz="Europe/London")
        dt = pd.Timestamp("2019-12-31 10:00", tz="Europe/London")
        result = get_nearest_eod(dt, times, direction=-1)
        assert result == times[0]


class TestLoadUsdConversion:
    def test_quote_is_usd_returns_ones(self, eod_dir):
        # EURUSD: quote ccy is USD, so conv rate should be 1.0
        conv = load_usd_conversion("EURUSD", eod_dir, pnl_ccy="USD")
        assert (conv == 1.0).all()

    def test_base_is_usd_finds_pair(self, eod_dir):
        # USDJPY: base is USD, quote is JPY. For pnl_ccy=USD, need JPYUSD.
        # We have USDJPY_EOD.csv, so it should use 1/USDJPY.
        conv = load_usd_conversion("USDJPY", eod_dir, pnl_ccy="USD")
        assert len(conv) > 0
        # Rates should be approximately 1/110 ≈ 0.009
        assert 0.005 < conv.mean() < 0.02

    def test_conv_has_eod_hour_index(self, eod_dir):
        conv = load_usd_conversion("EURUSD", eod_dir, pnl_ccy="USD")
        assert (conv.index.hour == 17).all()

    def test_missing_pair_raises(self, eod_dir):
        with pytest.raises(FileNotFoundError):
            load_usd_conversion("XYZABC", eod_dir, pnl_ccy="USD")
