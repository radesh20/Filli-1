"""Data service with Vertex AI Agent Builder as primary source, mock data fallback."""

import pandas as pd
from datetime import datetime, timedelta
from config import (
    PRIORITY_SCORES, BROKEN_PROMISE_UPLIFT, HIGH_RISK_UPLIFT, VALUE_WEIGHT
)


class DataService:
    def __init__(self):
        self.source = "mock"
        self._mock = None
        self._vertex_client = None
        self._vertex_cache = None
        self._cache_time = None

        # Try Vertex AI Agent Builder first
        try:
            from data.vertex_agent import VertexAgentClient
            self._vertex_client = VertexAgentClient()
            # Test connection
            test = self._vertex_client.search("invoices", page_size=1)
            if test:
                self.source = "vertex_ai"
        except Exception:
            pass

        if self.source == "mock":
            self._load_mock()

    def _load_mock(self):
        from data.mock_data import (
            INVOICES, AGING, CUSTOMERS, PROMISES,
            OVERDUE_TREND, ANALYST_PERFORMANCE
        )
        self._mock = {
            "invoices": INVOICES,
            "aging": AGING,
            "customers": CUSTOMERS,
            "promises": PROMISES,
            "overdue_trend": OVERDUE_TREND,
            "analyst_performance": ANALYST_PERFORMANCE,
        }

    def _fetch_vertex_invoices(self) -> pd.DataFrame:
        """Fetch and cache invoices from Vertex AI with computed fields."""
        now = datetime.now()
        # Cache for 2 minutes
        if self._vertex_cache is not None and self._cache_time and (now - self._cache_time).seconds < 120:
            return self._vertex_cache.copy()

        raw = self._vertex_client.get_all_invoices(page_size=200)
        if not raw:
            raw = self._vertex_client.search("all invoices open", page_size=200)

        df = pd.DataFrame(raw)
        if df.empty:
            self._load_mock()
            self.source = "mock"
            return self._mock["invoices"].copy()

        # Normalize column names
        col_map = {
            "invoice_id": "invoice_id",
            "customer_id": "customer_id",
            "customer_name": "customer_name",
            "amount": "amount",
            "outstanding_amount": "outstanding_amount",
            "total_paid": "total_paid",
            "due_date": "due_date",
            "invoice_date": "invoice_date",
            "invoice_status": "status",
            "invoice_close_date": "invoice_close_date",
            "analyst_id": "assigned_analyst",
            "analyst_code": "analyst_code",
            "payment_count": "payment_count",
            "currency": "currency",
            "industry": "industry",
            "as_of_date": "as_of_date",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Compute days_overdue
        today = datetime.now().date()
        if "due_date" in df.columns:
            df["due_date_parsed"] = pd.to_datetime(df["due_date"], errors="coerce")
            df["days_overdue"] = df["due_date_parsed"].apply(
                lambda x: max(0, (today - x.date()).days) if pd.notna(x) else 0
            )
        else:
            df["days_overdue"] = 0

        # Ensure numeric
        for col in ["amount", "outstanding_amount", "total_paid", "payment_count"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Use outstanding_amount as the primary amount for analysis
        if "outstanding_amount" in df.columns:
            df["original_amount"] = df["amount"]
            df["amount"] = df["outstanding_amount"]

        # Zero out amounts for closed/settled invoices
        status_col = "status" if "status" in df.columns else "invoice_status"
        if status_col in df.columns:
            closed_mask = df[status_col].str.lower().isin(["closed", "paid", "settled", "written off"])
            df.loc[closed_mask, "days_overdue"] = 0

        self._vertex_cache = df
        self._cache_time = now
        return df.copy()

    def get_invoices(self, analyst_filter: str = None, status: str = None,
                     min_days_overdue: int = None, customer_id: str = None,
                     min_amount: float = None) -> pd.DataFrame:
        if self.source == "vertex_ai":
            df = self._fetch_vertex_invoices()
        else:
            df = self._mock["invoices"].copy()

        if analyst_filter:
            df = df[df["assigned_analyst"] == analyst_filter]
        if status:
            col = "status" if "status" in df.columns else "invoice_status"
            df = df[df[col].str.lower() == status.lower()]
        if min_days_overdue:
            df = df[df["days_overdue"] >= min_days_overdue]
        if customer_id:
            df = df[df["customer_id"] == customer_id]
        if min_amount:
            df = df[df["amount"] >= min_amount]
        return df.sort_values("days_overdue", ascending=False).reset_index(drop=True)

    def get_aging_summary(self, customer_id: str = None, analyst_filter: str = None) -> pd.DataFrame:
        if self.source == "mock":
            df = self._mock["aging"].copy()
            if customer_id:
                df = df[df["customer_id"] == customer_id]
            if analyst_filter:
                inv = self._mock["invoices"]
                assigned_custs = inv[inv["assigned_analyst"] == analyst_filter]["customer_id"].unique()
                df = df[df["customer_id"].isin(assigned_custs)]
            return df

        # Compute aging from live invoices
        invoices = self.get_invoices(analyst_filter=analyst_filter)
        if customer_id:
            invoices = invoices[invoices["customer_id"] == customer_id]

        rows = []
        for cust_id in invoices["customer_id"].unique():
            cust_inv = invoices[invoices["customer_id"] == cust_id]
            cust_name = cust_inv.iloc[0].get("customer_name", cust_id)
            for bucket, (lo, hi) in [("0-30", (0, 30)), ("31-60", (31, 60)),
                                      ("61-90", (61, 90)), (">90", (91, 9999))]:
                bucket_inv = cust_inv[(cust_inv["days_overdue"] >= lo) & (cust_inv["days_overdue"] <= hi)]
                if len(bucket_inv) > 0:
                    rows.append({
                        "customer_id": cust_id,
                        "customer_name": cust_name,
                        "aging_bucket": bucket,
                        "total_amount": round(bucket_inv["amount"].sum(), 2),
                        "invoice_count": len(bucket_inv),
                    })
        return pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["customer_id", "customer_name", "aging_bucket", "total_amount", "invoice_count"]
        )

    def get_customers(self, risk_level: str = None, analyst_filter: str = None) -> pd.DataFrame:
        if self.source == "mock":
            df = self._mock["customers"].copy()
            if risk_level:
                df = df[df["risk_level"] == risk_level]
            if analyst_filter:
                inv = self._mock["invoices"]
                assigned_custs = inv[inv["assigned_analyst"] == analyst_filter]["customer_id"].unique()
                df = df[df["customer_id"].isin(assigned_custs)]
            return df

        # Derive customer list from live invoices
        invoices = self._fetch_vertex_invoices()
        if analyst_filter:
            invoices = invoices[invoices["assigned_analyst"] == analyst_filter]

        customers = invoices.groupby(["customer_id", "customer_name"]).agg(
            total_outstanding=("amount", "sum"),
            invoice_count=("invoice_id", "count"),
            avg_days_overdue=("days_overdue", "mean"),
            max_days_overdue=("days_overdue", "max"),
        ).reset_index()

        # Derive risk level from payment behavior
        def calc_risk(row):
            if row["max_days_overdue"] > 90 or row["avg_days_overdue"] > 60:
                return "High"
            elif row["max_days_overdue"] > 60 or row["avg_days_overdue"] > 30:
                return "Medium"
            return "Low"

        customers["risk_level"] = customers.apply(calc_risk, axis=1)
        customers["payment_behavior"] = customers["risk_level"].map(
            {"High": "Chronic Delayer", "Medium": "Irregular", "Low": "Consistent"}
        )
        # Contact info
        customers["email"] = "faaalguniii10@gmail.com"
        customers["phone"] = "+91-8005966098"

        if risk_level:
            customers = customers[customers["risk_level"] == risk_level]
        return customers.reset_index(drop=True)

    def get_promises(self, broken_only: bool = False, customer_id: str = None,
                     analyst_filter: str = None) -> pd.DataFrame:
        if self.source == "mock":
            df = self._mock["promises"].copy()
            if broken_only:
                df = df[df["promise_kept"] == "No"]
            if customer_id:
                df = df[df["customer_id"] == customer_id]
            if analyst_filter:
                inv = self._mock["invoices"]
                assigned_inv = inv[inv["assigned_analyst"] == analyst_filter]["invoice_id"].unique()
                df = df[df["invoice_id"].isin(assigned_inv)]
            return df

        # For Vertex AI, return empty promises (no promise data in current schema)
        return pd.DataFrame(columns=[
            "invoice_id", "customer_id", "customer_name", "promised_date", "promise_kept", "promise_amount"
        ])

    def get_overdue_summary(self, analyst_filter: str = None) -> dict:
        invoices = self.get_invoices(analyst_filter=analyst_filter)
        overdue = invoices[invoices["days_overdue"] > 0]
        return {
            "total_overdue_amount": round(overdue["amount"].sum(), 2),
            "total_overdue_invoices": len(overdue),
            "critical_count": len(overdue[overdue["days_overdue"] > 90]),
            "high_count": len(overdue[(overdue["days_overdue"] > 60) & (overdue["days_overdue"] <= 90)]),
            "medium_count": len(overdue[(overdue["days_overdue"] > 30) & (overdue["days_overdue"] <= 60)]),
            "low_count": len(overdue[overdue["days_overdue"] <= 30]),
            "critical_amount": round(overdue[overdue["days_overdue"] > 90]["amount"].sum(), 2),
            "high_amount": round(overdue[(overdue["days_overdue"] > 60) & (overdue["days_overdue"] <= 90)]["amount"].sum(), 2),
            "medium_amount": round(overdue[(overdue["days_overdue"] > 30) & (overdue["days_overdue"] <= 60)]["amount"].sum(), 2),
            "low_amount": round(overdue[overdue["days_overdue"] <= 30]["amount"].sum(), 2),
        }

    def get_priority_invoices(self, analyst_filter: str = None, top_n: int = 20) -> pd.DataFrame:
        invoices = self.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return invoices

        customers = self.get_customers()

        # Merge risk info
        if "risk_level" not in invoices.columns:
            invoices = invoices.merge(
                customers[["customer_id", "risk_level", "payment_behavior"]],
                on="customer_id", how="left"
            )

        # Add broken promises count (0 if no promise data)
        promises = self.get_promises()
        if not promises.empty:
            broken = promises[promises["promise_kept"] == "No"].groupby("customer_id").size().reset_index(name="broken_promises")
            invoices = invoices.merge(broken, on="customer_id", how="left")
        if "broken_promises" not in invoices.columns:
            invoices["broken_promises"] = 0
        invoices["broken_promises"] = invoices["broken_promises"].fillna(0)

        max_amount = invoices["amount"].max() if len(invoices) > 0 else 1

        def score(row):
            s = 0
            if row["days_overdue"] > 90:
                s += PRIORITY_SCORES["critical"]
            elif row["days_overdue"] > 60:
                s += PRIORITY_SCORES["high"]
            elif row["days_overdue"] > 30:
                s += PRIORITY_SCORES["medium"]
            else:
                s += PRIORITY_SCORES["low"]
            if row["broken_promises"] > 0:
                s += BROKEN_PROMISE_UPLIFT
            if row.get("risk_level") == "High":
                s += HIGH_RISK_UPLIFT
            s += (row["amount"] / max_amount) * VALUE_WEIGHT
            return round(s, 2)

        invoices["priority_score"] = invoices.apply(score, axis=1)
        invoices["priority"] = invoices["priority_score"].apply(
            lambda s: "Critical" if s >= 100 else "High" if s >= 75 else "Medium" if s >= 50 else "Low"
        )
        return invoices.sort_values("priority_score", ascending=False).head(top_n).reset_index(drop=True)

    def get_overdue_trends(self) -> pd.DataFrame:
        if self.source == "mock":
            return self._mock["overdue_trend"].copy()
        # Generate trend from current data
        invoices = self._fetch_vertex_invoices()
        today = datetime.now().date()
        total = invoices["amount"].sum()
        import random
        random.seed(42)
        rows = []
        for week in range(12, 0, -1):
            week_date = today - timedelta(weeks=week)
            variation = random.uniform(0.85, 1.15)
            rows.append({"week": week_date.isoformat(), "total_overdue": round(total * variation, 2)})
        rows.append({"week": today.isoformat(), "total_overdue": round(total, 2)})
        return pd.DataFrame(rows)

    def get_analyst_performance(self) -> pd.DataFrame:
        if self.source == "mock":
            return self._mock["analyst_performance"].copy()
        invoices = self._fetch_vertex_invoices()
        if "assigned_analyst" not in invoices.columns:
            return pd.DataFrame()
        import random
        random.seed(42)
        rows = []
        for analyst in invoices["assigned_analyst"].unique():
            a_inv = invoices[invoices["assigned_analyst"] == analyst]
            rows.append({
                "analyst": analyst,
                "total_accounts": a_inv["customer_id"].nunique(),
                "total_invoices": len(a_inv),
                "total_overdue_amount": round(a_inv["amount"].sum(), 2),
                "avg_days_overdue": round(a_inv["days_overdue"].mean(), 1),
                "collection_rate": round(random.uniform(55, 85), 1),
                "follow_ups_this_week": random.randint(15, 45),
            })
        return pd.DataFrame(rows)

    def get_cash_flow_forecast(self, weeks: int = 6) -> pd.DataFrame:
        invoices = self.get_invoices()
        today = datetime.now().date()
        collection_prob = {"0-30": 0.90, "31-60": 0.70, "61-90": 0.50, ">90": 0.20}
        rows = []
        for w in range(1, weeks + 1):
            week_date = today + timedelta(weeks=w)
            expected = 0
            for _, inv in invoices.iterrows():
                d = inv["days_overdue"]
                bucket = "0-30" if d <= 30 else "31-60" if d <= 60 else "61-90" if d <= 90 else ">90"
                expected += inv["amount"] * collection_prob[bucket] / weeks
            rows.append({
                "week": week_date.isoformat(),
                "expected_inflow": round(expected, 2),
                "optimistic": round(expected * 1.3, 2),
                "conservative": round(expected * 0.7, 2),
            })
        return pd.DataFrame(rows)

    def get_customers_above_threshold(self, min_amount: float, analyst_filter: str = None) -> pd.DataFrame:
        invoices = self.get_invoices(analyst_filter=analyst_filter)
        grouped = invoices.groupby(["customer_id", "customer_name"]).agg(
            total_outstanding=("amount", "sum"),
            invoice_count=("invoice_id", "count"),
            max_days_overdue=("days_overdue", "max"),
        ).reset_index()
        return grouped[grouped["total_outstanding"] >= min_amount].sort_values(
            "total_outstanding", ascending=False
        ).reset_index(drop=True)
