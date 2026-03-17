"""ApticReports — FastHTML web app for backtest processing and portfolio reporting."""

import os
import uuid
import traceback

from fasthtml.common import *

# ── App setup ────────────────────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EOD_DIR = os.path.join(DATA_DIR, "eod")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(EOD_DIR, exist_ok=True)

custom_css = Link(rel="stylesheet", href="/static/style.css")
app, rt = fast_app(hdrs=[custom_css], static_path=os.path.join(os.path.dirname(__file__), "static"))


# ── Shared UI components ─────────────────────────────────────────────────────

def page_shell(*content, active_tab="backtest"):
    """Main page layout with tab navigation."""
    return Title("ApticReports"), Main(
        H1("ApticReports"),
        Nav(
            A("Backtest", hx_get="/tab/backtest", hx_target="#tab-content",
              cls="active" if active_tab == "backtest" else "",
              **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));this.classList.add('active')"}),
            A("Portfolio", hx_get="/tab/portfolio", hx_target="#tab-content",
              cls="active" if active_tab == "portfolio" else "",
              **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));this.classList.add('active')"}),
            cls="tabs",
        ),
        Div(*content, id="tab-content"),
        cls="container",
    )


def metrics_display(stats: dict):
    """Render metrics as a grid."""
    items = []
    for k, v in stats.items():
        val_str = f"{v:.2f}" if isinstance(v, float) else str(v)
        items.append(Div(Span(k, cls="label"), Span(val_str, cls="value"), cls="metric-item"))
    return Div(*items, cls="metrics-grid")


def chart_img(b64: str, alt: str = "Chart"):
    """Render an inline base64 chart image."""
    return Div(Img(src=f"data:image/png;base64,{b64}", alt=alt), cls="chart-container")


def download_links(files: dict):
    """Render download buttons for generated files."""
    links = []
    for label, path in files.items():
        if path and os.path.exists(path):
            fname = os.path.basename(path)
            links.append(A(f"Download {label}", href=f"/download/{fname}"))
    return Div(*links, cls="downloads") if links else ""


def processing_indicator():
    return Div(Div(cls="spinner"), "Processing...", cls="processing")


def error_box(msg: str):
    return Div(f"Error: {msg}", cls="error-msg")


# ── Routes ───────────────────────────────────────────────────────────────────

@rt("/")
def get():
    return page_shell(backtest_tab())


@rt("/tab/backtest")
def get():
    return backtest_tab()


@rt("/tab/portfolio")
def get():
    return portfolio_tab()


# ── Backtest Tab ─────────────────────────────────────────────────────────────

def backtest_tab():
    return Div(
        H2("Backtest Processing"),
        P("Upload NinjaTrader trade CSV files to generate daily PnL and reports."),

        # EOD files directory
        Div(
            H4("EOD Price Files"),
            P(f"Place EOD price CSVs (e.g. EURUSD_EOD.csv) in: ", Code(os.path.abspath(EOD_DIR)),
              style="font-size:0.85rem; color:#666;"),
            cls="form-section",
        ),

        # Upload form
        Form(
            Div(
                H4("Trade File"),
                Div(
                    Input(type="file", name="tradefile", accept=".csv", required=True),
                    cls="upload-area",
                ),
                cls="form-section",
            ),
            Div(
                H4("Parameters"),
                Div(
                    Div(
                        Label("Timezone", fr="timezone"),
                        Select(
                            Option("America/Chicago", value="America/Chicago"),
                            Option("America/New_York", value="America/New_York"),
                            Option("Europe/London", value="Europe/London", selected=True),
                            Option("Europe/Berlin", value="Europe/Berlin"),
                            name="timezone", id="timezone",
                        ),
                    ),
                    Div(
                        Label("AUM", fr="aum"),
                        Input(type="number", name="aum", id="aum", value="100000000", step="1000000"),
                    ),
                    Div(
                        Label("Strategy Name", fr="strategy"),
                        Input(type="text", name="strategy", id="strategy", value="CIT1", required=True),
                    ),
                    Div(
                        Label("Timeframe", fr="timeframe"),
                        Select(
                            Option("15 min", value="15 min"),
                            Option("30 min", value="30 min"),
                            Option("60 min", value="60 min"),
                            Option("240 min", value="240 min", selected=True),
                            Option("1440 min", value="1440 min"),
                            name="timeframe", id="timeframe",
                        ),
                    ),
                    cls="param-grid",
                ),
                Div(
                    Label(
                        Input(type="checkbox", name="is_future", id="is_future"),
                        " Futures contract",
                    ),
                    Label("Point value", fr="pt_value", style="margin-left:1rem;"),
                    Input(type="number", name="pt_value", id="pt_value", value="1", step="0.01",
                          style="width:120px; display:inline-block;"),
                    style="margin-top:0.5rem;",
                ),
                cls="form-section",
            ),
            Button("Process Backtest", type="submit", cls="primary"),
            hx_post="/process/backtest",
            hx_target="#backtest-results",
            hx_indicator="#bt-spinner",
            hx_encoding="multipart/form-data",
        ),
        Div(processing_indicator(), id="bt-spinner", cls="htmx-indicator"),
        Div(id="backtest-results"),
    )


