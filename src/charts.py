"""
charts.py
---------
All Plotly figure builders for MoneyMind.

Each function accepts a processed DataFrame and returns a go.Figure.
Charts use a muted corporate palette with transparent backgrounds so
they sit cleanly on top of any dark surface.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import (
    CHART_LAYOUT, CHART_PALETTE, GRID_COLOR,
    C_BG, C_TEXT, C_TEXT_MUT, C_POSITIVE, C_NEGATIVE, C_ACCENT, C_WARNING,
    C_SURFACE, C_BORDER,
)
from data_processing import (
    category_spending, monthly_spending_trend, top_expense_categories,
    day_of_week_spending, monthly_category_heatmap_data,
    spending_summary, generate_savings_insights,
)


# ── Theme state (toggled by app.py when the user switches themes) ─────────────
_dark: bool = True


def set_dark(dark: bool) -> None:
    """Update the module-level dark flag. app.py calls this then refreshes the dashboard."""
    global _dark
    _dark = dark


def _t() -> str:
    """Primary text colour for the current theme."""
    return C_TEXT if _dark else "#0F172A"


def _tm() -> str:
    """Muted text colour for the current theme."""
    return C_TEXT_MUT if _dark else "#475569"


def _grid() -> str:
    """Grid / axis line colour for the current theme."""
    return GRID_COLOR if _dark else "rgba(203,213,225,0.5)"


# ── Shared helpers ────────────────────────────────────────────────────────────

def _base_layout(**overrides) -> dict:
    """Merge CHART_LAYOUT with theme-aware hover/font colors and per-chart overrides."""
    layout = CHART_LAYOUT.copy()
    # Override hover and font colors based on current theme
    if _dark:
        layout["hoverlabel"] = dict(
            bgcolor=C_SURFACE, bordercolor=C_BORDER,
            font_color=C_TEXT, font_size=12,
        )
    else:
        layout["hoverlabel"] = dict(
            bgcolor="#FFFFFF", bordercolor="#CBD5E1",
            font_color="#0F172A", font_size=12,
        )
        layout["font"] = dict(
            family="Inter, system-ui, sans-serif",
            color="#475569", size=12,
        )
    layout.update(overrides)
    return layout


def _axis(title: str = "", **kw) -> dict:
    """Standard axis style — colours adapt to current theme."""
    defaults = dict(
        title=dict(text=title, font=dict(size=11, color=_tm())),
        showgrid=True,
        gridcolor=_grid(),
        gridwidth=1,
        zeroline=False,
        tickfont=dict(size=11, color=_tm()),
        linecolor=_grid(),
    )
    defaults.update(kw)
    return defaults


def _no_grid_axis(title: str = "") -> dict:
    return _axis(title=title, showgrid=False)


# ── Category charts ───────────────────────────────────────────────────────────

def fig_spending_pie(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart — spending share by category (top 10).
    """
    cat_df = category_spending(df).head(10)

    fig = go.Figure(go.Pie(
        labels=cat_df["category"],
        values=cat_df["total_spent"],
        hole=0.52,
        marker=dict(
            colors=CHART_PALETTE,
            line=dict(color=C_BG if _dark else "#FFFFFF", width=2),
        ),
        textinfo="percent+label",
        textfont=dict(size=11, color=_t()),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}<br>%{percent}<extra></extra>",
        direction="clockwise",
        sort=True,
    ))

    fig.update_layout(**_base_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        annotations=[dict(
            text=f"₹{cat_df['total_spent'].sum():,.0f}",
            x=0.5, y=0.5, font_size=16,
            font_color=_t(),
            showarrow=False,
        )],
    ))
    return fig


