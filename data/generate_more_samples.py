"""
generate_more_samples.py
------------------------
Generates 10 additional realistic sample CSV files with 2000+ rows each.
Each file uses a distinct persona, date range, currency style, or column format
to stress-test the flexible ETL pipeline.
"""

import random
import csv
import os
from datetime import date, timedelta

random.seed(99)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════════════════════

def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def gen_rows(n: int, start: date, end: date,
             expense_pool, income_pool,
             income_ratio: float = 0.14) -> list:
    rows = []
    for _ in range(n):
        d = rand_date(start, end)
        is_income = random.random() < income_ratio
        pool = income_pool if is_income else expense_pool
        desc, cat, lo, hi = random.choice(pool)
        amount = round(random.uniform(lo, hi), 2)
        tx_type = "credit" if is_income else "debit"
        rows.append((d, desc, amount, tx_type, cat))
    rows.sort(key=lambda r: r[0])
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# Data pools  (persona-specific + shared Indian / global items)
# ══════════════════════════════════════════════════════════════════════════════

STANDARD_EXPENSES = [
    ("Swiggy Order",               "Food & Dining",    100,   900),
    ("Zomato Food Delivery",       "Food & Dining",    120,   850),
    ("Uber Ride",                  "Transportation",    80,   600),
    ("Ola Cab",                    "Transportation",    70,   500),
    ("Rapido Bike Taxi",           "Transportation",    30,   200),
    ("BigBasket Groceries",        "Groceries",        300,  4000),
    ("DMart Purchase",             "Groceries",        200,  3500),
    ("Reliance Fresh",             "Groceries",        150,  2000),
    ("More Supermarket",           "Groceries",        100,  1800),
    ("Amazon Purchase",            "Shopping",         200,  8000),
    ("Flipkart Order",             "Shopping",         300,  6000),
    ("Myntra Fashion",             "Shopping",         500,  4000),
    ("Ajio Clothing",              "Shopping",         400,  3500),
    ("Meesho Order",               "Shopping",         150,  2000),
    ("Netflix Subscription",       "Subscriptions",    149,   649),
    ("Amazon Prime",               "Subscriptions",    179,   999),
    ("Spotify Premium",            "Subscriptions",    119,   119),
    ("Hotstar Subscription",       "Subscriptions",    149,   899),
    ("YouTube Premium",            "Subscriptions",    139,   139),
    ("BookMyShow Tickets",         "Entertainment",    200,  1500),
    ("PVR Cinemas",                "Entertainment",    250,   800),
    ("Gaming Recharge",            "Entertainment",     50,  2000),
    ("Apollo Pharmacy",            "Healthcare",       100,  2000),
    ("1mg Medicine Order",         "Healthcare",        80,  1500),
    ("Gym Membership",             "Healthcare",       500,  2500),
    ("Doctor Consultation",        "Healthcare",       300,  2000),
    ("Electricity Bill",           "Utilities",        800,  5000),
    ("Water Bill",                 "Utilities",        200,   800),
    ("Airtel Mobile Bill",         "Utilities",        299,   999),
    ("Jio Recharge",               "Utilities",        199,   599),
    ("House Rent",                 "Housing",         8000, 30000),
    ("Maintenance Charges",        "Housing",          500,  3000),
    ("Petrol / Diesel",            "Transportation",   500,  4000),
    ("Metro Card Recharge",        "Transportation",   200,  1000),
    ("Coffee Shop",                "Food & Dining",     80,   500),
    ("Restaurant Dinner",          "Food & Dining",    400,  3000),
    ("School Fees",                "Education",       2000, 15000),
    ("Online Course",              "Education",        499,  5000),
    ("Book Purchase",              "Education",        200,  1500),
    ("Hair Salon",                 "Personal Care",    200,  1500),
    ("Spa Treatment",              "Personal Care",    500,  3000),
    ("Travel Booking",             "Travel",          2000, 20000),
    ("Hotel Stay",                 "Travel",          1500, 10000),
    ("Insurance Premium",          "Insurance",       1000, 10000),
    ("ATM Withdrawal",             "Miscellaneous",    500,  5000),
    ("Parking Charges",            "Transportation",    50,   300),
    ("Newspaper Subscription",     "Subscriptions",     99,   299),
]

