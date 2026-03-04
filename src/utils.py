"""
utils.py
--------
Shared constants, colour palette, and formatting helpers.
All modules import from here to ensure visual consistency.
"""

import os

# ── File paths ────────────────────────────────────────────────────────────────
SRC_DIR    = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.normpath(os.path.join(SRC_DIR, ".."))
DATA_PATH  = os.path.join(ROOT_DIR, "data", "transactions.csv")

# ── Colour palette  (muted, corporate) ────────────────────────────────────────
# Backgrounds / surfaces
C_BG        = "#0F172A"   # page background
C_SURFACE   = "#1E293B"   # card / panel surface
C_SURFACE2  = "#162032"   # slightly deeper surface
C_BORDER    = "#334155"   # dividers and borders
C_BORDER2   = "#1E293B"   # very subtle inner border

# Text
C_TEXT      = "#F1F5F9"   # primary text
C_TEXT_MUT  = "#94A3B8"   # muted / secondary text
C_TEXT_DIM  = "#475569"   # disabled / placeholder text

# Accent / semantic
C_ACCENT    = "#2563EB"   # primary blue accent
C_POSITIVE  = "#059669"   # income / positive delta
C_NEGATIVE  = "#DC2626"   # expense / negative delta
C_WARNING   = "#D97706"   # caution
C_NEUTRAL   = "#64748B"   # neutral metric

# Chart colour sequence  (8 muted tones)
CHART_PALETTE = [
    "#2563EB",  # blue
    "#0891B2",  # cyan
    "#059669",  # green
    "#D97706",  # amber
    "#9333EA",  # purple
    "#DC2626",  # red
    "#0F766E",  # teal
    "#B45309",  # warm-brown
]

# Plotly layout defaults (applied to every chart)
CHART_LAYOUT = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="Inter, system-ui, sans-serif",
                         color=C_TEXT_MUT, size=12),
    margin        = dict(t=30, b=40, l=10, r=10),
    legend        = dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    hoverlabel    = dict(bgcolor=C_SURFACE, bordercolor=C_BORDER,
                         font_color=C_TEXT, font_size=12),
)

GRID_COLOR  = "#1E3050"   # subtle chart grid lines

# ── Formatting helpers ─────────────────────────────────────────────────────────

def fmt_inr(value: float, decimals: int = 2) -> str:
    """Return a value formatted as Indian Rupee string, e.g. ₹1,23,456.78"""
    return f"₹{value:,.{decimals}f}"


def fmt_int(value: int) -> str:
    """Return a comma-formatted integer string."""
    return f"{value:,}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Return a percentage string."""
    return f"{value:.{decimals}f}%"
