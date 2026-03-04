"""
app.py
------
MoneyMind – Personal Finance Analytics
NiceGUI application entry point.

Run:
    python src/app.py
Opens at: http://localhost:8080

Architecture:
    utils.py           – constants, colours, formatters
    data_processing.py – pipeline wrapper + cache
    charts.py          – Plotly figure builders
    layout.py          – reusable NiceGUI components + global CSS
    app.py             – page assembly, sidebar, tabs, wiring
"""

import sys
import os
import asyncio
import datetime

# ── Path ──────────────────────────────────────────────────────────────────────
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pandas as pd
from nicegui import ui, events, app as ng_app

# ── Project modules ───────────────────────────────────────────────────────────
from utils import (
    C_TEXT, C_TEXT_MUT, C_TEXT_DIM, C_BG, C_SURFACE, C_BORDER,
    C_ACCENT, C_POSITIVE, C_NEGATIVE, C_WARNING, C_NEUTRAL,
    fmt_inr, fmt_int, fmt_pct,
)
from data_processing import (
    load_df, append_row, replace_data, invalidate_cache, CATEGORIES,
    spending_summary, monthly_spending_trend, generate_savings_insights,
    category_spending,
)
from charts import (
    fig_spending_pie, fig_treemap, fig_top_categories, fig_day_of_week,
    fig_monthly_trend, fig_cumulative_balance, fig_heatmap, fig_savings_gauge,
    set_dark as _set_chart_dark,
)
from layout import (
    page_title, page_subtitle, section_heading, card_title, divider,
    metric_card, chart_card, content_card,
    recommendation_item, stat_pill,
    GLOBAL_CSS,
)

# ── Plotly chart config  (hide mode-bar for clean look) ───────────────────────
_CFG = {"displayModeBar": False, "responsive": True}
# ── Accent colour presets ────────────────────────────────────────────────────
ACCENT_PRESETS = [
    ("#2563EB", "Blue"),
    ("#4F46E5", "Indigo"),
    ("#7C3AED", "Violet"),
    ("#0891B2", "Cyan"),
    ("#0F766E", "Teal"),
    ("#059669", "Emerald"),
    ("#D97706", "Amber"),
    ("#E11D48", "Rose"),
]

# ══════════════════════════════════════════════════════════════════════════════
# Refreshable dashboard  (re-renders only this subtree on data change)
# ══════════════════════════════════════════════════════════════════════════════