STANDARD_INCOME = [
    ("Salary Credit",              "Income",          40000, 120000),
    ("Freelance Payment",          "Income",           5000,  30000),
    ("Interest Credit",            "Income",            500,   3000),
    ("Dividend Credit",            "Income",           1000,  15000),
    ("Bonus Credit",               "Income",           5000,  50000),
    ("Rental Income",              "Income",           5000,  25000),
    ("Refund Credit",              "Income",            200,   5000),
    ("Cashback Credit",            "Income",             50,   1000),
    ("Transfer Received",          "Income",           1000,  50000),
    ("UPI Received",               "Income",            500,  20000),
]

# Startup employee — higher salary, lots of subscriptions + dining
STARTUP_EXPENSES = [
    ("Blinkit Grocery Delivery",   "Groceries",        300,  3000),
    ("Dunzo Quick Commerce",       "Groceries",        200,  2500),
    ("WeWork Cafe",                "Food & Dining",    150,   600),
    ("Starbucks Coffee",           "Food & Dining",    300,   700),
    ("Slack Pro",                  "Subscriptions",    875,   875),
    ("GitHub Copilot",             "Subscriptions",    837,   837),
    ("Figma Subscription",         "Subscriptions",   1250,  1250),
    ("AWS Bill",                   "Utilities",        500, 15000),
    ("DigitalOcean",               "Utilities",        200,  5000),
    ("MacBook Accessories",        "Shopping",        1000, 15000),
    ("Tech Gadget Purchase",       "Shopping",        2000, 30000),
    ("Swiggy Instamart",           "Groceries",        200,  1500),
    ("Cult.fit Membership",        "Healthcare",       750,  2999),
    ("Standing Desk",              "Shopping",        5000, 25000),
] + STANDARD_EXPENSES[:20]

STARTUP_INCOME = [
    ("Salary Credit ESOP",         "Income",          80000, 200000),
    ("Stock Vesting Credit",       "Income",          10000,  50000),
    ("Freelance Consulting",       "Income",          10000,  80000),
] + STANDARD_INCOME[2:]

# Student / young professional — low income, lots of food delivery + entertainment
STUDENT_EXPENSES = [
    ("Zomato Late Night",          "Food & Dining",     80,   400),
    ("Swiggy Campus Delivery",     "Food & Dining",     60,   350),
    ("College Canteen",            "Food & Dining",     30,   150),
    ("Stationery Purchase",        "Education",         50,   500),
    ("Exam Fee Payment",           "Education",        500,  3000),
    ("Hostel Fees",                "Housing",          5000, 15000),
    ("Steam Games",                "Entertainment",    200,  3000),
    ("PlayStation Store",          "Entertainment",    300,  4000),
    ("PUBG UC Purchase",           "Entertainment",     60,   800),
    ("Local Auto Rickshaw",        "Transportation",    40,   200),
    ("Bus Pass Recharge",          "Transportation",   100,   500),
    ("Udemy Course",               "Education",        399,   999),
    ("Coursera Subscription",      "Subscriptions",    399,   399),
    ("Movie Night",                "Entertainment",    200,   600),
    ("Dominos Pizza",              "Food & Dining",    200,   700),
] + STANDARD_EXPENSES[:15]

STUDENT_INCOME = [
    ("Pocket Money Transfer",      "Income",           5000, 15000),
    ("Part Time Job Payment",      "Income",           3000, 10000),
    ("Scholarship Credit",         "Income",           5000, 20000),
    ("Internship Stipend",         "Income",           5000, 25000),
    ("Refund Credit",              "Income",            200,  2000),
    ("Cashback Credit",            "Income",             50,   500),
]

