"""
layout.py
---------
Reusable NiceGUI UI component helpers.

All visual primitives live here so app.py stays clean and declarative.
Every function returns or yields the created NiceGUI element.
"""

from contextlib import contextmanager
from nicegui import ui

from utils import (
    C_BG, C_SURFACE, C_SURFACE2, C_BORDER, C_BORDER2,
    C_TEXT, C_TEXT_MUT, C_TEXT_DIM,
    C_ACCENT, C_POSITIVE, C_NEGATIVE, C_WARNING, C_NEUTRAL,
)

# ── Typography helpers ─────────────────────────────────────────────────────────

def page_title(text: str) -> ui.label:
    return ui.label(text).style(
        "font-size:1.25rem; font-weight:700; color:var(--mm-text);"
        "letter-spacing:-0.01em; line-height:1;"
    )


def page_subtitle(text: str) -> ui.label:
    return ui.label(text).style(
        "font-size:0.78rem; color:var(--mm-text-mut); margin-top:1px;"
    )


def section_heading(text: str) -> ui.label:
    """Small uppercase section label."""
    return ui.label(text).style(
        "font-size:0.62rem; font-weight:700; text-transform:uppercase;"
        "letter-spacing:0.10em; color:var(--mm-text-dim);"
    )


def card_title(text: str) -> ui.label:
    """Chart / section card heading."""
    return ui.label(text).style(
        "font-size:0.72rem; font-weight:600; text-transform:uppercase;"
        "letter-spacing:0.07em; color:var(--mm-text-mut);"
    )


def divider() -> ui.separator:
    return ui.separator().style(
        "background:var(--mm-border); opacity:1; margin:0;"
    )


# ── Metric card ────────────────────────────────────────────────────────────────

def metric_card(
    label: str,
    value: str,
    delta: str = "",
    delta_positive: bool | None = None,
    accent_color: str = C_NEUTRAL,
) -> None:
    """
    Flat metric card with a coloured left accent bar.

      label          – small uppercase label
      value          – large primary value string
      delta          – optional small change annotation
      delta_positive – True = green, False = red, None = muted
      accent_color   – colour of the 3px left border
    """
    delta_color = (
        C_POSITIVE if delta_positive is True
        else C_NEGATIVE if delta_positive is False
        else C_TEXT_MUT
    )

    with ui.element("div").classes("mm-metric-card").style(
        f"border-left:3px solid {accent_color};"
        "border-radius:6px; padding:14px 16px; flex:1; min-width:0;"
    ):
        ui.label(label).style(
            "font-size:0.65rem; font-weight:600; text-transform:uppercase;"
            "letter-spacing:0.09em; color:var(--mm-text-dim); display:block;"
        )
        ui.label(value).style(
            "font-size:1.35rem; font-weight:700; color:var(--mm-text);"
            "line-height:1.3; margin-top:4px; display:block;"
            "white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"
        )
        if delta:
            ui.label(delta).style(
                f"font-size:0.72rem; color:{delta_color};"
                "margin-top:3px; display:block;"
            )


# ── Card containers ────────────────────────────────────────────────────────────

@contextmanager
def chart_card(title: str = ""):
    """
    Context manager that wraps a Plotly chart in a flat bordered card.
    Usage:
        with chart_card("My Chart"):
            ui.plotly(fig).classes("w-full")
    """
    with ui.card().classes("flex-1 w-full mm-card").style(
        "border-radius:6px; padding:16px;"
    ):
        if title:
            card_title(title)
            ui.element("div").style("height:10px;")
        yield


@contextmanager
def content_card():
    """Generic bordered surface card (no title)."""
    with ui.card().classes("w-full mm-card").style(
        "border-radius:6px; padding:16px;"
    ):
        yield


# ── Insight callout rows ───────────────────────────────────────────────────────

def recommendation_item(text: str) -> None:
    """A single recommendation row inside the Insights tab."""
    with ui.element("div").classes("mm-rec-item").style(
        f"border-left:3px solid {C_WARNING};"
        "border-radius:4px; padding:9px 12px; margin-bottom:6px;"
    ):
        ui.label(text).style(
            "font-size:0.82rem; color:var(--mm-text-mut); line-height:1.55;"
        )


