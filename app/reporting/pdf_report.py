"""PDF report generation using reportlab — replaces LaTeX/Sweave pipeline."""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, Image, Flowable,
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
# Backtest PDF — single portrait A4 page
# ---------------------------------------------------------------------------

def _build_drawdown_table(dd_df: pd.DataFrame, col_widths=None) -> Table | None:
    """Build formal drawdown table matching R report style."""
    if dd_df.empty:
        return None

    data = [["Start", "Trough", "Recovery", "Max Drawdn (%)", "Duration"]]
    for _, row in dd_df.iterrows():
        start = row["Start"].strftime("%d-%m-%Y") if pd.notna(row["Start"]) else ""
        trough = row["Trough"].strftime("%d-%m-%Y") if pd.notna(row["Trough"]) else ""
        recovery = row["Recovery"].strftime("%d-%m-%Y") if pd.notna(row.get("Recovery")) else "ongoing"
        data.append([start, trough, recovery, f"{row['Max Drawdown (%)']:.2f}", str(row["Duration"])])

    if col_widths is None:
        col_widths = [20 * mm, 20 * mm, 20 * mm, 18 * mm, 14 * mm]
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (3, 0), (4, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
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
    daily_returns = metrics.fill_trading_days(daily_returns)
    pdf_path = os.path.join(output_path, f"{filestem}.pdf")

    page_w, page_h = A4  # 210 x 297 mm (portrait)
    margin_l = 10 * mm
    margin_r = 10 * mm
    margin_t = 10 * mm
    margin_b = 8 * mm

    usable_w = page_w - margin_l - margin_r
    usable_h = page_h - margin_t - margin_b

    # Layout matching R template (textpos absolute positions):
    #   Header:  top 14mm
    #   Middle:  stats/drawdown/monthly on left (48%), perf chart on right (50%)
    #   Bottom:  3 charts side by side
    # R positions (from page top): perf at 46mm, stats at 55mm, monthly at 138mm, bottom at 170mm
    header_h = 14 * mm

    # Left column = 50% of usable, right column = 48%
    left_w = usable_w * 0.50
    right_w = usable_w * 0.48
    col_gap = usable_w * 0.02

    # --- Styles ---
    styles = getSampleStyleSheet()
    section_style = ParagraphStyle(
        "BTSection", parent=styles["Normal"], fontSize=8,
        textColor=colors.black, fontName="Helvetica-Bold",
        leading=9, spaceBefore=1 * mm, spaceAfter=1 * mm,
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

    # Build ordered stats dict matching R report labels
    renamed_stats = {}
    key_order = [
        "Total Return (% AUM)",
        "Compounded Annual Return (%)",
        "Max Drawdown (% AUM)",
        "Days to Recovery",
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
            display_k = "Total " + k
            if "(% AUM)" not in display_k:
                display_k = display_k.replace("(%)", "(% AUM)")
            renamed_stats[display_k] = stats[k]

    # --- Generate charts ---
    # KEY: generate each chart at the SAME aspect ratio as its PDF frame,
    # but scaled up ~2× for legible text.  ReportLab then scales down to fit.
    # Layout dimensions (mm) — computed above:
    row1_top_from_top = 168 * mm
    row1_h = 45 * mm
    row2_top_from_top = 218 * mm
    row2_h = 40 * mm

    row1_top_y = page_h - row1_top_from_top
    row1_y = row1_top_y - row1_h
    row2_top_y = page_h - row2_top_from_top
    row2_y = row2_top_y - row2_h

    mid_frame_top = (page_h - margin_t - 13 * mm) - 1 * mm
    mid_frame_bottom = row1_top_y + 2 * mm
    mid_frame_h = mid_frame_top - mid_frame_bottom

    # Performance chart (right column): ~89mm × ~116mm
    perf_pdf_w = right_w - 2 * mm
    perf_pdf_h = perf_pdf_w * 1.3
    _scale = 2.0  # render at 2× PDF size for readable text
    # NOTE: all pdf dimensions are in points (72pt = 1 inch), divide by 72
    perf_fig = (perf_pdf_w / 72 * _scale, perf_pdf_h / 72 * _scale)
    perf_b64 = charts.performance_summary_formal(daily_returns, title="Strategy Performance",
                                                   figsize=perf_fig, fontscale=_scale)

    # Monthly bar (left column, wide and short)
    monthly_pdf_w = left_w - 2 * mm
    monthly_pdf_h = 25 * mm
    monthly_fig = (monthly_pdf_w / 72 * _scale, monthly_pdf_h / 72 * _scale)
    monthly_b64 = charts.monthly_returns_bar_formal(daily_returns, figsize=monthly_fig,
                                                      fontscale=_scale)

    # Bottom row 1: single 1×3 figure (histogram, volatility, timezone bar)
    row1_pdf_w = usable_w
    row1_pdf_h = row1_h - 2 * mm
    row1_fig = (row1_pdf_w / 72 * _scale, row1_pdf_h / 72 * _scale)
    row1_b64 = charts.bottom_row_charts_formal(pnl_raw, daily_returns, aum=aum,
                                                 figsize=row1_fig, fontscale=_scale)

    # Bottom row 2: timezone cumulative, full width ~190mm × 38mm
    tz_cum_pdf_w = usable_w
    tz_cum_pdf_h = row2_h - 2 * mm
    tz_cum_fig = (tz_cum_pdf_w / 72 * _scale, tz_cum_pdf_h / 72 * _scale)
    tz_cum_b64 = charts.timezone_cumulative_returns_formal(
        pnl_raw, daily_returns, aum=aum, figsize=tz_cum_fig, fontscale=_scale)

    # --- Build the PDF using canvas + frames for precise positioning ---
    from reportlab.pdfgen import canvas as canvasmod
    from reportlab.platypus.frames import Frame as RLFrame

    c = canvasmod.Canvas(pdf_path, pagesize=A4)

    # ---- HEADER ----
    x_start = margin_l
    y_top = page_h - margin_t

    # Title (R uses \Huge, we use 14pt bold)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    title_text = f"{strategy} : {ccy_pair} : {timeframe} : {strat_dir}"
    c.drawString(x_start, y_top - 5 * mm, title_text)

    # Subtitle (trades file)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.Color(0.3, 0.3, 0.3))
    c.drawString(x_start, y_top - 10 * mm, f"Trades file: {filestem}")

    # Horizontal rule
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    y_hrule = y_top - 13 * mm
    c.line(x_start, y_hrule, page_w - margin_r, y_hrule)

    # ---- LEFT COLUMN (stats tables + monthly chart) ----
    left_x = x_start
    left_story = []

    # Summary Statistics heading
    left_story.append(Paragraph("<b>Summary Statistics</b>", section_style))

    # Summary stats table — matching R's xtable style with scalebox=0.7
    summary_data = [["", "Strategy"]]
    for label, val in renamed_stats.items():
        if isinstance(val, float):
            val_str = f"{val:.2f}"
        else:
            val_str = str(val)
        summary_data.append([label, val_str])

    col_w1 = left_w - 20 * mm
    col_w2 = 19 * mm
    summary_tbl = Table(summary_data, colWidths=[col_w1, col_w2])
    summary_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_story.append(summary_tbl)
    left_story.append(Spacer(1, 1.5 * mm))

    # Drawdown heading and table
    if not dd_df.empty:
        left_story.append(Paragraph("<b>Drawdown Length and Recovery Times</b>", section_style))
        dd_col_widths = [18 * mm, 18 * mm, 18 * mm, 24 * mm, 14 * mm]
        dd_tbl = _build_drawdown_table(dd_df, col_widths=dd_col_widths)
        if dd_tbl:
            left_story.append(dd_tbl)
        left_story.append(Spacer(1, 1.5 * mm))

    # Monthly returns bar chart
    left_story.append(Paragraph("<b>Monthly Returns (% AUM)</b>", section_style))
    monthly_img = _chart_image(monthly_b64, width=monthly_pdf_w)
    left_story.append(monthly_img)

    # ---- Position frames (layout computed during chart generation above) ----
    # Draw left column
    left_frame = RLFrame(left_x, mid_frame_bottom, left_w, mid_frame_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    left_frame.addFromList(left_story, c)

    # ---- RIGHT COLUMN (Performance chart) ----
    right_x = left_x + left_w + col_gap
    right_story = []
    perf_img = _chart_image(perf_b64, width=perf_pdf_w, height=perf_pdf_h)
    right_story.append(perf_img)

    right_frame = RLFrame(right_x, mid_frame_bottom, right_w, mid_frame_h,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)
    right_frame.addFromList(right_story, c)

    # ---- BOTTOM ROW 1 (single 1×3 figure: histogram, volatility, timezone) ----
    row1_img = _chart_image(row1_b64, width=row1_pdf_w)
    row1_frame = RLFrame(x_start, row1_y, usable_w, row1_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    row1_frame.addFromList([row1_img], c)

    # ---- BOTTOM ROW 2 (timezone cumulative returns: London, NY, Asia) ----
    tz_cum_img = _chart_image(tz_cum_b64, width=tz_cum_pdf_w, height=tz_cum_pdf_h)
    row2_frame = RLFrame(x_start, row2_y, usable_w, row2_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    row2_frame.addFromList([tz_cum_img], c)

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
    """Generate a single-page portrait A4 portfolio PDF report. Returns path to PDF file."""
    from reportlab.pdfgen import canvas as canvasmod
    from reportlab.platypus.frames import Frame as RLFrame

    pdf_path = os.path.join(output_path, f"{report_name}.pdf")

    page_w, page_h = A4  # 210 x 297 mm (portrait)
    margin_l = 10 * mm
    margin_r = 10 * mm
    margin_t = 10 * mm
    margin_b = 8 * mm

    usable_w = page_w - margin_l - margin_r
    usable_h = page_h - margin_t - margin_b

    header_h = 14 * mm
    _scale = 2.0

    # --- Styles ---
    styles = getSampleStyleSheet()
    section_style = ParagraphStyle(
        "PTFSection", parent=styles["Normal"], fontSize=8,
        textColor=colors.black, fontName="Helvetica-Bold",
        leading=9, spaceBefore=1 * mm, spaceAfter=1 * mm,
    )

    # --- Compute data ---
    stats = {}
    for col in ptf_daily.columns:
        col_stats = metrics.compute_all_metrics(ptf_daily[col])
        stats[col] = col_stats

    dd_df = metrics.drawdown_table(portfolio, top=5)

    # --- Layout geometry ---
    # Middle section: left 50% (stats + drawdown), right 48% (performance chart)
    left_w = usable_w * 0.50
    right_w = usable_w * 0.48
    col_gap = usable_w * 0.02

    # Row positions (from page top)
    row1_top_from_top = 170 * mm
    row1_h = 40 * mm
    row2_top_from_top = 215 * mm
    row2_h = 45 * mm

    row1_top_y = page_h - row1_top_from_top
    row1_y = row1_top_y - row1_h
    row2_top_y = page_h - row2_top_from_top
    row2_y = row2_top_y - row2_h

    mid_frame_top = (page_h - margin_t - 13 * mm) - 1 * mm
    mid_frame_bottom = row1_top_y + 2 * mm
    mid_frame_h = mid_frame_top - mid_frame_bottom

    # --- Generate charts ---
    # Performance chart (right column)
    perf_pdf_w = right_w - 2 * mm
    perf_pdf_h = perf_pdf_w * 1.3
    perf_fig = (perf_pdf_w / 72 * _scale, perf_pdf_h / 72 * _scale)
    perf_b64 = charts.performance_summary_formal(portfolio, title=report_name,
                                                   figsize=perf_fig, fontscale=_scale)

    # Portfolio vs strategies (full width row)
    row1_pdf_w = usable_w
    row1_pdf_h = row1_h - 2 * mm
    row1_fig = (row1_pdf_w / 72 * _scale, row1_pdf_h / 72 * _scale)
    strat_b64 = charts.portfolio_strategies_formal(portfolio, strategy_returns, rel_returns,
                                                     figsize=row1_fig, fontscale=_scale)

    # Bottom row: correlation heatmap (left) + rolling vol (right)
    has_corr = strategy_returns.shape[1] >= 2
    if has_corr:
        half_w = usable_w * 0.48
        corr_pdf_w = half_w
        corr_pdf_h = row2_h - 2 * mm
        corr_fig = (corr_pdf_w / 72 * _scale, corr_pdf_h / 72 * _scale)
        corr_b64 = charts.correlation_heatmap_formal(strategy_returns,
                                                       figsize=corr_fig, fontscale=_scale)

        vol_pdf_w = half_w
        vol_pdf_h = row2_h - 2 * mm
        vol_fig = (vol_pdf_w / 72 * _scale, vol_pdf_h / 72 * _scale)
        vol_b64 = charts.rolling_vol_chart_formal(portfolio,
                                                    figsize=vol_fig, fontscale=_scale)
    else:
        # Rolling vol gets full width
        vol_pdf_w = usable_w
        vol_pdf_h = row2_h - 2 * mm
        vol_fig = (vol_pdf_w / 72 * _scale, vol_pdf_h / 72 * _scale)
        vol_b64 = charts.rolling_vol_chart_formal(portfolio,
                                                    figsize=vol_fig, fontscale=_scale)
        corr_b64 = None

    # --- Build the PDF using canvas ---
    c = canvasmod.Canvas(pdf_path, pagesize=A4)

    # ---- HEADER ----
    x_start = margin_l
    y_top = page_h - margin_t

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.black)
    c.drawString(x_start, y_top - 5 * mm, f"Portfolio: {report_name}")

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.Color(0.3, 0.3, 0.3))
    agg_method = "Average Returns" if rel_returns else "Sum of Cash PnL"
    c.drawString(x_start, y_top - 10 * mm, f"Aggregation: {agg_method}")
    c.drawRightString(page_w - margin_r, y_top - 10 * mm,
                      f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}")

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    y_hrule = y_top - 13 * mm
    c.line(x_start, y_hrule, page_w - margin_r, y_hrule)

    # ---- LEFT COLUMN (stats + drawdown tables) ----
    left_x = x_start
    left_story = []

    # Summary Statistics heading
    left_story.append(Paragraph("<b>Summary Statistics</b>", section_style))

    # Multi-column stats table
    metric_names = list(next(iter(stats.values())).keys())
    header = [""] + list(stats.keys())
    data = [header]
    for m in metric_names:
        row = [m]
        for col_name in stats:
            v = stats[col_name].get(m, "")
            row.append(f"{v:.2f}" if isinstance(v, float) else str(v))
        data.append(row)

    n_cols = len(header)
    label_w = left_w - 18 * mm * min(n_cols - 1, 3)
    val_w = 18 * mm
    col_widths = [max(label_w, 20 * mm)] + [val_w] * (n_cols - 1)
    # Ensure total doesn't exceed left_w
    total = sum(col_widths[:n_cols])
    if total > left_w:
        scale_f = left_w / total
        col_widths = [w * scale_f for w in col_widths]

    summary_tbl = Table(data, colWidths=col_widths[:n_cols])
    summary_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, -1), 6),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_story.append(summary_tbl)
    left_story.append(Spacer(1, 1.5 * mm))

    # Drawdown table
    if not dd_df.empty:
        left_story.append(Paragraph("<b>Drawdown Analysis</b>", section_style))
        dd_col_widths = [18 * mm, 18 * mm, 18 * mm, 18 * mm, 14 * mm]
        dd_tbl = _build_drawdown_table(dd_df, col_widths=dd_col_widths)
        if dd_tbl:
            left_story.append(dd_tbl)

    # Draw left column
    left_frame = RLFrame(left_x, mid_frame_bottom, left_w, mid_frame_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    left_frame.addFromList(left_story, c)

    # ---- RIGHT COLUMN (Performance chart) ----
    right_x = left_x + left_w + col_gap
    right_story = []
    perf_img = _chart_image(perf_b64, width=perf_pdf_w, height=perf_pdf_h)
    right_story.append(perf_img)

    right_frame = RLFrame(right_x, mid_frame_bottom, right_w, mid_frame_h,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)
    right_frame.addFromList(right_story, c)

    # ---- ROW 1: Portfolio vs Strategies (full width) ----
    strat_img = _chart_image(strat_b64, width=row1_pdf_w, height=row1_pdf_h)
    row1_frame = RLFrame(x_start, row1_y, usable_w, row1_h,
                         leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
    row1_frame.addFromList([strat_img], c)

    # ---- ROW 2: Correlation heatmap + Rolling volatility ----
    if has_corr and corr_b64:
        corr_img = _chart_image(corr_b64, width=corr_pdf_w, height=corr_pdf_h)
        corr_frame = RLFrame(x_start, row2_y, usable_w * 0.50, row2_h,
                             leftPadding=0, rightPadding=0,
                             topPadding=0, bottomPadding=0)
        corr_frame.addFromList([corr_img], c)

        vol_img = _chart_image(vol_b64, width=vol_pdf_w, height=vol_pdf_h)
        vol_frame = RLFrame(x_start + usable_w * 0.52, row2_y, usable_w * 0.48, row2_h,
                            leftPadding=0, rightPadding=0,
                            topPadding=0, bottomPadding=0)
        vol_frame.addFromList([vol_img], c)
    else:
        vol_img = _chart_image(vol_b64, width=vol_pdf_w, height=vol_pdf_h)
        vol_frame = RLFrame(x_start, row2_y, usable_w, row2_h,
                            leftPadding=0, rightPadding=0,
                            topPadding=0, bottomPadding=0)
        vol_frame.addFromList([vol_img], c)

    c.save()
    return pdf_path