# Retired couple — healthcare heavy, travel, low dining out
RETIRED_EXPENSES = [
    ("Hospital Bill",              "Healthcare",       2000, 50000),
    ("Diagnostic Tests",           "Healthcare",        500, 10000),
    ("Chemist Medical Store",      "Healthcare",        200,  5000),
    ("Home Nurse Service",         "Healthcare",       5000, 20000),
    ("Pilgrimage Travel",          "Travel",           3000, 30000),
    ("Train Ticket",               "Travel",            500,  8000),
    ("Bus Ticket",                 "Travel",            200,  2000),
    ("Vegetable Market",           "Groceries",        300,  2000),
    ("Kiryana Store",              "Groceries",        200,  1500),
    ("Milk Subscription",          "Groceries",         300,   900),
    ("Temple Donation",            "Miscellaneous",    100,  5000),
    ("Electricity Bill",           "Utilities",        500,  3000),
    ("LPG Cylinder",               "Utilities",        900,   950),
    ("Cable TV",                   "Subscriptions",    200,   500),
    ("Newspaper Home Delivery",    "Subscriptions",     150,   300),
    ("Post Office RD",             "Insurance",       2000, 10000),
    ("LIC Premium",                "Insurance",       2000, 20000),
    ("Grandchildren's Gift",       "Shopping",         500,  5000),
    ("Readymade Garments",         "Shopping",         300,  3000),
    ("Auto Rickshaw",              "Transportation",    60,   300),
]

RETIRED_INCOME = [
    ("Pension Credit",             "Income",          20000, 60000),
    ("Fixed Deposit Interest",     "Income",           5000, 30000),
    ("Post Office Interest",       "Income",           2000, 10000),
    ("PPF Withdrawal",             "Income",          10000, 50000),
    ("Rental Income",              "Income",           5000, 25000),
    ("Dividend Credit",            "Income",           1000, 15000),
    ("Children Transfer",          "Income",           5000, 30000),
]

# Freelancer — irregular income, many UPI debits, project-based spending
FREELANCER_EXPENSES = [
    ("Adobe Creative Cloud",       "Subscriptions",   1675,  1675),
    ("Canva Pro",                  "Subscriptions",    499,   499),
    ("Namecheap Domain",           "Utilities",        800,  2000),
    ("Hostinger Hosting",          "Utilities",       1000,  5000),
    ("LinkedIn Premium",           "Subscriptions",   2499,  2499),
    ("Zoom Pro",                   "Subscriptions",   1300,  1300),
    ("Notion Subscription",        "Subscriptions",    500,   500),
    ("Client Meeting Cab",         "Transportation",   200,  1000),
    ("Co-working Space",           "Housing",         3000, 12000),
    ("Equipment Purchase",         "Shopping",        3000, 50000),
    ("Invoice Software",           "Subscriptions",    500,  2000),
    ("Tally Software",             "Subscriptions",   9000,  9000),
    ("Chartered Accountant Fee",   "Miscellaneous",   3000, 15000),
] + STANDARD_EXPENSES[:25]

FREELANCER_INCOME = [
    ("Client Payment UPI",         "Income",          15000, 150000),
    ("Project Milestone",          "Income",          20000, 100000),
    ("Retainer Fee Credit",        "Income",          10000,  50000),
    ("Royalty Credit",             "Income",           1000,  20000),
    ("Course Sale Revenue",        "Income",           2000,  30000),
    ("Refund Credit",              "Income",            500,   5000),
    ("Cashback Credit",            "Income",             50,  1000),
]


# ══════════════════════════════════════════════════════════════════════════════
# FILE 6 — Startup employee  (YYYY-MM-DD, all 5 cols, 3-year span)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2022, 4, 1), date(2025, 3, 31)
rows = gen_rows(2200, START, END, STARTUP_EXPENSES, STARTUP_INCOME, 0.12)
path = os.path.join(OUT_DIR, "sample_06_startup_employee.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type", "category"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%Y-%m-%d"), desc, amt, tx, cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 7 — Student / young professional  (only date + signed amount — minimal)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2023, 6, 1), date(2025, 12, 31)
rows = gen_rows(2000, START, END, STUDENT_EXPENSES, STUDENT_INCOME, 0.20)
path = os.path.join(OUT_DIR, "sample_07_student_minimal.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount"])
    for d, desc, amt, tx, cat in rows:
        signed = amt if tx == "credit" else -amt
        w.writerow([d.strftime("%Y-%m-%d"), desc, signed])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 8 — Retired couple  (DD-MM-YYYY date format, Dr/Cr type column)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2021, 1, 1), date(2025, 12, 31)