@ui.refreshable
def render_dashboard() -> None:
    df = load_df()

    # ── Empty / no-data state ─────────────────────────────────────────────────
    if df is None:
        with ui.column().classes("w-full items-center").style("padding:6rem 0;"):
            ui.icon("insert_drive_file", size="3.5rem").style(
                f"color:{C_BORDER};"
            )
            ui.label("No transaction data").style(
                f"font-size:1.1rem; font-weight:600; color:{C_TEXT};"
                "margin-top:1rem;"
            )
            ui.label(
                "Use the Upload CSV or Add Transaction buttons in the toolbar above."
            ).style("font-size:0.82rem; color:var(--mm-text-dim); margin-top:4px;")
        return

    # ── Pre-compute summary ───────────────────────────────────────────────────
    summary = spending_summary(df)
    net     = summary["net_balance"]
    d_min   = df["date"].min().strftime("%d %b %Y")
    d_max   = df["date"].max().strftime("%d %b %Y")

    # ── Period bar ────────────────────────────────────────────────────────────
    with ui.row().classes("w-full items-center justify-between mm-border-bottom").style(
        "padding-bottom:12px; margin-bottom:20px;"
    ):
        ui.label(f"Period: {d_min} – {d_max}").style(
            "font-size:0.75rem; color:var(--mm-text-dim);"
        )
        ui.label(f"{len(df):,} records").style(
            "font-size:0.75rem; color:var(--mm-text-dim);"
        )

    # ── KPI row ───────────────────────────────────────────────────────────────
    with ui.row().classes("w-full gap-3 no-wrap").style("margin-bottom:24px;"):
        metric_card(
            "Total Income",
            fmt_inr(summary["total_income"]),
            accent_color=C_POSITIVE,
        )
        metric_card(
            "Total Expenses",
            fmt_inr(summary["total_spending"]),
            accent_color=C_NEGATIVE,
        )
        metric_card(
            "Net Balance",
            fmt_inr(net),
            delta=("+" if net >= 0 else "") + fmt_inr(net),
            delta_positive=net >= 0,
            accent_color=C_POSITIVE if net >= 0 else C_NEGATIVE,
        )
        metric_card(
            "Transactions",
            fmt_int(summary["transaction_count"]),
            accent_color=C_ACCENT,
        )
        metric_card(
            "Expense Entries",
            fmt_int(summary["expense_count"]),
            accent_color=C_NEUTRAL,
        )

    # ── Tab navigation ────────────────────────────────────────────────────────
    with ui.tabs().classes("w-full").props(
        "align=left dense no-caps indicator-color=primary"
    ) as tabs:
        t_ov  = ui.tab("Overview")
        t_cat = ui.tab("Categories")
        t_tr  = ui.tab("Trends")
        t_txn = ui.tab("Transactions")
        t_ins = ui.tab("Insights")

    with ui.tab_panels(tabs, value=t_ov).classes("w-full").style(
        "background:transparent; padding-top:20px;"
    ):

        # ── Overview ──────────────────────────────────────────────────────────
        with ui.tab_panel(t_ov):
            _render_overview(df)

        # ── Categories ────────────────────────────────────────────────────────
        with ui.tab_panel(t_cat):
            _render_categories(df)

        # ── Trends ────────────────────────────────────────────────────────────
        with ui.tab_panel(t_tr):
            _render_trends(df)

        # ── Transactions ──────────────────────────────────────────────────────
        with ui.tab_panel(t_txn):
            _render_transactions(df)

        # ── Insights ──────────────────────────────────────────────────────────
        with ui.tab_panel(t_ins):
            _render_insights(df, net)


# ══════════════════════════════════════════════════════════════════════════════
# Tab content renderers
# ══════════════════════════════════════════════════════════════════════════════

def _render_overview(df: pd.DataFrame) -> None:
    """Overview tab: donut + treemap, then monthly trend."""

    # Row 1: two charts side by side
    with ui.row().classes("w-full gap-4").style("margin-bottom:16px;"):
        with chart_card("Spending by Category"):
            ui.plotly(fig_spending_pie(df)).classes("w-full").style("height:340px;")
        with chart_card("Category Distribution"):
            ui.plotly(fig_treemap(df)).classes("w-full").style("height:340px;")

    # Row 2: monthly trend full width
    with chart_card("Monthly Income vs Expenses"):
        ui.plotly(fig_monthly_trend(df)).classes("w-full").style("height:300px;")


def _render_categories(df: pd.DataFrame) -> None:
    """Categories tab: bar charts + heatmap."""

    with ui.row().classes("w-full gap-4").style("margin-bottom:16px;"):
        with chart_card("Top Expense Categories"):
            ui.plotly(fig_top_categories(df)).classes("w-full").style("height:340px;")
        with chart_card("Spending by Day of Week"):
            ui.plotly(fig_day_of_week(df)).classes("w-full").style("height:340px;")

    with chart_card("Monthly Spending Heatmap"):
        ui.plotly(fig_heatmap(df)).classes("w-full").style("min-height:380px;")


