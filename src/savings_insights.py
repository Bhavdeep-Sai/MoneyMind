"""
savings_insights.py
-------------------
Generates actionable savings recommendations by analysing:
  - Largest spending categories
  - Recurring subscription services
  - High restaurant/dining spend
  - Impulse / discretionary purchases
  - Monthly overspend vs average
"""

import pandas as pd
import numpy as np
from typing import Optional


# ── Thresholds and configuration ──────────────────────────────────────────────
DINING_MONTHLY_THRESHOLD = 5000.00       # Alert if dining > ₹5,000/month
SUBSCRIPTION_MONTHLY_THRESHOLD = 1500.00 # Alert if subscriptions > ₹1,500/month
ENTERTAINMENT_MONTHLY_THRESHOLD = 3000.00
SHOPPING_MONTHLY_THRESHOLD = 8000.00
IMPULSE_SINGLE_THRESHOLD = 2000.00       # Flag single transactions > ₹2,000 in risky categories
SAVINGS_RATE_MIN = 0.20                  # Recommended 20% savings rate


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def generate_savings_insights(df: pd.DataFrame) -> dict:
    """
    Run the full insights pipeline and return a structured report.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned and categorized transaction DataFrame.

    Returns
    -------
    dict
        Keys:
          ``largest_category``    – Category with highest total spend.
          ``subscriptions``       – Recurring subscription details.
          ``dining_analysis``     – Dining spend analysis.
          ``shopping_analysis``   – Shopping spend analysis.
          ``impulse_purchases``   – List of likely impulse buys.
          ``savings_rate``        – Actual vs recommended savings rate.
          ``recommendations``     – List of plain-English recommendations.
          ``monthly_variance``    – Months where spending exceeds average.
    """
    insights = {}

    insights["largest_category"]  = _largest_spending_category(df)
    insights["subscriptions"]     = _subscription_analysis(df)
    insights["dining_analysis"]   = _dining_analysis(df)
    insights["shopping_analysis"] = _shopping_analysis(df)
    insights["impulse_purchases"] = _detect_impulse_purchases(df)
    insights["savings_rate"]      = _savings_rate_analysis(df)
    insights["monthly_variance"]  = _monthly_variance_analysis(df)
    insights["recommendations"]   = _build_recommendations(insights)

    return insights


# ══════════════════════════════════════════════════════════════════════════════
# Private analysis helpers
# ══════════════════════════════════════════════════════════════════════════════

def _largest_spending_category(df: pd.DataFrame) -> dict:
    """Identify the single largest expense category."""
    expense_df = df[df["transaction_type"] == "debit"]
    total = expense_df["amount"].sum()
    if total == 0:
        return {}
    by_cat = expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    top_cat = by_cat.index[0]
    top_amt = by_cat.iloc[0]
    return {
        "category": top_cat,
        "total_spent": round(top_amt, 2),
        "pct_of_total": round((top_amt / total) * 100, 2),
    }


def _subscription_analysis(df: pd.DataFrame) -> dict:
    """
    Analyse subscription services.
    Identifies individual recurring services and monthly totals.
    """
    sub_df = df[
        (df["transaction_type"] == "debit")
        & (df["category"].str.lower() == "subscriptions")
    ].copy()

    if sub_df.empty:
        return {"monthly_total": 0, "services": [], "alert": False}

    # Monthly totals
    monthly = sub_df.groupby("month_label")["amount"].sum()
    avg_monthly = monthly.mean()

    # Individual service breakdown
    service_totals = (
        sub_df.groupby("description")["amount"]
        .agg(total_paid="sum", occurrences="count", avg_cost="mean")
        .reset_index()
        .sort_values("total_paid", ascending=False)
        .round(2)
    )

    return {
        "monthly_total": round(avg_monthly, 2),
        "total_paid": round(sub_df["amount"].sum(), 2),
        "services": service_totals.to_dict(orient="records"),
        "alert": avg_monthly > SUBSCRIPTION_MONTHLY_THRESHOLD,
    }


def _dining_analysis(df: pd.DataFrame) -> dict:
    """Analyse Food & Dining spend with monthly breakdown and alerts."""
    dining_df = df[
        (df["transaction_type"] == "debit")
        & (df["category"].str.lower().isin(["food & dining", "food and dining"]))
    ].copy()

    if dining_df.empty:
        return {"monthly_avg": 0, "total": 0, "alert": False, "top_vendors": []}

    monthly = dining_df.groupby("month_label")["amount"].sum()
    avg_monthly = monthly.mean()

    top_vendors = (
        dining_df.groupby("description")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
        .rename(columns={"amount": "total_spent"})
        .round(2)
    )

    return {
        "total": round(dining_df["amount"].sum(), 2),
        "monthly_avg": round(avg_monthly, 2),
        "monthly_breakdown": monthly.round(2).to_dict(),
        "top_vendors": top_vendors.to_dict(orient="records"),
        "alert": avg_monthly > DINING_MONTHLY_THRESHOLD,
    }


def _shopping_analysis(df: pd.DataFrame) -> dict:
    """Analyse Shopping spend."""
    shop_df = df[
        (df["transaction_type"] == "debit")
        & (df["category"].str.lower() == "shopping")
    ].copy()

    if shop_df.empty:
        return {"monthly_avg": 0, "total": 0, "alert": False}

    monthly = shop_df.groupby("month_label")["amount"].sum()
    avg_monthly = monthly.mean()

    return {
        "total": round(shop_df["amount"].sum(), 2),
        "monthly_avg": round(avg_monthly, 2),
        "alert": avg_monthly > SHOPPING_MONTHLY_THRESHOLD,
    }


