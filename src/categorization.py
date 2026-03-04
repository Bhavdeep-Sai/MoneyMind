"""
categorization.py
-----------------
Automatically assigns spending categories to transactions that are
missing a category label, using a keyword-rules engine.
"""

import re
import pandas as pd
import numpy as np


# ══════════════════════════════════════════════════════════════════════════════
# Keyword Rule Map
# Keys   → canonical category name
# Values → list of lowercase keywords/patterns to match in description
# ══════════════════════════════════════════════════════════════════════════════
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Income": [
        "salary", "payroll", "freelance", "payment received",
        "direct deposit", "wage", "bonus", "refund", "cashback", "opening balance",
    ],
    "Housing": [
        "rent", "mortgage", "hoa", "property tax", "home insurance",
        "apartment", "lease",
    ],
    "Groceries": [
        "grocery", "groceries", "supermarket", "whole foods", "trader joe",
        "aldi", "kroger", "publix", "costco", "walmart grocery", "safeway",
        "food mart", "fresh market", "bbq supplies", "market",
    ],
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "starbucks", "mcdonald", "burger",
        "pizza", "chipotle", "sushi", "taco", "kfc", "subway", "doordash",
        "uber eats", "grubhub", "dining", "bar", "pub", "bakery",
        "diner", "applebee", "olive garden", "outback", "cheesecake factory",
    ],
    "Transportation": [
        "uber", "lyft", "taxi", "gas", "fuel", "shell", "bp", "chevron",
        "exxon", "transit", "bus", "metro", "train", "parking",
        "toll", "car wash",
    ],
    "Shopping": [
        "amazon", "target", "walmart", "best buy", "ebay", "etsy",
        "zara", "h&m", "gap", "nike", "adidas", "clothing", "apparel",
        "purchase", "store", "shop", "mall",
    ],
    "Subscriptions": [
        "netflix", "spotify", "hulu", "disney", "apple music",
        "youtube premium", "prime", "amazon prime", "adobe",
        "gym", "membership", "subscription", "patreon",
    ],
    "Utilities": [
        "electric", "electricity", "water", "gas bill", "internet",
        "phone", "at&t", "verizon", "t-mobile", "cable", "wifi",
        "utility", "bill",
    ],
    "Healthcare": [
        "doctor", "hospital", "pharmacy", "cvs", "walgreens",
        "dental", "dentist", "medical", "clinic", "prescription",
        "health", "insurance premium",
    ],
    "Entertainment": [
        "movie", "cinema", "amc", "concert", "ticket", "spotify",
        "steam", "game", "gaming", "museum", "theater", "amusement",
        "park", "sport", "event",
    ],
    "Travel": [
        "hotel", "motel", "airbnb", "booking", "expedia",
        "flight", "airline", "delta", "united", "southwest", "hilton",
        "marriott", "travel", "resort", "vacation",
    ],
    "Education": [
        "udemy", "coursera", "edx", "tuition", "course", "book",
        "textbook", "school", "university", "college",
    ],
    "Miscellaneous": [
        "miscellaneous", "misc", "other", "unknown",
    ],
}


def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing or empty ``category`` values using keyword matching rules.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transaction DataFrame (output of data_cleaning.clean_transactions).

    Returns
    -------
    pd.DataFrame
        DataFrame with fully populated ``category`` column.
    """
    df = df.copy()

    # Ensure category column exists as object dtype (never float64 / ArrowDtype)
    if "category" not in df.columns:
        df["category"] = ""
    # Coerce to plain numpy object so .loc assignment never hits dtype mismatch
    df["category"] = df["category"].astype(object)

    # Track which rows need categorisation
    needs_category_mask = (
        df["category"].isna()
        | (df["category"].astype(str).str.strip().str.lower().isin(["", "nan", "none"]))
    )

    fill_count = needs_category_mask.sum()
    if fill_count > 0:
        print(f"[Categorizer] Auto-categorizing {fill_count} uncategorized transactions...")
        # .tolist() converts any ArrowStringArray / ExtensionArray → plain Python list
        # so pandas never tries to coerce it into the column's dtype
        categorised_values = (
            df.loc[needs_category_mask, "description"]
            .astype(str)
            .apply(_keyword_match)
            .tolist()
        )
        df.loc[needs_category_mask, "category"] = categorised_values
        filled = (df["category"] != "Miscellaneous").sum()
        print(f"[Categorizer] Successfully categorized {fill_count} rows "
              f"({fill_count - (df.loc[needs_category_mask, 'category'] == 'Miscellaneous').sum()} "
              f"matched keywords, rest -> 'Miscellaneous').")

    # Normalise category capitalization
    df["category"] = df["category"].astype(str).str.strip().str.title()

    # Override Income/Credit logic: credits not labelled Income → Income
    credit_mask = (
        (df["transaction_type"] == "credit")
        & (~df["category"].str.lower().isin(["income"]))
    )
    if credit_mask.sum() > 0:
        df.loc[credit_mask, "category"] = "Income"

    return df


def _keyword_match(description: str) -> str:
    """
    Match a transaction description against the keyword rule map.

    Parameters
    ----------
    description : str
        Cleaned transaction description text.

    Returns
    -------
    str
        The matched category name, or 'Miscellaneous' if no match is found.
    """
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Use word-boundary-aware matching for short keywords
            pattern = rf"\b{re.escape(kw)}\b" if len(kw) > 3 else re.escape(kw)
            if re.search(pattern, desc_lower):
                return category
    return "Miscellaneous"