rows = gen_rows(2500, START, END, RETIRED_EXPENSES, RETIRED_INCOME, 0.18)
path = os.path.join(OUT_DIR, "sample_08_retired_couple.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Value Date", "Narration", "Amount", "Dr/Cr", "Category"])
    for d, desc, amt, tx, cat in rows:
        dr_cr = "Cr" if tx == "credit" else "Dr"
        w.writerow([d.strftime("%d-%m-%Y"), desc, amt, dr_cr, cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 9 — Freelancer  (₹ currency prefix, irregular income)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2022, 1, 1), date(2025, 12, 31)
rows = gen_rows(2300, START, END, FREELANCER_EXPENSES, FREELANCER_INCOME, 0.15)
path = os.path.join(OUT_DIR, "sample_09_freelancer.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type", "category"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%Y-%m-%d"), desc, f"₹{amt:,.2f}", tx, cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 10 — Family household  (INR prefix, semicolon-amenable, 5-year span)
# ══════════════════════════════════════════════════════════════════════════════
FAMILY_EXTRA_EXPENSES = [
    ("School Bus Fees",            "Education",        1500,  4000),
    ("Tuition Teacher",            "Education",        2000,  8000),
    ("Kids Clothing",              "Shopping",         500,  3000),
    ("Toys & Games",               "Shopping",         200,  5000),
    ("Children's Birthday Party",  "Entertainment",    2000, 15000),
    ("Family Restaurant",          "Food & Dining",    800,  4000),
    ("Vegetable Vendor",           "Groceries",        200,  1000),
    ("Milk Monthly",               "Groceries",        600,  1200),
    ("Household Repairs",          "Housing",         1000, 20000),
    ("Maid/Cook Salary",           "Miscellaneous",   3000, 10000),
    ("Car EMI",                    "Transportation",  8000, 20000),
    ("Car Servicing",              "Transportation",  2000, 12000),
    ("Family Vacation",            "Travel",          5000, 60000),
    ("Home Appliance Purchase",    "Shopping",       3000,  40000),
    ("Property Tax",               "Housing",         500,  8000),
] + STANDARD_EXPENSES[:20]

FAMILY_INCOME = [
    ("Husband Salary",             "Income",          60000, 150000),
    ("Wife Salary",                "Income",          40000, 100000),
    ("Rental Income",              "Income",           5000,  20000),
    ("Interest Credit",            "Income",           1000,   5000),
    ("Bonus Credit",               "Income",          10000,  80000),
    ("Cashback Credit",            "Income",             50,   2000),
    ("Refund Credit",              "Income",            200,   5000),
]

START, END = date(2020, 1, 1), date(2025, 12, 31)
rows = gen_rows(2800, START, END, FAMILY_EXTRA_EXPENSES, FAMILY_INCOME, 0.12)
path = os.path.join(OUT_DIR, "sample_10_family_household.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type", "category"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%Y-%m-%d"), desc, f"INR {amt:.2f}", tx, cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 11 — HDFC bank export style (Txn Date, Remarks, Debit, Credit columns)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2023, 1, 1), date(2025, 12, 31)
rows = gen_rows(2100, START, END, STANDARD_EXPENSES, STANDARD_INCOME, 0.14)
path = os.path.join(OUT_DIR, "sample_11_hdfc_style.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Txn Date", "Remarks", "Debit", "Credit"])
    for d, desc, amt, tx, cat in rows:
        debit  = amt if tx == "debit"  else ""
        credit = amt if tx == "credit" else ""
        w.writerow([d.strftime("%d/%m/%y"), desc, debit, credit])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 12 — SBI passbook export (Posting Date, description, Withdrawal, Deposit)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2022, 4, 1), date(2025, 3, 31)
rows = gen_rows(2050, START, END, STANDARD_EXPENSES, STANDARD_INCOME, 0.14)
path = os.path.join(OUT_DIR, "sample_12_sbi_passbook.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Posting Date", "Transaction Details", "Withdrawal Amt(INR)", "Deposit Amt(INR)"])
    for d, desc, amt, tx, cat in rows:
        withdrawal = f"{amt:.2f}" if tx == "debit"  else ""
        deposit    = f"{amt:.2f}" if tx == "credit" else ""
        w.writerow([d.strftime("%d %b %Y"), desc, withdrawal, deposit])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 13 — High-income professional  (Rs 1,234.56 format, no type column)