@rt("/process/backtest")
async def post(tradefile: UploadFile, timezone: str, aum: float, strategy: str,
               timeframe: str, is_future: bool = False, pt_value: float = 1.0):
    try:
        # Save uploaded file
        session_id = str(uuid.uuid4())[:8]
        filename = tradefile.filename
        save_path = os.path.join(UPLOAD_DIR, f"{session_id}_{filename}")
        content = await tradefile.read()
        with open(save_path, "wb") as f:
            f.write(content)

        # Process
        from .processing.daily_pnl import process_backtest
        result = process_backtest(
            filepath=save_path,
            eod_path=EOD_DIR,
            aum=aum,
            strategy=strategy,
            timeframe=timeframe,
            is_future=is_future,
            pt_value=pt_value,
            timezone=timezone,
            output_path=OUTPUT_DIR,
        )

        # Compute metrics
        from .reporting.metrics import compute_all_metrics
        daily_returns = result["pnl_daily"] / aum
        stats = compute_all_metrics(daily_returns, result["pnl_raw"], aum)

        # Generate charts
        from .reporting.charts import performance_summary, monthly_returns_bar, rolling_vol_chart
        perf_chart = performance_summary(daily_returns,
                                         title=f"{strategy} {result['ccy_pair']}")
        monthly_chart = monthly_returns_bar(daily_returns)

        # Generate PDF
        from .reporting.pdf_report import generate_backtest_pdf
        pdf_path = generate_backtest_pdf(
            daily_returns=daily_returns,
            pnl_raw=result["pnl_raw"],
            aum=aum,
            strategy=strategy,
            ccy_pair=result["ccy_pair"],
            timeframe=timeframe,
            strat_dir=result["strat_dir"],
            filestem=result["filestem"],
            output_path=OUTPUT_DIR,
        )
        result["files"]["pdf"] = pdf_path

        # Build results UI
        return Div(
            H3(f"Results: {strategy} {result['ccy_pair']} {timeframe} {result['strat_dir']}"),
            metrics_display(stats),
            chart_img(perf_chart, "Performance Summary"),
            chart_img(monthly_chart, "Monthly Returns"),
            download_links({
                "Daily PnL CSV": result["files"]["daily"],
                "Processed Trades": result["files"]["trades"],
                "Raw PnL": result["files"]["raw"],
                "PDF Report": result["files"].get("pdf"),
            }),
            cls="results-card",
        )

    except Exception as e:
        return error_box(f"{e}\n\n{traceback.format_exc()}")


# ── Portfolio Tab ────────────────────────────────────────────────────────────

def portfolio_tab():
    return Div(
        H2("Portfolio Combination"),
        P("Upload daily PnL CSV files (from backtest processing) to combine into a portfolio."),

        Form(
            Div(
                H4("Daily PnL Files"),
                Div(
                    Input(type="file", name="pnlfiles", accept=".csv", multiple=True, required=True),
                    cls="upload-area",
                ),
                cls="form-section",
            ),
            Div(
                H4("Parameters"),
                Div(
                    Div(
                        Label("Report Name", fr="report_name"),
                        Input(type="text", name="report_name", id="report_name",
                              value="Portfolio", required=True),
                    ),
                    Div(
                        Label("AUM", fr="ptf_aum"),
                        Input(type="number", name="aum", id="ptf_aum", value="100000000",
                              step="1000000"),
                    ),
                    Div(
                        Label("Start Date (dd/mm/yyyy)", fr="start_date"),
                        Input(type="text", name="start_date", id="start_date",
                              placeholder="01/01/2010"),
                    ),
                    Div(
                        Label("End Date (dd/mm/yyyy)", fr="end_date"),
                        Input(type="text", name="end_date", id="end_date",
                              placeholder="31/12/2025"),
                    ),
                    cls="param-grid",
                ),
                Div(
                    Label(
                        Input(type="checkbox", name="rel_returns", id="rel_returns"),
                        " Relative returns (average % returns instead of sum)",
                    ),
                    Label(
                        Input(type="checkbox", name="ptf_of_ptf", id="ptf_of_ptf"),
                        " Portfolio of portfolios",
                    ),
                    style="margin-top:0.5rem;",
                ),
                cls="form-section",
            ),

            # Benchmark files (optional)
            Div(
                H4("Benchmark Index (optional)"),
                P(f"Place NewEdge_CTA_Historical.csv in: ", Code(os.path.abspath(EOD_DIR)),
                  style="font-size:0.85rem; color:#666;"),
                cls="form-section",
            ),

            Button("Build Portfolio", type="submit", cls="primary"),
            hx_post="/process/portfolio",
            hx_target="#portfolio-results",
            hx_indicator="#ptf-spinner",
            hx_encoding="multipart/form-data",
        ),
        Div(processing_indicator(), id="ptf-spinner", cls="htmx-indicator"),
        Div(id="portfolio-results"),
    )


