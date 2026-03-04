"""
generate_samples.py
-------------------
Generates 5 realistic sample CSV files with 1000+ transactions each.
Each file uses a different format to exercise the flexible column handling.
"""

import random
import csv
import os
from datetime import date, timedelta

random.seed(42)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Shared data pools ──────────────────────────────────────────────────────────
EXPENSE_ITEMS = [
    ("Swiggy Order",             "Food & Dining",    100, 800),
    ("Zomato Food Delivery",     "Food & Dining",    120, 900),
    ("Uber Ride",                "Transport",         80, 600),
    ("Ola Cab",                  "Transport",         60, 500),
    ("BigBasket Groceries",      "Groceries",        300, 4000),
    ("DMart Purchase",           "Groceries",        200, 3500),
    ("Reliance Fresh",           "Groceries",        150, 2000),
    ("Amazon Purchase",          "Shopping",         200, 8000),
    ("Flipkart Order",           "Shopping",         300, 6000),
    ("Myntra Fashion",           "Shopping",         500, 4000),
    ("Netflix Subscription",     "Entertainment",    149, 649),
    ("Spotify Premium",          "Entertainment",    119, 119),
    ("BookMyShow Tickets",       "Entertainment",    200, 1500),
    ("PVR Cinemas",              "Entertainment",    250, 800),
    ("Apollo Pharmacy",          "Healthcare",       100, 2000),
    ("MedPlus Medical Store",    "Healthcare",       80,  1500),
    ("Gym Membership",           "Healthcare",       500, 2500),
    ("Electricity Bill",         "Utilities",        800, 5000),
    ("Water Bill",               "Utilities",        200, 800),
    ("Airtel Mobile Bill",       "Utilities",        299, 999),
    ("Jio Recharge",             "Utilities",        199, 599),
    ("House Rent",               "Housing",         8000,30000),
    ("Maintenance Charges",      "Housing",          500, 3000),
    ("Petrol/Diesel",            "Transport",        500, 4000),
    ("Metro Card Recharge",      "Transport",        200, 1000),
    ("Coffee Shop",              "Food & Dining",     80, 500),
    ("Restaurant Dinner",        "Food & Dining",    400, 3000),
    ("School Fees",              "Education",       2000,15000),
    ("Online Course",            "Education",        499, 5000),
    ("Book Purchase",            "Education",        200, 1500),
    ("Hair Salon",               "Personal Care",    200, 1500),
    ("Spa & Wellness",           "Personal Care",    500, 3000),
    ("Travel Booking",           "Travel",          2000,20000),
    ("Hotel Stay",               "Travel",          1500,10000),
    ("Insurance Premium",        "Insurance",       1000,10000),
    ("ATM Withdrawal",           "Others",          500, 5000),
]

INCOME_ITEMS = [
    ("Salary Credit",            "Salary",          40000, 120000),
    ("Freelance Payment",        "Freelance",        5000,  30000),
    ("Interest Credit",          "Interest",          500,   3000),
    ("Dividend Credit",          "Investment",       1000,  15000),
    ("Bonus Credit",             "Bonus",            5000,  50000),
    ("Rental Income",            "Rental",           5000,  25000),
    ("Refund Credit",            "Refund",            200,   5000),
    ("Cashback Credit",          "Cashback",           50,   1000),
    ("Transfer Received",        "Transfer",         1000,  50000),
]

CATEGORIES = sorted({i[1] for i in EXPENSE_ITEMS} | {i[1] for i in INCOME_ITEMS})

def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def gen_transactions(n: int, start: date, end: date):
    rows = []
    for _ in range(n):
        d = rand_date(start, end)
        is_income = random.random() < 0.15
        pool = INCOME_ITEMS if is_income else EXPENSE_ITEMS
        desc, cat, lo, hi = random.choice(pool)
        amount = round(random.uniform(lo, hi), 2)
        tx_type = "credit" if is_income else "debit"
        rows.append((d, desc, amount, tx_type, cat))
    rows.sort(key=lambda r: r[0])
    return rows

START = date(2023, 1, 1)
END   = date(2025, 12, 31)

# ══════════════════════════════════════════════════════════════════════════════
# FILE 1 — Standard format (all 5 columns, clean)
# ══════════════════════════════════════════════════════════════════════════════
rows = gen_transactions(1500, START, END)
path = os.path.join(OUT_DIR, "sample_01_standard.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type", "category"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%Y-%m-%d"), desc, amt, tx, cat])
print(f"Created {path}  ({len(rows)} rows)")

# ══════════════════════════════════════════════════════════════════════════════
# FILE 2 — Indian bank export style (narration, Dr/Cr, no category)
# ══════════════════════════════════════════════════════════════════════════════
rows = gen_transactions(1200, START, END)
path = os.path.join(OUT_DIR, "sample_02_bank_export.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Date", "Narration", "Amount", "Dr/Cr"])   # alias column names
    for d, desc, amt, tx, _ in rows:
        dr_cr = "Cr" if tx == "credit" else "Dr"
        w.writerow([d.strftime("%d/%m/%Y"), desc, amt, dr_cr])
print(f"Created {path}  ({len(rows)} rows)")

# ══════════════════════════════════════════════════════════════════════════════
# FILE 3 — Minimal (only date + amount, no other columns)
# ══════════════════════════════════════════════════════════════════════════════
rows = gen_transactions(1000, START, END)
path = os.path.join(OUT_DIR, "sample_03_minimal.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "amount"])
    for d, _, amt, tx, _ in rows:
        # Encode debit as negative, credit as positive for sign-inference
        signed = amt if tx == "credit" else -amt
        w.writerow([d.strftime("%Y-%m-%d"), signed])
print(f"Created {path}  ({len(rows)} rows)")

# ══════════════════════════════════════════════════════════════════════════════
# FILE 4 — US bank style (Transaction Date, Particulars, Debit/Credit Amount)
# ══════════════════════════════════════════════════════════════════════════════
rows = gen_transactions(1300, START, END)
path = os.path.join(OUT_DIR, "sample_04_us_bank.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Transaction Date", "Particulars", "Debit/Credit Amount", "Type", "Category"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%m/%d/%Y"), desc, amt, tx.capitalize(), cat])
print(f"Created {path}  ({len(rows)} rows)")

# ══════════════════════════════════════════════════════════════════════════════
# FILE 5 — High-volume with currency symbols and commas in amounts
# ══════════════════════════════════════════════════════════════════════════════
rows = gen_transactions(2000, START, END)
path = os.path.join(OUT_DIR, "sample_05_highvolume.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type", "category"])
    for d, desc, amt, tx, cat in rows:
        # Format amount with commas + Rs prefix (tests currency stripping)
        fancy_amt = f"Rs {amt:,.2f}"
        w.writerow([d.strftime("%Y-%m-%d"), desc, fancy_amt, tx, cat])
print(f"Created {path}  ({len(rows)} rows)")

print("\nAll 5 sample files generated successfully.")
