"""Tests for app.reporting.pdf_report — PDF generation produces valid files."""

import os

import numpy as np
import pandas as pd
import pytest

from app.reporting.pdf_report import generate_backtest_pdf, generate_portfolio_pdf


class TestGenerateBacktestPdf:
    def test_creates_pdf_file(self, sample_daily_returns, tmp_dir):
        pnl_raw = pd.Series(np.random.normal(100, 500, 50),
                            index=sample_daily_returns.index[:50])
        path = generate_backtest_pdf(
            daily_returns=sample_daily_returns,
            pnl_raw=pnl_raw,
            aum=1e8,
            strategy="CIT1",
            ccy_pair="EURUSD",
            timeframe="240 min",
            strat_dir="Long",
            filestem="test_backtest",
            output_path=tmp_dir,
        )
        assert os.path.exists(path)
        assert path.endswith(".pdf")

    def test_pdf_is_not_empty(self, sample_daily_returns, tmp_dir):
        pnl_raw = pd.Series(np.random.normal(100, 500, 50),
                            index=sample_daily_returns.index[:50])
        path = generate_backtest_pdf(
            daily_returns=sample_daily_returns,
            pnl_raw=pnl_raw,
            aum=1e8,
            strategy="CIT1",
            ccy_pair="EURUSD",
            timeframe="240 min",
            strat_dir="Long",
            filestem="test_bt2",
            output_path=tmp_dir,
        )
        assert os.path.getsize(path) > 1000  # Should be a substantial PDF

    def test_pdf_starts_with_magic_bytes(self, sample_daily_returns, tmp_dir):
        pnl_raw = pd.Series(np.random.normal(100, 500, 50),
                            index=sample_daily_returns.index[:50])
        path = generate_backtest_pdf(
            daily_returns=sample_daily_returns,
            pnl_raw=pnl_raw,
            aum=1e8,
            strategy="CIT1",
            ccy_pair="EURUSD",
            timeframe="240 min",
            strat_dir="Long",
            filestem="test_bt3",
            output_path=tmp_dir,
        )
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"


class TestGeneratePortfolioPdf:
    def test_creates_pdf_file(self, tmp_dir):
        np.random.seed(42)
        dates = pd.bdate_range("2020-01-01", periods=200, tz="Europe/London")
        portfolio = pd.Series(np.random.normal(0.001, 0.005, 200), index=dates, name="Portfolio")
        ptf_daily = pd.DataFrame({"Portfolio": portfolio})
        strategy_returns = pd.DataFrame({
            "EURUSD": np.random.normal(0.001, 0.005, 200),
            "GBPUSD": np.random.normal(0.0005, 0.003, 200),
        }, index=dates)
        metadata = pd.DataFrame({
            "ccy_pair": ["EURUSD", "GBPUSD"],
            "strategy": ["CIT1", "CIT2"],
            "timeframe": ["240 min", "60 min"],
            "direction": ["Long", "Short"],
        })

        path = generate_portfolio_pdf(
            ptf_daily=ptf_daily,
            portfolio=portfolio,
            strategy_returns=strategy_returns,
            metadata=metadata,
            report_name="TestPortfolio",
            rel_returns=False,
            output_path=tmp_dir,
        )
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"