@rt("/process/portfolio")
async def post(pnlfiles: list[UploadFile], report_name: str, aum: float,
               start_date: str = "", end_date: str = "",
               rel_returns: bool = False, ptf_of_ptf: bool = False):
    try:
        # Save uploaded files
        session_id = str(uuid.uuid4())[:8]
        saved_paths = []
        for uf in pnlfiles:
            fname = f"{session_id}_{uf.filename}"
            save_path = os.path.join(UPLOAD_DIR, fname)
            content = await uf.read()
            with open(save_path, "wb") as f:
                f.write(content)
            saved_paths.append(save_path)

        # Process
        from .processing.portfolio import combine_portfolio
        result = combine_portfolio(
            filepaths=saved_paths,
            aum=aum,
            report_name=report_name,
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            rel_returns=rel_returns,
            ptf_of_ptf=ptf_of_ptf,
            index_path=EOD_DIR,
            output_path=OUTPUT_DIR,
        )

        # Metrics
        from .reporting.metrics import compute_all_metrics
        stats = compute_all_metrics(result["portfolio"])

        # Charts
        from .reporting.charts import (
            performance_summary, portfolio_strategies_chart, correlation_heatmap,
        )
        perf_chart = performance_summary(result["portfolio"], title=report_name)
        strat_chart = portfolio_strategies_chart(
            result["portfolio"], result["strategy_returns"], rel_returns
        )

        # Generate PDF
        from .reporting.pdf_report import generate_portfolio_pdf
        pdf_path = generate_portfolio_pdf(
            ptf_daily=result["ptf_daily"],
            portfolio=result["portfolio"],
            strategy_returns=result["strategy_returns"],
            metadata=result["metadata"],
            report_name=report_name,
            rel_returns=rel_returns,
            output_path=OUTPUT_DIR,
        )
        result["files"]["pdf"] = pdf_path

        # Correlation heatmap (if multiple strategies)
        corr_html = ""
        if result["strategy_returns"].shape[1] >= 2:
            corr_chart = correlation_heatmap(result["strategy_returns"])
            corr_html = chart_img(corr_chart, "Strategy Correlations")

        # Strategy metadata table
        meta_rows = []
        meta = result["metadata"]
        if not meta.empty:
            for _, row in meta.iterrows():
                meta_rows.append(Tr(*[Td(str(v)) for v in row.values]))
        meta_table = ""
        if meta_rows:
            meta_table = Div(
                H4("Strategies"),
                Table(
                    Thead(Tr(Th("Pair"), Th("Strategy"), Th("Timeframe"), Th("Direction"))),
                    Tbody(*meta_rows),
                ),
                style="margin:1rem 0; font-size:0.9rem;",
            )

        return Div(
            H3(f"Portfolio: {report_name}"),
            meta_table,
            metrics_display(stats),
            chart_img(perf_chart, "Performance Summary"),
            chart_img(strat_chart, "Portfolio vs Strategies"),
            corr_html,
            download_links({
                "Daily PnL CSV": result["files"]["daily"],
                "Monthly PnL CSV": result["files"]["monthly"],
                "Portfolio Only CSV": result["files"]["only_daily"],
                "PDF Report": result["files"].get("pdf"),
            }),
            cls="results-card",
        )

    except Exception as e:
        return error_box(f"{e}\n\n{traceback.format_exc()}")


# ── File downloads ───────────────────────────────────────────────────────────

@rt("/download/{fname:path}")
def get(fname: str):
    filepath = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(filepath):
        return error_box(f"File not found: {fname}")
    return FileResponse(filepath, filename=fname)


# ── Run ──────────────────────────────────────────────────────────────────────

serve()
