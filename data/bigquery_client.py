"""JSON-backed data service (BigQuery replacement)."""
from __future__ import annotations

from datetime import datetime, timedelta
import pandas as pd
from config import PRIORITY_SCORES, BROKEN_PROMISE_UPLIFT, HIGH_RISK_UPLIFT, VALUE_WEIGHT
from data.mock_data import INVOICES, AGING, CUSTOMERS, PROMISES, OVERDUE_TREND, ANALYST_PERFORMANCE


class DataService:
    def __init__(self):
        self.source = "json"
        self._mock = {
            "invoices": INVOICES.copy(),
            "aging": AGING.copy(),
            "customers": CUSTOMERS.copy(),
            "promises": PROMISES.copy(),
            "overdue_trend": OVERDUE_TREND.copy(),
            "analyst_performance": ANALYST_PERFORMANCE.copy(),
        }

    def get_invoices(self, analyst_filter=None, status=None, min_days_overdue=None, customer_id=None, min_amount=None):
        df = self._mock["invoices"].copy()
        if analyst_filter:
            df = df[df["assigned_analyst"] == analyst_filter]
        if status:
            df = df[df["status"].str.lower() == status.lower()]
        if min_days_overdue is not None:
            df = df[df["days_overdue"] >= min_days_overdue]
        if customer_id:
            df = df[df["customer_id"] == customer_id]
        if min_amount is not None:
            df = df[df["amount"] >= min_amount]
        return df.sort_values("days_overdue", ascending=False).reset_index(drop=True)

    def get_aging_summary(self, customer_id=None, analyst_filter=None):
        df = self._mock["aging"].copy()
        if customer_id:
            df = df[df["customer_id"] == customer_id]
        if analyst_filter:
            assigned = self.get_invoices(analyst_filter=analyst_filter)["customer_id"].unique()
            df = df[df["customer_id"].isin(assigned)]
        return df.reset_index(drop=True)

    def get_customers(self, risk_level=None, analyst_filter=None):
        df = self._mock["customers"].copy()
        if risk_level:
            df = df[df["risk_level"] == risk_level]
        if analyst_filter:
            assigned = self.get_invoices(analyst_filter=analyst_filter)["customer_id"].unique()
            df = df[df["customer_id"].isin(assigned)]
        inv = self.get_invoices(analyst_filter=analyst_filter)
        if not inv.empty:
            agg = inv.groupby("customer_id").agg(total_outstanding=("amount", "sum"), invoice_count=("invoice_id", "count"), max_days_overdue=("days_overdue", "max")).reset_index()
            df = df.merge(agg, on="customer_id", how="left")
        return df.fillna({"total_outstanding": 0, "invoice_count": 0, "max_days_overdue": 0}).reset_index(drop=True)

    def get_promises(self, broken_only=False, customer_id=None, analyst_filter=None):
        df = self._mock["promises"].copy()
        if broken_only:
            df = df[df["promise_kept"] == "No"]
        if customer_id:
            df = df[df["customer_id"] == customer_id]
        if analyst_filter:
            ids = set(self.get_invoices(analyst_filter=analyst_filter)["invoice_id"].tolist())
            df = df[df["invoice_id"].isin(ids)]
        return df.reset_index(drop=True)

    def get_overdue_summary(self, analyst_filter=None):
        overdue = self.get_invoices(analyst_filter=analyst_filter)
        overdue = overdue[overdue["amount"] > 0]
        return {
            "total_overdue_amount": float(overdue["amount"].sum()),
            "total_overdue_invoices": int(len(overdue)),
            "critical_count": int(len(overdue[overdue["days_overdue"] > 90])),
            "high_count": int(len(overdue[(overdue["days_overdue"] > 60) & (overdue["days_overdue"] <= 90)])),
            "medium_count": int(len(overdue[(overdue["days_overdue"] > 30) & (overdue["days_overdue"] <= 60)])),
            "low_count": int(len(overdue[overdue["days_overdue"] <= 30])),
            "critical_amount": float(overdue[overdue["days_overdue"] > 90]["amount"].sum()),
            "high_amount": float(overdue[(overdue["days_overdue"] > 60) & (overdue["days_overdue"] <= 90)]["amount"].sum()),
            "medium_amount": float(overdue[(overdue["days_overdue"] > 30) & (overdue["days_overdue"] <= 60)]["amount"].sum()),
            "low_amount": float(overdue[overdue["days_overdue"] <= 30]["amount"].sum()),
        }

    def get_priority_invoices(self, analyst_filter=None, top_n=20):
        invoices = self.get_invoices(analyst_filter=analyst_filter)
        customers = self.get_customers(analyst_filter=analyst_filter)
        invoices = invoices.merge(customers[["customer_id", "risk_level"]], on="customer_id", how="left")
        broken = self.get_promises(broken_only=True, analyst_filter=analyst_filter).groupby("customer_id").size().reset_index(name="broken_promises")
        invoices = invoices.merge(broken, on="customer_id", how="left")
        invoices["broken_promises"] = invoices["broken_promises"].fillna(0)
        max_amount = max(float(invoices["amount"].max()), 1.0)

        def score(r):
            s = PRIORITY_SCORES["critical"] if r["days_overdue"] > 90 else PRIORITY_SCORES["high"] if r["days_overdue"] > 60 else PRIORITY_SCORES["medium"] if r["days_overdue"] > 30 else PRIORITY_SCORES["low"]
            if r["broken_promises"] > 0:
                s += BROKEN_PROMISE_UPLIFT
            if r.get("risk_level") == "High":
                s += HIGH_RISK_UPLIFT
            s += (r["amount"] / max_amount) * VALUE_WEIGHT
            return round(s, 2)

        invoices["priority_score"] = invoices.apply(score, axis=1)
        invoices["priority"] = invoices["priority_score"].apply(lambda s: "Critical" if s >= 100 else "High" if s >= 75 else "Medium" if s >= 50 else "Low")
        return invoices.sort_values("priority_score", ascending=False).head(top_n).reset_index(drop=True)

    def get_overdue_trends(self):
        return self._mock["overdue_trend"].copy().reset_index(drop=True)

    def get_analyst_performance(self):
        return self._mock["analyst_performance"].copy().reset_index(drop=True)

    def get_cash_flow_forecast(self, weeks=6):
        invoices = self.get_invoices()
        today = datetime.now().date()
        probs = {"0-30": 0.85, "31-60": 0.65, "61-90": 0.45, ">90": 0.2}
        rows = []
        for w in range(1, weeks + 1):
            expected = 0.0
            for _, inv in invoices.iterrows():
                d = inv["days_overdue"]
                bucket = "0-30" if d <= 30 else "31-60" if d <= 60 else "61-90" if d <= 90 else ">90"
                expected += float(inv["amount"]) * probs[bucket] / weeks
            rows.append({"week": (today + timedelta(weeks=w)).isoformat(), "expected_inflow": round(expected, 2), "optimistic": round(expected * 1.25, 2), "conservative": round(expected * 0.72, 2)})
        return pd.DataFrame(rows)

    def get_customers_above_threshold(self, min_amount, analyst_filter=None):
        inv = self.get_invoices(analyst_filter=analyst_filter)
        grp = inv.groupby(["customer_id", "customer_name"]).agg(total_outstanding=("amount", "sum"), invoice_count=("invoice_id", "count"), max_days_overdue=("days_overdue", "max")).reset_index()
        return grp[grp["total_outstanding"] >= min_amount].sort_values("total_outstanding", ascending=False).reset_index(drop=True)
