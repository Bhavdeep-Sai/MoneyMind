# MoneyMind — Personal Finance Dashboard

A production-ready personal finance analyzer built entirely in Python.  
Upload any bank export CSV, and MoneyMind automatically cleans, categorizes, and
visualizes your transactions in a real-time interactive dashboard — with savings
recommendations, trend analysis, static chart exports, and a fully themed UI.

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Tech Stack & Why](#tech-stack--why)
4. [Quickstart](#quickstart)
5. [Running the Dashboard](#running-the-dashboard)
6. [Input Data Format](#input-data-format)
7. [Sample CSV Files](#sample-csv-files)
8. [Module Reference](#module-reference)
9. [Dashboard Tabs](#dashboard-tabs)
10. [Settings & Theming](#settings--theming)
11. [Extending the Project](#extending-the-project)

---

## Features

| Feature | Description |
|---|---|
| **Flexible CSV import** | Only `date` + `amount` are required — description, transaction type, and category are inferred or defaulted |
| **Auto alias mapping** | Recognises common bank export column names: `Narration`, `Particulars`, `Dr/Cr`, `Transaction Date`, etc. |
| **Auto-categorization** | Keyword-rule engine assigns categories across 13+ expense types to unlabelled transactions |
| **Interactive dashboard** | 5 tabs: Overview, Trends, Categories, Day Analysis, Savings Insights |
| **Live theme switching** | Dark / Light mode toggle + 8 accent colour presets + custom hex input |
| **Upload CSV** | Upload any bank CSV directly from the browser — large files processed async without UI freeze |
| **Static chart export** | On upload, all dashboard charts are regenerated and saved as PNGs to `output/charts/` |
| **Add Transaction** | Manually add individual transactions via a form dialog |
| **Savings recommendations** | Plain-English ₹-denominated advice: savings rate, subscriptions, dining, overspend months |
| **Monthly heatmap** | Category × month spending heatmap (last 24 months, readable at any screen size) |
| **INR-first** | All currency labels use ₹, amounts formatted with Indian thousand separators |

---

## Project Structure

```
MoneyMind/
│
├── data/
│   ├── transactions.csv                      # Default dataset (auto-loaded on startup)
│   ├── sample_01_standard.csv                # 1 500 rows — standard 5-column format
│   ├── sample_02_bank_export.csv             # 1 200 rows — Indian bank style (Narration, Dr/Cr, DD/MM/YYYY)
│   ├── sample_03_minimal.csv                 # 1 000 rows — only date + signed amount
│   ├── sample_04_us_bank.csv                 # 1 300 rows — US bank style column names
│   ├── sample_05_highvolume.csv              # 2 000 rows — Rs 1,234.56 currency formatting
│   ├── sample_06_startup_employee.csv        # 2 200 rows — standard 5-column, YYYY-MM-DD
│   ├── sample_07_student_minimal.csv         # 2 000 rows — date + signed amount only
│   ├── sample_08_retired_couple.csv          # 2 500 rows — Value Date / Narration / Dr/Cr columns
│   ├── sample_09_freelancer.csv              # 2 300 rows — ₹ currency prefix
│   ├── sample_10_family_household.csv        # 2 800 rows — INR prefix
│   ├── sample_11_hdfc_style.csv              # 2 100 rows — split Debit / Credit columns
│   ├── sample_12_sbi_passbook.csv            # 2 050 rows — Withdrawal Amt(INR) / Deposit Amt(INR)
│   ├── sample_13_high_income_professional.csv# 2 000 rows — Rs signed amounts, no separate type
│   ├── sample_14_mixed_locale.csv            # 2 200 rows — Expense / Income type labels
│   ├── sample_15_five_year_history.csv       # 3 000 rows — YYYY/MM/DD, 5 years of data
│   ├── generate_samples.py                   # Generates sample_01 – sample_05
│   └── generate_more_samples.py              # Generates sample_06 – sample_15
│
├── output/
│   └── charts/                               # Auto-generated PNG charts on upload/regeneration
│
├── src/
│   ├── app.py                        # NiceGUI entry point — page, header, dialogs, dashboard
│   ├── layout.py                     # Reusable UI components + global CSS (theme vars)
│   ├── charts.py                     # Matplotlib/Seaborn chart builders + batch save helpers
│   ├── utils.py                      # Colour constants, number formatters (fmt_inr, fmt_pct)
│   ├── data_processing.py            # ETL orchestrator + file-mtime cache + replace_data()
│   ├── data_loader.py                # CSV loading, alias mapping, split-column merge, validation
│   ├── data_cleaning.py              # Date parsing, amount coercion, normalisation, dedup
│   ├── categorization.py             # Keyword-rule categorizer (13+ categories)
│   ├── analysis.py                   # Spending summaries, trends, pivot tables
│   └── savings_insights.py           # Savings rate, subscription audit, recommendations
│
├── static/
│   └── favicon.svg
│
├── requirements.txt
└── README.md
```

---

## Tech Stack & Why

### Python 3.11+
Python is the standard for data science and finance tooling. Its rich ecosystem
of data libraries (pandas, numpy, matplotlib, seaborn) and the availability of
browser-capable UI frameworks (NiceGUI) make it the ideal single-language choice
for building a full-stack personal finance app — no JavaScript required.

---

### pandas — Data Manipulation
**Why:** Every step of the ETL pipeline is expressed as DataFrame transformations.
pandas provides fast vectorised operations for date parsing, amount coercion,
pivot tables, groupbys, and deduplication — tasks that would require hundreds of
lines in plain Python.

Key uses in MoneyMind:
- `pd.to_datetime()` with multi-format fallback (incl. `dayfirst=True` retry for Indian bank exports)
- `pivot_table()` for the category × month heatmap
- `groupby().agg()` for spending summaries and monthly trend data
- `str.replace()` with regex for currency symbol stripping (`₹`, `Rs`, `$`, `£`, `,`)

---

### NumPy — Numerical Operations
**Why:** NumPy underpins pandas' vectorised math. Used directly for:
- `np.where()` — merges split Debit/Credit columns and derives signed amounts
- NaN detection and filling

---

### Matplotlib + Seaborn — Static Analytics Charts
**Why:** MoneyMind renders publication-style static charts server-side using
Matplotlib (figure generation/styling) and Seaborn (heatmap rendering), then
embeds them in the NiceGUI page as base64 PNGs.

Charts in MoneyMind:
- Donut — category spending share
- Grouped bars + line — monthly income vs spending + net balance
- Horizontal bars — top categories
- Area — cumulative balance
- Day analysis bars — total, count, and average by weekday
- Stacked bar — category × weekday breakdown
- Heatmap — category × month spending (last 24 months)
- Semi-donut gauge — savings rate vs target
- `set_theme(dark: bool)` switches chart theme at runtime
- `save_all(...)` exports chart PNGs to `output/charts/`

---

### NiceGUI — Dashboard UI Framework
**Why:** NiceGUI lets you build a full browser UI entirely in Python — no HTML
templates, no JavaScript, no REST API. It uses a Quasar (Vue 3) frontend that
communicates over WebSocket with a Python/asyncio backend.

Key NiceGUI features used:

| Feature | Usage in MoneyMind |
|---|---|
| `@ui.page("/")` | Single-page app entry point |
| `ui.header` | Top bar with Upload CSV, Add Transaction, Settings buttons |
| `ui.dialog` | Modal dialogs for all three actions above |
| `ui.upload` with `auto-upload` | In-browser CSV upload, triggers immediately on file select |
| `ui.html` | Embeds inline base64 PNG chart images generated by Matplotlib |
| `ui.dark_mode()` | Programmatic dark/light theme switching |
| `ui.colors(primary=…)` | Live accent colour changes without page reload |
| `@ui.refreshable` | Re-renders only the dashboard section when new data is loaded |
| `asyncio.run_in_executor` | Offloads heavy pandas ETL to a thread pool — the async event loop never freezes even on large files |

---

### CSS Custom Properties — Theming System
**Why:** Instead of hardcoding hex colours in Python strings (which would require
a full Python re-render to change), all component colours are expressed as CSS
variables (`--mm-bg`, `--mm-surface`, `--mm-text`, etc.) defined in
`:root/.body--dark` and overridden in `.body--light`. A single DOM class swap —
which `ui.dark_mode()` triggers — instantly re-themes every component.

```css
:root, .body--dark  { --mm-surface: #1E293B; --mm-text: #F1F5F9; ... }
.body--light        { --mm-surface: #FFFFFF; --mm-text: #0F172A; ... }
```

---

## Quickstart

### 1. Clone / open the workspace

```powershell
cd W:\Projects\MoneyMind
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Launch the dashboard

```powershell
python src/app.py
```

The browser opens automatically at **http://localhost:8080**.

---

## Running the Dashboard

```powershell
# Standard launch
python src/app.py

# Kill any existing instance first (avoids port 8080 conflict)
$p = (Get-NetTCPConnection -LocalPort 8080 -EA 0 | Select-Object -First 1).OwningProcess
if ($p) { Stop-Process -Id $p -Force }
Start-Sleep 1
python src/app.py
```

The dashboard auto-loads `data/transactions.csv` on startup if it exists.  
Uploading a new CSV via the **Upload CSV** button replaces the active dataset in
memory and on disk instantly, then regenerates all chart PNGs in `output/charts/`.

---

## Input Data Format

Only **`date`** and **`amount`** are required. Everything else is synthesised automatically.

| Column | Required | Auto-default if absent |
|---|---|---|
| `date` | **Yes** | — |
| `amount` | **Yes** | — |
| `description` | No | `"Unknown"` |
| `transaction_type` | No | Inferred from amount sign (`+` → credit, `−` → debit); fallback `"debit"` |
| `category` | No | Filled by keyword-rule engine |

### Split Debit / Credit columns (HDFC, SBI style)

If your CSV has **separate Debit and Credit columns** instead of a single Amount
column, the loader merges them automatically. Recognised column-name pairs:

| Debit column | Credit column |
|---|---|
| `Debit` | `Credit` |
| `Withdrawal Amt(INR)` | `Deposit Amt(INR)` |
| `Withdrawal Amount` | `Deposit Amount` |
| `Withdrawal` | `Deposit` |
| `Debit Amount` | `Credit Amount` |
| `Dr Amount` | `Cr Amount` |
| `Dr` | `Cr` |

### Accepted column name aliases

The loader automatically renames these before processing:

| Canonical name | Accepted aliases |
|---|---|
| `date` | `transaction date`, `txn date`, `value date`, `trans date`, `posting date` |
| `amount` | `transaction amount`, `txn amount`, `net amount`, `debit/credit amount` |
| `description` | `transaction description`, `narration`, `particulars`, `remarks`, `details`, `memo`, `transaction details`, `beneficiary`, `payee` |
| `transaction_type` | `type`, `txn type`, `dr/cr`, `debit/credit`, `cr/dr` |
| `category` | `expense category`, `spending category` |

### Accepted `transaction_type` values

| Treated as **income (credit)** | Treated as **expense (debit)** |
|---|---|
| `credit`, `cr`, `c`, `income`, `in` | `debit`, `dr`, `d`, `expense`, `out` |

### Accepted date formats

Most formats are auto-detected by pandas. `DD/MM/YYYY` (common in Indian bank
exports) is handled by a `dayfirst=True` retry pass when the standard parse fails.

### Accepted amount formats

Currency symbols and thousand separators are stripped automatically before
conversion: `₹`, `Rs`, `INR`, `$`, `£`, `€`, and commas (`,`).

---

## Sample CSV Files

Fifteen ready-to-upload files are included in `data/`:

| File | Rows | Format / Persona |
|---|---|---|
| `sample_01_standard.csv` | 1 500 | Full 5-column standard, `YYYY-MM-DD` |
| `sample_02_bank_export.csv` | 1 200 | Indian bank — `Narration`, `Dr/Cr`, `DD/MM/YYYY` |
| `sample_03_minimal.csv` | 1 000 | Only `date` + signed amount |
| `sample_04_us_bank.csv` | 1 300 | US bank aliases — `Transaction Date`, `Particulars` |
| `sample_05_highvolume.csv` | 2 000 | `Rs 1,234.56` formatting, 3-year history |
| `sample_06_startup_employee.csv` | 2 200 | Startup employee — standard 5-column |
| `sample_07_student_minimal.csv` | 2 000 | Student — date + signed amount only |
| `sample_08_retired_couple.csv` | 2 500 | Retired couple — `Value Date` / `Narration` / `Dr/Cr` |
| `sample_09_freelancer.csv` | 2 300 | Freelancer — `₹` currency prefix |
| `sample_10_family_household.csv` | 2 800 | Family household — `INR` prefix |
| `sample_11_hdfc_style.csv` | 2 100 | HDFC-style — separate `Debit` and `Credit` columns |
| `sample_12_sbi_passbook.csv` | 2 050 | SBI passbook — `Withdrawal Amt(INR)` / `Deposit Amt(INR)` |
| `sample_13_high_income_professional.csv` | 2 000 | High income — `Rs` signed amounts, no type column |
| `sample_14_mixed_locale.csv` | 2 200 | Mixed — `Expense` / `Income` type labels |
| `sample_15_five_year_history.csv` | 3 000 | 5-year history — `YYYY/MM/DD` dates |

Regenerate at any time:

```powershell
# Original 5 files
python data/generate_samples.py

# Additional 10 files (sample_06 – sample_15)
python data/generate_more_samples.py
```

---

## Module Reference

### `src/app.py` — Dashboard Entry Point
- `index()` — `@ui.page("/")` handler; builds the full page
- `render_dashboard()` — `@ui.refreshable` — KPI cards + 5-tab layout
- `_build_upload_dialog()` — Modal CSV uploader; async processing with spinner notification
- `_build_add_txn_dialog()` — Manual transaction entry form (date, description, amount, type, category)
- `_build_settings_dialog()` — Dark/light toggle + 8 accent presets + custom hex input

### `src/layout.py` — UI Components & CSS
- `metric_card(label, value, delta, delta_positive, accent_color)` — KPI summary card with delta indicator and accent bar
- `chart_card(title)` — Styled card wrapper for chart image content
- `content_card()` — Styled card for text/table content
- `recommendation_item(text)` — Left-bordered advice block
- `GLOBAL_CSS` — Full CSS custom property theme system + all `mm-*` component classes

### `src/charts.py` — Matplotlib/Seaborn Chart Builders
- `set_theme(dark)` — Switches all charts between dark and light colour scheme; called by the theme toggle

| Function | Chart | Description |
|---|---|---|
| `fig_spending_pie` | Donut | Category share of total expenses |
| `fig_monthly_trend` | Bar + line | Monthly income vs spending with net balance line |
| `fig_top_categories` | Horizontal bar | Top 10 expense categories ranked by total |
| `fig_cumulative_balance` | Area | Cumulative net balance over time |
| `fig_day_of_week` | Bar | Total spending by day of week |
| `fig_day_transaction_count` | Bar | Transaction count by day of week |
| `fig_day_avg_transaction` | Bar | Average transaction value by day |
| `fig_day_category_breakdown` | Stacked bar | Category × day-of-week spending |
| `fig_heatmap` | Heatmap | Category (Y) × month (X), last 24 months |
| `fig_savings_gauge` | Gauge | Savings rate vs 20% target with delta |
| `build_all` | Batch builder | Returns a name→figure mapping for all charts |
| `save_all` | Export helper | Saves all figures as PNG files to a target directory |

### `src/data_processing.py` — ETL Orchestrator
- `load_df()` — Returns processed DataFrame; rebuilds only when the CSV file's mtime changes
- `replace_data(csv_bytes)` — Validates, aliases, fills defaults, writes to disk, invalidates cache; returns `(bool, message)`
- `append_row(…)` — Appends one manually entered transaction row to CSV
- `invalidate_cache()` — Forces a full rebuild on next `load_df()`
- `CATEGORIES` — Sorted category names for UI dropdowns

### `src/data_loader.py` — CSV Loading & Validation
- `load_transactions(filepath)` — Load CSV, apply aliases, merge split columns, validate, fill missing optional columns
- `_apply_aliases(df)` — In-place rename of bank export column names to canonical names
- `_merge_split_amount_columns(df)` — Detects HDFC/SBI-style separate Debit/Credit columns and merges them into `amount` + `transaction_type`
- `_fill_missing_optional(df)` — Add `description`, `transaction_type`, `category` defaults when absent
- `_validate_schema(df)` — Raise `ValueError` only if `date` or `amount` are missing
- `_SPLIT_AMOUNT_PAIRS` — Recognised debit/credit column-name pairs (7 variants)

### `src/data_cleaning.py` — Preprocessing Pipeline
`clean_transactions(df)` runs these steps in order:
1. Strip whitespace from all string columns
2. Parse dates — standard inference, then `dayfirst=True` retry for `DD/MM/YYYY`
3. Coerce amounts — strip `₹ Rs INR $ £ € ,` then `pd.to_numeric`
4. Normalise `transaction_type` — expand abbreviations (`dr`→`debit`, `cr`→`credit`, etc.), default unknown to `debit`
5. Create `signed_amount` — credits positive, debits negative
6. Normalise descriptions — title case, collapse whitespace, fill NaN with `"Unknown"`
7. Remove duplicate rows (keyed on date + description + amount + transaction_type)
8. Drop rows missing `date` or `amount`
9. Add temporal columns: `year`, `month`, `month_label`, `week`, `day_of_week`

### `src/categorization.py` — Auto-Categorization
- `categorize_transactions(df)` — Fills blank `category` using keyword rules across 13+ categories
- `CATEGORY_KEYWORDS` — Editable dict mapping category names to keyword lists

### `src/analysis.py` — Analytics
- `spending_summary(df)` — Total income, spending, net balance + transaction counts
- `monthly_spending_trend(df)` — Month-by-month income/spend/net DataFrame
- `category_spending(df)` — Per-category totals, counts, percentages
- `top_expense_categories(df, top_n)` — Ranked expense categories
- `day_of_week_spending(df)` — Total + average spend and transaction count per weekday
- `monthly_category_heatmap_data(df)` — Pivot: categories (rows) × months (columns)

### `src/savings_insights.py` — Savings Engine
`generate_savings_insights(df)` returns a structured dict:
- `savings_rate` — actual rate, 20% target, on-track flag, monthly deficit in ₹
- `subscriptions` — list of recurring services, monthly total, alert flag
- `dining_analysis` — monthly average, alert flag
- `shopping_analysis` — monthly average, alert flag
- `impulse_purchases` — transactions flagged as impulse buys
- `monthly_variance` — months where spending exceeded the rolling average
- `largest_category` — top expense category with % of total spend
- `recommendations` — list of plain-English ₹-denominated advice strings

### `src/utils.py` — Shared Utilities
- `C_BG`, `C_SURFACE`, `C_TEXT`, `C_TEXT_MUT`, `C_POSITIVE`, `C_NEGATIVE` — colour constants
- `CHART_PALETTE` — 8-colour palette shared across all charts
- `fmt_inr(value)` — Format as `₹1,23,456`
- `fmt_pct(value)` — Format as `12.3%`
- `fmt_int(value)` — Format with thousand separators

---

## Dashboard Tabs

| Tab | Content |
|---|---|
| **Overview** | 5 KPI cards + category share + top categories + monthly trend + cumulative balance |
| **Trends** | Focused monthly trend and cumulative balance views |
| **Categories** | Monthly spending heatmap + full category breakdown table |
| **Day Analysis** | KPI cards + total spend, transaction count, avg transaction, and category×day charts |
| **Savings Insights** | Savings rate gauge + plain-English ₹ recommendations |

---

## Settings & Theming

Click the **gear icon** in the top-right header to open Settings.

**Theme toggle** — switches between:
- **Dark mode** (default): deep navy backgrounds (`#0F172A`), slate card surfaces (`#1E293B`)
- **Light mode**: white card surfaces, light grey page background, dark text

**Accent colour presets**

| Name | Hex |
|---|---|
| Blue (default) | `#2563EB` |
| Indigo | `#4F46E5` |
| Violet | `#7C3AED` |
| Cyan | `#0891B2` |
| Teal | `#0D9488` |
| Emerald | `#059669` |
| Amber | `#D97706` |
| Rose | `#E11D48` |

**Custom hex** — type any 6-digit hex and click **Apply** for a fully custom accent.

---

## Extending the Project

### Add a new expense category

Open `src/categorization.py` and add an entry to `CATEGORY_KEYWORDS`:

```python
CATEGORY_KEYWORDS = {
    ...
    "Pets": ["vet", "petco", "petsmart", "pet food", "grooming"],
}
```

### Adjust savings alert thresholds

Open `src/savings_insights.py` and edit the constants near the top:

```python
SAVINGS_RATE_MIN                = 0.20    # 20% target savings rate
SUBSCRIPTION_MONTHLY_THRESHOLD  = 1500.00 # ₹/month alert threshold
DINING_MONTHLY_THRESHOLD        = 5000.00 # ₹/month alert threshold
SHOPPING_MONTHLY_THRESHOLD      = 8000.00 # ₹/month alert threshold
IMPULSE_SINGLE_THRESHOLD        = 2000.00 # single-transaction impulse flag
```

### Use your own bank CSV

1. Export transactions from your bank's internet banking portal
2. Click **Upload CSV** in the dashboard header
3. The file is validated, alias-mapped, cleaned, and loaded instantly
4. No manual column renaming needed — supported formats include HDFC, SBI,
   ICICI, Axis, and most international bank statement exports

---

## Requirements

```
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
nicegui>=2.0.0
```

```powershell
pip install -r requirements.txt
```

---

## License

MIT — free to use and modify for personal finance projects.