def _detect_impulse_purchases(df: pd.DataFrame) -> list[dict]:
    """
    Flag potentially impulsive transactions based on:
    - Category is discretionary (Shopping, Entertainment, Food & Dining)
    - Single transaction exceeds the impulse threshold
    """
    DISCRETIONARY = {"shopping", "entertainment", "food & dining", "miscellaneous"}
    impulse_df = df[
        (df["transaction_type"] == "debit")
        & (df["category"].str.lower().isin(DISCRETIONARY))
        & (df["amount"] >= IMPULSE_SINGLE_THRESHOLD)
    ].copy()

    if impulse_df.empty:
        return []

    return (
        impulse_df[["date", "description", "amount", "category"]]
        .sort_values("amount", ascending=False)
        .assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d"))
        .head(10)
        .round(2)
        .to_dict(orient="records")
    )


def _savings_rate_analysis(df: pd.DataFrame) -> dict:
    """
    Calculate actual savings rate and compare to recommended 20% rate.

    Savings rate = (Income - Spending) / Income
    """
    income    = df[df["transaction_type"] == "credit"]["amount"].sum()
    spending  = df[df["transaction_type"] == "debit"]["amount"].sum()
    savings   = income - spending
    rate      = savings / income if income > 0 else 0.0

    return {
        "total_income":    round(income, 2),
        "total_spending":  round(spending, 2),
        "total_savings":   round(savings, 2),
        "savings_rate":    round(rate * 100, 2),
        "recommended_rate": round(SAVINGS_RATE_MIN * 100, 2),
        "on_track":        rate >= SAVINGS_RATE_MIN,
    }


def _monthly_variance_analysis(df: pd.DataFrame) -> list[dict]:
    """
    Identify months where spending significantly exceeded the monthly average.
    Returns months with spending > 1 standard deviation above mean.
    """
    expense_df = df[df["transaction_type"] == "debit"]
    monthly = expense_df.groupby("month_label")["amount"].sum()

    if len(monthly) < 2:
        return []

    mean_spend = monthly.mean()
    std_spend  = monthly.std()
    threshold  = mean_spend + std_spend

    overspend_months = monthly[monthly > threshold].reset_index()
    overspend_months.columns = ["month", "total_spent"]
    overspend_months["above_average_by"] = (
        overspend_months["total_spent"] - mean_spend
    ).round(2)
    overspend_months["total_spent"] = overspend_months["total_spent"].round(2)
    return overspend_months.to_dict(orient="records")


def _build_recommendations(insights: dict) -> list[str]:
    """
    Translate analysis insights into plain-English savings recommendations.

    Parameters
    ----------
    insights : dict
        The partial insights dict (without the 'recommendations' key yet).

    Returns
    -------
    list[str]
        Ordered list of actionable recommendation strings.
    """
    recs = []

    # ── Savings rate ──────────────────────────────────────────────────────────
    sr = insights.get("savings_rate", {})
    if not sr.get("on_track", True):
        deficit = (sr["recommended_rate"] - sr["savings_rate"])
        recs.append(
            f"You are saving {sr['savings_rate']:.1f}% of your income. "
            f"Aim for at least {sr['recommended_rate']:.0f}% — "
            f"try to cut expenses by ~₹{sr['total_income'] * deficit / 100:,.0f}/month."
        )

    # ── Subscriptions ─────────────────────────────────────────────────────────
    subs = insights.get("subscriptions", {})
    if subs.get("alert"):
        services = [s["description"] for s in subs.get("services", [])][:3]
        recs.append(
            f"Subscriptions cost ~₹{subs['monthly_total']:.0f}/month. "
            f"Review: {', '.join(services)}. "
            "Consider cancelling unused services."
        )

    # ── Dining ────────────────────────────────────────────────────────────────
    dining = insights.get("dining_analysis", {})
    if dining.get("alert"):
        recs.append(
            f"Dining out averages ₹{dining['monthly_avg']:.0f}/month. "
            f"Cooking at home even 3 extra nights/week could save ~₹"
            f"{dining['monthly_avg'] * 0.30:,.0f}/month."
        )

    # ── Shopping ──────────────────────────────────────────────────────────────
    shop = insights.get("shopping_analysis", {})
    if shop.get("alert"):
        recs.append(
            f"Shopping spending averages ₹{shop['monthly_avg']:.0f}/month. "
            "Apply a 24-hour rule before non-essential purchases."
        )

    # ── Impulse purchases ─────────────────────────────────────────────────────
    impulse = insights.get("impulse_purchases", [])
    if impulse:
        total_impulse = sum(p["amount"] for p in impulse)
        recs.append(
            f"Detected {len(impulse)} potential impulse purchases totalling "
            f"₹{total_impulse:,.2f}. Create a monthly discretionary budget cap."
        )

    # ── Monthly variance ──────────────────────────────────────────────────────
    variance = insights.get("monthly_variance", [])
    if variance:
        months = [v["month"] for v in variance]
        recs.append(
            f"Overspending detected in: {', '.join(months)}. "
            "Set a monthly spending alert in your bank app."
        )

    # ── Largest category ──────────────────────────────────────────────────────
    largest = insights.get("largest_category", {})
    if largest and largest.get("pct_of_total", 0) > 30:
        recs.append(
            f"{largest['category']} accounts for {largest['pct_of_total']:.1f}% "
            f"of total spending (₹{largest['total_spent']:,.2f}). "
            "Consider strategies to reduce this category."
        )

    if not recs:
        recs.append("Great job! Your spending looks healthy. Keep maintaining your budget discipline.")

    return recs
