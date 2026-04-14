"""Realistic mock data for the Collections Assistant PoC.

Covers 25 diverse Indian companies across industries with realistic
invoice amounts, aging patterns, and analyst assignments matching
config (A101=Falguni Sharma, A102=Arjun Singh).
"""

import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(2026)

# --- Customer Master Data ---
CUSTOMERS = pd.DataFrame([
    # IT & Software
    {"customer_id": "CUST-001", "customer_name": "Zenith Infotech Pvt Ltd", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "IT Services"},
    {"customer_id": "CUST-002", "customer_name": "CloudNine Solutions", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "IT Services"},
    {"customer_id": "CUST-003", "customer_name": "Nexgen Data Systems", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "IT Services"},

    # Manufacturing & Industrial
    {"customer_id": "CUST-004", "customer_name": "Bharat Heavy Electricals", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Manufacturing"},
    {"customer_id": "CUST-005", "customer_name": "Precision Auto Components", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Manufacturing"},
    {"customer_id": "CUST-006", "customer_name": "Steelcraft Industries", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Manufacturing"},

    # Pharma & Healthcare
    {"customer_id": "CUST-007", "customer_name": "MedLife Pharmaceuticals", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Pharma"},
    {"customer_id": "CUST-008", "customer_name": "Sanjivani Healthcare", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Healthcare"},
    {"customer_id": "CUST-009", "customer_name": "AyurVeda Naturals", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Pharma"},

    # Construction & Real Estate
    {"customer_id": "CUST-010", "customer_name": "Skyline Constructions Ltd", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Construction"},
    {"customer_id": "CUST-011", "customer_name": "Metro Infrastructure Corp", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Construction"},

    # Retail & FMCG
    {"customer_id": "CUST-012", "customer_name": "FreshBasket Retail Pvt Ltd", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Retail"},
    {"customer_id": "CUST-013", "customer_name": "Spice Route Trading Co", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "FMCG"},
    {"customer_id": "CUST-014", "customer_name": "Urban Threads Fashion", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Retail"},

    # Logistics & Transport
    {"customer_id": "CUST-015", "customer_name": "SwiftMove Logistics", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Logistics"},
    {"customer_id": "CUST-016", "customer_name": "TransIndia Freight Services", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Logistics"},

    # Energy & Utilities
    {"customer_id": "CUST-017", "customer_name": "GreenPower Energy Solutions", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Energy"},
    {"customer_id": "CUST-018", "customer_name": "Surya Solar Systems", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Energy"},

    # Financial Services
    {"customer_id": "CUST-019", "customer_name": "Pinnacle Capital Advisors", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Financial Services"},
    {"customer_id": "CUST-020", "customer_name": "Trustwell Insurance Brokers", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Financial Services"},

    # Hospitality & Food
    {"customer_id": "CUST-021", "customer_name": "Royal Orchid Hotels", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Hospitality"},
    {"customer_id": "CUST-022", "customer_name": "Tandoor Express Chain", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Food & Beverage"},

    # Education & EdTech
    {"customer_id": "CUST-023", "customer_name": "LearnSphere EdTech", "risk_level": "Low", "payment_behavior": "Consistent", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Education"},
    {"customer_id": "CUST-024", "customer_name": "Vidya Global Academy", "risk_level": "Medium", "payment_behavior": "Irregular", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Education"},

    # Textiles
    {"customer_id": "CUST-025", "customer_name": "Rajasthan Textiles Mill", "risk_level": "High", "payment_behavior": "Chronic Delayer", "email": "faaalguniii10@gmail.com", "phone": "+91-8005966098", "industry": "Textiles"},
])


def _generate_invoices():
    """Generate realistic invoice data with proper analyst IDs."""
    today = datetime.now().date()
    statuses = ["Open", "Partially Paid", "Promised", "Escalated", "Disputed"]
    analysts = ["A101", "A102"]  # Match config: A101=Falguni, A102=Arjun
    rows = []

    # Realistic amount ranges per industry
    industry_amounts = {
        "IT Services": (15000, 450000),
        "Manufacturing": (50000, 800000),
        "Pharma": (20000, 350000),
        "Healthcare": (10000, 200000),
        "Construction": (100000, 1200000),
        "Retail": (8000, 150000),
        "FMCG": (12000, 250000),
        "Logistics": (15000, 300000),
        "Energy": (75000, 600000),
        "Financial Services": (25000, 500000),
        "Hospitality": (10000, 180000),
        "Food & Beverage": (5000, 120000),
        "Education": (8000, 200000),
        "Textiles": (20000, 400000),
    }

    invoice_id = 1
    for _, cust in CUSTOMERS.iterrows():
        # High-risk customers get more invoices
        if cust["risk_level"] == "High":
            num_invoices = random.randint(3, 7)
        elif cust["risk_level"] == "Medium":
            num_invoices = random.randint(2, 5)
        else:
            num_invoices = random.randint(1, 4)

        industry = cust.get("industry", "General")
        amt_lo, amt_hi = industry_amounts.get(industry, (10000, 300000))

        # Assign customers to analysts in a balanced way
        assigned_analyst = analysts[invoice_id % 2]

        for j in range(num_invoices):
            # Realistic aging distribution: more recent invoices, fewer very old
            if cust["risk_level"] == "High":
                days_overdue = random.choices(
                    [random.randint(5, 30), random.randint(31, 60),
                     random.randint(61, 90), random.randint(91, 180)],
                    weights=[15, 20, 25, 40]
                )[0]
            elif cust["risk_level"] == "Medium":
                days_overdue = random.choices(
                    [random.randint(3, 30), random.randint(31, 60),
                     random.randint(61, 90), random.randint(91, 120)],
                    weights=[30, 35, 25, 10]
                )[0]
            else:
                days_overdue = random.choices(
                    [random.randint(1, 30), random.randint(31, 60),
                     random.randint(61, 90), random.randint(91, 100)],
                    weights=[50, 30, 15, 5]
                )[0]

            due_date = today - timedelta(days=days_overdue)
            invoice_date = due_date - timedelta(days=random.randint(15, 60))

            # Diverse realistic amounts — not always round numbers
            amount = round(random.uniform(amt_lo, amt_hi), 2)
            # Occasionally have cleaner amounts
            if random.random() < 0.3:
                amount = round(amount / 1000) * 1000

            # Partial payments for some
            total_paid = 0
            outstanding = amount
            if random.random() < 0.25:
                total_paid = round(amount * random.uniform(0.1, 0.6), 2)
                outstanding = round(amount - total_paid, 2)

            # Status based on aging, payment, and risk — includes Closed/Paid
            if total_paid >= amount * 0.99:
                # Fully paid
                status = "Closed"
                outstanding = 0
                total_paid = amount
            elif random.random() < 0.12:
                # ~12% chance of being closed/written-off regardless
                status = random.choice(["Closed", "Written Off"])
                outstanding = 0
                total_paid = amount
            elif days_overdue > 90:
                status = random.choice(["Open", "Escalated", "Escalated", "Disputed"])
            elif days_overdue > 60:
                status = random.choice(["Open", "Escalated", "Promised"])
            elif total_paid > 0:
                status = "Partially Paid"
            elif days_overdue < 15:
                status = random.choice(["Open", "Promised"])
            else:
                status = random.choice(statuses[:3])

            rows.append({
                "invoice_id": f"INV-2026-{invoice_id:04d}",
                "customer_id": cust["customer_id"],
                "customer_name": cust["customer_name"],
                "amount": outstanding,
                "original_amount": amount,
                "total_paid": total_paid,
                "outstanding_amount": outstanding,
                "due_date": due_date.isoformat(),
                "invoice_date": invoice_date.isoformat(),
                "days_overdue": days_overdue,
                "status": status,
                "assigned_analyst": assigned_analyst,
                "currency": "INR",
                "industry": industry,
                "payment_count": random.randint(0, 3) if total_paid > 0 else 0,
            })
            invoice_id += 1

    return pd.DataFrame(rows)


INVOICES = _generate_invoices()


def _generate_aging():
    """Generate aging bucket summary from invoices."""
    rows = []
    for cust_id in CUSTOMERS["customer_id"]:
        cust_inv = INVOICES[INVOICES["customer_id"] == cust_id]
        for bucket, (lo, hi) in [("0-30", (0, 30)), ("31-60", (31, 60)),
                                  ("61-90", (61, 90)), (">90", (91, 9999))]:
            bucket_inv = cust_inv[(cust_inv["days_overdue"] >= lo) & (cust_inv["days_overdue"] <= hi)]
            if len(bucket_inv) > 0:
                rows.append({
                    "customer_id": cust_id,
                    "customer_name": cust_inv.iloc[0]["customer_name"],
                    "aging_bucket": bucket,
                    "total_amount": round(bucket_inv["amount"].sum(), 2),
                    "invoice_count": len(bucket_inv),
                })
    return pd.DataFrame(rows)


AGING = _generate_aging()


def _generate_promises():
    """Generate promise-to-pay records with realistic outcomes."""
    today = datetime.now().date()
    rows = []

    # Pick invoices that would realistically have promises
    eligible = INVOICES[INVOICES["days_overdue"] > 15]
    promised_invoices = eligible.sample(n=min(30, len(eligible)), random_state=2026)

    for _, inv in promised_invoices.iterrows():
        cust = CUSTOMERS[CUSTOMERS["customer_id"] == inv["customer_id"]].iloc[0]

        # Promise dates: some past (broken/kept), some future (pending)
        if random.random() < 0.6:
            # Past promise
            days_ago = random.randint(3, 30)
            promised_date = today - timedelta(days=days_ago)
            if cust["payment_behavior"] == "Chronic Delayer":
                promise_kept = random.choices(["No", "No", "Yes"], weights=[60, 30, 10])[0]
            elif cust["payment_behavior"] == "Irregular":
                promise_kept = random.choices(["No", "Yes", "Yes"], weights=[40, 30, 30])[0]
            else:
                promise_kept = random.choices(["Yes", "Yes", "No"], weights=[60, 30, 10])[0]
        else:
            # Future promise
            days_ahead = random.randint(1, 21)
            promised_date = today + timedelta(days=days_ahead)
            promise_kept = "Pending"

        # Promise amount — sometimes partial
        if random.random() < 0.3:
            promise_amount = round(inv["amount"] * random.uniform(0.3, 0.7), 2)
        else:
            promise_amount = inv["amount"]

        rows.append({
            "invoice_id": inv["invoice_id"],
            "customer_id": inv["customer_id"],
            "customer_name": inv["customer_name"],
            "promised_date": promised_date.isoformat(),
            "promise_kept": promise_kept,
            "promise_amount": promise_amount,
        })
    return pd.DataFrame(rows)


PROMISES = _generate_promises()


def _generate_weekly_overdue_trend():
    """Generate 12-week historical overdue trend with realistic movement."""
    today = datetime.now().date()
    total_overdue = INVOICES["amount"].sum()
    rows = []

    # Simulate a gradual increase with some collection dips
    base = total_overdue * 0.78
    for week in range(12, 0, -1):
        week_date = today - timedelta(weeks=week)
        # Gradual upward trend with weekly variation
        growth = 1 + (12 - week) * 0.018
        # Some weeks have collection spikes (lower overdue)
        if week in [9, 6, 3]:
            dip = random.uniform(0.88, 0.94)
        else:
            dip = random.uniform(0.97, 1.05)
        value = base * growth * dip
        rows.append({
            "week": week_date.isoformat(),
            "total_overdue": round(value, 2),
        })
    rows.append({"week": today.isoformat(), "total_overdue": round(total_overdue, 2)})
    return pd.DataFrame(rows)


OVERDUE_TREND = _generate_weekly_overdue_trend()


def _generate_analyst_performance():
    """Generate analyst performance KPIs matching config analyst IDs."""
    rows = []
    for analyst_id in ["A101", "A102"]:
        analyst_inv = INVOICES[INVOICES["assigned_analyst"] == analyst_id]
        if analyst_inv.empty:
            continue

        total_amount = analyst_inv["amount"].sum()
        # Simulate collected amount for rate calculation
        collected = total_amount * random.uniform(0.55, 0.80)

        rows.append({
            "analyst": analyst_id,
            "total_accounts": analyst_inv["customer_id"].nunique(),
            "total_invoices": len(analyst_inv),
            "total_overdue_amount": round(analyst_inv["amount"].sum(), 2),
            "avg_days_overdue": round(analyst_inv["days_overdue"].mean(), 1),
            "collection_rate": round(collected / total_amount * 100, 1),
            "follow_ups_this_week": random.randint(18, 42),
        })
    return pd.DataFrame(rows)


ANALYST_PERFORMANCE = _generate_analyst_performance()
