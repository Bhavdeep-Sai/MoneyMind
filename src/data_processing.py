"""
data_processing.py
------------------
Single entry-point for all data operations.

Wraps the existing pipeline modules (data_loader, data_cleaning,
categorization, analysis, savings_insights) and adds a lightweight
file-mtime cache so the DataFrame is only rebuilt when the CSV changes.
"""

import os
import io
import pandas as pd

from utils import DATA_PATH

# ── Import existing pipeline ───────────────────────────────────────────────────
from data_loader      import load_transactions
from data_cleaning    import clean_transactions
from categorization   import categorize_transactions, CATEGORY_KEYWORDS
from analysis import (
    spending_summary,
    monthly_spending_trend,
    category_spending,
    top_expense_categories,
    day_of_week_spending,
    monthly_category_heatmap_data,
)
from savings_insights import generate_savings_insights

# Public re-exports so callers only need to import from data_processing
__all__ = [
    "load_df", "invalidate_cache", "append_row", "replace_data",
    "CATEGORIES",
    # analysis helpers
    "spending_summary", "monthly_spending_trend", "category_spending",
    "top_expense_categories", "day_of_week_spending",
    "monthly_category_heatmap_data", "generate_savings_insights",
]

CATEGORIES: list[str] = sorted(CATEGORY_KEYWORDS.keys())

# ── In-process cache ───────────────────────────────────────────────────────────
_cache: dict = {"mtime": -1.0, "df": None}


def _rebuild() -> pd.DataFrame:
    """Run the full ETL pipeline and cache the result."""
    raw          = load_transactions(DATA_PATH)
    cleaned      = clean_transactions(raw)
    categorised  = categorize_transactions(cleaned)
    _cache["df"]    = categorised
    _cache["mtime"] = os.path.getmtime(DATA_PATH)
    return categorised


def load_df() -> pd.DataFrame | None:
    """Return the processed DataFrame, rebuilding only if the file changed."""
    if not os.path.exists(DATA_PATH):
        return None
    mtime = os.path.getmtime(DATA_PATH)
    if mtime != _cache["mtime"] or _cache["df"] is None:
        _rebuild()
    return _cache["df"]


def invalidate_cache() -> None:
    """Force the next load_df() call to rebuild from disk."""
    _cache["mtime"] = -1.0


# ── Write helpers ──────────────────────────────────────────────────────────────

def append_row(
    date: str,
    description: str,
    amount: float,
    category: str,
    tx_type: str,
) -> None:
    """Append a single transaction row to the CSV file."""
    row = pd.DataFrame([{
        "date":             date,
        "description":      description,
        "amount":           amount,
        "category":         category,
        "transaction_type": tx_type.lower(),
    }])
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    write_header = not os.path.exists(DATA_PATH)
    row.to_csv(DATA_PATH, mode="a", header=write_header, index=False)
    invalidate_cache()


def replace_data(csv_bytes: bytes) -> tuple[bool, str]:
    """
    Overwrite the data file with a new CSV uploaded by the user.

    Only ``date`` and ``amount`` are required; all other columns are
    synthesised if absent so any bank export format will be accepted.

    Returns (success: bool, message: str).
    """
    from data_loader import _apply_aliases, _merge_split_amount_columns, _fill_missing_optional
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
        df.columns = [c.strip().lower() for c in df.columns]

        # Apply alias substitutions (e.g. 'narration' -> 'description')
        _apply_aliases(df)

        # Merge split debit/credit columns if present (HDFC, SBI style)
        _merge_split_amount_columns(df)

        # Only date + amount are truly required
        required = {"date", "amount"}
        missing  = required - set(df.columns)
        if missing:
            return False, f"Missing columns: {', '.join(sorted(missing))}. Your CSV must have at least: date, amount."

        # Synthesise any missing optional columns
        df = _fill_missing_optional(df)

        os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
        df.to_csv(DATA_PATH, index=False)
        invalidate_cache()
        return True, f"Loaded {len(df):,} transactions."
    except Exception as exc:
        return False, f"Error reading file: {exc}"
