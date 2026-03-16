"""
app.py
------
MoneyMind – Personal Finance Analytics
NiceGUI dashboard with static Matplotlib / Seaborn charts.

Run:
    python src/app.py
Opens at: http://localhost:8080

Architecture:
    utils.py           – constants, formatters
    data_processing.py – ETL pipeline + cache
    charts.py          – Matplotlib figure builders (dark + light theme)
    layout.py          – reusable NiceGUI components + CSS
    app.py             – page assembly, header, dialogs, tabs
"""

import sys
import os
import io
import base64
import asyncio
import datetime
import pandas as pd

# ── Windows UTF-8 stdout ──────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Path setup ────────────────────────────────────────────────────────────────
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(SRC_DIR, ".."))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Use Agg backend so matplotlib never tries to open a display window
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nicegui import ui, events, app as ng_app

from utils import (
    C_ACCENT, C_POSITIVE, C_NEGATIVE, C_WARNING, C_NEUTRAL,
    fmt_inr, fmt_pct, fmt_int, DATA_PATH,
)
from layout import (
    GLOBAL_CSS, page_title, page_subtitle, card_title,
    metric_card, chart_card, content_card, recommendation_item,
)
import charts as _charts
from data_processing import (
    load_df, invalidate_cache, append_row, replace_data,
    spending_summary, category_spending,
    monthly_spending_trend, generate_savings_insights,
    day_of_week_spending,
    CATEGORIES,
)
from data_loader import _COL_ALIASES, _SPLIT_AMOUNT_PAIRS

# ── Serve static assets ───────────────────────────────────────────────────────
_STATIC_DIR = os.path.join(ROOT_DIR, "static")

# ── Output directory for saved chart PNGs ─────────────────────────────────────
_OUT_DIR = os.path.join(ROOT_DIR, "output", "charts")
if os.path.isdir(_STATIC_DIR):
    ng_app.add_static_files("/static", _STATIC_DIR)

# ── Module-level theme flag ───────────────────────────────────────────────────
_dark: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# Chart → base64 helper
# ══════════════════════════════════════════════════════════════════════════════

