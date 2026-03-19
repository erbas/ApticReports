"""PDF report generation using reportlab — replaces LaTeX/Sweave pipeline."""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
    KeepTogether, BaseDocTemplate, Frame, PageTemplate, Flowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import charts, metrics

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


class _HRule(Flowable):
    """A thin horizontal rule flowable."""
    def __init__(self, width, thickness=0.5, color=colors.black):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color

    def wrap(self, availWidth, availHeight):
        return (self.width, self.thickness + 1 * mm)

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)


# ---------------------------------------------------------------------------
# Backtest PDF — single landscape A4 page
# ---------------------------------------------------------------------------

def _build_summary_table(stats: dict) -> Table:
    """Build formal summary statistics table with metric/Strategy columns."""
    # Ordered metrics matching R report
    ordered_keys = [
        "Total Return (% AUM)",
        "Compounded Annual Return (%)",
        "Max Drawdown (% AUM)",
        "Days to Recovery",
        "Max Consecutive Losers",
        "Annualized Volatility (%)",
        "Sharpe Ratio",
        "Win/Loss Ratio",
    ]
    # Add yearly returns
    yearly_keys = sorted([k for k in stats if k.startswith("Return since")])
    ordered_keys.extend(yearly_keys)

    data = [["", "Strategy"]]
    for k in ordered_keys:
        if k not in stats:
            continue
        v = stats[k]
        label = k
        # Rename for display
        if k == "Max Consecutive Losers":
            label = "Max Consecutive Losing Trades"
        if k.startswith("Return since"):
            label = "Total " + k.replace("Return", "Return").replace("(%)", "(% AUM)")
            if "(% AUM)" not in label:
                label = label.replace("(%)", "(% AUM)")
        if isinstance(v, float):
            val_str = f"{v:.2f}"
        else:
            val_str = str(v)
        data.append([label, val_str])

    col_w1 = 58 * mm
    col_w2 = 18 * mm
    t = Table(data, colWidths=[col_w1, col_w2])
    style_cmds = [
        # Header row
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 5.5),
        ("FONTSIZE", (0, 1), (-1, -1), 5),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        # Thin black lines for borders
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
        # Alternating row backgrounds
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def _build_drawdown_table(dd_df: pd.DataFrame) -> Table | None:
    """Build formal drawdown table."""
    if dd_df.empty:
        return None

    data = [["Start", "Trough", "Recovery", "Max Drawdn (%)", "Duration"]]
    for _, row in dd_df.iterrows():
        start = row["Start"].strftime("%d-%m-%Y") if pd.notna(row["Start"]) else ""
        trough = row["Trough"].strftime("%d-%m-%Y") if pd.notna(row["Trough"]) else ""
        recovery = row["Recovery"].strftime("%d-%m-%Y") if pd.notna(row.get("Recovery")) else "ongoing"
        data.append([start, trough, recovery, f"{row['Max Drawdown (%)']:.2f}", str(row["Duration"])])

    col_widths = [17 * mm, 17 * mm, 17 * mm, 14 * mm, 11 * mm]
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 4.5),
        ("FONTSIZE", (0, 1), (-1, -1), 4.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (3, 0), (4, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ]
    t.setStyle(TableStyle(style_cmds))
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
    """Generate a single-page portrait A4 backtest PDF report. Returns path to PDF file."""
    pdf_path = os.path.join(output_path, f"{filestem}.pdf")

    page_w, page_h = A4  # 210 x 297 mm (portrait)
    margin_l = 10 * mm
    margin_r = 10 * mm
    margin_t = 10 * mm
    margin_b = 8 * mm

    usable_w = page_w - margin_l - margin_r
    usable_h = page_h - margin_t - margin_b

    # Layout: fixed middle height then bottom row immediately below
    header_h = 14 * mm
    middle_section_h = 125 * mm  # ~4.9" for stats/perf chart area
    bottom_chart_h = 55 * mm     # bottom row charts
    bottom_gap = 3 * mm

    # Compute positions (reportlab y = 0 at page bottom)
    middle_top_y = page_h - margin_t - header_h - 2 * mm
    middle_bottom_y = middle_top_y - middle_section_h
    middle_h = middle_section_h

    bottom_row_top = middle_bottom_y - bottom_gap
    bottom_row_y = bottom_row_top - bottom_chart_h

    left_w = usable_w * 0.48
    right_w = usable_w * 0.50
    col_gap = usable_w * 0.02

    # --- Styles ---
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BTTitle", parent=styles["Title"], fontSize=13,
        textColor=colors.black, fontName="Times-Bold",
        leading=15, spaceAfter=1 * mm,
    )
    subtitle_style = ParagraphStyle(
        "BTSubtitle", parent=styles["Normal"], fontSize=7,
        textColor=colors.Color(0.3, 0.3, 0.3), fontName="Times-Roman",
        leading=9, spaceAfter=0,
    )
    section_style = ParagraphStyle(
        "BTSection", parent=styles["Normal"], fontSize=7,
        textColor=colors.black, fontName="Times-Bold",
        leading=9, spaceBefore=1.5 * mm, spaceAfter=1 * mm,
    )

    # --- Compute data ---
    stats = metrics.compute_all_metrics(daily_returns, pnl_raw, aum)

    # Add "Days to Recovery" from drawdown table
    dd_df = metrics.drawdown_table(daily_returns, top=5)
    if not dd_df.empty and "Days to Recovery" in dd_df.columns:
        first_recovery = dd_df.iloc[0].get("Days to Recovery")
        if first_recovery is not None and not pd.isna(first_recovery):
            stats["Days to Recovery"] = int(first_recovery)
        else:
            stats["Days to Recovery"] = "ongoing"
    else:
        stats["Days to Recovery"] = "N/A"

    # Rename metrics for R-style display
    renamed_stats = {}
    key_order = [
        "Total Return (% AUM)",
        "Compounded Annual Return (%)",
        "Max Drawdown (% AUM)",
        "Days to Recovery",
        "Max Consecutive Losers",
        "Annualized Volatility (%)",
        "Sharpe Ratio",
        "Win/Loss Ratio",
    ]
    for k in key_order:
        if k in stats:
            renamed_stats[k] = stats[k]
    # Add yearly returns
    for k in sorted(stats.keys()):
        if k.startswith("Return since"):
            # Convert "Return since 1 Jan 2020 (%)" -> "Total Return since 1 Jan 2020 (% AUM)"
            display_k = "Total " + k
            if "(% AUM)" not in display_k:
                display_k = display_k.replace("(%)", "(% AUM)")
            renamed_stats[display_k] = stats[k]

    # --- Generate charts as base64 (sized for portrait A4) ---
    # Right column performance chart — 3-panel, should be tall (like R: fig.width=4, fig.height=5)
    perf_fig_w = right_w / (25.4)  # mm to inches
    perf_fig_h = middle_h / (25.4) * 0.92  # fill most of middle section height
    perf_b64 = charts.performance_summary_formal(daily_returns, title="Strategy Performance",
                                                   figsize=(perf_fig_w, perf_fig_h))
    # Monthly bar in left column
    monthly_fig_w = left_w / (25.4)
    monthly_b64 = charts.monthly_returns_bar_formal(daily_returns, figsize=(monthly_fig_w, 1.1))

    # Bottom row: three charts, each ~62mm wide, compact landscape aspect
    bot_chart_w = (usable_w - 4 * mm) / 3
    bot_fig_w = bot_chart_w / (25.4)
    bot_fig_h = bottom_chart_h / (25.4) * 0.85  # fill ~85% of frame height

    try:
        hist_b64 = charts.returns_histogram_formal(pnl_raw, aum, figsize=(bot_fig_w, bot_fig_h))
    except Exception:
        hist_b64 = None

    vol_b64 = charts.rolling_vol_chart_formal(daily_returns, figsize=(bot_fig_w, bot_fig_h))
    tz_b64 = charts.timezone_chart_formal(pnl_raw, figsize=(bot_fig_w, bot_fig_h))

    # --- Build the PDF using canvas directly for precise positioning ---
    from reportlab.pdfgen import canvas as canvasmod
    from reportlab.platypus.frames import Frame as RLFrame

    c = canvasmod.Canvas(pdf_path, pagesize=A4)

    # ---- HEADER ----
    x_start = margin_l
    y_top = page_h - margin_t

    # Title
    c.setFont("Times-Bold", 13)
    c.setFillColor(colors.black)
    title_text = f"{strategy} : {ccy_pair} : {timeframe} : {strat_dir}"
    c.drawString(x_start, y_top - 4 * mm, title_text)

    # Subtitle
    c.setFont("Times-Roman", 7)
    c.setFillColor(colors.Color(0.3, 0.3, 0.3))
    c.drawString(x_start, y_top - 9 * mm, f"Trades file: {filestem}")

    # Horizontal rule
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    y_hrule = y_top - 12 * mm
    c.line(x_start, y_hrule, page_w - margin_r, y_hrule)

    # ---- LEFT COLUMN ----
    left_x = x_start
    left_top = y_hrule - 2 * mm

    # Use frames to place flowables in the left column
    left_story = []

    # Summary Statistics heading
    left_story.append(Paragraph("Summary Statistics", section_style))

    # Summary stats table
    summary_data = [["", "Strategy"]]
    for label, val in renamed_stats.items():
        if isinstance(val, float):
            val_str = f"{val:.2f}"
        else:
            val_str = str(val)
        summary_data.append([label, val_str])

    col_w1 = left_w - 18 * mm
    col_w2 = 17 * mm
    summary_tbl = Table(summary_data, colWidths=[col_w1, col_w2])
    summary_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 5),
        ("FONTSIZE", (0, 1), (-1, -1), 4.8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.94, 0.94, 0.94)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
    ]))
    left_story.append(summary_tbl)
    left_story.append(Spacer(1, 2 * mm))

    # Drawdown heading and table
    if not dd_df.empty:
        left_story.append(Paragraph("Drawdown Length and Recovery Times", section_style))
        dd_tbl = _build_drawdown_table(dd_df)
        if dd_tbl:
            left_story.append(dd_tbl)
        left_story.append(Spacer(1, 2 * mm))

    # Monthly returns bar chart (compact, in left column)
    left_story.append(Paragraph("Monthly Returns (% AUM)", section_style))
    monthly_img = _chart_image(monthly_b64, width=left_w - 2 * mm)
    left_story.append(monthly_img)

    # Middle section: from below hrule to middle_bottom_y
    mid_frame_top = y_hrule - 2 * mm
    mid_frame_h = mid_frame_top - middle_bottom_y

    # Draw left column using a Frame
    left_frame = RLFrame(left_x, middle_bottom_y, left_w, mid_frame_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    left_frame.addFromList(left_story, c)

    # ---- RIGHT COLUMN (Performance charts) ----
    right_x = left_x + left_w + col_gap

    right_story = []
    perf_img = _chart_image(perf_b64, width=right_w - 2 * mm, height=mid_frame_h - 2 * mm)
    right_story.append(perf_img)

    right_frame = RLFrame(right_x, middle_bottom_y, right_w, mid_frame_h,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)
    right_frame.addFromList(right_story, c)

    # ---- BOTTOM ROW (three charts side by side) ----
    chart_w = (usable_w - 4 * mm) / 3

    bottom_charts = []
    if hist_b64:
        bottom_charts.append(hist_b64)
    else:
        bottom_charts.append(vol_b64)
    bottom_charts.append(vol_b64)
    bottom_charts.append(tz_b64)

    for i, b64 in enumerate(bottom_charts):
        chart_x = x_start + i * (chart_w + 2 * mm)
        frame_story = [_chart_image(b64, width=chart_w - 1 * mm, height=bottom_chart_h - 2 * mm)]
        bottom_frame = RLFrame(chart_x, bottom_row_y, chart_w, bottom_chart_h,
                               leftPadding=0, rightPadding=0,
                               topPadding=0, bottomPadding=0)
        bottom_frame.addFromList(frame_story, c)

    c.save()
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
        dd_t = _drawdown_table_portfolio(dd_df)
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


def _drawdown_table_portfolio(dd_df: pd.DataFrame) -> Table | None:
    """Build drawdown table for portfolio reports (original style)."""
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
