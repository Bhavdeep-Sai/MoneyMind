"""
charts.py
---------
Static Matplotlib / Seaborn chart builders for MoneyMind.

Each function accepts a processed DataFrame, creates a Figure, and returns it.

Theme control:
    import charts
    charts.set_theme(dark=True)   # default – dark navy style
    charts.set_theme(dark=False)  # clean white / light style

    figures = charts.build_all(df, insights)
    charts.save_all(figures, out_dir="output")
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from utils import (
    CHART_PALETTE, GRID_COLOR,
    C_BG, C_SURFACE, C_TEXT, C_TEXT_MUT,
    C_POSITIVE, C_NEGATIVE, C_ACCENT, C_WARNING,
    L_BG, L_SURFACE, L_BORDER, L_TEXT, L_TEXT_MUT, L_GRID,
)
from analysis import (
    category_spending, monthly_spending_trend, top_expense_categories,
    day_of_week_spending, monthly_category_heatmap_data,
)


# ── Theme state ───────────────────────────────────────────────────────────────
_dark: bool = True


def set_theme(dark: bool = True) -> None:
    """Switch between dark (default) and light chart themes."""
    global _dark
    _dark = dark


# ── Theme-aware colour helpers ────────────────────────────────────────────────
def _bg()     -> str: return C_BG       if _dark else L_BG
def _surf()   -> str: return C_SURFACE  if _dark else L_SURFACE
def _txt()    -> str: return C_TEXT     if _dark else L_TEXT
def _txtm()   -> str: return C_TEXT_MUT if _dark else L_TEXT_MUT
def _grd()    -> str: return GRID_COLOR if _dark else L_GRID
def _border() -> str: return "#334155"  if _dark else L_BORDER
def _legend_bg() -> str: return C_SURFACE if _dark else "#F1F5F9"


# ── Shared rc / figure helpers ────────────────────────────────────────────────
def _style_dict() -> dict:
    return {
        "figure.facecolor":  _bg(),
        "axes.facecolor":    _surf(),
        "axes.edgecolor":    _border(),
        "axes.labelcolor":   _txtm(),
        "xtick.color":       _txtm(),
        "ytick.color":       _txtm(),
        "text.color":        _txt(),
        "grid.color":        _grd(),
        "grid.linestyle":    "--",
        "grid.linewidth":    0.5,
        "legend.facecolor":  _legend_bg(),
        "legend.edgecolor":  _border(),
        "font.family":       "sans-serif",
        "font.size":         11,
    }


def _apply_style() -> None:
    plt.rcParams.update(_style_dict())


def _new_fig(w: float = 10, h: float = 5):
    _apply_style()
    fig, ax = plt.subplots(figsize=(w, h), facecolor=_bg())
    ax.set_facecolor(_surf())
    ax.spines[:].set_edgecolor(_border())
    ax.tick_params(colors=_txtm())
    return fig, ax


def _fmt_inr(v: float) -> str:
    return f"\u20b9{v:,.0f}"


# ── Chart functions ────────────────────────────────────────────────────────────

def fig_spending_pie(df: pd.DataFrame) -> plt.Figure:
    """Donut chart — spending share by category (top 10)."""
    cat_df = category_spending(df).head(10)
    _apply_style()
    fig, ax = plt.subplots(figsize=(7, 6), facecolor=_bg())
    ax.set_facecolor(_bg())

    colors = (CHART_PALETTE * 2)[:len(cat_df)]
    wedges, texts, autotexts = ax.pie(
        cat_df["total_spent"],
        labels=cat_df["category"],
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.52, edgecolor=_bg(), linewidth=2),
        textprops=dict(color=_txt(), fontsize=9),
        pctdistance=0.80,
    )
    for at in autotexts:
        at.set_color(_txt())
        at.set_fontsize(8)

    total = cat_df["total_spent"].sum()
    ax.text(0, 0, _fmt_inr(total), ha="center", va="center",
            fontsize=14, fontweight="bold", color=_txt())
    ax.set_title("Category Spending Share", color=_txt(), fontsize=13, pad=12)
    fig.tight_layout()
    return fig


def fig_top_categories(df: pd.DataFrame) -> plt.Figure:
    """Horizontal bar — top 10 expense categories."""
    top = top_expense_categories(df, top_n=10).sort_values("total_spent")
    fig, ax = _new_fig(10, 6)

    colors = (CHART_PALETTE * 2)[:len(top)]
    bars = ax.barh(top["category"], top["total_spent"],
                   color=colors, edgecolor="none")

    max_val = top["total_spent"].max()
    for bar, val in zip(bars, top["total_spent"]):
        ax.text(
            bar.get_width() + max_val * 0.01,
            bar.get_y() + bar.get_height() / 2,
            _fmt_inr(val), va="center", ha="left",
            fontsize=9, color=_txtm(),
        )

    ax.set_xlabel("Total Spent (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Top 10 Expense Categories", color=_txt(), fontsize=13, pad=12)
    ax.xaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.yaxis.grid(False)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))
    fig.tight_layout()
    return fig


def fig_monthly_trend(df: pd.DataFrame) -> plt.Figure:
    """Grouped bar + twin-axis line — monthly income vs expenses + net balance."""
    m = monthly_spending_trend(df)
    x = np.arange(len(m))
    w = 0.35

    fig, ax = _new_fig(max(12, len(m) * 0.55), 5)

    ax.bar(x - w / 2, m["total_income"],   w, label="Income",
           color=C_POSITIVE, alpha=0.85, edgecolor="none")
    ax.bar(x + w / 2, m["total_spending"], w, label="Expenses",
           color=C_NEGATIVE, alpha=0.85, edgecolor="none")

    ax2 = ax.twinx()
    ax2.set_facecolor(_surf())
    ax2.spines[:].set_edgecolor(_border())
    ax2.plot(x, m["net_balance"], color=C_ACCENT, linewidth=2,
             marker="o", markersize=4, label="Net Balance", zorder=5)
    ax2.axhline(0, color=_border(), linewidth=0.8, linestyle="--")
    ax2.tick_params(colors=_txtm())
    ax2.set_ylabel("Net Balance (\u20b9)", color=_txtm(), fontsize=10)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))

    ax.set_xticks(x)
    ax.set_xticklabels(m["month_label"], rotation=45, ha="right",
                       fontsize=8, color=_txtm())
    ax.set_ylabel("Amount (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Monthly Income vs Expenses", color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2,
              facecolor=_legend_bg(), edgecolor=_border(),
              labelcolor=_txtm(), fontsize=9, loc="upper left")
    fig.tight_layout()
    return fig


def fig_cumulative_balance(df: pd.DataFrame) -> plt.Figure:
    """Area chart — cumulative account balance over time."""
    df_s = df.sort_values("date").copy()
    df_s["cumulative"] = df_s["signed_amount"].cumsum()

    fig, ax = _new_fig(12, 4)
    ax.fill_between(df_s["date"], df_s["cumulative"],
                    color=C_ACCENT, alpha=0.18)
    ax.plot(df_s["date"], df_s["cumulative"],
            color=C_ACCENT, linewidth=1.5)
    ax.axhline(0, color=_border(), linewidth=0.8, linestyle="--")
    ax.set_xlabel("Date", color=_txtm(), fontsize=10)
    ax.set_ylabel("Balance (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Cumulative Account Balance", color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))
    fig.tight_layout()
    return fig


def fig_day_of_week(df: pd.DataFrame) -> plt.Figure:
    """Bar chart — total spending per day of week."""
    dow = day_of_week_spending(df)
    fig, ax = _new_fig(8, 4)

    ax.bar(dow["day_of_week"], dow["total_spent"],
           color=C_ACCENT, alpha=0.85, edgecolor="none")
    ax.set_xlabel("Day of Week", color=_txtm(), fontsize=10)
    ax.set_ylabel("Total Spent (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Spending by Day of Week", color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))
    fig.tight_layout()
    return fig


def fig_heatmap(df: pd.DataFrame) -> plt.Figure:
    """Heatmap — category x month spending (last 24 months)."""
    hm = monthly_category_heatmap_data(df)
    if hm.empty:
        _apply_style()
        fig, ax = plt.subplots(facecolor=_bg())
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=_txtm(), transform=ax.transAxes)
        return fig

    if hm.shape[1] > 24:
        hm = hm.iloc[:, -24:]

    n_cats = hm.shape[0]
    height = max(5, n_cats * 0.5 + 2)
    _apply_style()
    fig, ax = plt.subplots(figsize=(16, height), facecolor=_bg())
    ax.set_facecolor(_surf())

    if _dark:
        cmap = LinearSegmentedColormap.from_list(
            "mm_blue", ["#0F172A", "#1E3A5F", "#1D4ED8", "#60A5FA"]
        )
    else:
        cmap = LinearSegmentedColormap.from_list(
            "mm_blue_light", ["#EFF6FF", "#BFDBFE", "#3B82F6", "#1D4ED8"]
        )

    sns.heatmap(
        hm, ax=ax, cmap=cmap,
        linewidths=0.5, linecolor=_bg(),
        cbar_kws={"shrink": 0.6, "label": "\u20b9 Spent"},
        annot=False,
    )
    ax.set_title("Category \u00d7 Month Spending Heatmap",
                 color=_txt(), fontsize=13, pad=12)
    ax.set_xlabel("Month", color=_txtm(), fontsize=10)
    ax.set_ylabel("Category", color=_txtm(), fontsize=10)
    ax.tick_params(colors=_txtm(), labelsize=9)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)

    cbar = ax.collections[0].colorbar
    if cbar:
        cbar.ax.tick_params(colors=_txtm(), labelsize=9)
        cbar.ax.yaxis.label.set_color(_txtm())

    fig.tight_layout()
    return fig


def fig_savings_gauge(gauge_val: float, target: float = 20.0) -> plt.Figure:
    """Semi-donut savings rate gauge."""
    _apply_style()
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=_bg(),
                           subplot_kw=dict(aspect="equal"))
    ax.set_facecolor(_bg())

    track_bg = "#1E3A5F" if _dark else "#DBEAFE"
    theta_bg = np.linspace(np.pi, 0, 300)
    r = 1.0
    ax.plot(np.cos(theta_bg) * r, np.sin(theta_bg) * r,
            color=track_bg, linewidth=22, solid_capstyle="round", zorder=1)

    fill_frac = min(max(gauge_val / 100.0, 0.0), 1.0)
    theta_val = np.linspace(np.pi, np.pi - fill_frac * np.pi, 300)
    color = (C_POSITIVE if gauge_val >= target
             else C_WARNING if gauge_val >= target * 0.7
             else C_NEGATIVE)
    ax.plot(np.cos(theta_val) * r, np.sin(theta_val) * r,
            color=color, linewidth=22, solid_capstyle="round", zorder=2)

    t_ang = np.pi - (target / 100.0) * np.pi
    ax.plot(
        [np.cos(t_ang) * 0.78, np.cos(t_ang) * 1.18],
        [np.sin(t_ang) * 0.78, np.sin(t_ang) * 1.18],
        color=_txtm(), linewidth=2, zorder=3,
    )
    ax.text(np.cos(t_ang) * 1.30, np.sin(t_ang) * 1.30,
            f"Target\n{target:.0f}%", ha="center", va="center",
            fontsize=8, color=_txtm())

    ax.text(0, 0.15, f"{gauge_val:.1f}%", ha="center", va="center",
            fontsize=26, fontweight="bold", color=_txt(), zorder=4)
    ax.text(0, -0.22, "Savings Rate", ha="center", va="center",
            fontsize=11, color=_txtm())
    delta = gauge_val - target
    delta_color = C_POSITIVE if delta >= 0 else C_NEGATIVE
    sign = "+" if delta >= 0 else ""
    ax.text(0, -0.48, f"{sign}{delta:.1f}% vs target",
            ha="center", va="center", fontsize=9, color=delta_color)

    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.7, 1.3)
    ax.axis("off")
    fig.tight_layout()
    return fig


def fig_day_transaction_count(df: pd.DataFrame) -> plt.Figure:
    """Bar chart — number of transactions per day of week."""
    dow = day_of_week_spending(df)
    fig, ax = _new_fig(8, 4)

    bars = ax.bar(dow["day_of_week"], dow["transaction_count"],
                  color=C_POSITIVE, alpha=0.85, edgecolor="none")
    max_val = dow["transaction_count"].max() if len(dow) else 1
    for bar, val in zip(bars, dow["transaction_count"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_val * 0.015,
            str(int(val)), ha="center", va="bottom",
            fontsize=9, color=_txtm(),
        )

    ax.set_xlabel("Day of Week", color=_txtm(), fontsize=10)
    ax.set_ylabel("Number of Transactions", color=_txtm(), fontsize=10)
    ax.set_title("Transaction Count by Day", color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    fig.tight_layout()
    return fig


def fig_day_avg_transaction(df: pd.DataFrame) -> plt.Figure:
    """Bar chart — average transaction value per day of week."""
    dow = day_of_week_spending(df)
    fig, ax = _new_fig(8, 4)

    bars = ax.bar(dow["day_of_week"], dow["avg_spent"],
                  color=C_WARNING, alpha=0.85, edgecolor="none")
    max_val = dow["avg_spent"].max() if len(dow) else 1
    for bar, val in zip(bars, dow["avg_spent"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_val * 0.015,
            _fmt_inr(val), ha="center", va="bottom",
            fontsize=8, color=_txtm(),
        )

    ax.set_xlabel("Day of Week", color=_txtm(), fontsize=10)
    ax.set_ylabel("Avg Transaction (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Avg Transaction Value by Day", color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))
    fig.tight_layout()
    return fig


def fig_day_category_breakdown(df: pd.DataFrame) -> plt.Figure:
    """Stacked bar chart — top 6 expense categories by day of week."""
    day_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    expense_df = df[df["transaction_type"] == "debit"].copy()
    if expense_df.empty:
        _apply_style()
        fig, ax = plt.subplots(facecolor=_bg())
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=_txtm(), transform=ax.transAxes)
        return fig

    pivot = expense_df.pivot_table(
        index="day_of_week", columns="category",
        values="amount", aggfunc="sum", fill_value=0,
    )
    top_cats = pivot.sum().nlargest(6).index.tolist()
    pivot = pivot[top_cats]
    pivot.index = pd.Categorical(pivot.index, categories=day_order, ordered=True)
    pivot = pivot.sort_index()

    _apply_style()
    fig, ax = plt.subplots(figsize=(12, 5), facecolor=_bg())
    ax.set_facecolor(_surf())
    ax.spines[:].set_edgecolor(_border())
    ax.tick_params(colors=_txtm())

    colors = (CHART_PALETTE * 2)[:len(top_cats)]
    bottom = np.zeros(len(pivot))
    for cat, color in zip(top_cats, colors):
        vals = pivot[cat].values
        ax.bar(pivot.index.astype(str), vals, bottom=bottom,
               label=cat, color=color, alpha=0.90, edgecolor="none")
        bottom += vals

    ax.set_xlabel("Day of Week", color=_txtm(), fontsize=10)
    ax.set_ylabel("Total Spent (\u20b9)", color=_txtm(), fontsize=10)
    ax.set_title("Spending by Category \u00d7 Day of Week",
                 color=_txt(), fontsize=13, pad=12)
    ax.yaxis.grid(True, color=_grd(), linestyle="--", linewidth=0.5)
    ax.xaxis.grid(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: _fmt_inr(x)))
    ax.legend(facecolor=_legend_bg(), edgecolor=_border(),
              labelcolor=_txtm(), fontsize=9, loc="upper right")
    fig.tight_layout()
    return fig


# ── Batch helpers ──────────────────────────────────────────────────────────────

def build_all(df: pd.DataFrame, insights: dict) -> dict:
    """
    Build all charts and return a name -> Figure mapping.
    Call set_theme(dark=True/False) before this to control styling.
    """
    savings_rate = insights.get("savings_rate", {}).get("savings_rate", 0.0)
    return {
        "spending_pie":            fig_spending_pie(df),
        "top_categories":          fig_top_categories(df),
        "monthly_trend":           fig_monthly_trend(df),
        "cumulative_balance":      fig_cumulative_balance(df),
        "day_of_week":             fig_day_of_week(df),
        "day_transaction_count":   fig_day_transaction_count(df),
        "day_avg_transaction":     fig_day_avg_transaction(df),
        "day_category_breakdown":  fig_day_category_breakdown(df),
        "heatmap":                 fig_heatmap(df),
        "savings_gauge":           fig_savings_gauge(savings_rate),
    }


def save_all(figures: dict, out_dir: str, dpi: int = 150) -> list:
    """Save all figures to `out_dir` as PNG files. Returns list of saved paths."""
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for name, fig in figures.items():
        path = os.path.join(out_dir, f"{name}.png")
        fig.savefig(path, dpi=dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        saved.append(path)
    return saved