def _fig_to_html(fig, width: str = "100%") -> str:
    """Render a matplotlib Figure to an inline <img> HTML tag with fade-in animation."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return (
        f'<div class="mm-chart-wrap" style="width:{width};">'
        f'<img src="data:image/png;base64,{b64}" '
        f'style="width:100%;border-radius:6px;display:block;">'
        f'</div>'
    )


def _chart(fig) -> None:
    """Embed a matplotlib figure directly into the current NiceGUI context."""
    ui.html(_fig_to_html(fig)).classes("w-full")


# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════

def _build_upload_dialog() -> ui.dialog:
    with ui.dialog() as dlg, ui.card().classes("mm-dialog-card").style(
        "min-width:460px; max-width:620px;"
    ):
        ui.label("Upload CSV").style(
            "font-size:1.15rem; font-weight:700; color:var(--mm-text);"
        )
        ui.label("Upload your file, verify required fields, then generate charts.").style(
            "font-size:0.82rem; color:var(--mm-text-mut); margin-top:4px;"
        )

        ui.separator().style("margin:12px 0; background:var(--mm-border);")

        with ui.element("div").classes("w-full").style(
            "background:var(--mm-surface2); border:1px solid var(--mm-border);"
            "border-radius:8px; padding:12px;"
        ):
            ui.label("Required to generate charts").style(
                "font-size:0.74rem; font-weight:700; letter-spacing:0.06em;"
                "text-transform:uppercase; color:var(--mm-text-dim);"
            )
            ui.label("1. date (or Transaction Date / Value Date / Txn Date)").style(
                "font-size:0.80rem; color:var(--mm-text-mut); margin-top:4px;"
            )
            ui.label("2. amount (or Transaction Amount / Net Amount)").style(
                "font-size:0.80rem; color:var(--mm-text-mut);"
            )
            ui.label("Tip: Debit + Credit split columns are also supported.").style(
                "font-size:0.76rem; color:var(--mm-text-dim); margin-top:2px;"
            )

        ui.separator().style("margin:12px 0; background:var(--mm-border);")

        # Validation status row: spinner + message
        with ui.row().classes("items-center w-full").style("gap:8px; min-height:26px;"):
            spinner_el = (
                ui.spinner("dots", size="20px", color="primary")
                .style("display:none;")
            )
            status_label = ui.label("").style(
                "font-size:0.80rem; color:var(--mm-text-mut);"
            )

        # Required fields checklist
        with ui.element("div").classes("w-full").style(
            "border:1px solid var(--mm-border); border-radius:8px; padding:12px;"
            "background:var(--mm-surface);"
        ):
            with ui.row().classes("items-center w-full").style("gap:8px; margin-bottom:6px;"):
                date_icon = ui.icon("radio_button_unchecked").style("color:var(--mm-text-dim);")
                date_label = ui.label("date column").style("font-size:0.82rem; color:var(--mm-text-mut);")

            with ui.row().classes("items-center w-full").style("gap:8px;"):
                amount_icon = ui.icon("radio_button_unchecked").style("color:var(--mm-text-dim);")
                amount_label = ui.label("amount column").style("font-size:0.82rem; color:var(--mm-text-mut);")

        parsed_cols_label = ui.label("").style(
            "font-size:0.76rem; color:var(--mm-text-dim); margin-top:6px;"
        )

        state = {
            "raw": None,
            "name": "",
            "valid": False,
        }

        def _set_check(icon_el, label_el, ok: bool, label_text: str) -> None:
            if ok:
                icon_el.props("name=check_circle")
                icon_el.style(f"color:{C_POSITIVE};")
                label_el.set_text(f"{label_text} ✓")
                label_el.style(f"font-size:0.82rem; color:{C_POSITIVE};")
            else:
                icon_el.props("name=cancel")
                icon_el.style(f"color:{C_NEGATIVE};")
                label_el.set_text(f"{label_text} missing")
                label_el.style(f"font-size:0.82rem; color:{C_NEGATIVE};")

        def _normalize_columns(cols: list[str]) -> set[str]:
            return {str(c).strip().lower() for c in cols if str(c).strip()}

        def _has_date_column(cols: set[str]) -> bool:
            return ("date" in cols) or any(a in cols for a in _COL_ALIASES["date"])

        def _has_amount_column(cols: set[str]) -> bool:
            if ("amount" in cols) or any(a in cols for a in _COL_ALIASES["amount"]):
                return True
            for debit_col, credit_col in _SPLIT_AMOUNT_PAIRS:
                if debit_col in cols and credit_col in cols:
                    return True
            return False

        async def _generate_charts():
            if not state["raw"]:
                ui.notify("Please upload a CSV file first.", type="warning", position="top-right")
                return
            if not state["valid"]:
                ui.notify("Required fields are missing. Please fix your CSV.", type="negative", position="top-right")
                return

            spinner_el.style("display:inline-block;")
            status_label.set_text("Generating charts…")
            status_label.style("color:var(--mm-text-mut);")
            generate_btn.disable()

            loop = asyncio.get_event_loop()
            ok, msg = await loop.run_in_executor(None, replace_data, state["raw"])

            if ok:
                notify = ui.notification(
                    "Building charts — please wait…",
                    type="ongoing",
                    spinner=True,
                    position="top-right",
                    timeout=None,
                    close_button=False,
                )

                def _build_and_save():
                    df_new = load_df()
                    ins_new = generate_savings_insights(df_new)
                    _charts.set_theme(dark=_dark)
                    figs_new = _charts.build_all(df_new, ins_new)
                    try:
                        saved = _charts.save_all(figs_new, _OUT_DIR)
                        print(f"[Charts] Saved {len(saved)} PNGs -> {_OUT_DIR}")
                    except Exception as exc:
                        print(f"[Charts] Save error: {exc}")

                await loop.run_in_executor(None, _build_and_save)
                render_dashboard.refresh()
                notify.dismiss()
                spinner_el.style("display:none;")
                status_label.set_text(f"✓  {msg}")
                status_label.style(f"color:{C_POSITIVE};")
                ui.notify("Charts generated", type="positive", position="top-right", timeout=2200)
                await asyncio.sleep(0.35)
                dlg.close()
            else:
                spinner_el.style("display:none;")
                status_label.set_text(f"✗  {msg}")
                status_label.style(f"color:{C_NEGATIVE};")
                generate_btn.enable()

        async def _handle_upload(e: events.UploadEventArguments):
            spinner_el.style("display:inline-block;")
            status_label.set_text("Reading file and validating columns…")
            status_label.style("color:var(--mm-text-mut);")

            try:
                raw = await e.file.read()
                state["raw"] = raw
                state["name"] = getattr(e, "name", "uploaded.csv")

                preview_df = pd.read_csv(io.BytesIO(raw), nrows=5)
                cols = _normalize_columns(list(preview_df.columns))
                has_date = _has_date_column(cols)
                has_amount = _has_amount_column(cols)

                _set_check(date_icon, date_label, has_date, "date column")
                _set_check(amount_icon, amount_label, has_amount, "amount column")

                shown_cols = ", ".join(sorted(cols)[:8])
                extra = " ..." if len(cols) > 8 else ""
                parsed_cols_label.set_text(f"Detected columns: {shown_cols}{extra}")

                state["valid"] = bool(has_date and has_amount)
                if state["valid"]:
                    status_label.set_text("✓  All required fields detected. Click Generate Charts.")
                    status_label.style(f"color:{C_POSITIVE};")
                    generate_btn.enable()
                else:
                    status_label.set_text("✗  Missing required fields. Please upload a valid CSV.")
                    status_label.style(f"color:{C_NEGATIVE};")
                    generate_btn.disable()
            except Exception as exc:
                state["raw"] = None
                state["valid"] = False
                _set_check(date_icon, date_label, False, "date column")
                _set_check(amount_icon, amount_label, False, "amount column")
                parsed_cols_label.set_text("")
                status_label.set_text(f"✗  Could not read CSV: {exc}")
                status_label.style(f"color:{C_NEGATIVE};")
                generate_btn.disable()
            finally:
                spinner_el.style("display:none;")

        (ui.upload(label="Choose CSV file", on_upload=_handle_upload, auto_upload=True)
           .props("accept=.csv flat bordered")
           .classes("w-full")
           .style("font-size:0.82rem;"))

        ui.separator().style("margin:12px 0; background:var(--mm-border);")
        with ui.row().classes("w-full justify-between items-center"):
            (ui.button("Cancel", on_click=dlg.close)
               .props("flat no-caps dense")
               .style("color:var(--mm-text-mut); font-size:0.80rem;"))
            generate_btn = (
                ui.button("Generate Charts", on_click=_generate_charts)
                .props("unelevated no-caps dense color=primary")
                .style("font-size:0.80rem; padding:0 16px; height:34px;")
            )
            generate_btn.disable()
    return dlg


def _build_add_txn_dialog() -> ui.dialog:
    with ui.dialog() as dlg, ui.card().classes("mm-dialog-card").style(
        "min-width:420px; max-width:520px;"
    ):
        ui.label("Add Transaction").style(
            "font-size:1.05rem; font-weight:700; color:var(--mm-text);"
        )
        ui.separator().style("margin:10px 0; background:var(--mm-border);")

        today = datetime.date.today().isoformat()
        f_date  = ui.input("Date (YYYY-MM-DD)", value=today).props("outlined dense").classes("w-full")
        f_desc  = ui.input("Description").props("outlined dense").classes("w-full")
        f_amt   = ui.number("Amount (₹)", format="%.2f").props("outlined dense").classes("w-full")
        f_type  = ui.select(["debit", "credit"], value="debit", label="Type").props("outlined dense").classes("w-full")
        f_cat   = ui.select(CATEGORIES, label="Category").props("outlined dense").classes("w-full")

        err_label = ui.label("").style("font-size:0.78rem; color:#DC2626;")

        def _save():
            if not f_date.value or not f_desc.value or not f_amt.value:
                err_label.set_text("Date, description and amount are required.")
                return
            try:
                datetime.date.fromisoformat(f_date.value)
            except ValueError:
                err_label.set_text("Invalid date — use YYYY-MM-DD.")
                return
            append_row(
                date=f_date.value,
                description=f_desc.value,
                amount=float(f_amt.value),
                category=f_cat.value or "Miscellaneous",
                tx_type=f_type.value,
            )
            render_dashboard.refresh()
            dlg.close()

        ui.separator().style("margin:10px 0; background:var(--mm-border);")
        with ui.row().classes("gap-2 justify-end w-full"):
            (ui.button("Cancel", on_click=dlg.close)
               .props("flat no-caps dense")
               .style("color:var(--mm-text-mut); font-size:0.80rem;"))
            (ui.button("Save", on_click=_save)
               .props("unelevated no-caps dense color=primary")
               .style("font-size:0.80rem; padding:0 18px; height:32px;"))
    return dlg


def _build_settings_dialog(dark_mode_el) -> ui.dialog:
    ACCENTS = [
        ("Blue",    "#2563EB"),
        ("Indigo",  "#4F46E5"),
        ("Violet",  "#7C3AED"),
        ("Cyan",    "#0891B2"),
        ("Teal",    "#0D9488"),
        ("Emerald", "#059669"),
        ("Amber",   "#D97706"),
        ("Rose",    "#E11D48"),
    ]

    with ui.dialog() as dlg, ui.card().classes("mm-dialog-card").style(
        "min-width:360px; max-width:440px;"
    ):
        ui.label("Settings").style(
            "font-size:1.05rem; font-weight:700; color:var(--mm-text);"
        )
        ui.separator().style("margin:10px 0; background:var(--mm-border);")

        # Theme toggle
        with ui.row().classes("items-center justify-between w-full"):
            ui.label("Dark mode").style("font-size:0.84rem; color:var(--mm-text);")

            def _toggle(e):
                global _dark
                _dark = e.value
                dark_mode_el.enable() if e.value else dark_mode_el.disable()
                _charts.set_theme(dark=e.value)
                render_dashboard.refresh()

            ui.switch(value=_dark, on_change=_toggle).props("color=primary")

        ui.separator().style("margin:10px 0; background:var(--mm-border);")
        ui.label("Accent colour").style(
            "font-size:0.72rem; font-weight:600; text-transform:uppercase;"
            "letter-spacing:0.07em; color:var(--mm-text-mut);"
        )
        with ui.row().classes("flex-wrap gap-2 mt-1"):
            for name, hex_val in ACCENTS:
                (ui.button(name)
                   .props("unelevated no-caps dense size=sm")
                   .style(
                       f"background:{hex_val}; color:#fff;"
                       "font-size:0.72rem; padding:0 10px; height:26px;"
                   )
                   .on("click", lambda _h=hex_val: ui.colors(primary=_h)))

        ui.separator().style("margin:10px 0; background:var(--mm-border);")
        ui.label("Custom hex").style(
            "font-size:0.72rem; font-weight:600; text-transform:uppercase;"
            "letter-spacing:0.07em; color:var(--mm-text-mut);"
        )
        with ui.row().classes("gap-2 items-center mt-1 w-full"):
            hex_input = (ui.input(placeholder="#2563EB")
                           .props("outlined dense")
                           .style("flex:1;"))
            (ui.button("Apply")
               .props("unelevated no-caps dense color=primary")
               .style("font-size:0.78rem; height:32px; padding:0 14px;")
               .on("click", lambda: ui.colors(primary=hex_input.value)
                   if hex_input.value.startswith("#") else None))

        ui.separator().style("margin:10px 0; background:var(--mm-border);")
        (ui.button("Close", on_click=dlg.close)
           .props("flat no-caps dense")
           .style("color:var(--mm-text-mut); font-size:0.80rem;"))
    return dlg


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════════

@ui.refreshable
def render_dashboard() -> None:
    df = load_df()

    if df is None or df.empty:
        with ui.column().classes("w-full items-center justify-center").style(
            "padding:80px 20px;"
        ):
            ui.html('''
            <svg xmlns="http://www.w3.org/2000/svg" width="56" height="56"
                 fill="#475569" viewBox="0 0 16 16" style="margin-bottom:16px;">
              <path d="M7.964 1.527c-2.977 0-5.571 1.704-6.32 4.125h-.55A1 1 0 0 0
                .11 6.824l.254 1.46a1.5 1.5 0 0 0 1.478 1.243h.263c.3.513.688.978
                1.145 1.382l-.729 2.477a.5.5 0 0 0 .48.641h2a.5.5 0 0 0
                .471-.332l.482-1.351c.635.173 1.31.267 2.011.267.707 0
                1.388-.095 2.028-.272l.543 1.372a.5.5 0 0 0 .465.316h2a.5.5 0 0 0
                .478-.645l-.761-2.506C13.81 9.895 14.5 8.559 14.5
                7.069q0-.218-.02-.431c.261-.11.508-.266.705-.444.315.306.815.306.815-.417
                0 .223-.5.223-.461-.026a1 1 0 0 0 .09-.255.7.7 0 0
                0-.202-.645.58.58 0 0 0-.707-.098.74.74 0 0 0-.375.562c-.024.243.082.48.32.654a2
                2 0 0 1-.259.153c-.534-2.664-3.284-4.595-6.442-4.595m7.173
                3.876a.6.6 0 0 1-.098.21l-.044-.025c-.146-.09-.157-.175-.152-.223a.24.24
                0 0 1 .117-.173c.049-.027.08-.021.113.012a.2.2 0 0
                1 .064.199m-8.999-.65a.5.5 0 1 1-.276-.96A7.6 7.6 0 0 1 7.964
                3.5c.763 0 1.497.11 2.18.315a.5.5 0 1 1-.287.958A6.6 6.6 0 0
                0 7.964 4.5c-.64 0-1.255.09-1.826.254ZM5
                6.25a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0"/>
            </svg>
            ''')
            ui.label("No data loaded").style(
                "font-size:1.1rem; font-weight:600; color:var(--mm-text);"
            )
            ui.label("Upload a CSV file to get started.").style(
                "font-size:0.84rem; color:var(--mm-text-mut); margin-top:4px;"
            )
        return

    summary  = spending_summary(df)
    insights = generate_savings_insights(df)
    sr       = insights.get("savings_rate", {})
    savings_rate_val = sr.get("savings_rate", 0.0)

    # ── Build all charts (respects current theme) ──────────────────────────────
    _charts.set_theme(dark=_dark)
    figs = _charts.build_all(df, insights)

    # ── KPI row ────────────────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-3 no-wrap").style("margin-bottom:20px;"):
        net = summary["net_balance"]
        metric_card("Total Income",    fmt_inr(summary["total_income"]),
                    accent_color=C_POSITIVE)
        metric_card("Total Expenses",  fmt_inr(summary["total_spending"]),
                    accent_color=C_NEGATIVE)
        metric_card("Net Balance",     fmt_inr(net),
                    delta_positive=(net >= 0),
                    accent_color=C_POSITIVE if net >= 0 else C_NEGATIVE)
        metric_card("Transactions",    fmt_int(summary["transaction_count"]),
                    accent_color=C_ACCENT)
        metric_card("Savings Rate",    fmt_pct(savings_rate_val),
                    delta="On track ✓" if sr.get("on_track") else "Below target",
                    delta_positive=sr.get("on_track"),
                    accent_color=C_POSITIVE if sr.get("on_track") else C_WARNING)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    with ui.tabs().props("dense indicator-color=primary align=left").classes(
        "w-full"
    ).style("border-bottom:1px solid var(--mm-border);") as tabs:
        t_overview   = ui.tab("Overview")
        t_trends     = ui.tab("Trends")
        t_categories = ui.tab("Categories")
        t_day        = ui.tab("Day Analysis")
        t_savings    = ui.tab("Savings Insights")

    with ui.tab_panels(tabs, value=t_overview).classes("w-full").style(
        "background:transparent; padding:0; margin-top:16px;"
    ):
        # ── Overview ──────────────────────────────────────────────────────────
        with ui.tab_panel(t_overview).style("padding:0;"):
            with ui.row().classes("w-full gap-4"):
                with chart_card("Category Spending Share"):
                    _chart(figs["spending_pie"])
                with chart_card("Top Expense Categories"):
                    _chart(figs["top_categories"])
            ui.element("div").style("height:16px;")
            with ui.row().classes("w-full gap-4"):
                with chart_card("Monthly Income vs Expenses"):
                    _chart(figs["monthly_trend"])
                with chart_card("Cumulative Account Balance"):
                    _chart(figs["cumulative_balance"])

        # ── Trends ────────────────────────────────────────────────────────────
        with ui.tab_panel(t_trends).style("padding:0;"):
            with chart_card("Monthly Income vs Expenses"):
                _chart(figs["monthly_trend"])
            ui.element("div").style("height:16px;")
            with chart_card("Cumulative Account Balance"):
                _chart(figs["cumulative_balance"])

        # ── Categories ────────────────────────────────────────────────────────
        with ui.tab_panel(t_categories).style("padding:0;"):
            cat_df = category_spending(df)
            with chart_card("Monthly Spending Heatmap"):
                _chart(figs["heatmap"])
            ui.element("div").style("height:16px;")
            with content_card():
                card_title("All Categories")
                ui.element("div").style("height:8px;")
                cols = [
                    {"name": "category",          "label": "Category",      "field": "category",          "align": "left"},
                    {"name": "total_spent",        "label": "Total Spent",   "field": "total_spent_fmt",   "align": "right"},
                    {"name": "transaction_count",  "label": "Txns",          "field": "transaction_count", "align": "right"},
                    {"name": "pct_of_total",       "label": "Share",         "field": "pct_of_total_fmt",  "align": "right"},
                ]
                rows = [
                    {
                        "category":          r["category"],
                        "total_spent_fmt":   fmt_inr(r["total_spent"]),
                        "transaction_count": int(r["transaction_count"]),
                        "pct_of_total_fmt":  fmt_pct(r["pct_of_total"]),
                    }
                    for _, r in cat_df.iterrows()
                ]
                ui.table(columns=cols, rows=rows, row_key="category").props(
                    "flat dense bordered separator=cell"
                ).classes("w-full")

        # ── Day Analysis ──────────────────────────────────────────────────────
        with ui.tab_panel(t_day).style("padding:0;"):
            # ── Stat cards ────────────────────────────────────────────────────
            dow_df = day_of_week_spending(df)
            if not dow_df.empty:
                peak_day   = dow_df.loc[dow_df["total_spent"].idxmax(),       "day_of_week"]
                busy_day   = dow_df.loc[dow_df["transaction_count"].idxmax(), "day_of_week"]
                avg_daily  = dow_df["total_spent"].mean()
                low_day    = dow_df.loc[dow_df["total_spent"].idxmin(),       "day_of_week"]
            else:
                peak_day = busy_day = low_day = "—"
                avg_daily = 0.0
            with ui.row().classes("w-full gap-4").style("margin-bottom:16px;"):
                metric_card(
                    "Peak Spending Day", str(peak_day),
                    delta="Highest total outflow",
                    delta_positive=None, accent_color=C_NEGATIVE,
                )
                metric_card(
                    "Busiest Day", str(busy_day),
                    delta="Most transactions",
                    delta_positive=None, accent_color=C_ACCENT,
                )
                metric_card(
                    "Avg Daily Expense", fmt_inr(avg_daily),
                    delta="Mean across all days",
                    delta_positive=None, accent_color=C_WARNING,
                )
                metric_card(
                    "Lightest Spending Day", str(low_day),
                    delta="Lowest total outflow",
                    delta_positive=True, accent_color=C_POSITIVE,
                )

            # ── Row 1: Total Spending | Transaction Count ──────────────────
            with ui.row().classes("w-full gap-4").style("margin-bottom:16px;"):
                with chart_card("Total Spending by Day"):
                    _chart(figs["day_of_week"])
                with chart_card("Transaction Count by Day"):
                    _chart(figs["day_transaction_count"])

            # ── Row 2: Avg Transaction Value | (full-width category breakdown)
            with chart_card("Avg Transaction Value by Day"):
                _chart(figs["day_avg_transaction"])

            ui.element("div").style("height:16px;")

            # ── Row 3: Category × Day stacked bar ─────────────────────────
            with chart_card("Spending by Category × Day of Week"):
                _chart(figs["day_category_breakdown"])

        # ── Savings Insights ──────────────────────────────────────────────────
        with ui.tab_panel(t_savings).style("padding:0;"):
            with ui.row().classes("w-full no-wrap").style("gap:16px; align-items:stretch;"):

                # Left column – gauge chart (50 %)
                with ui.card().classes("mm-card").style(
                    "flex:0 0 calc(50% - 8px); min-width:0; border-radius:6px; padding:16px;"
                ):
                    card_title("Savings Rate")
                    ui.element("div").style("height:10px;")
                    _chart(figs["savings_gauge"])

                # Right column – recommendations (50 %)
                with ui.card().classes("mm-card").style(
                    "flex:1 1 0; min-width:0; border-radius:6px; padding:16px;"
                ):
                    card_title("Recommendations")
                    ui.element("div").style("height:8px;")
                    recs = insights.get("recommendations", [])
                    if recs:
                        for rec in recs:
                            recommendation_item(rec)
                    else:
                        ui.label("No recommendations — great financial health!").style(
                            "font-size:0.82rem; color:var(--mm-text-mut);"
                        )

                    subs = insights.get("subscriptions", {})
                    if subs.get("alert"):
                        ui.element("div").style("height:16px;")
                        card_title("Subscription Alert")
                        with ui.element("div").style(
                            f"border-left:3px solid {C_WARNING}; padding:8px 12px; "
                            "border-radius:4px; background:var(--mm-surface2); margin-top:8px;"
                        ):
                            ui.label(
                                f"Monthly subscriptions: {fmt_inr(subs.get('monthly_total', 0))}"
                            ).style("font-size:0.82rem; color:var(--mm-text-mut);")


# ══════════════════════════════════════════════════════════════════════════════
# Page
# ══════════════════════════════════════════════════════════════════════════════

@ui.page("/")
def index() -> None:
    global _dark
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    dark_mode_el = ui.dark_mode()
    if _dark:
        dark_mode_el.enable()

    ui.colors(primary=C_ACCENT)

    upload_dlg   = _build_upload_dialog()
    add_txn_dlg  = _build_add_txn_dialog()
    settings_dlg = _build_settings_dialog(dark_mode_el)

    # ── Header ─────────────────────────────────────────────────────────────────
    with ui.header(elevated=False).style("padding:0 20px; height:52px;"):
        with ui.row().classes("h-full w-full items-center justify-between no-wrap"):

            # Brand
            with ui.row().classes("items-center gap-4 no-wrap"):
                ui.html(f'''
                <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26"
                                         fill="currentColor" style="color:var(--q-primary);" viewBox="0 0 16 16">
                  <path d="M7.964 1.527c-2.977 0-5.571 1.704-6.32 4.125h-.55A1 1 0 0 0
                    .11 6.824l.254 1.46a1.5 1.5 0 0 0 1.478 1.243h.263c.3.513.688.978
                    1.145 1.382l-.729 2.477a.5.5 0 0 0 .48.641h2a.5.5 0 0 0
                    .471-.332l.482-1.351c.635.173 1.31.267 2.011.267.707 0
                    1.388-.095 2.028-.272l.543 1.372a.5.5 0 0 0 .465.316h2a.5.5 0 0 0
                    .478-.645l-.761-2.506C13.81 9.895 14.5 8.559 14.5
                    7.069q0-.218-.02-.431c.261-.11.508-.266.705-.444.315.306.815.306.815-.417
                    0 .223-.5.223-.461-.026a1 1 0 0 0 .09-.255.7.7 0 0
                    0-.202-.645.58.58 0 0 0-.707-.098.74.74 0 0
                    0-.375.562c-.024.243.082.48.32.654a2 2 0 0 1-.259.153c-.534-2.664-3.284-4.595-6.442-4.595m7.173
                    3.876a.6.6 0 0 1-.098.21l-.044-.025c-.146-.09-.157-.175-.152-.223a.24.24
                    0 0 1 .117-.173c.049-.027.08-.021.113.012a.2.2 0 0 1
                    .064.199m-8.999-.65a.5.5 0 1 1-.276-.96A7.6 7.6 0 0 1 7.964
                    3.5c.763 0 1.497.11 2.18.315a.5.5 0 1 1-.287.958A6.6 6.6 0 0
                    0 7.964 4.5c-.64 0-1.255.09-1.826.254ZM5 6.25a.75.75 0 1
                    1-1.5 0 .75.75 0 0 1 1.5 0"/>
                </svg>
                ''')
                with ui.column().classes("gap-0"):
                    page_title("MoneyMind")
                    page_subtitle("Personal Finance Analytics")

            # Right side buttons
            with ui.row().classes("items-center gap-2 no-wrap"):
                (ui.button("Upload CSV", icon="upload_file",
                           on_click=upload_dlg.open)
                   .props("flat no-caps no-shadow dense")
                   .style(
                       "color:var(--mm-text); font-size:0.78rem; font-weight:500;"
                       "border:1px solid var(--mm-border); border-radius:4px;"
                       "padding:0 12px; height:30px;"
                   ))
                (ui.button("Add Transaction", icon="add",
                           on_click=add_txn_dlg.open)
                   .props("unelevated no-caps no-shadow dense color=primary")
                   .style(
                       "font-size:0.78rem; font-weight:600;"
                       "padding:0 14px; height:30px;"
                   ))
                ui.separator().props("vertical").style(
                    "background:var(--mm-border); height:22px; margin:0 4px;"
                )
                (ui.button(icon="settings", on_click=settings_dlg.open)
                   .props("flat round dense size=sm")
                   .style("color:var(--mm-text-mut);"))
                ui.label("v4.0").style(
                    "font-size:0.65rem; color:var(--mm-text-dim);"
                    "background:var(--mm-bg); padding:2px 8px;"
                    "border:1px solid var(--mm-border); border-radius:3px;"
                    "margin-left:2px;"
                )

    # ── Main content ───────────────────────────────────────────────────────────
    with ui.column().classes("w-full mm-page").style(
        "padding:28px 36px; min-height:100vh;"
    ):
        render_dashboard()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    _favicon = os.path.join(_STATIC_DIR, "favicon.svg")
    ui.run(
        title="MoneyMind",
        favicon=_favicon if os.path.isfile(_favicon) else "🐷",
        port=8080,
        dark=True,
        reload=False,
        show=True,
    )
