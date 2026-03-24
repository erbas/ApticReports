"""Performance metrics — port of PerformanceAnalytics calculations from the R reports."""

import numpy as np
import pandas as pd


def fill_trading_days(daily_returns: pd.Series) -> pd.Series:
    """Reindex daily returns to all business days, filling missing days with 0.

    The input series typically only contains dates where trades exited.
    Days with no trade activity still have zero return and must be included
    for correct volatility, Sharpe ratio, and drawdown duration calculations.
    """
    if daily_returns.empty:
        return daily_returns
    idx = pd.bdate_range(daily_returns.index.min(), daily_returns.index.max(),
                         tz=daily_returns.index.tz)
    return daily_returns.reindex(idx, fill_value=0.0)


def total_return(daily_returns: pd.Series) -> float:
    """Total cumulative return (sum of daily returns)."""
    return daily_returns.sum()


def annualized_return(daily_returns: pd.Series, scale: int = 252, geometric: bool = True) -> float:
    """Compounded annual return."""
    n = len(daily_returns)
    if n == 0:
        return 0.0
    if geometric:
        cum = (1 + daily_returns).prod()
        years = n / scale
        if years == 0:
            return 0.0
        return cum ** (1.0 / years) - 1.0
    else:
        return daily_returns.mean() * scale


def annualized_volatility(daily_returns: pd.Series, scale: int = 252) -> float:
    """Annualized standard deviation."""
    vol = daily_returns.std()
    if np.isnan(vol):
        return 0.0
    return vol * np.sqrt(scale)


def sharpe_ratio(daily_returns: pd.Series, rf_annual: float = 0.0025, scale: int = 252,
                 geometric: bool = True) -> float:
    """Annualized Sharpe ratio."""
    vol = annualized_volatility(daily_returns, scale)
    if vol == 0:
        return 0.0
    ann_ret = annualized_return(daily_returns, scale, geometric)
    return (ann_ret - rf_annual) / vol


def sortino_ratio(daily_returns: pd.Series, target: float = 0.0) -> float:
    """Sortino ratio (downside deviation)."""
    downside = daily_returns[daily_returns < target]
    if len(downside) == 0:
        return float("inf")
    downside_std = np.sqrt((downside ** 2).mean())
    if downside_std == 0:
        return float("inf")
    return daily_returns.mean() / downside_std


def max_drawdown(daily_returns: pd.Series, geometric: bool = True) -> float:
    """Maximum drawdown as a positive fraction."""
    if geometric:
        cum = (1 + daily_returns).cumprod()
    else:
        cum = daily_returns.cumsum() + 1
    running_max = cum.cummax()
    drawdowns = (cum - running_max) / running_max
    return abs(drawdowns.min()) if len(drawdowns) > 0 else 0.0


def drawdown_series(daily_returns: pd.Series, geometric: bool = True) -> pd.Series:
    """Full drawdown time series (negative values = underwater)."""
    if geometric:
        cum = (1 + daily_returns).cumprod()
    else:
        cum = daily_returns.cumsum() + 1
    running_max = cum.cummax()
    return (cum - running_max) / running_max


