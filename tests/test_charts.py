"""Tests for app.reporting.charts — chart generation produces valid base64 PNGs."""

import base64

import numpy as np
import pandas as pd
import pytest

from app.reporting.charts import (
    performance_summary,
    monthly_returns_bar,
    rolling_vol_chart,
    portfolio_strategies_chart,
    correlation_heatmap,
)


def _is_valid_png_base64(b64: str) -> bool:
    """Check that base64 string decodes to valid PNG."""
    try:
        data = base64.b64decode(b64)
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    except Exception:
        return False


class TestPerformanceSummary:
    def test_returns_valid_png(self, sample_daily_returns):
        b64 = performance_summary(sample_daily_returns, "Test")
        assert _is_valid_png_base64(b64)

    def test_with_title(self, sample_daily_returns):
        b64 = performance_summary(sample_daily_returns, "My Strategy")
        assert len(b64) > 1000  # Should produce a substantial image

    def test_short_series(self):
        r = pd.Series([0.01, -0.005, 0.02],
                       index=pd.bdate_range("2020-01-01", periods=3, tz="Europe/London"))
        b64 = performance_summary(r)
        assert _is_valid_png_base64(b64)


class TestMonthlyReturnsBar:
    def test_returns_valid_png(self, sample_daily_returns):
        b64 = monthly_returns_bar(sample_daily_returns)
        assert _is_valid_png_base64(b64)


class TestRollingVolChart:
    def test_returns_valid_png(self, sample_daily_returns):
        b64 = rolling_vol_chart(sample_daily_returns)
        assert _is_valid_png_base64(b64)

    def test_short_series_still_works(self):
        r = pd.Series(np.random.normal(0, 0.01, 30),
                       index=pd.bdate_range("2020-01-01", periods=30, tz="Europe/London"))
        b64 = rolling_vol_chart(r)
        assert _is_valid_png_base64(b64)


class TestPortfolioStrategiesChart:
    def test_returns_valid_png(self):
        dates = pd.bdate_range("2020-01-01", periods=100)
        np.random.seed(42)
        ptf = pd.Series(np.random.normal(0.001, 0.005, 100), index=dates, name="Portfolio")
        strats = pd.DataFrame({
            "Strat1": np.random.normal(0.001, 0.005, 100),
            "Strat2": np.random.normal(0.0005, 0.003, 100),
        }, index=dates)
        b64 = portfolio_strategies_chart(ptf, strats)
        assert _is_valid_png_base64(b64)


class TestCorrelationHeatmap:
    def test_returns_valid_png(self):
        np.random.seed(42)
        dates = pd.bdate_range("2020-01-01", periods=100)
        strats = pd.DataFrame({
            "A": np.random.normal(0, 0.01, 100),
            "B": np.random.normal(0, 0.01, 100),
            "C": np.random.normal(0, 0.01, 100),
        }, index=dates)
        b64 = correlation_heatmap(strats)
        assert _is_valid_png_base64(b64)

    def test_single_strategy_handles_gracefully(self):
        dates = pd.bdate_range("2020-01-01", periods=50)
        strats = pd.DataFrame({"A": np.random.normal(0, 0.01, 50)}, index=dates)
        b64 = correlation_heatmap(strats)
        assert _is_valid_png_base64(b64)  # Should show "Need 2+ strategies"
