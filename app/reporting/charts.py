"""Chart generation using matplotlib — matching the R report visualizations."""

import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, ScalarFormatter

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


def _apply_formal_style(ax, fontsize=11, fontscale=1.0):
    """Apply formal styling to an axes."""
    fs = fontsize * fontscale
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_LIGHT_GRAY)
    ax.spines["bottom"].set_color(_LIGHT_GRAY)
    ax.spines["left"].set_linewidth(0.5 * fontscale)
    ax.spines["bottom"].set_linewidth(0.5 * fontscale)
    ax.tick_params(axis="both", which="both", labelsize=fs, colors=_DARK_GRAY,
                   length=3 * fontscale, width=0.5 * fontscale)
    ax.yaxis.label.set_size(fs)
    ax.xaxis.label.set_size(fs)
    ax.grid(True, axis="y", linewidth=0.3 * fontscale, color="#dddddd", alpha=0.7)
    ax.set_facecolor("white")
    # Disable scientific notation on y-axis (no "1e9" etc)
    ax.yaxis.get_major_formatter().set_useOffset(False)
    try:
        ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    except (AttributeError, ValueError):
        pass


def _format_date_axis(ax, fontsize=11, fontscale=1.0, year_interval=1):
    """Apply consistent date formatting to x-axis."""
    fs = fontsize * fontscale
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(year_interval))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha="center", fontsize=fs)