def _render_trends(df: pd.DataFrame) -> None:
    """Trends tab: cumulative balance + monthly summary table."""

    with chart_card("Cumulative Balance Over Time"):
        ui.plotly(fig_cumulative_balance(df)).classes("w-full").style("height:300px;")

    ui.element("div").style("height:16px;")

    # Monthly summary as a clean table
    with content_card():
        card_title("Monthly Summary")
        ui.element("div").style("height:10px;")

        monthly = monthly_spending_trend(df)
        rows    = monthly[
            ["month_label", "total_income", "total_spending", "net_balance"]
        ].round(2).to_dict("records")

        (ui.table(
            columns=[
                {"name": "month_label",    "label": "Month",        "field": "month_label",    "sortable": True},
                {"name": "total_income",   "label": "Income (₹)",   "field": "total_income",   "sortable": True},
                {"name": "total_spending", "label": "Expenses (₹)", "field": "total_spending", "sortable": True},
                {"name": "net_balance",    "label": "Net (₹)",      "field": "net_balance",    "sortable": True},
            ],
            rows=rows,
            row_key="month_label",
            pagination={"rowsPerPage": 15},
        )
        .classes("w-full")
        .props("dense flat"))


def _render_transactions(df: pd.DataFrame) -> None:
    """Transactions tab: filter bar + sortable paginated table."""

    with content_card():
        # Filter controls
        with ui.row().classes("w-full gap-3 items-end flex-wrap mm-border-bottom").style(
            "padding-bottom:14px; margin-bottom:12px;"
        ):
            search_in = (
                ui.input(placeholder="Search description…")
                .props("dense outlined clearable")
                .style("flex:3; min-width:200px;")
            )
            cat_opts = ["All categories"] + sorted(
                df["category"].dropna().unique().tolist()
            )
            cat_in = (
                ui.select(cat_opts, label="Category", value="All categories")
                .props("dense outlined")
                .style("flex:2; min-width:160px;")
            )
            type_in = (
                ui.select(
                    ["All types", "debit", "credit"],
                    label="Type", value="All types",
                )
                .props("dense outlined")
                .style("min-width:130px;")
            )
            max_in = (
                ui.number(label="Max rows", value=200, min=10, max=5000, step=50)
                .props("dense outlined")
                .style("width:110px;")
            )

        # Table columns definition
        TXN_COLS = [
            {"name": "date",             "label": "Date",        "field": "date",             "sortable": True},
            {"name": "description",      "label": "Description", "field": "description",      "sortable": True, "align": "left"},
            {"name": "category",         "label": "Category",    "field": "category",         "sortable": True},
            {"name": "amount",           "label": "Amount (₹)",  "field": "amount",           "sortable": True},
            {"name": "transaction_type", "label": "Type",        "field": "transaction_type", "sortable": True},
            {"name": "month_label",      "label": "Month",       "field": "month_label",      "sortable": True},
        ]

        DISP = ["date", "description", "category", "amount",
                "transaction_type", "month_label"]

        def _build_rows(n: int = 200) -> list[dict]:
            filt = df[DISP].copy()
            filt["date"] = filt["date"].astype(str)
            s   = (search_in.value or "").strip().lower()
            cat = cat_in.value  or "All categories"
            typ = type_in.value or "All types"
            if s:
                filt = filt[
                    filt["description"].str.lower().str.contains(s, na=False)
                ]
            if cat != "All categories":
                filt = filt[filt["category"] == cat]
            if typ != "All types":
                filt = filt[filt["transaction_type"] == typ]
            return (filt.sort_values("date", ascending=False)
                        .head(n).to_dict("records"))

        txn_table = (
            ui.table(
                columns=TXN_COLS,
                rows=_build_rows(),
                row_key="description",
                pagination={"rowsPerPage": 25, "sortBy": "date", "descending": True},
            )
            .classes("w-full")
            .props("dense flat")
        )

        status_lbl = ui.label(
            f"Showing {min(len(df), 200):,} of {len(df):,} rows"
        ).style("font-size:0.72rem; color:var(--mm-text-dim); margin-top:6px;")

        def _apply(_=None) -> None:
            n    = int(max_in.value or 200)
            rows = _build_rows(n)
            txn_table.rows = rows
            txn_table.update()
            status_lbl.set_text(
                f"Showing {len(rows):,} of {len(df):,} rows"
            )

        search_in.on("update:model-value", _apply)
        cat_in.on("update:model-value",    _apply)
        type_in.on("update:model-value",   _apply)
        max_in.on("update:model-value",    _apply)


