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


# ---------------------------------------------------------------------------
# Formal style helpers — using web app color palette
# ---------------------------------------------------------------------------
_BRAND_BLUE = "#2E86AB"
_BRAND_RED = "#E84855"
_DARK_GRAY = "#333333"
_LIGHT_GRAY = "#999999"
_FILL_BLUE = "#2E86AB"
_FILL_RED = "#E84855"
_MUTED_BG = "#F0F4F8"

def _apply_formal_style(ax, fontsize=9):
    """Apply formal styling to an axes."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_LIGHT_GRAY)
    ax.spines["bottom"].set_color(_LIGHT_GRAY)
    ax.spines["left"].set_linewidth(0.5)
    ax.spines["bottom"].set_linewidth(0.5)
    ax.tick_params(axis="both", which="both", labelsize=fontsize, colors=_DARK_GRAY,
                   length=2, width=0.5)
    ax.yaxis.label.set_size(fontsize)
    ax.xaxis.label.set_size(fontsize)
    ax.grid(True, axis="y", linewidth=0.3, color="#dddddd", alpha=0.7)
    ax.set_facecolor("white")


def _format_date_axis(ax, fontsize=9):
    """Apply consistent date formatting to x-axis."""
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha="center", fontsize=fontsize)


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


# ---------------------------------------------------------------------------
# Backtest-specific charts (formal style)
# ---------------------------------------------------------------------------

def performance_summary_formal(daily_returns: pd.Series, title: str = "",
                                figsize=(7.5, 4.2)) -> str:
    """Three-panel chart: cumulative returns, daily returns, drawdowns.
    Uses web app color palette. Returns base64 PNG."""
    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1.5]})
    fig.patch.set_facecolor("white")

    dates = daily_returns.index
    cum = daily_returns.cumsum() * 100

    # Cumulative returns
    axes[0].plot(dates, cum, color=_DARK_GRAY, linewidth=0.9)
    axes[0].fill_between(dates, 0, cum, alpha=0.15, color=_LIGHT_GRAY)
    axes[0].set_ylabel("Cumulative Return (% AUM)", fontsize=9, color=_DARK_GRAY)
    axes[0].axhline(0, color=_LIGHT_GRAY, linewidth=0.3)
    if title:
        axes[0].set_title(title, fontsize=10, fontweight="bold", color="black",
                          fontfamily="serif")
    _apply_formal_style(axes[0], fontsize=8)

    # Daily returns bar
    clrs = [_DARK_GRAY if v >= 0 else _LIGHT_GRAY for v in daily_returns.values]
    axes[1].bar(dates, daily_returns.values * 100, color=clrs, width=1.5, linewidth=0)
    axes[1].set_ylabel("Daily (%)", fontsize=9, color=_DARK_GRAY)
    axes[1].axhline(0, color=_LIGHT_GRAY, linewidth=0.3)
    _apply_formal_style(axes[1], fontsize=8)

    # Drawdowns
    dd = drawdown_series(daily_returns, geometric=False)
    axes[2].fill_between(dates, 0, dd.values * 100, color=_LIGHT_GRAY, alpha=0.5)
    axes[2].plot(dates, dd.values * 100, color=_DARK_GRAY, linewidth=0.6)
    axes[2].set_ylabel("Drawdown (%)", fontsize=9, color=_DARK_GRAY)
    _apply_formal_style(axes[2], fontsize=8)

    _format_date_axis(axes[2], fontsize=8)
    fig.tight_layout(pad=0.3)
    fig.subplots_adjust(hspace=0.08)
    return _fig_to_base64(fig)


def monthly_returns_bar_formal(daily_returns: pd.Series,
                                figsize=(4.8, 1.4)) -> str:
    """Monthly returns bar chart, compact formal style. Returns base64 PNG."""
    monthly = daily_returns.resample("ME").sum() * 100
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    clrs = [_DARK_GRAY if v >= 0 else _LIGHT_GRAY for v in monthly.values]
    ax.bar(monthly.index, monthly.values, width=25, color=clrs, linewidth=0)
    ax.set_ylabel("Monthly Return\n(% AUM)", fontsize=9, color=_DARK_GRAY)
    ax.axhline(0, color=_LIGHT_GRAY, linewidth=0.3)
    _apply_formal_style(ax, fontsize=8)
    _format_date_axis(ax, fontsize=8)
    fig.tight_layout(pad=0.2)
    return _fig_to_base64(fig)


def returns_histogram_formal(pnl_raw: pd.Series, aum: float = 1.0,
                              figsize=(3.2, 1.8)) -> str:
    """Histogram of trade returns with fitted normal curve. Returns base64 PNG."""
    data = (pnl_raw / aum * 100).dropna()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(data) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                fontsize=8, color=_DARK_GRAY)
        return _fig_to_base64(fig)

    n, bins, patches = ax.hist(data, bins=25, density=False, color="darkgrey",
                               alpha=0.85, edgecolor="white", linewidth=0.3)
    total = len(data)
    for p in patches:
        p.set_height(p.get_height() / total * 100)
    ax.set_ylim(0, max(n) / total * 100 * 1.1)

    # Fitted normal overlay (matching R: blue line)
    try:
        x = np.linspace(data.min(), data.max(), 200)
        from scipy.stats import norm
        mu, sigma = data.mean(), data.std()
        y = norm.pdf(x, mu, sigma)
        y_scaled = y * (bins[1] - bins[0]) * 100
        ax.plot(x, y_scaled, color=_BRAND_BLUE, linewidth=1.5)
    except ImportError:
        pass

    ax.set_xlabel("Returns (% AUM)", fontsize=9, color=_DARK_GRAY)
    ax.set_ylabel("% Trades", fontsize=9, color=_DARK_GRAY)
    ax.set_title("Histogram of Trade Returns", fontsize=10, fontweight="bold",
                 color="black", fontfamily="serif")
    _apply_formal_style(ax, fontsize=8)
    fig.tight_layout(pad=0.3)
    return _fig_to_base64(fig)


def rolling_vol_chart_formal(daily_returns: pd.Series,
                              figsize=(3.2, 1.8)) -> str:
    """Rolling volatility chart. Returns base64 PNG."""
    window = 252 if len(daily_returns) > 500 else 63
    vol = rolling_volatility(daily_returns, window)
    months = round(12 * window / 252)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if vol.empty:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center",
                fontsize=8, color=_DARK_GRAY)
        return _fig_to_base64(fig)

    ax.plot(vol.index, vol.values * 100, color=_DARK_GRAY, linewidth=1.0)
    ax.fill_between(vol.index, 0, vol.values * 100, alpha=0.12, color=_LIGHT_GRAY)
    ax.set_ylabel("Volatility (%)", fontsize=9, color=_DARK_GRAY)
    ax.set_title(f"Volatility (rolling {months} month)", fontsize=10,
                 fontweight="bold", color="black", fontfamily="serif")
    _apply_formal_style(ax, fontsize=8)
    _format_date_axis(ax, fontsize=8)
    fig.tight_layout(pad=0.3)
    return _fig_to_base64(fig)


def timezone_chart_formal(pnl_raw: pd.Series, figsize=(3.2, 1.8)) -> str:
    """Trades and returns by timezone (London/NY/Asia). Returns base64 PNG."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(pnl_raw) == 0 or pnl_raw.index.tz is None:
        ax.text(0.5, 0.5, "No timezone data", ha="center", va="center",
                fontsize=8, color=_DARK_GRAY)
        _apply_formal_style(ax, fontsize=6)
        fig.tight_layout(pad=0.3)
        return _fig_to_base64(fig)

    # Classify entry times into sessions (matching R: T06-T18=London, T18-T22=NY, T22-T06=Asia)
    utc_hours = pnl_raw.index.tz_convert("UTC").hour
    zones = []
    for h in utc_hours:
        if 6 <= h < 18:
            zones.append("London")
        elif 18 <= h < 22:
            zones.append("New York")
        else:
            zones.append("Asia")

    df = pd.DataFrame({"zone": zones, "pnl": pnl_raw.values})
    zone_order = ["London", "New York", "Asia"]
    total_trades = len(df)
    total_pnl = df["pnl"].sum()

    pct_trades = []
    pct_returns = []
    for z in zone_order:
        mask = df["zone"] == z
        pct_trades.append(mask.sum() / total_trades * 100 if total_trades > 0 else 0)
        pct_returns.append(df.loc[mask, "pnl"].sum() / abs(total_pnl) * 100
                          if total_pnl != 0 else 0)

    x = np.arange(len(zone_order))
    w = 0.35
    ax.bar(x - w/2, pct_trades, w, color=_LIGHT_GRAY, label="% Trades")
    ax.bar(x + w/2, pct_returns, w, color=_DARK_GRAY, label="% Returns")
    ax.set_xticks(x)
    ax.set_xticklabels(zone_order, fontsize=9)
    ax.set_ylabel("% Trades", fontsize=9, color=_DARK_GRAY)
    ax.set_title("Trades and Returns by Timezone", fontsize=10, fontweight="bold",
                 color="black", fontfamily="serif")
    ax.legend(fontsize=8, loc="best", framealpha=0.7)
    _apply_formal_style(ax, fontsize=8)
    fig.tight_layout(pad=0.3)
    return _fig_to_base64(fig)


