"""PDF report generation using reportlab — replaces LaTeX/Sweave pipeline."""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
    KeepTogether,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import charts, metrics

import pandas as pd


def _chart_image(base64_png: str, width: float = 180 * mm, height: float = 0) -> Image:
    """Convert base64 chart to reportlab Image."""
    import base64
    png_bytes = base64.b64decode(base64_png)
    buf = io.BytesIO(png_bytes)
    if height == 0:
        # Auto-calculate height from aspect ratio
        from PIL import Image as PILImage
        pil = PILImage.open(io.BytesIO(png_bytes))
        aspect = pil.height / pil.width
        height = width * aspect
    return Image(buf, width=width, height=height)


def _metrics_table(stats: dict, styles) -> Table:
    """Build a formatted stats table."""
    data = [["Metric", "Value"]]
    for k, v in stats.items():
        if isinstance(v, float):
            data.append([k, f"{v:.2f}"])
        else:
            data.append([k, str(v)])

    t = Table(data, colWidths=[130 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _drawdown_table(dd_df: pd.DataFrame) -> Table | None:
    """Build drawdown table from DataFrame."""
    if dd_df.empty:
        return None

    data = [["Start", "Trough", "Recovery", "Max DD (%)", "Duration"]]
    for _, row in dd_df.iterrows():
        start = row["Start"].strftime("%d-%m-%Y") if pd.notna(row["Start"]) else ""
        trough = row["Trough"].strftime("%d-%m-%Y") if pd.notna(row["Trough"]) else ""
        recovery = row["Recovery"].strftime("%d-%m-%Y") if pd.notna(row.get("Recovery")) else "ongoing"
        data.append([start, trough, recovery, f"{row['Max Drawdown (%)']:.2f}", str(row["Duration"])])

    t = Table(data, colWidths=[32 * mm, 32 * mm, 32 * mm, 25 * mm, 20 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E84855")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF0F0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def generate_backtest_pdf(
    daily_returns: pd.Series,
    pnl_raw: pd.Series,
    aum: float,
    strategy: str,
    ccy_pair: str,
    timeframe: str,
    strat_dir: str,
    filestem: str,
    output_path: str,
) -> str:
    """Generate a backtest PDF report. Returns path to PDF file."""
    pdf_path = os.path.join(output_path, f"{filestem}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18,
                                 textColor=colors.HexColor("#2E86AB"))
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12,
                                   textColor=colors.HexColor("#2E86AB"))

    story = []

    # Title
    story.append(Paragraph(f"{strategy} : {ccy_pair} : {timeframe} : {strat_dir}", title_style))
    story.append(Paragraph(f"Trades file: {filestem}", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 8 * mm))

    # Summary statistics
    story.append(Paragraph("Summary Statistics", section_style))
    stats = metrics.compute_all_metrics(daily_returns, pnl_raw, aum)
    story.append(_metrics_table(stats, styles))
    story.append(Spacer(1, 5 * mm))

    # Drawdown table
    dd_df = metrics.drawdown_table(daily_returns, top=5)
    if not dd_df.empty:
        story.append(Paragraph("Drawdown Analysis", section_style))
        dd_t = _drawdown_table(dd_df)
        if dd_t:
            story.append(dd_t)
        story.append(Spacer(1, 5 * mm))

    # Performance chart
    story.append(PageBreak())
    story.append(Paragraph("Performance Summary", section_style))
    perf_b64 = charts.performance_summary(daily_returns, title=f"{strategy} {ccy_pair}")
    story.append(_chart_image(perf_b64, width=250 * mm))
    story.append(Spacer(1, 5 * mm))

    # Monthly returns
    story.append(Paragraph("Monthly Returns", section_style))
    monthly_b64 = charts.monthly_returns_bar(daily_returns)
    story.append(_chart_image(monthly_b64, width=250 * mm))

    # Rolling volatility + histogram
    story.append(PageBreak())
    vol_b64 = charts.rolling_vol_chart(daily_returns)
    story.append(Paragraph("Rolling Volatility", section_style))
    story.append(_chart_image(vol_b64, width=120 * mm))

    try:
        hist_b64 = charts.returns_histogram(pnl_raw, aum)
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("Trade Returns Distribution", section_style))
        story.append(_chart_image(hist_b64, width=120 * mm))
    except ImportError:
        pass  # scipy not available, skip histogram

    doc.build(story)
    return pdf_path


def generate_portfolio_pdf(
    ptf_daily: pd.DataFrame,
    portfolio: pd.Series,
    strategy_returns: pd.DataFrame,
    metadata: pd.DataFrame,
    report_name: str,
    rel_returns: bool,
    output_path: str,
) -> str:
    """Generate a portfolio PDF report. Returns path to PDF file."""
    pdf_path = os.path.join(output_path, f"{report_name}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=18,
                                 textColor=colors.HexColor("#2E86AB"))
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=10,
                                    textColor=colors.grey)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12,
                                   textColor=colors.HexColor("#2E86AB"))

    story = []

    # Title
    story.append(Paragraph(f"Portfolio Report: {report_name}", title_style))
    agg_method = "Average Returns" if rel_returns else "Sum of Cash PnL"
    story.append(Paragraph(f"Aggregation: {agg_method}", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", subtitle_style))
    story.append(Spacer(1, 8 * mm))

    # Summary statistics for portfolio and benchmark columns
    story.append(Paragraph("Summary Statistics", section_style))
    stats = {}
    for col in ptf_daily.columns:
        col_stats = metrics.compute_all_metrics(ptf_daily[col])
        stats[col] = col_stats

    # Build multi-column table
    metric_names = list(next(iter(stats.values())).keys())
    header = ["Metric"] + list(stats.keys())
    data = [header]
    for m in metric_names:
        row = [m]
        for col in stats:
            v = stats[col].get(m, "")
            row.append(f"{v:.2f}" if isinstance(v, float) else str(v))
        data.append(row)

    n_cols = len(header)
    col_widths = [80 * mm] + [35 * mm] * (n_cols - 1)
    t = Table(data, colWidths=col_widths[:n_cols])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F4F8")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(Spacer(1, 5 * mm))

    # Drawdown table
    dd_df = metrics.drawdown_table(portfolio, top=5)
    if not dd_df.empty:
        story.append(Paragraph("Drawdown Analysis", section_style))
        dd_t = _drawdown_table(dd_df)
        if dd_t:
            story.append(dd_t)

    # Performance chart
    story.append(PageBreak())
    story.append(Paragraph("Performance Summary", section_style))
    perf_b64 = charts.performance_summary(portfolio, title=report_name)
    story.append(_chart_image(perf_b64, width=250 * mm))

    # Portfolio vs strategies
    story.append(PageBreak())
    story.append(Paragraph("Portfolio vs Strategies", section_style))
    strat_b64 = charts.portfolio_strategies_chart(portfolio, strategy_returns, rel_returns)
    story.append(_chart_image(strat_b64, width=250 * mm))

    # Correlation heatmap
    if strategy_returns.shape[1] >= 2:
        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("Strategy Correlations", section_style))
        corr_b64 = charts.correlation_heatmap(strategy_returns)
        story.append(_chart_image(corr_b64, width=140 * mm))

    # Rolling volatility
    story.append(PageBreak())
    story.append(Paragraph("Rolling Volatility", section_style))
    vol_b64 = charts.rolling_vol_chart(portfolio)
    story.append(_chart_image(vol_b64, width=160 * mm))

    doc.build(story)
    return pdf_path