def fig_treemap(df: pd.DataFrame) -> go.Figure:
    """
    Treemap — category spending distribution.
    """
    cat_df = category_spending(df)

    fig = px.treemap(
        cat_df,
        path=["category"],
        values="total_spent",
        color="total_spent",
        color_continuous_scale=[
            [0.0, "#1E3A5F"],
            [0.5, "#2563EB"],
            [1.0, "#60A5FA"],
        ],
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}<extra></extra>",
        texttemplate="%{label}<br>₹%{value:,.0f}",
        textfont=dict(size=11),
    )
    fig.update_layout(**_base_layout(
        coloraxis_showscale=False,
        margin=dict(t=10, b=10, l=10, r=10),
    ))
    return fig


def fig_top_categories(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar — top 10 expense categories.
    """
    top = top_expense_categories(df, top_n=10).sort_values("total_spent")

    fig = go.Figure(go.Bar(
        x=top["total_spent"],
        y=top["category"],
        orientation="h",
        marker=dict(
            color=top["total_spent"],
            colorscale=[[0, "#1E3A5F"], [1, "#2563EB"]],
            showscale=False,
            line=dict(width=0),
        ),
        text=top["total_spent"].apply(lambda v: f"₹{v:,.0f}"),
        textposition="outside",
        textfont=dict(size=10, color=_tm()),
        hovertemplate="<b>%{y}</b><br>₹%{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        xaxis=_axis("Total Spent (₹)", tickprefix="₹"),
        yaxis=_no_grid_axis(),
        margin=dict(t=10, b=40, l=10, r=90),
    ))
    return fig


def fig_day_of_week(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart — average spending per day of week.
    """
    dow = day_of_week_spending(df)

    fig = go.Figure(go.Bar(
        x=dow["day_of_week"],
        y=dow["total_spent"],
        marker=dict(color=C_ACCENT, opacity=0.85, line=dict(width=0)),
        text=dow["total_spent"].apply(lambda v: f"₹{v:,.0f}"),
        textposition="outside",
        textfont=dict(size=10, color=_tm()),
        hovertemplate="<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(
        xaxis=_no_grid_axis(),
        yaxis=_axis("Total Spent (₹)", tickprefix="₹"),
        margin=dict(t=10, b=40, l=10, r=20),
    ))
    return fig


# ── Trend charts ──────────────────────────────────────────────────────────────

def fig_monthly_trend(df: pd.DataFrame) -> go.Figure:
    """
    Combined line + bar chart — monthly income, expenses, net balance.
    """
    m = monthly_spending_trend(df)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Net balance bars (secondary axis, behind lines)
    fig.add_trace(go.Bar(
        x=m["month_label"], y=m["net_balance"],
        name="Net Balance",
        marker_color=[C_POSITIVE if v >= 0 else C_NEGATIVE
                      for v in m["net_balance"]],
        opacity=0.30,
        hovertemplate="<b>%{x}</b><br>Net ₹%{y:,.2f}<extra></extra>",
    ), secondary_y=False)

    # Income line
    fig.add_trace(go.Scatter(
        x=m["month_label"], y=m["total_income"],
        name="Income",
        mode="lines+markers",
        line=dict(color=C_POSITIVE, width=2),
        marker=dict(size=5, color=C_POSITIVE),
        hovertemplate="Income ₹%{y:,.2f}<extra></extra>",
    ), secondary_y=False)

    # Expenses line
    fig.add_trace(go.Scatter(
        x=m["month_label"], y=m["total_spending"],
        name="Expenses",
        mode="lines+markers",
        line=dict(color=C_NEGATIVE, width=2),
        marker=dict(size=5, color=C_NEGATIVE),
        hovertemplate="Expenses ₹%{y:,.2f}<extra></extra>",
    ), secondary_y=False)

    fig.update_layout(**_base_layout(
        barmode="overlay",
        hovermode="x unified",
        xaxis=_no_grid_axis(),
        yaxis=_axis("Amount (₹)", tickprefix="₹"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            font=dict(size=11, color=_tm()),
        ),
        margin=dict(t=30, b=40, l=10, r=10),
    ))
    return fig


def fig_cumulative_balance(df: pd.DataFrame) -> go.Figure:
    """
    Area chart — running cumulative account balance over time.
    """
    df_s = df.sort_values("date").copy()
    df_s["cumulative"] = df_s["signed_amount"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_s["date"],
        y=df_s["cumulative"],
        mode="lines",
        line=dict(color=C_ACCENT, width=2),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.10)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Balance ₹%{y:,.2f}<extra></extra>",
        name="Balance",
    ))
    fig.update_layout(**_base_layout(
        xaxis=_no_grid_axis(),
        yaxis=_axis("Balance (₹)", tickprefix="₹"),
        showlegend=False,
        margin=dict(t=10, b=40, l=10, r=10),
    ))
    return fig


