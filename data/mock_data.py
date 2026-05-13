"""Load mock collections data from local JSON only."""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent / "mock_data.json"

with DATA_PATH.open("r", encoding="utf-8") as f:
    _raw = json.load(f)

CUSTOMERS = pd.DataFrame(_raw.get("customers", []))
INVOICES = pd.DataFrame(_raw.get("invoices", []))
PROMISES = pd.DataFrame(_raw.get("promises", []))
OVERDUE_TREND = pd.DataFrame(_raw.get("overdue_trend", []))
ANALYST_PERFORMANCE = pd.DataFrame(_raw.get("analyst_performance", []))

if not INVOICES.empty:
    rows = []
    for cust_id, grp in INVOICES.groupby("customer_id"):
        cust_name = grp.iloc[0]["customer_name"]
        for bucket, lo, hi in [("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), (">90", 91, 9999)]:
            g = grp[(grp["days_overdue"] >= lo) & (grp["days_overdue"] <= hi) & (grp["amount"] > 0)]
            if not g.empty:
                rows.append(
                    {
                        "customer_id": cust_id,
                        "customer_name": cust_name,
                        "aging_bucket": bucket,
                        "total_amount": float(g["amount"].sum()),
                        "invoice_count": int(len(g)),
                    }
                )
    AGING = pd.DataFrame(rows)
else:
    AGING = pd.DataFrame(columns=["customer_id", "customer_name", "aging_bucket", "total_amount", "invoice_count"])