def _render_insights(df: pd.DataFrame, net: float) -> None:
    """Insights tab: savings gauge + recommendations + anomalies."""

    insights   = generate_savings_insights(df)
    sr         = insights.get("savings_rate", {})
    gauge_val  = float(sr.get("savings_rate", 0))
    target_pct = float(sr.get("recommended_rate", 20))
    savings    = float(sr.get("total_savings", net))
    delta      = gauge_val - target_pct
    delta_col  = C_POSITIVE if delta >= 0 else C_NEGATIVE

    with ui.row().classes("w-full gap-4 items-start"):

        # Left column – gauge + stats
        with ui.element("div").style("flex:1; min-width:0;"):
            with content_card():
                ui.plotly(fig_savings_gauge(gauge_val, target_pct)).classes("w-full")

                divider()
                ui.element("div").style("height:10px;")

                with ui.row().classes("w-full justify-around"):
                    stat_pill(
                        "Net Savings",
                        fmt_inr(savings),
                        C_POSITIVE if savings >= 0 else C_NEGATIVE,
                    )
                    stat_pill(
                        "Savings Rate",
                        fmt_pct(gauge_val),
                        C_POSITIVE if gauge_val >= target_pct else C_NEGATIVE,
                    )
                    stat_pill(
                        "Target",
                        fmt_pct(target_pct),
                        C_TEXT_MUT,
                    )

                ui.element("div").style("height:8px;")
                delta_sym = "+" if delta >= 0 else ""
                ui.label(
                    f"{delta_sym}{fmt_pct(delta)} vs {fmt_pct(target_pct)} target"
                ).style(
                    f"font-size:0.76rem; color:{delta_col};"
                    "text-align:center; width:100%; display:block;"
                    "padding-bottom:4px;"
                )

        # Right column – recommendations
        with ui.element("div").style("flex:1; min-width:0;"):
            with content_card():
                card_title("Recommendations")
                ui.element("div").style("height:10px;")

                recs = insights.get("recommendations", [])
                if recs:
                    for rec in recs:
                        recommendation_item(rec)
                else:
                    with ui.row().classes("items-center gap-2").style("padding:6px 0;"):
                        ui.icon("check_circle_outline", size="1.3rem").style(
                            f"color:{C_POSITIVE};"
                        )
                        ui.label("No major concerns detected.").style(
                            f"font-size:0.84rem; color:{C_POSITIVE}; font-weight:600;"
                        )

    # Flagged purchases
    impulse_list = insights.get("impulse_purchases", [])
    if impulse_list:
        ui.element("div").style("height:16px;")
        with content_card():
            with ui.row().classes("items-center gap-2").style("margin-bottom:10px;"):
                card_title("Flagged Purchases")
                ui.label(f"  {len(impulse_list)} detected").style(
                    f"font-size:0.70rem; color:{C_NEGATIVE};"
                )
            imp_cols = [
                {"name": k, "label": k.replace("_", " ").title(),
                 "field": k, "sortable": True}
                for k in impulse_list[0].keys()
            ]
            (ui.table(columns=imp_cols, rows=impulse_list, row_key="description")
               .classes("w-full").props("dense flat"))

    # Monthly variance anomalies
    mv_list = insights.get("monthly_variance", [])
    if mv_list:
        ui.element("div").style("height:16px;")
        with content_card():
            with ui.row().classes("items-center gap-2").style("margin-bottom:10px;"):
                card_title("Spending Anomalies")
                ui.label(f"  {len(mv_list)} above-average months").style(
                    f"font-size:0.70rem; color:{C_WARNING};"
                )
            mv_cols = [
                {"name": k, "label": k.replace("_", " ").title(),
                 "field": k, "sortable": True}
                for k in mv_list[0].keys()
            ]
            (ui.table(columns=mv_cols, rows=mv_list, row_key="month")
               .classes("w-full").props("dense flat"))