def _fig_to_base64(fig: plt.Figure, dpi: int = 120) -> str:
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                pad_inches=0.05, facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _fig_to_bytes(fig: plt.Figure) -> bytes:
    """Convert matplotlib figure to PNG bytes (for PDF embedding)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                pad_inches=0.05, facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Backtest-specific charts (formal style)
# ---------------------------------------------------------------------------

def performance_summary_formal(daily_returns: pd.Series, title: str = "",
                                figsize=(10, 5.6), fontscale: float = 1.0) -> str:
    """Three-panel chart: cumulative returns, daily returns, drawdowns.
    Uses web app color palette. Returns base64 PNG."""
    s = fontscale
    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True,
                             gridspec_kw={"height_ratios": [3, 1, 1.5]})
    fig.patch.set_facecolor("white")

    dates = daily_returns.index
    cum = daily_returns.cumsum() * 100

    # Cumulative returns
    axes[0].plot(dates, cum, color=_DARK_GRAY, linewidth=0.9 * s)
    axes[0].fill_between(dates, 0, cum, alpha=0.15, color=_LIGHT_GRAY)
    axes[0].set_ylabel("Cumulative Return (% AUM)", fontsize=9 * s, color=_DARK_GRAY)
    axes[0].axhline(0, color=_LIGHT_GRAY, linewidth=0.3 * s)
    if title:
        axes[0].set_title(title, fontsize=10 * s, fontweight="bold", color="black",
                          fontfamily="serif")
    _apply_formal_style(axes[0], fontsize=9, fontscale=s)

    # Daily returns bar
    clrs = [_DARK_GRAY if v >= 0 else _LIGHT_GRAY for v in daily_returns.values]
    axes[1].bar(dates, daily_returns.values * 100, color=clrs, width=1.5, linewidth=0)
    axes[1].set_ylabel("Daily (%)", fontsize=9 * s, color=_DARK_GRAY)
    axes[1].axhline(0, color=_LIGHT_GRAY, linewidth=0.3 * s)
    _apply_formal_style(axes[1], fontsize=9, fontscale=s)

    # Drawdowns
    dd = drawdown_series(daily_returns, geometric=False)
    axes[2].fill_between(dates, 0, dd.values * 100, color=_LIGHT_GRAY, alpha=0.5)
    axes[2].plot(dates, dd.values * 100, color=_DARK_GRAY, linewidth=0.6 * s)
    axes[2].set_ylabel("Drawdown (%)", fontsize=9 * s, color=_DARK_GRAY)
    _apply_formal_style(axes[2], fontsize=9, fontscale=s)

    _format_date_axis(axes[2], fontsize=9, fontscale=s)
    fig.tight_layout(pad=0.5)
    fig.subplots_adjust(hspace=0.12)
    return _fig_to_base64(fig)


def monthly_returns_bar_formal(daily_returns: pd.Series,
                                figsize=(10, 3), fontscale: float = 1.0) -> str:
    """Monthly returns bar chart. Returns base64 PNG."""
    s = fontscale
    effective_w = figsize[0] / s
    yi = 1 if effective_w > 3 else 2
    monthly = daily_returns.resample("ME").sum() * 100
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    clrs = [_DARK_GRAY if v >= 0 else _LIGHT_GRAY for v in monthly.values]
    ax.bar(monthly.index, monthly.values, width=25, color=clrs, linewidth=0)
    ax.set_ylabel("Monthly (%)", fontsize=11 * s, color=_DARK_GRAY)
    ax.axhline(0, color=_LIGHT_GRAY, linewidth=0.3 * s)
    _apply_formal_style(ax, fontsize=10, fontscale=s)
    _format_date_axis(ax, fontsize=10, fontscale=s, year_interval=yi)
    fig.tight_layout(pad=0.8)
    return _fig_to_base64(fig)


def returns_histogram_formal(pnl_raw: pd.Series, aum: float = 1.0,
                              figsize=(10, 6), fontscale: float = 1.0) -> str:
    """Histogram of trade returns with fitted normal curve. Returns base64 PNG."""
    s = fontscale
    data = (pnl_raw / aum * 100).dropna()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(data) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                fontsize=12 * s, color=_DARK_GRAY)
        return _fig_to_base64(fig)

    n, bins, patches = ax.hist(data, bins=25, density=False, color="darkgrey",
                               alpha=0.85, edgecolor="white", linewidth=0.3 * s)
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
        ax.plot(x, y_scaled, color=_BRAND_BLUE, linewidth=2 * s)
    except ImportError:
        pass

    ax.set_xlabel("Returns (% AUM)", fontsize=12 * s, color=_DARK_GRAY)
    ax.set_ylabel("% Trades", fontsize=12 * s, color=_DARK_GRAY)
    ax.set_title("Histogram of Trade Returns", fontsize=13 * s, fontweight="bold",
                 color="black", fontfamily="serif")
    _apply_formal_style(ax, fontsize=11, fontscale=s)
    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)


def rolling_vol_chart_formal(daily_returns: pd.Series,
                              figsize=(10, 6), fontscale: float = 1.0) -> str:
    """Rolling volatility chart. Returns base64 PNG."""
    s = fontscale
    window = 252 if len(daily_returns) > 500 else 63
    vol = rolling_volatility(daily_returns, window)
    months = round(12 * window / 252)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if vol.empty:
        ax.text(0.5, 0.5, "Insufficient data", ha="center", va="center",
                fontsize=12 * s, color=_DARK_GRAY)
        return _fig_to_base64(fig)

    effective_w = figsize[0] / s
    yi = 1 if effective_w > 3 else 2
    ax.plot(vol.index, vol.values * 100, color=_DARK_GRAY, linewidth=1.0 * s)
    ax.fill_between(vol.index, 0, vol.values * 100, alpha=0.12, color=_LIGHT_GRAY)
    ax.set_ylabel("Volatility (%)", fontsize=12 * s, color=_DARK_GRAY)
    ax.set_title(f"Volatility (rolling {months} month)", fontsize=13 * s,
                 fontweight="bold", color="black", fontfamily="serif")
    _apply_formal_style(ax, fontsize=11, fontscale=s)
    _format_date_axis(ax, fontsize=11, fontscale=s, year_interval=yi)
    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)


def timezone_chart_formal(pnl_raw: pd.Series, aum: float = 1.0,
                           figsize=(10, 6), fontscale: float = 1.0) -> str:
    """Trades and returns by timezone (London/NY/Asia). Returns base64 PNG."""
    s = fontscale
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(pnl_raw) == 0 or pnl_raw.index.tz is None:
        ax.text(0.5, 0.5, "No timezone data", ha="center", va="center",
                fontsize=12 * s, color=_DARK_GRAY)
        _apply_formal_style(ax, fontsize=11, fontscale=s)
        fig.tight_layout(pad=0.5)
        return _fig_to_base64(fig)

    # Normalize by AUM (matching R: pnl.xts <- pnl.raw/AUM)
    pnl_norm = pnl_raw / aum

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

    df = pd.DataFrame({"zone": zones, "pnl": pnl_norm.values})
    zone_order = ["London", "New York", "Asia"]
    total_trades = len(df)

    # Matching R: barplot of trade counts with return labels
    pct_trades = []
    tz_rtns = []
    for z in zone_order:
        mask = df["zone"] == z
        pct_trades.append(mask.sum() / total_trades * 100 if total_trades > 0 else 0)
        tz_rtns.append(df.loc[mask, "pnl"].sum() * 100)

    x = np.arange(len(zone_order))
    effective_w = figsize[0] / s
    if effective_w > 3:
        labels = [f"{z}\n{r:.1f}%" for z, r in zip(zone_order, tz_rtns)]
        tick_fs = 12 * s
    else:
        short = {"London": "Ldn", "New York": "NY", "Asia": "Asia"}
        labels = [f"{short[z]}\n{r:.0f}%" for z, r in zip(zone_order, tz_rtns)]
        tick_fs = 9 * s
    ax.bar(x, pct_trades, color=_DARK_GRAY)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=tick_fs)
    ax.set_ylabel("% Trades", fontsize=12 * s, color=_DARK_GRAY)
    ax.set_title("Trades & Returns by TZ", fontsize=13 * s, fontweight="bold",
                 color="black", fontfamily="serif")
    _apply_formal_style(ax, fontsize=11, fontscale=s)
    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)


def bottom_row_charts_formal(pnl_raw: pd.Series, daily_returns: pd.Series,
                              aum: float = 1.0,
                              figsize=(10, 3.5), fontscale: float = 1.0) -> str:
    """Three-panel row: histogram, rolling volatility, timezone bar.
    Single figure ensures aligned x-axes. Returns base64 PNG."""
    s = fontscale
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    fig.patch.set_facecolor("white")

    # Panel 1: Histogram of trade returns
    data = (pnl_raw / aum * 100).dropna()
    if len(data) > 0:
        n, bins, patches = axes[0].hist(data, bins=25, density=False, color="darkgrey",
                                         alpha=0.85, edgecolor="white", linewidth=0.3 * s)
        total = len(data)
        for p in patches:
            p.set_height(p.get_height() / total * 100)
        axes[0].set_ylim(0, max(n) / total * 100 * 1.1)
        try:
            x = np.linspace(data.min(), data.max(), 200)
            from scipy.stats import norm
            mu, sigma = data.mean(), data.std()
            y = norm.pdf(x, mu, sigma)
            y_scaled = y * (bins[1] - bins[0]) * 100
            axes[0].plot(x, y_scaled, color=_BRAND_BLUE, linewidth=2 * s)
        except ImportError:
            pass
    axes[0].set_xlabel("Returns (% AUM)", fontsize=10 * s, color=_DARK_GRAY)
    axes[0].set_ylabel("% Trades", fontsize=10 * s, color=_DARK_GRAY)
    axes[0].set_title("Trade Returns", fontsize=10 * s, fontweight="bold",
                       color="black", fontfamily="serif")
    _apply_formal_style(axes[0], fontsize=8, fontscale=s)

    # Panel 2: Rolling volatility
    window = 252 if len(daily_returns) > 500 else 63
    vol = rolling_volatility(daily_returns, window)
    months = round(12 * window / 252)
    if not vol.empty:
        axes[1].plot(vol.index, vol.values * 100, color=_DARK_GRAY, linewidth=1.0 * s)
        axes[1].fill_between(vol.index, 0, vol.values * 100, alpha=0.12, color=_LIGHT_GRAY)
    axes[1].set_ylabel("Volatility (%)", fontsize=10 * s, color=_DARK_GRAY)
    axes[1].set_title(f"Volatility ({months}m rolling)", fontsize=10 * s,
                       fontweight="bold", color="black", fontfamily="serif")
    _apply_formal_style(axes[1], fontsize=8, fontscale=s)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[1].xaxis.set_major_locator(mdates.YearLocator(2))
    plt.setp(axes[1].xaxis.get_majorticklabels(), rotation=0, ha="center", fontsize=8 * s)

    # Panel 3: Timezone bar chart
    if len(pnl_raw) > 0 and pnl_raw.index.tz is not None:
        pnl_norm = pnl_raw / aum
        utc_hours = pnl_raw.index.tz_convert("UTC").hour
        zones = []
        for h in utc_hours:
            if 6 <= h < 18:
                zones.append("London")
            elif 18 <= h < 22:
                zones.append("New York")
            else:
                zones.append("Asia")
        df = pd.DataFrame({"zone": zones, "pnl": pnl_norm.values})
        zone_order = ["London", "New York", "Asia"]
        total_trades = len(df)
        pct_trades = []
        tz_rtns = []
        for z in zone_order:
            mask = df["zone"] == z
            pct_trades.append(mask.sum() / total_trades * 100 if total_trades > 0 else 0)
            tz_rtns.append(df.loc[mask, "pnl"].sum() * 100)
        xp = np.arange(len(zone_order))
        short = {"London": "Ldn", "New York": "NY", "Asia": "Asia"}
        labels = [f"{short[z]}\n{r:.0f}%" for z, r in zip(zone_order, tz_rtns)]
        axes[2].bar(xp, pct_trades, color=_DARK_GRAY)
        axes[2].set_xticks(xp)
        axes[2].set_xticklabels(labels, fontsize=9 * s)
    else:
        axes[2].text(0.5, 0.5, "No TZ data", ha="center", va="center",
                     fontsize=10 * s, color=_DARK_GRAY)
    axes[2].set_ylabel("% Trades", fontsize=10 * s, color=_DARK_GRAY)
    axes[2].set_title("Trades & Returns by TZ", fontsize=10 * s, fontweight="bold",
                       color="black", fontfamily="serif")
    _apply_formal_style(axes[2], fontsize=8, fontscale=s)

    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)


def timezone_cumulative_returns_formal(pnl_raw: pd.Series, daily_returns: pd.Series,
                                        aum: float = 1.0,
                                        figsize=(10, 3), fontscale: float = 1.0) -> str:
    """Three-panel cumulative returns by timezone (London/NY/Asia).
    Matches R template: my_plot.xts(cumsum(pnl.london2)*100, ...).
    Returns base64 PNG."""
    s = fontscale
    fig, axes = plt.subplots(1, 3, figsize=figsize)
    fig.patch.set_facecolor("white")

    if len(pnl_raw) == 0 or pnl_raw.index.tz is None:
        for ax in axes:
            ax.text(0.5, 0.5, "No timezone data", ha="center", va="center",
                    fontsize=12 * s, color=_DARK_GRAY)
            _apply_formal_style(ax, fontsize=10, fontscale=s)
        fig.tight_layout(pad=0.5)
        return _fig_to_base64(fig)

    # Normalize by AUM (matching R: pnl.xts <- pnl.raw/AUM)
    pnl_norm = pnl_raw / aum

    # Classify trades by timezone (R: T06-T18=London, T18-T22=NY, rest=Asia)
    utc_hours = pnl_raw.index.tz_convert("UTC").hour
    london_mask = (utc_hours >= 6) & (utc_hours < 18)
    ny_mask = (utc_hours >= 18) & (utc_hours < 22)
    asia_mask = ~london_mask & ~ny_mask

    zones = [
        ("London Trades", london_mask),
        ("New York Trades", ny_mask),
        ("Asia Trades", asia_mask),
    ]

    for ax, (label, mask) in zip(axes, zones):
        zone_pnl = pnl_norm[mask]
        if len(zone_pnl) > 0:
            # Build daily series from zone trades
            zone_daily = zone_pnl.resample("D").sum().fillna(0)
            cum = zone_daily.cumsum() * 100
            ax.plot(cum.index, cum.values, color=_DARK_GRAY, linewidth=0.9 * s)
            ax.fill_between(cum.index, 0, cum.values, alpha=0.12, color=_LIGHT_GRAY)
        ax.set_title(label, fontsize=10 * s, fontweight="bold", color="black", fontfamily="serif")
        ax.set_ylabel("% AUM", fontsize=9 * s, color=_DARK_GRAY)
        _apply_formal_style(ax, fontsize=8, fontscale=s)
        # Use sparser date ticks for narrow panels
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8 * s)

    fig.tight_layout(pad=0.5)
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


# ---------------------------------------------------------------------------
# Portfolio formal charts
# ---------------------------------------------------------------------------

def portfolio_strategies_formal(portfolio: pd.Series, strategy_returns: pd.DataFrame,
                                 rel_returns: bool = False,
                                 figsize=(10, 4), fontscale: float = 1.0) -> str:
    """Cumulative returns of portfolio vs individual strategies (formal style). Returns base64 PNG."""
    s = fontscale
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")

    cum_ptf = portfolio.cumsum() * 100
    ax.plot(cum_ptf.index, cum_ptf.values, color="black", linewidth=2.0 * s, label="Portfolio")

    colors_arr = plt.cm.Set2(np.linspace(0, 1, max(strategy_returns.shape[1], 1)))
    for i, col in enumerate(strategy_returns.columns):
        cum_s = strategy_returns[col].cumsum() * 100
        ax.plot(cum_s.index, cum_s.values, color=colors_arr[i], linewidth=0.8 * s,
                label=col, alpha=0.7)

    title = "Average Portfolio and Strategies" if rel_returns else "Portfolio and Strategies"
    ax.set_title(title, fontsize=11 * s, fontweight="bold", color="black", fontfamily="serif")
    ax.set_ylabel("Cumulative Return (% AUM)", fontsize=10 * s, color=_DARK_GRAY)
    ax.legend(fontsize=7 * s, ncol=3, loc="best")
    ax.axhline(0, color=_LIGHT_GRAY, linewidth=0.3 * s)
    _apply_formal_style(ax, fontsize=9, fontscale=s)

    effective_w = figsize[0] / s
    yi = 1 if effective_w > 3 else 2
    _format_date_axis(ax, fontsize=9, fontscale=s, year_interval=yi)
    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)


def correlation_heatmap_formal(strategy_returns: pd.DataFrame,
                                figsize=(6, 5), fontscale: float = 1.0) -> str:
    """Correlation heatmap of strategies (formal style). Returns base64 PNG."""
    s = fontscale
    if strategy_returns.shape[1] < 2:
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor("white")
        ax.text(0.5, 0.5, "Need 2+ strategies", ha="center", va="center",
                fontsize=12 * s, color=_DARK_GRAY)
        return _fig_to_base64(fig)

    corr = strategy_returns.corr()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("white")
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    fig.colorbar(im, ax=ax, shrink=0.8)

    n = len(corr)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    labels = [str(i + 1) for i in range(n)]
    ax.set_xticklabels(labels, fontsize=8 * s)
    ax.set_yticklabels(labels, fontsize=8 * s)

    if n <= 10:
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center",
                        fontsize=7 * s)

    ax.set_title("Strategy Correlations", fontsize=11 * s, fontweight="bold",
                 color="black", fontfamily="serif")
    fig.tight_layout(pad=0.5)
    return _fig_to_base64(fig)
