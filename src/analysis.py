"""
analysis.py
-----------
Core spending analysis functions. All functions operate on a cleaned,
categorized DataFrame produced by the earlier pipeline stages.

Provides:
  - Spending summary (income, expenses, net balance)
  - Monthly / weekly spending trends
  - Category-wise spending breakdown
  - Top N expense categories
  - Average spend per category
  - Day-of-week spending patterns
"""

import pandas as pd
import numpy as np
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# High-Level Summary
# ══════════════════════════════════════════════════════════════════════════════

def spending_summary(df: pd.DataFrame) -> dict:
    """
    Return total income, total spending, and net balance.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and categorized transaction DataFrame.

    Returns
    -------
    dict
        Keys: ``total_income``, ``total_spending``, ``net_balance``,
        ``transaction_count``, ``expense_count``, ``income_count``.
    """
    income_df = df[df["transaction_type"] == "credit"]
    expense_df = df[df["transaction_type"] == "debit"]

    total_income = income_df["amount"].sum()
    total_spending = expense_df["amount"].sum()
    net_balance = total_income - total_spending

    return {
        "total_income": round(total_income, 2),
        "total_spending": round(total_spending, 2),
        "net_balance": round(net_balance, 2),
        "transaction_count": len(df),
        "expense_count": len(expense_df),
        "income_count": len(income_df),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Monthly Trends
# ══════════════════════════════════════════════════════════════════════════════

def monthly_spending_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute total spending and income per calendar month.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transaction DataFrame.

    Returns
    -------
    pd.DataFrame
        Indexed by ``month_label`` with columns:
        ``total_spending``, ``total_income``, ``net_balance``, ``transaction_count``.
    """
    monthly = (
        df.groupby("month_label")
        .apply(
            lambda g: pd.Series({
                "total_spending": g.loc[g["transaction_type"] == "debit", "amount"].sum(),
                "total_income":   g.loc[g["transaction_type"] == "credit", "amount"].sum(),
                "transaction_count": len(g),
            })
        )
        .reset_index()
    )
    monthly["net_balance"] = monthly["total_income"] - monthly["total_spending"]
    monthly = monthly.sort_values("month_label").reset_index(drop=True)
    return monthly


# ══════════════════════════════════════════════════════════════════════════════
# Category-Wise Analysis
# ══════════════════════════════════════════════════════════════════════════════

def category_spending(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate total spending, transaction count, and percentage
    of overall spend broken down by category.

    Only debit (expense) transactions are included.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and categorized transaction DataFrame.

    Returns
    -------
    pd.DataFrame
        Sorted descending by ``total_spent``.  Columns:
        ``category``, ``total_spent``, ``transaction_count``,
        ``avg_per_transaction``, ``pct_of_total``.
    """
    expense_df = df[df["transaction_type"] == "debit"].copy()
    total = expense_df["amount"].sum()

    cat_df = (
        expense_df.groupby("category")
        .agg(
            total_spent=("amount", "sum"),
            transaction_count=("amount", "count"),
        )
        .reset_index()
    )
    cat_df["avg_per_transaction"] = (
        cat_df["total_spent"] / cat_df["transaction_count"]
    ).round(2)
    cat_df["pct_of_total"] = ((cat_df["total_spent"] / total) * 100).round(2)
    cat_df = cat_df.sort_values("total_spent", ascending=False).reset_index(drop=True)
    return cat_df


def top_expense_categories(
    df: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    """
    Return the top N expense categories by total spend.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and categorized transaction DataFrame.
    top_n : int
        Number of categories to return. Default is 5.

    Returns
    -------
    pd.DataFrame
        Top N rows from category_spending(), same schema.
    """
    return category_spending(df).head(top_n)


# ══════════════════════════════════════════════════════════════════════════════
# Day-of-Week Patterns
# ══════════════════════════════════════════════════════════════════════════════

def day_of_week_spending(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute average daily spending for each day of the week.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transaction DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: ``day_of_week``, ``total_spent``, ``avg_spent``,
        ``transaction_count``.  Ordered Monday → Sunday.
    """
    day_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]
    expense_df = df[df["transaction_type"] == "debit"].copy()
    dow_df = (
        expense_df.groupby("day_of_week")["amount"]
        .agg(
            total_spent="sum",
            avg_spent="mean",
            transaction_count="count",
        )
        .reset_index()
        .round(2)
    )
    dow_df["day_of_week"] = pd.Categorical(
        dow_df["day_of_week"], categories=day_order, ordered=True
    )
    return dow_df.sort_values("day_of_week").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# Monthly Category Heatmap Data
# ══════════════════════════════════════════════════════════════════════════════

def monthly_category_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a pivot table of monthly spending per category for heatmap rendering.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and categorized transaction DataFrame.

    Returns
    -------
    pd.DataFrame
        Pivot table where rows = categories, columns = month_labels,
        values = total spending (NaN filled with 0).
    """
    expense_df = df[df["transaction_type"] == "debit"].copy()
    pivot = expense_df.pivot_table(
        index="category",
        columns="month_label",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    # Sort rows by total descending
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).drop(columns="_total")
    return pivot