# ══════════════════════════════════════════════════════════════════════════════
# Modal dialogs  (replace the old sidebar)
# ══════════════════════════════════════════════════════════════════════════════

def _build_upload_dialog() -> ui.dialog:
    """Returns a modal dialog containing the CSV upload widget."""
    with ui.dialog().props("persistent") as dlg:
        with ui.card().classes("mm-card mm-dialog-card").style(
            "min-width:420px; max-width:520px; padding:24px;"
        ):
            # Header row
            with ui.row().classes("w-full items-center justify-between mm-border-bottom").style(
                "margin-bottom:16px; padding-bottom:12px;"
            ):
                section_heading("Upload CSV")
                ui.button(icon="close", on_click=dlg.close).props(
                    "flat round dense size=sm"
                ).style("color:var(--mm-text-dim);")

            ui.label(
                "Select a CSV file to replace the current dataset. "
                "Required columns: date, description, amount, transaction_type."
            ).style("font-size:0.78rem; color:var(--mm-text-dim); margin-bottom:16px; line-height:1.5;")
            async def _on_upload(e: events.UploadEventArguments) -> None:
                dlg.close()
                n = ui.notification("Reading file…", type="ongoing", timeout=0)
                try:
                    data = await e.file.read()
                    n.message = "Processing CSV… (this may take a moment for large files)"
                    loop = asyncio.get_event_loop()
                    ok, msg = await loop.run_in_executor(None, replace_data, data)
                    if ok:
                        render_dashboard.refresh()
                        ui.notify(msg, type="positive", timeout=4000)
                    else:
                        ui.notify(msg, type="negative", timeout=8000)
                except Exception as exc:
                    ui.notify(f"Upload error: {exc}", type="negative", timeout=8000)
                finally:
                    n.dismiss()

            (ui.upload(on_upload=_on_upload)
               .props("accept=.csv color=primary label='Choose CSV file' auto-upload")
               .classes("w-full"))

            ui.element("div").style("height:8px;")
            ui.label("data/transactions.csv").style(
                "font-size:0.62rem; color:var(--mm-text-dim);"
            )
    return dlg


def _build_add_txn_dialog() -> ui.dialog:
    """Returns a modal dialog containing the add-transaction form."""
    with ui.dialog().props("persistent") as dlg:
        with ui.card().classes("mm-card mm-dialog-card").style(
            "min-width:440px; max-width:540px; padding:24px;"
        ):
            # Header row
            with ui.row().classes("w-full items-center justify-between mm-border-bottom").style(
                "margin-bottom:16px; padding-bottom:12px;"
            ):
                section_heading("Add Transaction")
                ui.button(icon="close", on_click=dlg.close).props(
                    "flat round dense size=sm"
                ).style("color:var(--mm-text-dim);")

            with ui.column().classes("w-full gap-3"):
                date_in = (
                    ui.input(
                        "Date",
                        value=str(datetime.date.today()),
                        placeholder="YYYY-MM-DD",
                    )
                    .props("dense outlined")
                    .classes("w-full")
                )
                desc_in = (
                    ui.input("Description", placeholder="e.g. Amazon order")
                    .props("dense outlined")
                    .classes("w-full")
                )
                amt_in = (
                    ui.number("Amount (₹)", min=0.01, format="%.2f", step=1)
                    .props("dense outlined")
                    .classes("w-full")
                )

                with ui.row().classes("w-full gap-3"):
                    type_in = (
                        ui.select(
                            ["Debit", "Credit"],
                            label="Type",
                            value="Debit",
                        )
                        .props("dense outlined")
                        .style("flex:1;")
                    )
                    cat_in = (
                        ui.select(
                            ["Auto-detect"] + CATEGORIES,
                            label="Category",
                            value="Auto-detect",
                        )
                        .props("dense outlined")
                        .style("flex:2;")
                    )

            ui.element("div").style("height:6px;")

            def _on_add() -> None:
                desc = str(desc_in.value or "").strip()
                if not desc:
                    ui.notify("Description is required.", type="warning")
                    return
                amt = float(amt_in.value or 0)
                if amt <= 0:
                    ui.notify("Amount must be greater than zero.", type="warning")
                    return

                raw_date  = str(date_in.value or datetime.date.today())
                norm_date = raw_date.replace("/", "-")
                category  = "" if cat_in.value == "Auto-detect" else str(cat_in.value)

                append_row(
                    date=norm_date, description=desc,
                    amount=amt, category=category,
                    tx_type=str(type_in.value),
                )
                render_dashboard.refresh()
                dlg.close()
                ui.notify(f"Added ₹{amt:,.2f} — {desc}", type="positive")
                desc_in.value = ""
                amt_in.value  = 0

            with ui.row().classes("w-full gap-2 justify-end").style("margin-top:8px;"):
                (ui.button("Cancel", on_click=dlg.close)
                   .props("flat no-caps no-shadow")
                   .style("color:var(--mm-text-dim);"))
                (ui.button("Add Transaction", on_click=_on_add)
                   .props("color=primary unelevated no-caps no-shadow")
                   .style("font-weight:600;"))
    return dlg


