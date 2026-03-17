# ApticReports Python Web App — Implementation Plan

## Overview

Port the R backtest/portfolio reporting system to a Python web app using **FastHTML** (Jeremy Howard's framework) with **HTMX** for interactivity. Two-tab UI: **Backtest** (load trade files → daily PnL) and **Portfolio** (combine daily PnL files → portfolio).

---

## Architecture

```
ApticReports/
├── app/
│   ├── main.py              # FastHTML app, routes, tabs
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── trades.py         # NinjaTrader CSV parser, trade loading
│   │   ├── daily_pnl.py      # Trade splitting, daily PnL calc (port of daily_PnL_v5.R)
│   │   ├── portfolio.py      # Portfolio combination (port of PortfolioMakeReport.R)
│   │   └── eod.py            # EOD price loading, currency conversion
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── metrics.py        # Performance metrics (Sharpe, drawdown, etc.)
│   │   ├── charts.py         # Matplotlib/plotly chart generation
│   │   └── pdf_report.py     # PDF generation (matplotlib + reportlab or weasyprint)
│   ├── static/
│   │   └── style.css         # Minimal custom CSS (Pico handles most styling)
│   └── templates/            # Any Jinja snippets if needed (FastHTML mostly inline)
├── data/
│   └── eod/                  # EOD price CSV files (EURUSD_EOD.csv, etc.)
├── uploads/                  # Temp storage for uploaded files
├── output/                   # Generated reports
├── requirements.txt
└── README.md
```

---

## Step-by-step Implementation

### Step 1: Project scaffold & dependencies

Create `requirements.txt`:
```
python-fasthtml
pandas
matplotlib
reportlab
plotly
```

Create `app/` directory structure, `main.py` with minimal FastHTML app, two-tab layout using Pico CSS tabs (simple `<nav>` + HTMX `hx-get` to swap tab content).

### Step 2: Core processing — EOD prices & currency conversion (`app/processing/eod.py`)

Port from R (`daily_PnL_v5.R`):
- `load_eod_prices(ccy_pair, path)` → pandas Series indexed by datetime
- `load_usd_conversion(ccy_pair, path, pnl_ccy="USD")` → pandas Series
- `get_nearest_eod(dt, eod_times, direction=1)` → nearest EOD datetime
- `add_time_to_date(dates, eod_hour=17, tz="Europe/London")` → datetime index

Key: Use `pandas` DatetimeIndex with timezone support instead of R's `xts`.

### Step 3: Core processing — Trade loading (`app/processing/trades.py`)

Port `get.ninja.trades()`:
- `load_ninja_trades(filepath)` → DataFrame with columns: Instrument, Direction, Entry_price, Exit_price, Entry_time, Exit_time, Quantity, Entry_name
- Parse datetime formats: `dd/mm/yyyy HH:MM:SS` and `dd/mm/yyyy HH:MM`
- Extract currency pair from Instrument (strip "$" prefix)
- Extract strategy direction from Entry_name

### Step 4: Core processing — Daily PnL calculation (`app/processing/daily_pnl.py`)

Port `make.daily.pnl()` — this is the critical algorithm:

1. **`split_trades(trades_df, eod_prices)`** — Split multi-day trades into daily segments:
   - For each trade, find EOD dates between entry and exit
   - Same-day trades: keep as-is
   - Multi-day: create synthetic sub-trades at EOD boundaries
   - Track TradeID (original) and SplitID (sequence position)

2. **`calculate_daily_pnl(trades_df, eod_prices, usd_conv)`** → dict with:
   - `trades`: all trades DataFrame (split + original)
   - `pnl_daily`: daily PnL Series (USD)
   - `pnl_raw`: raw unsplit PnL Series (USD)

3. **`process_backtest(filepath, eod_path, aum, strategy, timeframe, is_future, pt_value, timezone)`** — orchestrator:
   - Load trades → load EOD → load conversion → split → calculate → return results
   - Save CSV outputs: `_processed.csv`, `_pnl_daily.csv`, `_pnl_raw.csv`

### Step 5: Core processing — Portfolio combination (`app/processing/portfolio.py`)

Port from `Unreactive_PortfolioMakeReport.R`:

- `load_daily_pnl_files(filepaths)` → list of Series, with metadata parsed from filenames
- `combine_portfolio(pnl_series_list, rel_returns=False)` → combined daily PnL Series
  - `rel_returns=True`: average of percentage returns
  - `rel_returns=False`: sum of cash PnLs
- `aggregate_monthly(daily_pnl)` → monthly PnL Series
- Save outputs: `_pnl_daily.csv`, `_pnl_monthly.csv`

### Step 6: Reporting — Performance metrics (`app/reporting/metrics.py`)

Calculate all key metrics from daily PnL series:
- Annualized return, annualized volatility
- Sharpe ratio, Sortino ratio
- Max drawdown (depth, duration, recovery)
- Calmar ratio
- Win rate, profit factor
- Monthly returns table
- Cumulative returns series

### Step 7: Reporting — Charts (`app/reporting/charts.py`)

Generate charts using **matplotlib** (for PDF) and optionally **plotly** (for inline web preview):

- **Equity curve** (cumulative PnL)
- **Drawdown chart** (underwater plot)
- **Monthly returns heatmap** (year × month grid)
- **Daily PnL bar chart**
- **Distribution histogram** of daily returns

For PDF: matplotlib renders to PNG/bytes → embedded in PDF.
For web preview: render matplotlib to base64 PNG, serve inline.

### Step 8: Reporting — PDF generation (`app/reporting/pdf_report.py`)

Use **reportlab** to build PDF reports:
- Title page with strategy name, date range, AUM
- Performance summary table (key metrics)
- Equity curve chart
- Drawdown chart
- Monthly returns heatmap
- Trade statistics (for backtest reports)
- For portfolio: individual strategy breakdown + combined view

### Step 9: FastHTML UI — Backtest Tab (`app/main.py`)

**Tab 1: Backtest Processing**

Layout (top to bottom):
1. **File upload area** — multi-file upload for NinjaTrader CSVs (`hx-post="/upload/backtest"`)
2. **Parameters form** (appears after upload):
   - Timezone dropdown (Chicago/New York/London/Berlin)
   - AUM input (default 100,000,000)
   - Strategy name input
   - Timeframe dropdown (15min, 30min, 60min, 240min, 1440min)
   - Futures checkbox → conditional point value input
3. **Process button** → `hx-post="/process/backtest"` with progress indicator
4. **Results area** (swapped in via HTMX after processing):
   - Summary metrics card
   - Inline equity curve chart (base64 PNG)
   - Download links: Daily PnL CSV, Processed trades CSV, PDF Report

HTMX flow:
- Upload file → server validates, stores temp, returns parameter form
- Submit params → server processes, returns results partial
- Download links serve files from `/output/` directory

### Step 10: FastHTML UI — Portfolio Tab (`app/main.py`)

**Tab 2: Portfolio Combination**

Layout:
1. **File upload area** — multi-file upload for `*_pnl_daily.csv` files
2. **Parameters form**:
   - Portfolio/report name input
   - AUM input
   - Relative returns checkbox (average % returns vs sum cash PnL)
   - Date range picker (start/end, optional — defaults to full overlap)
3. **Process button** → `hx-post="/process/portfolio"`
4. **Results area**:
   - Portfolio summary metrics
   - Combined equity curve
   - Individual strategy breakdown table
   - Download links: Portfolio daily PnL CSV, Monthly CSV, PDF Report

### Step 11: Tab navigation & app shell

```python
from fasthtml.common import *

app, rt = fast_app(hdrs=[picolink, Style(custom_css)])

@rt('/')
def get():
    return Title("ApticReports"), Main(
        H1("ApticReports"),
        Nav(
            A("Backtest", hx_get="/tab/backtest", hx_target="#tab-content",
              cls="active", id="tab-bt"),
            A("Portfolio", hx_get="/tab/portfolio", hx_target="#tab-content",
              id="tab-pf"),
        ),
        Div(id="tab-content", hx_get="/tab/backtest", hx_trigger="load"),
        cls="container"
    )
```

---

## Key Design Decisions

1. **pandas over xts** — DatetimeIndex with tz support handles everything xts does
2. **matplotlib for charts** — Works in PDF and web (base64 inline), no JS needed
3. **reportlab for PDF** — Pure Python, no LaTeX dependency (simpler deployment)
4. **HTMX for interactivity** — File upload → form → results flow, no page reloads
5. **Pico CSS** — Clean default styling with zero config, comes with FastHTML
6. **Temp file management** — Upload to `uploads/`, output to `output/`, clean up old files

## Implementation Order

1. Steps 1-4: Get the core backtest processing working (test with a real file)
2. Steps 5-6: Portfolio combination + metrics
3. Steps 7-8: Charts and PDF
4. Steps 9-11: Wire up the FastHTML UI
5. Integration testing with real NinjaTrader files