def timezone_cumulative_returns_formal(pnl_raw: pd.Series, daily_returns: pd.Series,
                                        figsize=(8.5, 2.0)) -> str:
    """Three-panel cumulative returns by timezone (London/NY/Asia).
    Matches R template: my_plot.xts(cumsum(pnl.london2)*100, ...).
    Returns base64 PNG."""
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(pnl_raw) == 0 or pnl_raw.index.tz is None:
        for ax in axes:
            ax.text(0.5, 0.5, "No timezone data", ha="center", va="center",
                    fontsize=8, color=_DARK_GRAY)
            _apply_formal_style(ax, fontsize=6)
        fig.tight_layout(pad=0.3)
        return _fig_to_base64(fig)

    # Classify trades by timezone (R: T06-T18=London, T18-T22=NY, rest=Asia)
    utc_hours = pnl_raw.index.tz_convert("UTC").hour
    london_mask = (utc_hours >= 6) & (utc_hours < 18)
    ny_mask = (utc_hours >= 18) & (utc_hours < 22)
    asia_mask = ~london_mask & ~ny_mask

    zones = [
        ("Returns from London Trades", london_mask),
        ("Returns from New York Trades", ny_mask),
        ("Returns from Asia Trades", asia_mask),
    ]

    for ax, (label, mask) in zip(axes, zones):
        zone_pnl = pnl_raw[mask]
        if len(zone_pnl) > 0:
            # Build daily series from zone trades
            zone_daily = zone_pnl.resample("D").sum().fillna(0)
            cum = zone_daily.cumsum() * 100
            ax.plot(cum.index, cum.values, color=_DARK_GRAY, linewidth=0.9)
            ax.fill_between(cum.index, 0, cum.values, alpha=0.12, color=_LIGHT_GRAY)
        ax.set_title(label, fontsize=9, fontweight="bold", color="black", fontfamily="serif")
        ax.set_ylabel("% AUM", fontsize=8, color=_DARK_GRAY)
        _apply_formal_style(ax, fontsize=7)
        _format_date_axis(ax, fontsize=7)

    fig.tight_layout(pad=0.4)
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Original style charts (used by portfolio reports, kept unchanged)
# ---------------------------------------------------------------------------

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
    colors_list = ["#2E86AB" if v >= 0 else "#E84855" for v in daily_returns.values]
    axes[1].bar(dates, daily_returns.values * 100, color=colors_list, width=1.5, linewidth=0)
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
    colors_list = ["#2E86AB" if v >= 0 else "#E84855" for v in monthly.values]
    ax.bar(monthly.index, monthly.values, width=25, color=colors_list, linewidth=0)
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
    colors_arr = plt.cm.Set2(np.linspace(0, 1, strategy_returns.shape[1]))
    for i, col in enumerate(strategy_returns.columns):
        cum_s = strategy_returns[col].cumsum() * 100
        ax.plot(cum_s.index, cum_s.values, color=colors_arr[i], linewidth=1, label=col, alpha=0.7)

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