def drawdown_table(daily_returns: pd.Series, top: int = 5, geometric: bool = True) -> pd.DataFrame:
    """Table of top N drawdowns with start, trough, recovery, depth, and duration."""
    daily_returns = fill_trading_days(daily_returns)
    dd = drawdown_series(daily_returns, geometric)
    if dd.empty:
        return pd.DataFrame()

    # Find drawdown periods
    is_dd = dd < 0
    periods = []
    in_dd = False
    start = None

    for i in range(len(dd)):
        if is_dd.iloc[i] and not in_dd:
            start = i
            in_dd = True
        elif not is_dd.iloc[i] and in_dd:
            periods.append((start, i - 1, i))
            in_dd = False

    # Handle ongoing drawdown
    if in_dd:
        periods.append((start, len(dd) - 1, None))

    # Build table
    rows = []
    for start_i, trough_scan_end, recovery_i in periods:
        period_dd = dd.iloc[start_i : trough_scan_end + 1]
        trough_i = period_dd.idxmin()
        trough_idx = dd.index.get_loc(trough_i)
        depth = dd.loc[trough_i]

        start_date = dd.index[start_i]
        trough_date = trough_i
        recovery_date = dd.index[recovery_i] if recovery_i is not None else None
        duration = trough_scan_end - start_i + 1
        if recovery_i is not None:
            duration = recovery_i - start_i
        to_trough = trough_idx - start_i
        to_recovery = (recovery_i - trough_idx) if recovery_i is not None else None

        rows.append({
            "Start": start_date,
            "Trough": trough_date,
            "Recovery": recovery_date,
            "Max Drawdown (%)": depth * 100,
            "Duration": duration,
            "Days to Trough": to_trough,
            "Days to Recovery": to_recovery,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.sort_values("Max Drawdown (%)").head(top).reset_index(drop=True)
    return df


def omega_ratio(daily_returns: pd.Series, threshold: float = 0.0) -> float:
    """Omega ratio."""
    gains = daily_returns[daily_returns > threshold] - threshold
    losses = threshold - daily_returns[daily_returns <= threshold]
    if losses.sum() == 0:
        return float("inf")
    return gains.sum() / losses.sum()


def kelly_fraction(daily_returns: pd.Series) -> float:
    """Kelly criterion fraction."""
    mean = daily_returns.mean()
    var = daily_returns.var()
    if var == 0:
        return 0.0
    return mean / var


def win_loss_ratio(pnl_raw: pd.Series) -> float:
    """Fraction of winning trades."""
    if len(pnl_raw) == 0:
        return 0.0
    return (pnl_raw > 0).sum() / len(pnl_raw)


def max_consecutive_losers(pnl_raw: pd.Series) -> int:
    """Maximum consecutive losing trades."""
    if len(pnl_raw) == 0:
        return 0
    signs = np.sign(pnl_raw.values)
    max_run = 0
    current_run = 0
    for s in signs:
        if s < 0:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


def rolling_volatility(daily_returns: pd.Series, window: int = 252) -> pd.Series:
    """Rolling annualized volatility, sampled at month ends."""
    if len(daily_returns) < window:
        window = max(21, len(daily_returns) // 4)
    vol = daily_returns.rolling(window).std() * np.sqrt(window)
    # Sample at month ends
    vol = vol.resample("ME").last().dropna()
    return vol


def compute_all_metrics(daily_returns: pd.Series, pnl_raw: pd.Series | None = None,
                        aum: float = 1.0) -> dict:
    """Compute all summary statistics for a backtest or portfolio.

    daily_returns should be fractional returns (PnL / AUM).
    pnl_raw is optional (for trade-level metrics like win/loss).
    """
    daily_returns = fill_trading_days(daily_returns)
    metrics = {
        "Total Return (% AUM)": total_return(daily_returns) * 100,
        "Compounded Annual Return (%)": annualized_return(daily_returns) * 100,
        "Annualized Volatility (%)": annualized_volatility(daily_returns) * 100,
        "Max Drawdown (% AUM)": max_drawdown(daily_returns) * 100,
        "Sharpe Ratio": sharpe_ratio(daily_returns),
        "Sortino Ratio": sortino_ratio(daily_returns),
        "Omega Ratio": omega_ratio(daily_returns),
        "Kelly Fraction": kelly_fraction(daily_returns),
    }

    if pnl_raw is not None and len(pnl_raw) > 0:
        metrics["Win/Loss Ratio"] = win_loss_ratio(pnl_raw)
        metrics["Max Consecutive Losers"] = max_consecutive_losers(pnl_raw)

    # Returns since specific years
    for year in range(2020, 2027):
        mask = daily_returns.index >= pd.Timestamp(f"{year}-01-01", tz=daily_returns.index.tz)
        subset = daily_returns[mask]
        if len(subset) > 0:
            metrics[f"Return since 1 Jan {year} (%)"] = total_return(subset) * 100

    return metrics