def fig_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap — monthly spending by category.
    Categories on Y (8 rows), months on X (last 24 months).
    """
    hm = monthly_category_heatmap_data(df)
    if hm.empty:
        return go.Figure()

    # hm: rows=categories, columns=month_labels
    # Keep only last 24 months to avoid overcrowding the X axis
    if hm.shape[1] > 24:
        hm = hm.iloc[:, -24:]

    n_cats   = hm.shape[0]
    n_months = hm.shape[1]
    cell_h   = max(36, min(60, 400 // max(n_cats, 1)))
    height   = cell_h * n_cats + 120  # rows + axis labels margin

    fig = px.imshow(
        hm,                        # categories on Y, months on X
        aspect="auto",
        color_continuous_scale=[[0, "#0F172A"], [0.35, "#1E3A5F"], [0.7, "#1D4ED8"], [1, "#60A5FA"]],
        text_auto=False,           # no per-cell annotations — too cluttered
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x}<br><b>₹%{z:,.0f}</b><extra></extra>",
        xgap=2,
        ygap=2,
    )
    fig.update_layout(**_base_layout(
        height=height,
        coloraxis_showscale=True,
        coloraxis_colorbar=dict(
            tickfont=dict(color=_tm(), size=10),
            title=dict(text="\u20b9 Spent", font=dict(color=_tm(), size=10)),
            thickness=12,
            len=0.8,
        ),
        xaxis=dict(
            showgrid=False,
            tickangle=-45,
            tickfont=dict(size=10, color=_tm()),
            title=None,
            side="bottom",
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(size=11, color=_t()),
            title=None,
            autorange="reversed",  # top category first
        ),
        margin=dict(t=10, b=90, l=120, r=80),
    ))
    return fig


# ── Insights charts ───────────────────────────────────────────────────────────

def fig_savings_gauge(gauge_val: float, target: float) -> go.Figure:
    """
    Gauge indicator — current savings rate vs target.
    """
    # Determine bar colour based on performance
    if gauge_val >= target:
        bar_color = C_POSITIVE
    elif gauge_val >= target * 0.7:
        bar_color = C_WARNING
    else:
        bar_color = C_NEGATIVE

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=gauge_val,
        delta={
            "reference":    target,
            "valueformat":  ".1f",
            "suffix":       "%",
            "increasing":   {"color": C_POSITIVE},
            "decreasing":   {"color": C_NEGATIVE},
        },
        number={"suffix": "%", "font": {"size": 38, "color": _t()}},
        title={"text": "Savings Rate", "font": {"size": 13, "color": _tm()}},
        gauge={
            "axis": {
                "range":      [0, 100],
                "ticksuffix": "%",
                "tickfont":   {"size": 10, "color": _tm()},
            },
            "bar":   {"color": bar_color, "thickness": 0.65},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  10],  "color": "rgba(220,38,38,0.12)"},
                {"range": [10, 20],  "color": "rgba(217,119,6,0.12)"},
                {"range": [20, 100], "color": "rgba(5,150,105,0.12)"},
            ],
            "threshold": {
                "line":      {"color": _tm(), "width": 2},
                "thickness": 0.75,
                "value":     target,
            },
        },
    ))
    fig.update_layout(**_base_layout(
        height=230,
        margin=dict(t=30, b=20, l=20, r=20),
    ))
    return fig