# ══════════════════════════════════════════════════════════════════════════════
HIP_EXPENSES = [
    ("Business Class Flight",      "Travel",          25000, 150000),
    ("5-Star Hotel",               "Travel",          10000,  80000),
    ("Fine Dining Restaurant",     "Food & Dining",    3000,  20000),
    ("Premium Whisky Shop",        "Food & Dining",    2000,  15000),
    ("BMW Service Center",         "Transportation",   5000,  50000),
    ("Parking Premium Mall",       "Transportation",    200,   800),
    ("Designer Brand Store",       "Shopping",        5000, 100000),
    ("Luxury Watch Service",       "Shopping",       10000,  80000),
    ("Golf Club Membership",       "Healthcare",      5000,  30000),
    ("Premium Gym",                "Healthcare",      2500,   5000),
    ("Interior Design Service",    "Housing",        25000, 200000),
    ("Security System",            "Housing",        5000,  30000),
    ("Chartered Accountant",       "Miscellaneous",  10000,  50000),
    ("Investment Advisory Fee",    "Miscellaneous",   5000,  20000),
] + STANDARD_EXPENSES[:20]

HIP_INCOME = [
    ("Salary CTC Credit",          "Income",         200000, 600000),
    ("Annual Bonus",               "Income",         100000, 500000),
    ("Stock Options",              "Income",          50000, 300000),
    ("Rental Income",              "Income",          20000,  80000),
    ("Dividend Credit",            "Income",          10000,  80000),
    ("Business Profit Transfer",   "Income",          50000, 300000),
    ("Interest Credit",            "Income",           5000,  30000),
]

START, END = date(2022, 1, 1), date(2025, 12, 31)
rows = gen_rows(2000, START, END, HIP_EXPENSES, HIP_INCOME, 0.12)
path = os.path.join(OUT_DIR, "sample_13_high_income_professional.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    # Signed amount only (positive=credit, negative=debit), no type col
    w.writerow(["date", "description", "amount", "category"])
    for d, desc, amt, tx, cat in rows:
        signed = amt if tx == "credit" else -amt
        w.writerow([d.strftime("%Y-%m-%d"), desc, f"Rs {abs(signed):,.2f}", cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 14 — Mixed locale (MM-DD-YYYY dates, Expense/Income as type)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2023, 1, 1), date(2025, 12, 31)
rows = gen_rows(2200, START, END, STANDARD_EXPENSES, STANDARD_INCOME, 0.14)
path = os.path.join(OUT_DIR, "sample_14_mixed_locale.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Transaction Date", "Description", "Net Amount", "Type", "Spending Category"])
    for d, desc, amt, tx, cat in rows:
        type_str = "Income" if tx == "credit" else "Expense"
        w.writerow([d.strftime("%m-%d-%Y"), desc, amt, type_str, cat])
print(f"Created {path}  ({len(rows)} rows)")


# ══════════════════════════════════════════════════════════════════════════════
# FILE 15 — 5-year long-term (YYYY/MM/DD format, no category)
# ══════════════════════════════════════════════════════════════════════════════
START, END = date(2020, 1, 1), date(2025, 12, 31)
rows = gen_rows(3000, START, END, STANDARD_EXPENSES, STANDARD_INCOME, 0.14)
path = os.path.join(OUT_DIR, "sample_15_five_year_history.csv")
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["date", "description", "amount", "transaction_type"])
    for d, desc, amt, tx, cat in rows:
        w.writerow([d.strftime("%Y/%m/%d"), desc, amt, tx])
print(f"Created {path}  ({len(rows)} rows)")


print("\nAll 10 additional sample files generated successfully.")
