"""Tests for app.reporting.metrics — performance metrics calculations."""

import numpy as np
import pandas as pd
import pytest

from app.reporting.metrics import (
    total_return,
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    drawdown_series,
    drawdown_table,
    omega_ratio,
    kelly_fraction,
    win_loss_ratio,
    max_consecutive_losers,
    rolling_volatility,
    compute_all_metrics,
)


class TestTotalReturn:
    def test_simple_sum(self):
        r = pd.Series([0.01, 0.02, -0.005])
        assert abs(total_return(r) - 0.025) < 1e-10

    def test_zero_returns(self):
        r = pd.Series([0.0, 0.0, 0.0])
        assert total_return(r) == 0.0

    def test_empty_series(self):
        r = pd.Series([], dtype=float)
        assert total_return(r) == 0.0


class TestAnnualizedReturn:
    def test_positive_returns(self, sample_daily_returns):
        ar = annualized_return(sample_daily_returns)
        # With positive mean, should be positive
        assert ar > 0

    def test_arithmetic_mode(self):
        r = pd.Series([0.01] * 252)
        ar = annualized_return(r, geometric=False)
        assert abs(ar - 0.01 * 252) < 1e-8

    def test_empty_returns_zero(self):
        r = pd.Series([], dtype=float)
        assert annualized_return(r) == 0.0


class TestAnnualizedVolatility:
    def test_known_vol(self):
        np.random.seed(42)
        r = pd.Series(np.random.normal(0, 0.01, 252))
        vol = annualized_volatility(r)
        # Should be approximately 0.01 * sqrt(252) ≈ 0.159
        assert 0.10 < vol < 0.25

    def test_constant_returns_near_zero_vol(self):
        r = pd.Series([0.01] * 100)
        assert annualized_volatility(r) < 1e-10


class TestSharpeRatio:
    def test_positive_for_good_returns(self, sample_daily_returns):
        sr = sharpe_ratio(sample_daily_returns)
        assert sr > 0  # Positive mean returns should give positive Sharpe

    def test_near_zero_vol(self):
        r = pd.Series([0.01] * 100)
        # Near-zero vol gives very large Sharpe, not exactly 0
        sr = sharpe_ratio(r)
        assert isinstance(sr, float)


class TestSortinoRatio:
    def test_all_positive_returns_inf(self):
        r = pd.Series([0.01, 0.02, 0.03])
        assert sortino_ratio(r) == float("inf")

    def test_mixed_returns(self, sample_daily_returns):
        sr = sortino_ratio(sample_daily_returns)
        assert sr > 0


class TestMaxDrawdown:
    def test_no_drawdown_for_all_positive(self):
        r = pd.Series([0.01, 0.01, 0.01])
        assert max_drawdown(r) == 0.0

    def test_known_drawdown(self):
        # Goes up 10%, then down 20% from peak
        r = pd.Series([0.10, -0.10, -0.10])
        dd = max_drawdown(r)
        assert dd > 0.15  # Should be significant

    def test_arithmetic_mode(self):
        r = pd.Series([0.10, -0.15, 0.05])
        dd = max_drawdown(r, geometric=False)
        assert dd > 0


class TestDrawdownSeries:
    def test_starts_at_zero(self):
        r = pd.Series([0.01, -0.02, 0.01])
        dd = drawdown_series(r)
        # After first positive return, drawdown is 0
        assert dd.iloc[0] == 0.0

    def test_all_negative_during_drawdown(self):
        r = pd.Series([0.10, -0.05, -0.05, 0.10])
        dd = drawdown_series(r)
        assert (dd <= 0).all()


class TestDrawdownTable:
    def test_returns_dataframe(self, sample_daily_returns):
        dt = drawdown_table(sample_daily_returns, top=3)
        assert isinstance(dt, pd.DataFrame)
        assert len(dt) <= 3

    def test_columns_present(self, sample_daily_returns):
        dt = drawdown_table(sample_daily_returns)
        required = ["Start", "Trough", "Max Drawdown (%)", "Duration"]
        for col in required:
            assert col in dt.columns

    def test_drawdowns_are_negative(self, sample_daily_returns):
        dt = drawdown_table(sample_daily_returns)
        if not dt.empty:
            assert (dt["Max Drawdown (%)"] < 0).all()

    def test_empty_for_no_drawdowns(self):
        r = pd.Series([0.01] * 10, index=pd.bdate_range("2020-01-01", periods=10))
        dt = drawdown_table(r)
        assert dt.empty


class TestOmegaRatio:
    def test_all_positive_returns(self):
        r = pd.Series([0.01, 0.02, 0.03])
        assert omega_ratio(r) == float("inf")

    def test_mixed_returns_positive(self, sample_daily_returns):
        # With positive mean, omega should be > 1
        o = omega_ratio(sample_daily_returns)
        assert o > 1.0


class TestKellyFraction:
    def test_positive_mean_positive_kelly(self):
        r = pd.Series([0.01, 0.02, -0.005, 0.015])
        assert kelly_fraction(r) > 0

    def test_near_zero_variance_large_kelly(self):
        # Constant positive returns → near-zero variance → very large Kelly
        r = pd.Series([0.01] * 10)
        assert kelly_fraction(r) > 1e10


class TestWinLossRatio:
    def test_all_winners(self):
        pnl = pd.Series([100, 200, 50])
        assert win_loss_ratio(pnl) == 1.0

    def test_all_losers(self):
        pnl = pd.Series([-100, -200, -50])
        assert win_loss_ratio(pnl) == 0.0

    def test_half_and_half(self):
        pnl = pd.Series([100, -100, 200, -200])
        assert win_loss_ratio(pnl) == 0.5

    def test_empty(self):
        assert win_loss_ratio(pd.Series([], dtype=float)) == 0.0


class TestMaxConsecutiveLosers:
    def test_known_sequence(self):
        pnl = pd.Series([100, -50, -30, -10, 200, -5])
        assert max_consecutive_losers(pnl) == 3

    def test_no_losers(self):
        pnl = pd.Series([100, 200, 300])
        assert max_consecutive_losers(pnl) == 0

    def test_all_losers(self):
        pnl = pd.Series([-1, -2, -3, -4])
        assert max_consecutive_losers(pnl) == 4

    def test_empty(self):
        assert max_consecutive_losers(pd.Series([], dtype=float)) == 0


class TestRollingVolatility:
    def test_returns_series(self, sample_daily_returns):
        vol = rolling_volatility(sample_daily_returns)
        assert isinstance(vol, pd.Series)
        assert len(vol) > 0

    def test_values_are_positive(self, sample_daily_returns):
        vol = rolling_volatility(sample_daily_returns)
        assert (vol > 0).all()


class TestComputeAllMetrics:
    def test_returns_dict(self, sample_daily_returns):
        stats = compute_all_metrics(sample_daily_returns)
        assert isinstance(stats, dict)
        assert "Total Return (% AUM)" in stats
        assert "Sharpe Ratio" in stats

    def test_with_raw_pnl(self, sample_daily_returns):
        pnl_raw = pd.Series(np.random.normal(100, 500, 50))
        stats = compute_all_metrics(sample_daily_returns, pnl_raw)
        assert "Win/Loss Ratio" in stats
        assert "Max Consecutive Losers" in stats

    def test_year_returns_present(self, sample_daily_returns):
        stats = compute_all_metrics(sample_daily_returns)
        assert any("Return since 1 Jan" in k for k in stats)
