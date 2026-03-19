"""ApticReports — FastHTML web app for backtest processing and portfolio reporting."""

import os
import hashlib
import hmac
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

# ── Auth ─────────────────────────────────────────────────────────────────────

APP_PASSWORD = os.environ.get("APP_PASSWORD", "aptic2024")
LOGIN_SKIP = frozenset(["/login", "/static"])


def _check_auth(req, sess):
    """Beforeware: redirect to /login if not authenticated."""
    if any(req.url.path.startswith(p) for p in LOGIN_SKIP):
        return
    if not sess.get("authed"):
        return RedirectResponse("/login", status_code=303)


bware = Beforeware(_check_auth, skip=list(LOGIN_SKIP))

custom_css = Link(rel="stylesheet", href="/static/style.css")
app, rt = fast_app(
    hdrs=[custom_css],
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    before=bware,
    secret_key=os.environ.get("SESSION_SECRET", hashlib.sha256(APP_PASSWORD.encode()).hexdigest()),
)


# ── Shared UI components ─────────────────────────────────────────────────────

def page_shell(*content, active_tab="backtest"):
    """Main page layout with tab navigation."""
    return Title("ApticReports"), Main(
        Div(
            H1("ApticReports", style="margin:0;"),
            A("Logout", href="/logout", cls="logout-btn"),
            style="display:flex; justify-content:space-between; align-items:center;",
        ),
        Nav(
            A("Backtest", hx_get="/tab/backtest", hx_target="#tab-content",
              cls="active" if active_tab == "backtest" else "",
              **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));this.classList.add('active')"}),
            A("Portfolio", hx_get="/tab/portfolio", hx_target="#tab-content",
              cls="active" if active_tab == "portfolio" else "",
              **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));this.classList.add('active')"}),
            A("Reference Data", hx_get="/tab/refdata", hx_target="#tab-content",
              cls="active" if active_tab == "refdata" else "",
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


# ── Auth routes ──────────────────────────────────────────────────────────────

def login_page(error: str = ""):
    return Title("ApticReports — Login"), Main(
        Div(
            H1("ApticReports"),
            Form(
                Div(
                    Label("Password", fr="password"),
                    Input(type="password", name="password", id="password",
                          placeholder="Enter password", autofocus=True, required=True),
                    cls="form-section",
                ),
                error_box(error) if error else "",
                Button("Sign in", type="submit", cls="primary"),
                method="post", action="/login",
            ),
            cls="login-card",
        ),
        cls="container login-container",
    )


@rt("/login")
def get():
    return login_page()


@rt("/login")
def post(password: str, sess):
    if hmac.compare_digest(password, APP_PASSWORD):
        sess["authed"] = True
        return RedirectResponse("/", status_code=303)
    return login_page(error="Wrong password. Try again.")


@rt("/logout")
def get(sess):
    sess.clear()
    return RedirectResponse("/login", status_code=303)


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
    # Check for available EOD files
    eod_files = sorted(f for f in os.listdir(EOD_DIR) if f.endswith("_EOD.csv")) if os.path.isdir(EOD_DIR) else []
    eod_notice = Div(
        P("Available EOD files: ", ", ".join(eod_files) if eod_files else "None",
          style="font-size:0.85rem; color:#666;"),
        P(A("Upload EOD files in Reference Data tab →", hx_get="/tab/refdata", hx_target="#tab-content",
             **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));document.querySelector('.tabs a:nth-child(3)').classList.add('active')"}),
          style="font-size:0.85rem;") if not eod_files else "",
        cls="form-section",
    )

    return Div(
        H2("Backtest Processing"),
        P("Upload NinjaTrader trade CSV files to generate daily PnL and reports."),
        eod_notice,

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
                P("Upload NewEdge_CTA_Historical.csv via the ",
                  A("Reference Data tab", hx_get="/tab/refdata", hx_target="#tab-content",
                    **{"hx-on::after-request": "document.querySelectorAll('.tabs a').forEach(a=>a.classList.remove('active'));document.querySelector('.tabs a:nth-child(3)').classList.add('active')"}),
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


# ── Reference Data Tab ───────────────────────────────────────────────────

@rt("/tab/refdata")
def get():
    return refdata_tab()


def _eod_file_list():
    """Build the list of currently uploaded EOD/reference files."""
    if not os.path.isdir(EOD_DIR):
        return Div(P("No reference data uploaded yet.", style="color:#666;"))
    files = sorted(os.listdir(EOD_DIR))
    if not files:
        return Div(P("No reference data uploaded yet.", style="color:#666;"))
    rows = []
    for f in files:
        fpath = os.path.join(EOD_DIR, f)
        size_kb = os.path.getsize(fpath) / 1024
        rows.append(Tr(
            Td(f),
            Td(f"{size_kb:.1f} KB"),
            Td(Button("Delete", hx_delete=f"/refdata/{f}", hx_target="#refdata-files",
                       hx_confirm=f"Delete {f}?", cls="small danger")),
        ))
    return Table(
        Thead(Tr(Th("Filename"), Th("Size"), Th(""))),
        Tbody(*rows),
        style="width:100%; font-size:0.9rem;",
    )


def refdata_tab():
    return Div(
        H2("Reference Data"),
        P("Upload EOD price files, FX rate files, and benchmark indices used by backtests."),

        Div(
            H4("Upload Reference Files"),
            P("Accepted formats: ", Code("EURUSD_EOD.csv"), ", ", Code("USDJPY_EOD.csv"),
              ", ", Code("NewEdge_CTA_Historical.csv"), ", etc.",
              style="font-size:0.85rem; color:#666;"),
            P("CSV format: header row, skip row, then [Date (dd/mm/yyyy), Price] columns.",
              style="font-size:0.85rem; color:#666;"),
            Form(
                Div(
                    Input(type="file", name="reffiles", accept=".csv", multiple=True, required=True),
                    cls="upload-area",
                ),
                Button("Upload Files", type="submit", cls="primary"),
                hx_post="/refdata/upload",
                hx_target="#refdata-files",
                hx_encoding="multipart/form-data",
                style="margin-top:0.5rem;",
            ),
            cls="form-section",
        ),

        Div(
            H4("Current Reference Files"),
            Div(_eod_file_list(), id="refdata-files"),
            cls="form-section",
        ),
    )


@rt("/refdata/upload")
async def post(reffiles: list[UploadFile]):
    try:
        uploaded = []
        for uf in reffiles:
            fname = uf.filename
            save_path = os.path.join(EOD_DIR, fname)
            content = await uf.read()
            with open(save_path, "wb") as f:
                f.write(content)
            uploaded.append(fname)
        return Div(
            Div(f"Uploaded: {', '.join(uploaded)}", cls="success-msg"),
            _eod_file_list(),
        )
    except Exception as e:
        return Div(error_box(str(e)), _eod_file_list())


@rt("/refdata/{fname:path}")
def delete(fname: str):
    fpath = os.path.join(EOD_DIR, fname)
    if os.path.exists(fpath):
        os.remove(fpath)
    return _eod_file_list()


# ── File downloads ───────────────────────────────────────────────────────────

@rt("/download/{fname:path}")
def get(fname: str):
    filepath = os.path.join(OUTPUT_DIR, fname)
    if not os.path.exists(filepath):
        return error_box(f"File not found: {fname}")
    return FileResponse(filepath, filename=fname)


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    serve(
        appname="app.main" if __package__ else None,
        port=int(os.environ.get("PORT", 5001)),
        reload=os.environ.get("RENDER") is None,
    )