# ══════════════════════════════════════════════════════════════════════════════
# Settings dialog
# ══════════════════════════════════════════════════════════════════════════════

def _build_settings_dialog(dark_mode_el: ui.dark_mode) -> ui.dialog:
    """Settings modal: theme toggle + accent colour picker."""

    # Track which swatch is currently selected
    _state = {"accent": C_ACCENT, "dark": True}
    _swatch_els: dict[str, ui.element] = {}

    def _apply_accent(color: str) -> None:
        _state["accent"] = color
        ui.colors(primary=color)
        # Update swatch borders
        for c, el in _swatch_els.items():
            if c == color:
                el.classes(add="selected")
            else:
                el.classes(remove="selected")

    def _toggle_theme(is_dark: bool) -> None:
        _state["dark"] = is_dark
        if is_dark:
            dark_mode_el.enable()
        else:
            dark_mode_el.disable()
        _set_chart_dark(is_dark)
        render_dashboard.refresh()

    with ui.dialog().props("no-backdrop-dismiss") as dlg:
        with ui.card().classes("mm-card mm-dialog-card").style(
            "min-width:380px; max-width:460px; padding:24px;"
        ):
            # ─ Header ──────────────────────────────────────────────────
            with ui.row().classes("w-full items-center justify-between mm-border-bottom").style(
                "margin-bottom:20px; padding-bottom:14px;"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("tune", size="1.1rem").style(f"color:{C_ACCENT};")
                    section_heading("Appearance Settings")
                ui.button(icon="close", on_click=dlg.close).props(
                    "flat round dense size=sm"
                ).style("color:var(--mm-text-dim);")

            # ─ Theme toggle ────────────────────────────────────────────
            with ui.element("div").style("margin-bottom:22px;"):
                ui.label("Theme").style(
                    "font-size:0.70rem; font-weight:700; text-transform:uppercase;"
                    "letter-spacing:0.09em; color:var(--mm-text-dim); display:block; margin-bottom:10px;"
                )
                with ui.row().classes("gap-3"):
                    for label, is_dark, icon_name in [
                        ("Dark",  True,  "dark_mode"),
                        ("Light", False, "light_mode"),
                    ]:
                        def _mk_theme_btn(val=is_dark, lbl=label, ico=icon_name):
                            btn = (
                                ui.button(lbl, icon=ico,
                                          on_click=lambda v=val: _toggle_theme(v))
                                .props("unelevated no-caps no-shadow")
                                .style(
                                    "font-size:0.78rem; font-weight:600;"
                                    "padding:0 14px; height:32px;"
                                    + ("color:#fff; background:var(--q-primary);" if val == _state["dark"]
                                       else "color:var(--mm-text-dim); background:var(--mm-bg); border:1px solid var(--mm-border);")
                                )
                            )
                            return btn
                        _mk_theme_btn()

            # ─ Accent colour ────────────────────────────────────────────
            with ui.element("div"):
                ui.label("Accent Colour").style(
                    "font-size:0.70rem; font-weight:700; text-transform:uppercase;"
                    "letter-spacing:0.09em; color:var(--mm-text-dim); display:block; margin-bottom:12px;"
                )
                with ui.row().classes("gap-3 flex-wrap"):
                    for hex_color, name in ACCENT_PRESETS:
                        swatch = (
                            ui.element("div")
                            .classes("mm-swatch" + (" selected" if hex_color == _state["accent"] else ""))
                            .style(f"background:{hex_color};")
                            .on("click", lambda c=hex_color: _apply_accent(c))
                        )
                        swatch.tooltip(name)
                        _swatch_els[hex_color] = swatch

                ui.element("div").style("height:16px;")

                # Custom hex input
                with ui.row().classes("w-full items-center gap-2"):
                    custom_in = (
                        ui.input("Custom hex", placeholder="#RRGGBB")
                        .props("dense outlined")
                        .style("flex:1;")
                    )
                    (ui.button("Apply", on_click=lambda: _apply_accent(
                        custom_in.value.strip() if custom_in.value else _state["accent"]
                    ))
                     .props("unelevated no-caps no-shadow dense color=primary")
                     .style("height:36px; padding:0 14px; font-weight:600;"))

    return dlg


# ══════════════════════════════════════════════════════════════════════════════
# Page definition
# ══════════════════════════════════════════════════════════════════════════════

@ui.page("/")
def index() -> None:
    """Assemble the full page: CSS → header → main content."""

    # Inject global styles
    ui.add_css(GLOBAL_CSS)
    dark_mode_el = ui.dark_mode()
    dark_mode_el.enable()
    ui.colors(primary=C_ACCENT)

    # Build dialogs (must be created inside the page context)
    upload_dlg   = _build_upload_dialog()
    add_txn_dlg  = _build_add_txn_dialog()
    settings_dlg = _build_settings_dialog(dark_mode_el)

    # ── Top navigation bar ────────────────────────────────────────────────────
    with ui.header(elevated=False).style("padding:0 20px; height:52px;"):
        with ui.row().classes("h-full w-full items-center justify-between no-wrap"):

            # Brand
            with ui.row().classes("items-center gap-4 no-wrap"):
                ui.html(f"""
                <svg viewBox="0 0 20 20" width="20" height="20" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                  <path d="M17.5 10V6.25H4.375A1.875 1.875 0 0 1 4.375 2.5H17.5V6.25H4.375"
                        stroke="{C_ACCENT}" stroke-width="1.6"
                        stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2.5 4.375v12.5A1.875 1.875 0 0 0 4.375 18.75H17.5V14.375"
                        stroke="{C_ACCENT}" stroke-width="1.6"
                        stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M15 10a1.875 1.875 0 0 0 0 3.75h4.375V10H15z"
                        stroke="{C_ACCENT}" stroke-width="1.6"
                        stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                """)
                with ui.column().classes("gap-0"):
                    page_title("MoneyMind")
                    page_subtitle("Personal Finance Analytics")

            # Right side – action buttons + version tag
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
                ui.label("v3.0").style(
                    "font-size:0.65rem; color:var(--mm-text-dim);"
                    "background:var(--mm-bg); padding:2px 8px;"
                    "border:1px solid var(--mm-border); border-radius:3px;"
                    "margin-left:2px;"
                )

    # ── Main content area (full width, no drawer) ─────────────────────────────
    with ui.column().classes("w-full mm-page").style(
        "padding:28px 36px; min-height:100vh;"
    ):
        render_dashboard()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ui.run(
        title="MoneyMind",
        port=8080,
        dark=True,
        reload=False,
        show=True,
    )
