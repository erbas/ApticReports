"""Chart generation using matplotlib — matching the R report visualizations."""

import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

from .metrics import drawdown_series, rolling_volatility


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _fig_to_bytes(fig: plt.Figure) -> bytes:
    """Convert matplotlib figure to PNG bytes (for PDF embedding)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _format_date_axis(ax):
    """Apply consistent date formatting to x-axis."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def performance_summary(daily_returns: pd.Series, title: str = "") -> str:
    """Three-panel chart: cumulative returns, daily returns, drawdowns.

    Mirrors R's charts.PerformanceSummary().
    Returns base64 PNG.
    """
    fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1.5]})

    dates = daily_returns.index
    cum = daily_returns.cumsum() * 100

    # Cumulative returns
    axes[0].plot(dates, cum, color="#2E86AB", linewidth=1.2)
    axes[0].fill_between(dates, 0, cum, alpha=0.15, color="#2E86AB")
    axes[0].set_ylabel("Cumulative Return (% AUM)")
    axes[0].axhline(0, color="gray", linewidth=0.5)
    if title:
        axes[0].set_title(title, fontsize=12, fontweight="bold")

    # Daily returns bar
    colors = ["#2E86AB" if v >= 0 else "#E84855" for v in daily_returns.values]
    axes[1].bar(dates, daily_returns.values * 100, color=colors, width=1.5, linewidth=0)
    axes[1].set_ylabel("Daily (%)")
    axes[1].axhline(0, color="gray", linewidth=0.5)

    # Drawdowns
    dd = drawdown_series(daily_returns, geometric=False)
    axes[2].fill_between(dates, 0, dd.values * 100, color="#E84855", alpha=0.5)
    axes[2].plot(dates, dd.values * 100, color="#E84855", linewidth=0.8)
    axes[2].set_ylabel("Drawdown (%)")

    _format_date_axis(axes[2])
    fig.tight_layout()
    return _fig_to_base64(fig)


def monthly_returns_bar(daily_returns: pd.Series) -> str:
    """Monthly returns bar chart. Returns base64 PNG."""
    monthly = daily_returns.resample("ME").sum() * 100
    fig, ax = plt.subplots(figsize=(10, 3))
    colors = ["#2E86AB" if v >= 0 else "#E84855" for v in monthly.values]
    ax.bar(monthly.index, monthly.values, width=25, color=colors, linewidth=0)
    ax.set_ylabel("Monthly Return (% AUM)")
    ax.set_title("Monthly Returns")
    ax.axhline(0, color="gray", linewidth=0.5)
    _format_date_axis(ax)
    fig.tight_layout()
    return _fig_to_base64(fig)


def returns_histogram(pnl_raw: pd.Series, aum: float = 1.0) -> str:
    """Histogram of trade returns with fitted normal. Returns base64 PNG."""
    data = (pnl_raw / aum * 100).dropna()
    if len(data) == 0:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        return _fig_to_base64(fig)

    fig, ax = plt.subplots(figsize=(5, 3))
    n, bins, patches = ax.hist(data, bins=25, density=False, color="gray", alpha=0.7,
                               edgecolor="white")
    # Scale to percentage of trades
    total = len(data)
    for p in patches:
        p.set_height(p.get_height() / total * 100)
    ax.set_ylim(0, max(n) / total * 100 * 1.1)

    # Fitted normal
    x = np.linspace(data.min(), data.max(), 200)
    from scipy.stats import norm
    mu, sigma = data.mean(), data.std()
    y = norm.pdf(x, mu, sigma)
    y_scaled = y * (bins[1] - bins[0]) * 100  # Scale to match histogram
    ax.plot(x, y_scaled, "b-", linewidth=2)

    ax.set_xlabel("Returns (% AUM)")
    ax.set_ylabel("% Trades")
    ax.set_title("Histogram of Trade Returns")
    fig.tight_layout()
    return _fig_to_base64(fig)


def rolling_vol_chart(daily_returns: pd.Series) -> str:
    """Rolling volatility chart. Returns base64 PNG."""
    window = 252 if len(daily_returns) > 500 else 63
    vol = rolling_volatility(daily_returns, window)
    if vol.empty:
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center")
        return _fig_to_base64(fig)

    months = round(12 * window / 252)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot(vol.index, vol.values * 100, color="#2E86AB", linewidth=1.5)
    ax.set_ylabel("Volatility (%)")
    ax.set_title(f"Rolling {months}-Month Volatility")
    _format_date_axis(ax)
    fig.tight_layout()
    return _fig_to_base64(fig)


def portfolio_strategies_chart(portfolio: pd.Series, strategy_returns: pd.DataFrame,
                               rel_returns: bool = False) -> str:
    """Cumulative returns of portfolio vs individual strategies. Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=(10, 4))

    # Portfolio line (thick)
    cum_ptf = portfolio.cumsum() * 100
    ax.plot(cum_ptf.index, cum_ptf.values, color="black", linewidth=2.5, label="Portfolio")

    # Strategy lines (thinner, colored)
    colors = plt.cm.Set2(np.linspace(0, 1, strategy_returns.shape[1]))
    for i, col in enumerate(strategy_returns.columns):
        cum_s = strategy_returns[col].cumsum() * 100
        ax.plot(cum_s.index, cum_s.values, color=colors[i], linewidth=1, label=col, alpha=0.7)

    title = "Average Portfolio and Strategies" if rel_returns else "Portfolio and Strategies"
    ax.set_title(title)
    ax.set_ylabel("Cumulative Return (% AUM)")
    ax.legend(fontsize=7, ncol=3, loc="best")
    ax.axhline(0, color="gray", linewidth=0.5)
    _format_date_axis(ax)
    fig.tight_layout()
    return _fig_to_base64(fig)


def correlation_heatmap(strategy_returns: pd.DataFrame) -> str:
    """Correlation heatmap of strategies. Returns base64 PNG."""
    if strategy_returns.shape[1] < 2:
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.text(0.5, 0.5, "Need 2+ strategies", ha="center", va="center")
        return _fig_to_base64(fig)

    corr = strategy_returns.corr()
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    fig.colorbar(im, ax=ax, shrink=0.8)

    n = len(corr)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    labels = [str(i + 1) for i in range(n)]
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)

    # Annotate with values
    if n <= 10:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)

    ax.set_title("Strategy Correlations")
    fig.tight_layout()
    return _fig_to_base64(fig)