def stat_pill(label: str, value: str, color: str = C_NEUTRAL) -> None:
    """Compact inline stat used beneath the savings gauge."""
    with ui.column().classes("items-center gap-0"):
        ui.label(label).style(
            "font-size:0.62rem; text-transform:uppercase;"
            "letter-spacing:0.09em; color:var(--mm-text-dim);"
        )
        ui.label(value).style(
            f"font-size:1.25rem; font-weight:700; color:{color};"
        )


# ── Global CSS injection ───────────────────────────────────────────────────────

GLOBAL_CSS = f"""
/* ── CSS custom properties (theme tokens) ─────────────────────── */
:root, .body--dark {{
  --mm-bg:       {C_BG};
  --mm-surface:  {C_SURFACE};
  --mm-surface2: {C_SURFACE2};
  --mm-border:   {C_BORDER};
  --mm-text:     {C_TEXT};
  --mm-text-mut: {C_TEXT_MUT};
  --mm-text-dim: {C_TEXT_DIM};
}}
.body--light {{
  --mm-bg:       #F1F5F9;
  --mm-surface:  #FFFFFF;
  --mm-surface2: #F8FAFC;
  --mm-border:   #CBD5E1;
  --mm-text:     #0F172A;
  --mm-text-mut: #475569;
  --mm-text-dim: #94A3B8;
}}

/* ── Reset & base ─────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}

body, .q-page {{
    background: var(--mm-bg) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    color: var(--mm-text);
}}

/* ── Card / surface classes ───────────────────────────────────── */
.mm-metric-card {{
    background: var(--mm-surface);
    border: 1px solid var(--mm-border);
    box-shadow: 0 1px 3px rgba(0,0,0,0.18);
}}
.mm-card {{
    background: var(--mm-surface) !important;
    border: 1px solid var(--mm-border) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.18) !important;
}}
.mm-dialog-card {{
    background: var(--mm-surface) !important;
    border: 1px solid var(--mm-border) !important;
    border-radius: 8px;
}}
.mm-rec-item {{
    background: var(--mm-surface2);
    border: 1px solid var(--mm-border);
}}
.mm-page {{
    background: var(--mm-bg) !important;
}}
.mm-border-bottom {{
    border-bottom: 1px solid var(--mm-border) !important;
}}
.mm-separator {{
    background: var(--mm-border) !important; height:1px;
}}

/* ── Top header ───────────────────────────────────────────────── */
.q-header {{
    background: var(--mm-surface) !important;
    border-bottom: 1px solid var(--mm-border) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
}}

/* ── Left drawer (sidebar) ────────────────────────────────────── */
.q-drawer {{
    background: var(--mm-surface) !important;
    border-right: 1px solid var(--mm-border) !important;
    box-shadow: none !important;
}}

/* ── Tabs ─────────────────────────────────────────────────────── */
.q-tabs {{
    background: transparent !important;
    border-bottom: 1px solid {C_BORDER};
}}
.q-tab {{
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    text-transform: none !important;
    letter-spacing: 0.01em;
    color: var(--mm-text-mut) !important;
    padding: 0 18px !important;
    min-height: 40px !important;
}}
.q-tab--active {{
    color: var(--mm-text) !important;
}}
div[data-baseweb="tab-highlight"],
.q-tab-indicator {{
    background: var(--q-primary) !important;
    height: 2px !important;
}}
.q-tab-panels {{ background: transparent !important; }}

/* ── Form fields ──────────────────────────────────────────────── */
.q-field--outlined .q-field__control {{
    background: var(--mm-bg) !important;
    border-radius: 4px !important;
}}
.q-field__label {{ color: var(--mm-text-dim) !important; font-size:0.78rem !important; }}
.q-field__native, .q-field__input {{
    color: var(--mm-text) !important; font-size:0.84rem !important;
}}
.q-field--outlined:hover .q-field__control:before {{
    border-color: var(--mm-border) !important;
}}
.q-field--focused .q-field__control:after {{
    border-color: {C_ACCENT} !important;
}}

/* ── Buttons ──────────────────────────────────────────────────── */
.q-btn.no-shadow {{ box-shadow: none !important; }}

/* ── Quasar tables ────────────────────────────────────────────── */
.q-table__container {{ background: transparent !important; }}
.q-table tbody td  {{
    color: var(--mm-text-mut) !important;
    font-size: 0.82rem !important;
    border-color: var(--mm-border) !important;
    padding: 8px 10px !important;
}}
.q-table thead th  {{
    color: var(--mm-text-dim) !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-color: var(--mm-border) !important;
    padding: 8px 10px !important;
    background: var(--mm-surface2) !important;
    font-weight: 600 !important;
}}
.q-table tr:hover td {{
    background: rgba(var(--q-primary-rgb, 37,99,235), 0.06) !important;
}}
.q-table__bottom {{
    color: var(--mm-text-dim) !important;
    font-size: 0.78rem !important;
    border-color: var(--mm-border) !important;
}}

/* ── Expansion panel ──────────────────────────────────────────── */
.q-expansion-item .q-item {{ padding: 8px 0 !important; }}
.q-expansion-item__content {{ padding: 0 !important; }}

/* ── Scrollbars ───────────────────────────────────────────────── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:{C_BG}; }}
::-webkit-scrollbar-thumb {{ background:{C_BORDER}; border-radius:3px; }}
::-webkit-scrollbar-thumb:hover {{ background:{C_TEXT_DIM}; }}

/* ── Quasar notification ──────────────────────────────────────── */
.q-notification {{ font-size:0.82rem !important; }}

/* ── Separator override ───────────────────────────────────────── */
.q-separator {{ background:{C_BORDER} !important; opacity:1 !important; }}

/* ── Light mode overrides ─────────────────────────────────────── */
.body--light,
.body--light .q-page {{
    background: #F1F5F9 !important;
    color: #0F172A !important;
}}
.body--light .q-header {{
    background: #FFFFFF !important;
    border-bottom: 1px solid #CBD5E1 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}}
.body--light .mm-card {{
    background: #FFFFFF !important;
    border-color: #CBD5E1 !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}}
.body--light .mm-page {{
    background: #F1F5F9 !important;
}}
.body--light .q-tabs {{
    border-bottom-color: #CBD5E1 !important;
}}
.body--light .q-tab {{ color: #64748B !important; }}
.body--light .q-tab--active {{ color: #0F172A !important; }}
.body--light .q-table tbody td {{
    color: #334155 !important;
    border-color: #E2E8F0 !important;
}}
.body--light .q-table thead th {{
    color: #64748B !important;
    background: #F8FAFC !important;
    border-color: #E2E8F0 !important;
}}
.body--light .q-table__bottom {{ color: #94A3B8 !important; border-color: #E2E8F0 !important; }}
.body--light .q-field--outlined .q-field__control {{ background: #FFFFFF !important; }}
.body--light .q-field__native, .body--light .q-field__input {{ color: #0F172A !important; }}
.body--light .q-field__label {{ color: #94A3B8 !important; }}
.body--light ::-webkit-scrollbar-track {{ background: #F1F5F9; }}
.body--light ::-webkit-scrollbar-thumb {{ background: #CBD5E1; }}
.body--light .q-separator {{ background: #E2E8F0 !important; }}

/* ── Settings panel swatches ──────────────────────────────────── */
.mm-swatch {{
    width: 28px; height: 28px; border-radius: 50%;
    cursor: pointer; border: 2px solid transparent;
    transition: transform 0.15s, border-color 0.15s;
    flex-shrink: 0;
}}
.mm-swatch:hover {{ transform: scale(1.15); }}
.mm-swatch.selected {{ border-color: #FFFFFF !important; box-shadow: 0 0 0 2px rgba(255,255,255,0.6); }}
.body--light .mm-swatch.selected {{ border-color: #0F172A !important; box-shadow: 0 0 0 2px rgba(0,0,0,0.25); }}

/* ── Chart skeleton shimmer & fade-in ──────────────────────── */
@keyframes mm-shimmer {{
  0%   {{ background-position: -600px 0; }}
  100% {{ background-position:  600px 0; }}
}}
@keyframes mm-fadein {{
  from {{ opacity: 0; transform: translateY(10px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
.mm-skeleton {{
  background: linear-gradient(90deg,
    var(--mm-surface) 25%,
    var(--mm-border)  50%,
    var(--mm-surface) 75%);
  background-size: 800px 100%;
  animation: mm-shimmer 1.4s infinite linear;
  border-radius: 6px;
  min-height: 260px;
  width: 100%;
  margin-top: 4px;
}}
.mm-chart-wrap {{
  animation: mm-fadein 0.45s ease;
}}
"""
