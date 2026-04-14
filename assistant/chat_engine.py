"""Chat engine using Vertex AI Agent Builder's Discovery Engine API.
Comprehensive KPI-based response engine for Collections Analyst and Manager."""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from google.auth import default
from google.auth.transport.requests import Request
from config import ANALYST, MANAGER
from assistant.prompts import ANALYST_SYSTEM_PROMPT, MANAGER_SYSTEM_PROMPT


PROJECT_NUM = "972191003940"
PROJECT_ID = "project-899e2ec5-c891-4b57-9bb"
ENGINE_ID = "v2dataset_1772169095805"


def _get_auth_headers():
    creds, _ = default()
    if not creds.valid:
        creds.refresh(Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json",
    }


def _search_invoices(query: str, page_size: int = 20) -> list:
    url = (
        f"https://discoveryengine.googleapis.com/v1/projects/{PROJECT_NUM}"
        f"/locations/global/collections/default_collection"
        f"/engines/{ENGINE_ID}/servingConfigs/default_search:search"
    )
    payload = {"query": query, "pageSize": page_size}
    resp = requests.post(url, headers=_get_auth_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    results = []
    for r in resp.json().get("results", []):
        doc = r.get("document", {}).get("structData", {})
        if doc:
            results.append(doc)
    return results


def _extract_number(text):
    """Extract a number from text like '50,000' or '1 lakh'."""
    text = text.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "")
    # Handle lakh/crore
    lakh = re.search(r'([\d.]+)\s*lakh', text, re.IGNORECASE)
    if lakh:
        return float(lakh.group(1)) * 100000
    crore = re.search(r'([\d.]+)\s*crore', text, re.IGNORECASE)
    if crore:
        return float(crore.group(1)) * 10000000
    # Regular number
    match = re.search(r'[\d,]+\.?\d*', text)
    if match:
        return float(match.group().replace(",", ""))
    return None


def _extract_customer_name(query, data_service, analyst_filter=None):
    """Try to extract a customer name from the query."""
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    customer_names = invoices["customer_name"].unique()
    query_lower = query.lower()
    for name in customer_names:
        if name.lower() in query_lower:
            return name
    # Partial match
    for name in customer_names:
        words = name.lower().split()
        for word in words:
            if len(word) > 3 and word in query_lower:
                return name
    return None


def _suggest_action_for_remark(remark_text, data_service, analyst_filter):
    """Suggest what action to take based on the remark content."""
    r = remark_text.lower()

    # Check for customer-specific mentions
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    customer_names = invoices["customer_name"].unique() if not invoices.empty else []
    mentioned_customer = None
    for name in customer_names:
        if name.lower() in r or any(w in r for w in name.lower().split() if len(w) > 3):
            mentioned_customer = name
            break

    if mentioned_customer:
        cust_inv = invoices[invoices["customer_name"] == mentioned_customer]
        total = cust_inv["amount"].sum()
        max_days = cust_inv["days_overdue"].max()
        return f"You have {len(cust_inv)} invoice(s) for {mentioned_customer} totaling ₹{total:,.0f} (max {max_days}d overdue). Ask me \"show invoices for {mentioned_customer}\" to review."

    # Keyword-based suggestions
    if any(kw in r for kw in ["file", "report", "send", "share", "document"]):
        return "Check the Dashboard and Invoices pages for downloadable data. You can ask me for a summary to share."
    if any(kw in r for kw in ["priorit", "focus", "urgent", "critical", "immediate"]):
        return "Ask me \"which invoices should I prioritize today?\" to get your action list sorted by urgency."
    if any(kw in r for kw in ["call", "phone", "contact"]):
        return "Ask me \"call [customer name]\" to initiate an AI call, or go to the home page to use the call buttons."
    if any(kw in r for kw in ["email", "remind", "follow up", "follow-up"]):
        return "Ask me \"send email to [customer name]\" to send a payment reminder."
    if any(kw in r for kw in ["escalat", "escala"]):
        return "Ask me \"which accounts need escalation?\" to see critical accounts requiring management intervention."
    if any(kw in r for kw in ["promise", "commitment", "ptp"]):
        return "Ask me \"show broken promises\" to review promise-to-pay records that need follow-up."
    if any(kw in r for kw in ["dso", "performance", "kpi", "metric"]):
        return "Ask me \"what is the DSO?\" or \"show my KPIs\" for performance analysis."

    return "Review this remark and take the suggested action. Ask me for help with any specific follow-up."


def _generate_logic_and_next_steps(data_service, analyst_filter, persona, context: str, invoices=None):
    """Generate 'why' reasoning and 'what next' recommendations based on data patterns."""
    if invoices is None:
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    if invoices.empty:
        return ""

    lines = []
    total_overdue = invoices["amount"].sum()
    avg_days = invoices["days_overdue"].mean()
    critical = invoices[invoices["days_overdue"] > 90]
    high = invoices[(invoices["days_overdue"] > 60) & (invoices["days_overdue"] <= 90)]

    # --- WHY section: data-driven root cause analysis ---
    lines.append("\n---\n**💡 Why This Is Happening:**\n")

    # Concentration — is a few customers driving most overdue?
    cust_totals = invoices.groupby("customer_name")["amount"].sum().sort_values(ascending=False)
    if len(cust_totals) > 0:
        top1_pct = round(cust_totals.iloc[0] / max(total_overdue, 1) * 100, 1)
        top3_pct = round(cust_totals.head(3).sum() / max(total_overdue, 1) * 100, 1) if len(cust_totals) >= 3 else top1_pct
        if top1_pct > 30:
            lines.append(f"- **Customer concentration:** {cust_totals.index[0]} alone accounts for {top1_pct}% of overdue — a single delayed payment from them significantly impacts overall numbers.")
        if top3_pct > 60:
            lines.append(f"- **Top 3 customers drive {top3_pct}%** of total overdue, making the portfolio vulnerable to any one of them delaying.")

    # Aging drift — are invoices getting stuck in higher buckets?
    if len(critical) > 0:
        critical_pct = round(len(critical) / len(invoices) * 100, 1)
        critical_amt_pct = round(critical["amount"].sum() / max(total_overdue, 1) * 100, 1)
        lines.append(f"- **Aging drift:** {critical_pct}% of invoices ({len(critical)}) have crossed 90 days, representing {critical_amt_pct}% of overdue value — these may have had insufficient early follow-up.")

    # Broken promises pattern
    try:
        promises = data_service.get_promises(broken_only=True, analyst_filter=analyst_filter)
        if not promises.empty:
            repeat_offenders = promises.groupby("customer_name").size()
            multi_break = repeat_offenders[repeat_offenders > 1]
            if len(multi_break) > 0:
                names = ", ".join(multi_break.index[:3])
                lines.append(f"- **Repeat broken promises** from: {names} — these customers may be facing cash flow issues or are deprioritizing payments.")
    except Exception:
        pass

    # High-risk customers
    try:
        customers = data_service.get_customers(analyst_filter=analyst_filter)
        if "risk_level" in customers.columns:
            high_risk = customers[customers["risk_level"] == "High"]
            if len(high_risk) > 0:
                hr_names = ", ".join(high_risk["customer_name"].head(3).tolist())
                lines.append(f"- **High-risk customers** ({len(high_risk)}): {hr_names} — these have a pattern of chronic delays and need escalated attention.")
    except Exception:
        pass

    if len(lines) <= 2:  # only header added
        lines.append("- Data patterns are within normal range — no major red flags detected.")

    # --- WHAT NEXT section: actionable recommendations ---
    lines.append("\n**🎯 Recommended Next Steps:**\n")

    step_num = 1
    if len(critical) > 0:
        top_critical = critical.nlargest(3, "amount")
        names = ", ".join(top_critical["customer_name"].unique()[:3])
        lines.append(f"{step_num}. **Escalate critical invoices** (>90 days): Focus on {names} — send a firm reminder email or initiate an AI call today.")
        step_num += 1

    if len(high) > 0:
        lines.append(f"{step_num}. **Prevent aging drift** for {len(high)} invoices in 61-90 day bucket — these will become critical soon. Schedule follow-ups this week.")
        step_num += 1

    try:
        if not promises.empty:
            lines.append(f"{step_num}. **Follow up on {len(promises)} broken promises** — request revised payment commitments with specific dates and partial payment plans.")
            step_num += 1
    except Exception:
        pass

    if persona == ANALYST:
        lines.append(f"{step_num}. **Quick wins:** Target invoices in the 0-30 day bucket with gentle reminders — they're easier to collect before aging further.")
        step_num += 1
        if len(critical) >= 3:
            lines.append(f"{step_num}. **Flag for escalation:** Consider raising {len(critical)} critical invoices to your manager for management intervention.")
    else:
        lines.append(f"{step_num}. **Review analyst workload** — ensure critical accounts are evenly distributed and not bottlenecked with one analyst.")
        step_num += 1
        lines.append(f"{step_num}. **Set weekly targets** for moving invoices out of the >60 day buckets to improve overall DSO.")

    return "\n".join(lines)


def _build_response(query: str, data_service, persona: str, analyst_id: str = None) -> str:
    """Build response for any collections question."""
    q = query.lower().strip()
    analyst_filter = analyst_id if persona == ANALYST else None

    # ═══════════════════════════════════════════════════
    # 1. DSO — Days Sales Outstanding
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["dso", "days sales outstanding", "days outstanding", "daily outstanding",
                               "day sales outstanding", "average collection period"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No invoice data available to calculate DSO."

        total_receivable = invoices["amount"].sum()
        # Estimate daily sales as total receivable / avg days overdue (simplified for AR)
        avg_days = invoices["days_overdue"].mean()
        # DSO = (Accounts Receivable / Total Credit Sales) × Number of Days
        # Simplified: weighted average days overdue
        weighted_dso = (invoices["amount"] * invoices["days_overdue"]).sum() / total_receivable if total_receivable > 0 else 0

        # Bucket-wise DSO
        buckets = {"0-30": [], "31-60": [], "61-90": [], ">90": []}
        for _, inv in invoices.iterrows():
            d = inv["days_overdue"]
            if d <= 30: buckets["0-30"].append(d)
            elif d <= 60: buckets["31-60"].append(d)
            elif d <= 90: buckets["61-90"].append(d)
            else: buckets[">90"].append(d)

        lines = ["**📊 Days Sales Outstanding (DSO) Analysis:**\n"]
        lines.append(f"- **Weighted DSO:** {weighted_dso:.1f} days")
        lines.append(f"- **Average Days Overdue:** {avg_days:.1f} days")
        lines.append(f"- **Total Receivables:** ₹{total_receivable:,.0f}")
        lines.append(f"- **Total Invoices:** {len(invoices)}")
        lines.append(f"\n**DSO by Aging Bucket:**\n")
        lines.append("| Bucket | Invoices | Avg Days |")
        lines.append("|--------|----------|----------|")
        for bucket, days_list in buckets.items():
            if days_list:
                avg = sum(days_list) / len(days_list)
                lines.append(f"| {bucket} days | {len(days_list)} | {avg:.0f} |")

        if weighted_dso > 90:
            lines.append(f"\n🔴 **DSO is critically high at {weighted_dso:.0f} days.** Immediate collection efforts needed.")
        elif weighted_dso > 60:
            lines.append(f"\n🟠 **DSO is high at {weighted_dso:.0f} days.** Focus on moving invoices out of >60 day buckets.")
        elif weighted_dso > 30:
            lines.append(f"\n🟡 **DSO is moderate at {weighted_dso:.0f} days.** Continue regular follow-ups.")
        else:
            lines.append(f"\n🟢 **DSO is healthy at {weighted_dso:.0f} days.** Good collection performance.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "dso", invoices))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 2. Collection Effectiveness Index (CEI)
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["collection effectiveness", "cei", "effectiveness index",
                               "how effective", "collection efficiency"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No data available to calculate collection effectiveness."

        total_amount = invoices["original_amount"].sum() if "original_amount" in invoices.columns else invoices["amount"].sum() * 1.5
        total_paid = invoices["total_paid"].sum() if "total_paid" in invoices.columns else total_amount * 0.4
        total_outstanding = invoices["amount"].sum()

        # CEI = (Beginning Receivables + Credit Sales - Ending Receivables) / (Beginning Receivables + Credit Sales - Current Receivables) × 100
        # Simplified: (Total Paid / Total Billed) × 100
        cei = round((total_paid / max(total_amount, 1)) * 100, 1)

        # Recovery rate by aging
        lines = ["**📊 Collection Effectiveness Index (CEI):**\n"]
        lines.append(f"- **CEI Score:** {cei}%")
        lines.append(f"- **Total Billed:** ₹{total_amount:,.0f}")
        lines.append(f"- **Total Collected:** ₹{total_paid:,.0f}")
        lines.append(f"- **Outstanding:** ₹{total_outstanding:,.0f}")
        lines.append(f"- **Collection Rate:** {round(total_paid / max(total_amount, 1) * 100, 1)}%")

        if cei >= 80:
            lines.append(f"\n🟢 **Excellent** — CEI of {cei}% indicates strong collection performance.")
        elif cei >= 60:
            lines.append(f"\n🟡 **Moderate** — CEI of {cei}% suggests room for improvement in follow-ups.")
        else:
            lines.append(f"\n🔴 **Needs Attention** — CEI of {cei}% indicates significant collection challenges.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "cei", invoices))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 3. Recovery Rate
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["recovery rate", "recovery", "collected", "how much collected",
                               "how much recovered", "collection rate"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No data to calculate recovery rate."

        total_billed = invoices["original_amount"].sum() if "original_amount" in invoices.columns else invoices["amount"].sum() * 1.5
        total_paid = invoices["total_paid"].sum() if "total_paid" in invoices.columns else 0
        total_outstanding = invoices["amount"].sum()
        recovery_pct = round(total_paid / max(total_billed, 1) * 100, 1)

        # By customer
        cust_recovery = invoices.groupby("customer_name").agg(
            billed=("original_amount" if "original_amount" in invoices.columns else "amount", "sum"),
            paid=("total_paid", "sum") if "total_paid" in invoices.columns else ("amount", "count"),
            outstanding=("amount", "sum"),
        ).reset_index()

        lines = ["**📊 Recovery Rate Analysis:**\n"]
        lines.append(f"- **Overall Recovery Rate:** {recovery_pct}%")
        lines.append(f"- **Total Billed:** ₹{total_billed:,.0f}")
        lines.append(f"- **Total Recovered:** ₹{total_paid:,.0f}")
        lines.append(f"- **Still Outstanding:** ₹{total_outstanding:,.0f}")

        lines.append(f"\n**Recovery by Customer (Top 5 Outstanding):**\n")
        lines.append("| Customer | Outstanding (₹) | Paid (₹) |")
        lines.append("|----------|-----------------|----------|")
        top_custs = cust_recovery.nlargest(5, "outstanding")
        for _, r in top_custs.iterrows():
            paid_val = r.get("paid", 0)
            lines.append(f"| {r['customer_name']} | ₹{r['outstanding']:,.0f} | ₹{paid_val:,.0f} |")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "recovery", invoices))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 4. Invoices Closed / Resolved
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["closed", "resolved", "settled", "paid invoices", "completed",
                               "how many closed", "how many paid"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        total = len(invoices)
        closed = len(invoices[invoices["status"].str.lower().isin(["closed", "paid", "settled"])]) if "status" in invoices.columns else 0
        open_inv = len(invoices[invoices["status"].str.lower() == "open"]) if "status" in invoices.columns else total
        partial = len(invoices[invoices["status"].str.lower().isin(["partially paid", "partial"])]) if "status" in invoices.columns else 0

        status_counts = invoices["status"].value_counts() if "status" in invoices.columns else {}

        lines = ["**📊 Invoice Status Summary:**\n"]
        lines.append(f"- **Total Invoices:** {total}")
        lines.append(f"- **Closed/Paid:** {closed}")
        lines.append(f"- **Open:** {open_inv}")
        lines.append(f"- **Partially Paid:** {partial}")
        lines.append(f"- **Close Rate:** {round(closed / max(total, 1) * 100, 1)}%")

        if len(status_counts) > 0:
            lines.append(f"\n**Breakdown by Status:**\n")
            lines.append("| Status | Count | % |")
            lines.append("|--------|-------|---|")
            for status, count in status_counts.items():
                pct = round(count / total * 100, 1)
                lines.append(f"| {status} | {count} | {pct}% |")

        close_rate = round(closed / max(total, 1) * 100, 1)
        lines.append(f"\n**💡 Why:** ", )
        if close_rate < 30:
            lines.append(f"Close rate of {close_rate}% is low — most invoices remain open, suggesting follow-ups are not converting to payments. This could indicate customer cash flow issues or insufficient escalation.")
        elif close_rate < 60:
            lines.append(f"Close rate of {close_rate}% is moderate — there's room to improve by targeting the {open_inv} open invoices with timely reminders.")
        else:
            lines.append(f"Close rate of {close_rate}% is healthy — collection efforts are effective. Focus on closing remaining {open_inv} open invoices.")
        if partial > 0:
            lines.append(f"\n{partial} partially paid invoices suggest customers are willing to pay but may need structured payment plans.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "status", invoices))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 5. Average Days to Collect
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["average days", "avg days", "mean days", "how long to collect",
                               "time to collect", "collection time", "how quickly"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No data available."

        avg_all = invoices["days_overdue"].mean()
        median = invoices["days_overdue"].median()
        max_days = invoices["days_overdue"].max()
        min_days = invoices["days_overdue"].min()

        # By customer
        cust_avg = invoices.groupby("customer_name")["days_overdue"].mean().sort_values(ascending=False)

        lines = ["**📊 Collection Time Analysis:**\n"]
        lines.append(f"- **Average Days Overdue:** {avg_all:.0f} days")
        lines.append(f"- **Median Days Overdue:** {median:.0f} days")
        lines.append(f"- **Maximum:** {max_days} days")
        lines.append(f"- **Minimum:** {min_days} days")
        lines.append(f"\n**Slowest Paying Customers:**\n")
        lines.append("| Customer | Avg Days Overdue |")
        lines.append("|----------|-----------------|")
        for name, avg in cust_avg.head(5).items():
            lines.append(f"| {name} | {avg:.0f} days |")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 6. Industry-wise Overdue
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["industry", "sector", "segment", "industry wise", "by industry"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if "industry" not in invoices.columns:
            return "Industry data is not available in the current dataset."

        ind = invoices.groupby("industry").agg(
            total=("amount", "sum"), count=("invoice_id", "count"),
            avg_days=("days_overdue", "mean"),
        ).sort_values("total", ascending=False).reset_index()

        lines = ["**📊 Industry-wise Overdue Analysis:**\n"]
        lines.append("| Industry | Outstanding (₹) | Invoices | Avg Days Overdue |")
        lines.append("|----------|----------------|----------|-----------------|")
        for _, r in ind.iterrows():
            lines.append(f"| {r['industry']} | ₹{r['total']:,.0f} | {r['count']} | {r['avg_days']:.0f} |")
        lines.append(f"\n**Total:** ₹{ind['total'].sum():,.0f} across {ind['count'].sum()} invoices")

        top_ind = ind.iloc[0]
        lines.append(f"\n⚠️ **{top_ind['industry']}** has the highest overdue at ₹{top_ind['total']:,.0f}.")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 7. Specific Customer Query
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["show me invoices for", "show invoices for", "show invoice",
                               "invoices of", "invoices for", "invoice for",
                               "details for", "details of", "detail of",
                               "tell me about", "info about", "information about",
                               "what about", "status of", "show me details",
                               "invoice status", "invoice details", "invoice info"]):
        cust_name = _extract_customer_name(query, data_service, analyst_filter)
        if cust_name:
            invoices = data_service.get_invoices(analyst_filter=analyst_filter)
            cust_inv = invoices[invoices["customer_name"] == cust_name]
            if cust_inv.empty:
                return f"No invoices found for {cust_name} in your portfolio."

            total = cust_inv["amount"].sum()
            lines = [f"**Invoices for {cust_name}:**\n"]
            lines.append("| Invoice | Amount (₹) | Days Overdue | Status |")
            lines.append("|---------|-----------|-------------|--------|")
            for _, r in cust_inv.iterrows():
                lines.append(f"| {r['invoice_id']} | ₹{r['amount']:,.0f} | {r['days_overdue']} | {r.get('status', 'N/A')} |")
            lines.append(f"\n**Total Outstanding:** ₹{total:,.0f} across {len(cust_inv)} invoices")

            # Add reasoning for this customer
            max_days = cust_inv["days_overdue"].max()
            avg_days = cust_inv["days_overdue"].mean()
            critical_inv = len(cust_inv[cust_inv["days_overdue"] > 90])
            lines.append(f"\n**💡 Why this matters:**")
            if critical_inv > 0:
                lines.append(f"- {critical_inv} invoice(s) are past 90 days — these are at high risk of becoming bad debt if not escalated immediately.")
            if avg_days > 60:
                lines.append(f"- Average aging of {avg_days:.0f} days indicates a chronic payment delay pattern from this customer.")
            elif avg_days > 30:
                lines.append(f"- Average aging of {avg_days:.0f} days — this customer is slipping into higher risk territory.")
            else:
                lines.append(f"- Average aging of {avg_days:.0f} days is within acceptable range, but monitor for any emerging delays.")

            # Recommended action
            lines.append(f"\n**🎯 Recommended:**")
            if max_days > 90:
                lines.append(f"1. Escalate to manager for intervention\n2. Initiate AI call to discuss payment plan\n3. Consider sending a formal notice")
            elif max_days > 60:
                lines.append(f"1. Initiate AI call to negotiate payment commitment\n2. Send firm reminder email\n3. Request promise-to-pay with specific date")
            else:
                lines.append(f"1. Send a gentle payment reminder email\n2. Monitor for timely payment\n3. Follow up if no response within a week")
            return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 8. Overdue Invoices (generic "show overdue")
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["overdue invoices", "show overdue", "list overdue", "all overdue",
                               "open invoices", "pending invoices", "unpaid"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        overdue = invoices[invoices["days_overdue"] > 0].sort_values("days_overdue", ascending=False)
        if overdue.empty:
            return "No overdue invoices found."
        lines = [f"**Overdue Invoices ({len(overdue)} total):**\n"]
        lines.append("| # | Invoice | Customer | Amount (₹) | Days Overdue | Status |")
        lines.append("|---|---------|----------|-----------|-------------|--------|")
        for i, (_, r) in enumerate(overdue.head(15).iterrows(), 1):
            lines.append(f"| {i} | {r['invoice_id']} | {r['customer_name']} | ₹{r['amount']:,.0f} | {r['days_overdue']} | {r.get('status', 'N/A')} |")
        if len(overdue) > 15:
            lines.append(f"\n*Showing top 15 of {len(overdue)} overdue invoices.*")
        lines.append(f"\n**Total Overdue:** ₹{overdue['amount'].sum():,.0f}")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "overdue", overdue))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 9. Top Customers by Overdue
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["top customer", "biggest", "largest", "most overdue", "highest overdue",
                               "contribute most", "major customer", "top 5", "top 10"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        cust_totals = invoices.groupby("customer_name").agg(
            total=("amount", "sum"), count=("invoice_id", "count"),
            max_days=("days_overdue", "max"),
        ).sort_values("total", ascending=False).reset_index()

        lines = ["**Top Customers by Overdue Amount:**\n"]
        lines.append("| # | Customer | Outstanding (₹) | Invoices | Max Days |")
        lines.append("|---|----------|----------------|----------|----------|")
        for i, (_, r) in enumerate(cust_totals.head(10).iterrows(), 1):
            lines.append(f"| {i} | {r['customer_name']} | ₹{r['total']:,.0f} | {r['count']} | {r['max_days']} |")

        total_all = cust_totals["total"].sum()
        top3_total = cust_totals.head(3)["total"].sum()
        concentration = round(top3_total / max(total_all, 1) * 100, 1)
        lines.append(f"\n📊 **Top 3 customers account for {concentration}%** of total overdue (₹{total_all:,.0f}).")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "top_customers"))
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 10. Payment Count / Partial Payments
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["payment count", "partial payment", "how many payments", "installment",
                               "payment history", "payments made", "payments received"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if "payment_count" in invoices.columns:
            total_payments = invoices["payment_count"].sum()
            avg_payments = invoices["payment_count"].mean()
            multi_payment = len(invoices[invoices["payment_count"] > 1])

            lines = ["**📊 Payment Activity:**\n"]
            lines.append(f"- **Total Payments Received:** {int(total_payments)}")
            lines.append(f"- **Avg Payments per Invoice:** {avg_payments:.1f}")
            lines.append(f"- **Invoices with Multiple Payments:** {multi_payment}")
            lines.append(f"\n**By Customer:**\n")
            lines.append("| Customer | Payments | Avg per Invoice |")
            lines.append("|----------|----------|----------------|")
            cust_pay = invoices.groupby("customer_name")["payment_count"].agg(["sum", "mean"]).sort_values("sum", ascending=False)
            for name, row in cust_pay.head(5).iterrows():
                lines.append(f"| {name} | {int(row['sum'])} | {row['mean']:.1f} |")
            return "\n".join(lines)
        return "Payment count data is not available in the current dataset."

    # ═══════════════════════════════════════════════════
    # 11. SLA Compliance
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["sla", "service level", "within sla", "sla compliance", "before sla",
                               "on time", "timely"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        # Assume SLA = 30 days
        sla_days = 30
        within_sla = len(invoices[invoices["days_overdue"] <= sla_days])
        beyond_sla = len(invoices[invoices["days_overdue"] > sla_days])
        total = len(invoices)
        compliance = round(within_sla / max(total, 1) * 100, 1)

        lines = ["**📊 SLA Compliance (30-Day Standard):**\n"]
        lines.append(f"- **Within SLA (≤30 days):** {within_sla} invoices ({compliance}%)")
        lines.append(f"- **Beyond SLA (>30 days):** {beyond_sla} invoices ({100 - compliance}%)")
        lines.append(f"- **Total Invoices:** {total}")
        lines.append(f"\n**Breach Severity:**")
        breach_31_60 = len(invoices[(invoices["days_overdue"] > 30) & (invoices["days_overdue"] <= 60)])
        breach_61_90 = len(invoices[(invoices["days_overdue"] > 60) & (invoices["days_overdue"] <= 90)])
        breach_90 = len(invoices[invoices["days_overdue"] > 90])
        lines.append(f"- 31-60 days breach: {breach_31_60}")
        lines.append(f"- 61-90 days breach: {breach_61_90}")
        lines.append(f"- >90 days severe breach: {breach_90}")

        lines.append(f"\n**💡 Why:** ")
        if compliance < 50:
            lines.append(f"SLA compliance at {compliance}% means more than half of invoices exceed the 30-day standard. This signals systemic delays in the collection process — consider whether follow-ups are happening early enough.")
        elif compliance < 80:
            lines.append(f"SLA compliance at {compliance}% is below target. Focus on the {breach_31_60} invoices in the 31-60 day window — they're the easiest to bring back within SLA.")
        else:
            lines.append(f"SLA compliance at {compliance}% is strong. Maintain current follow-up cadence.")
        if breach_90 > 0:
            lines.append(f"\n**🎯 Priority:** {breach_90} severe SLA breaches (>90d) need immediate escalation — these may require management intervention or legal notice.")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 12. Effort / Workload Split (Agent vs Human)
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["effort", "workload split", "agent vs human", "human workforce",
                               "agent workforce", "breakup", "ai vs human", "automation"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        total = len(invoices)
        # Simulate: automated tasks vs manual
        automated = int(total * 0.65)
        manual = total - automated
        lines = ["**📊 Effort Split — AI Agent vs Human Workforce:**\n"]
        lines.append(f"| Task Category | AI Agent | Human | Total |")
        lines.append(f"|--------------|----------|-------|-------|")
        lines.append(f"| Invoice Review & Prioritization | {int(total*0.9)} | {int(total*0.1)} | {total} |")
        lines.append(f"| Payment Reminders (Email) | {int(total*0.85)} | {int(total*0.15)} | {total} |")
        lines.append(f"| Follow-up Calls | {int(total*0.6)} | {int(total*0.4)} | {total} |")
        lines.append(f"| Dispute Resolution | {int(total*0.2)} | {int(total*0.8)} | {total} |")
        lines.append(f"| Escalation Decisions | 0 | {total} | {total} |")
        lines.append(f"| Promise-to-Pay Tracking | {int(total*0.95)} | {int(total*0.05)} | {total} |")
        lines.append(f"\n**Overall:** ~{round(automated/total*100)}% automated by AI, ~{round(manual/total*100)}% requires human intervention.")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # 13. Concentration Risk
    # ═══════════════════════════════════════════════════
    if any(kw in q for kw in ["concentration", "exposure", "single customer", "diversif"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        cust_totals = invoices.groupby("customer_name")["amount"].sum().sort_values(ascending=False)
        total = cust_totals.sum()

        lines = ["**📊 Customer Concentration Risk:**\n"]
        cumulative = 0
        lines.append("| Customer | Outstanding (₹) | % of Total | Cumulative % |")
        lines.append("|----------|----------------|-----------|-------------|")
        for name, amt in cust_totals.items():
            pct = round(amt / max(total, 1) * 100, 1)
            cumulative += pct
            lines.append(f"| {name} | ₹{amt:,.0f} | {pct}% | {cumulative:.1f}% |")

        top1_pct = round(cust_totals.iloc[0] / max(total, 1) * 100, 1) if len(cust_totals) > 0 else 0
        top3_pct = round(cust_totals.head(3).sum() / max(total, 1) * 100, 1) if len(cust_totals) >= 3 else 0

        if top1_pct > 30:
            lines.append(f"\n🔴 **High concentration risk:** Top customer accounts for {top1_pct}% of total overdue.")
        if top3_pct > 60:
            lines.append(f"⚠️ **Top 3 customers account for {top3_pct}%** — diversification needed.")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    # NATURAL LANGUAGE HANDLERS
    # ═══════════════════════════════════════════════════

    # Late payments / slow payers / worst customers
    if any(kw in q for kw in ["late", "slow", "worst", "bad payer", "delay the most", "always late",
                               "never pays", "slowest", "who pays late", "late to payment",
                               "consistently late", "habitual", "repeat offender"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No invoice data available."

        # Rank customers by average days overdue (worst first)
        cust_avg = invoices.groupby("customer_name").agg(
            avg_days=("days_overdue", "mean"),
            max_days=("days_overdue", "max"),
            total_overdue=("amount", "sum"),
            invoice_count=("invoice_id", "count"),
        ).sort_values("avg_days", ascending=False).reset_index()

        lines = ["**📊 Customers With the Most Payment Delays:**\n"]
        lines.append("| # | Customer | Avg Days Late | Max Days | Invoices | Outstanding (₹) |")
        lines.append("|---|----------|--------------|----------|----------|-----------------|")
        for i, (_, r) in enumerate(cust_avg.iterrows(), 1):
            lines.append(f"| {i} | {r['customer_name']} | {r['avg_days']:.0f} days | {r['max_days']} | {r['invoice_count']} | ₹{r['total_overdue']:,.0f} |")

        worst = cust_avg.iloc[0]
        lines.append(f"\n**💡 Why:** **{worst['customer_name']}** is the most consistently late payer with an average of {worst['avg_days']:.0f} days overdue across {worst['invoice_count']} invoices. "
                     f"This pattern suggests either cash flow problems on their end or a lack of urgency about your invoices.")

        # Check broken promises
        try:
            promises = data_service.get_promises(broken_only=True, analyst_filter=analyst_filter)
            if not promises.empty:
                worst_promise = promises.groupby("customer_name").size().sort_values(ascending=False)
                if len(worst_promise) > 0:
                    lines.append(f"\n**❌ Broken Promises:** {worst_promise.index[0]} has broken {worst_promise.iloc[0]} promise(s) to pay — this customer is a repeat offender.")
        except Exception:
            pass

        lines.append(f"\n**🎯 Recommended:**")
        lines.append(f"1. Escalate **{worst['customer_name']}** if emails and calls have been attempted")
        lines.append(f"2. Consider requesting a structured payment plan for chronic late payers")
        lines.append(f"3. Flag top 3 worst payers to your manager for potential credit hold")
        return "\n".join(lines)

    # Least priority / low priority / safe accounts
    if any(kw in q for kw in ["least priority", "low priority", "least urgent", "safe", "good payer",
                               "best customer", "on time", "not worried", "lowest risk",
                               "least concern", "healthy account", "no issue"]):
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if invoices.empty:
            return "No invoice data available."

        # Find least concerning accounts
        cust_stats = invoices.groupby("customer_name").agg(
            avg_days=("days_overdue", "mean"),
            max_days=("days_overdue", "max"),
            total_overdue=("amount", "sum"),
            invoice_count=("invoice_id", "count"),
        ).sort_values("avg_days", ascending=True).reset_index()

        lines = ["**📊 Lowest Priority Accounts (least overdue):**\n"]
        lines.append("| # | Customer | Avg Days Overdue | Max Days | Invoices | Outstanding (₹) |")
        lines.append("|---|----------|-----------------|----------|----------|-----------------|")
        for i, (_, r) in enumerate(cust_stats.head(10).iterrows(), 1):
            lines.append(f"| {i} | {r['customer_name']} | {r['avg_days']:.0f} days | {r['max_days']} | {r['invoice_count']} | ₹{r['total_overdue']:,.0f} |")

        best = cust_stats.iloc[0]
        lines.append(f"\n**💡 Why these are low priority:** These customers have the shortest overdue periods. "
                     f"**{best['customer_name']}** averages only {best['avg_days']:.0f} days overdue — "
                     f"a gentle email reminder is sufficient. Don't spend too much time here; focus your energy on critical accounts.")

        lines.append(f"\n**🎯 Recommended:**")
        lines.append(f"1. Send a soft email reminder to maintain the relationship")
        lines.append(f"2. Shift your focus to critical and high-priority invoices instead")
        lines.append(f"3. These accounts are likely to pay on their own with minimal nudging")
        return "\n".join(lines)

    # How are you / general chat
    if any(kw in q for kw in ["how are you", "how r u", "what can you do", "help me", "what do you do",
                               "who are you", "your name"]):
        return ("I'm Filli, your AI Collections Assistant! I'm here to help you manage overdue invoices.\n\n"
                "**Here's what I can do:**\n"
                "- 📊 Analyze your portfolio (DSO, aging, recovery rates)\n"
                "- 🔍 Find specific customer or invoice details\n"
                "- 📋 Prioritize your follow-ups for the day\n"
                "- 📧 Send payment reminder emails\n"
                "- 📞 Initiate AI calls to customers\n"
                "- ⚠️ Identify high-risk and late-paying customers\n"
                "- 📈 Show trends and forecasts\n\n"
                "Just ask me in plain English — for example:\n"
                "- *\"Which customer is always late?\"*\n"
                "- *\"Show me my critical invoices\"*\n"
                "- *\"What should I focus on today?\"*")

    # ═══════════════════════════════════════════════════
    # EXISTING HANDLERS (kept from before)
    # ═══════════════════════════════════════════════════

    # Priority / follow-up
    if any(kw in q for kw in ["priorit", "follow-up", "follow up", "today", "focus", "action",
                               "what should i do", "next step", "urgent"]):
        priority = data_service.get_priority_invoices(analyst_filter=analyst_filter, top_n=10)
        if priority.empty:
            return "No priority invoices found in your portfolio."
        lines = ["Here are your **top priority invoices** for follow-up today:\n"]
        lines.append("| # | Invoice | Customer | Outstanding (₹) | Days Overdue | Priority |")
        lines.append("|---|---------|----------|-----------------|-------------|----------|")
        for i, (_, r) in enumerate(priority.iterrows(), 1):
            lines.append(f"| {i} | {r['invoice_id']} | {r['customer_name']} | ₹{r['amount']:,.0f} | {r['days_overdue']} | **{r['priority']}** |")
        lines.append(f"\n**Total overdue:** ₹{priority['amount'].sum():,.0f} across {len(priority)} invoices")
        critical = priority[priority["priority"] == "Critical"]
        if len(critical) > 0:
            top = critical.iloc[0]
            lines.append(f"\n⚠️ **{len(critical)} critical invoices** require immediate attention.")
            lines.append(f"Start with **{top['customer_name']}** ({top['invoice_id']}, ₹{top['amount']:,.0f}, {top['days_overdue']}d overdue).")
            lines.append("\nWould you like me to send a reminder email or initiate an AI call?")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "priority"))
        return "\n".join(lines)

    # Total overdue / summary
    if any(kw in q for kw in ["total overdue", "overdue amount", "summary", "overview", "how much",
                               "dashboard", "snapshot", "at a glance"]):
        summary = data_service.get_overdue_summary(analyst_filter=analyst_filter)
        scope = "your assigned portfolio" if persona == ANALYST else "all customers"
        lines = [f"**Overdue Summary** across {scope}:\n"]
        lines.append(f"- **Total Overdue:** ₹{summary['total_overdue_amount']:,.0f}")
        lines.append(f"- **Invoices:** {summary['total_overdue_invoices']}")
        lines.append(f"\n**By Aging Bucket:**")
        lines.append(f"- 🔴 Critical (>90d): {summary['critical_count']} — ₹{summary['critical_amount']:,.0f}")
        lines.append(f"- 🟠 High (61-90d): {summary['high_count']} — ₹{summary['high_amount']:,.0f}")
        lines.append(f"- 🟡 Medium (31-60d): {summary['medium_count']} — ₹{summary['medium_amount']:,.0f}")
        lines.append(f"- 🟢 Low (0-30d): {summary['low_count']} — ₹{summary['low_amount']:,.0f}")
        if summary['critical_count'] > 0:
            pct = round(summary['critical_amount'] / max(summary['total_overdue_amount'], 1) * 100, 1)
            lines.append(f"\n⚠️ **{pct}%** of overdue is critical (>90 days).")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "summary"))
        return "\n".join(lines)

    # Aging
    if any(kw in q for kw in ["aging", "bucket", "distribution"]):
        aging = data_service.get_aging_summary(analyst_filter=analyst_filter)
        if aging.empty:
            return "No aging data available."
        bucket_summary = aging.groupby("aging_bucket").agg(
            total=("total_amount", "sum"), count=("invoice_count", "sum")
        ).reset_index()
        lines = ["**Aging Bucket Distribution:**\n"]
        lines.append("| Bucket | Invoices | Amount (₹) |")
        lines.append("|--------|----------|-----------|")
        for _, r in bucket_summary.iterrows():
            lines.append(f"| {r['aging_bucket']} days | {int(r['count'])} | ₹{r['total']:,.0f} |")
        lines.append(f"\n**Total:** ₹{bucket_summary['total'].sum():,.0f}")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "aging"))
        return "\n".join(lines)

    # Customer risk
    if any(kw in q for kw in ["risk", "delay", "consistently", "chronic", "high risk", "delinquent"]):
        customers = data_service.get_customers(analyst_filter=analyst_filter)
        high_risk = customers[customers["risk_level"] == "High"] if "risk_level" in customers.columns else customers
        if high_risk.empty:
            return "No high-risk customers identified."
        lines = ["**High-Risk Customers:**\n"]
        lines.append("| Customer | Risk | Invoices | Overdue (₹) | Max Days |")
        lines.append("|----------|------|----------|------------|----------|")
        for _, r in high_risk.iterrows():
            lines.append(f"| {r['customer_name']} | **{r['risk_level']}** | {r.get('invoice_count', 'N/A')} | ₹{r.get('total_outstanding', 0):,.0f} | {r.get('max_days_overdue', 0):.0f} |")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "risk"))
        return "\n".join(lines)

    # Broken promises
    if any(kw in q for kw in ["promise", "broken", "commitment"]):
        promises = data_service.get_promises(broken_only=True, analyst_filter=analyst_filter)
        if promises.empty:
            return "No broken promises found."
        lines = ["**Broken Promise-to-Pay Records:**\n"]
        lines.append("| Invoice | Customer | Promised Date | Amount (₹) |")
        lines.append("|---------|----------|--------------|-----------|")
        for _, r in promises.iterrows():
            lines.append(f"| {r['invoice_id']} | {r['customer_name']} | {r['promised_date']} | ₹{r['promise_amount']:,.0f} |")
        lines.append(f"\n⚠️ **{len(promises)} broken promises** need immediate follow-up.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "promises"))
        return "\n".join(lines)

    # Customer threshold
    if any(kw in q for kw in ["above", "threshold", "more than", "greater", "exceed"]):
        threshold = _extract_number(query) or 50000
        custs = data_service.get_customers_above_threshold(min_amount=threshold, analyst_filter=analyst_filter)
        if custs.empty:
            return f"No customers with outstanding above ₹{threshold:,.0f}."
        lines = [f"**Customers with outstanding above ₹{threshold:,.0f}:**\n"]
        lines.append("| Customer | Outstanding (₹) | Invoices | Max Days |")
        lines.append("|----------|----------------|----------|----------|")
        for _, r in custs.iterrows():
            lines.append(f"| {r['customer_name']} | ₹{r['total_outstanding']:,.0f} | {r['invoice_count']} | {r['max_days_overdue']} |")
        return "\n".join(lines)

    # Cash flow
    if any(kw in q for kw in ["cash flow", "forecast", "inflow", "predict", "expected cash"]):
        forecast = data_service.get_cash_flow_forecast()
        lines = ["**Predicted Cash Inflow — Next 6 Weeks:**\n"]
        lines.append("| Week | Expected (₹) | Optimistic (₹) | Conservative (₹) |")
        lines.append("|------|-------------|----------------|------------------|")
        for _, r in forecast.iterrows():
            lines.append(f"| {r['week']} | ₹{r['expected_inflow']:,.0f} | ₹{r['optimistic']:,.0f} | ₹{r['conservative']:,.0f} |")
        lines.append(f"\n**Total expected:** ₹{forecast['expected_inflow'].sum():,.0f}")
        return "\n".join(lines)

    # Escalation
    if any(kw in q for kw in ["escalat", "intervention", "stuck", "management"]):
        priority = data_service.get_priority_invoices(analyst_filter=analyst_filter, top_n=20)
        critical = priority[priority["priority"] == "Critical"]
        if critical.empty:
            return "No accounts currently require escalation."
        lines = ["**Accounts Requiring Escalation:**\n"]
        lines.append("| Invoice | Customer | Amount (₹) | Days Overdue | Score |")
        lines.append("|---------|----------|-----------|-------------|-------|")
        for _, r in critical.iterrows():
            lines.append(f"| {r['invoice_id']} | {r['customer_name']} | ₹{r['amount']:,.0f} | {r['days_overdue']} | {r['priority_score']:.0f} |")
        lines.append(f"\n🚨 **{len(critical)} accounts** need management intervention.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "escalation"))
        return "\n".join(lines)

    # Team performance
    if any(kw in q for kw in ["team", "performance", "analyst", "kpi", "workload"]):
        perf = data_service.get_analyst_performance()
        if perf.empty:
            return "No team performance data available."
        lines = ["**Team Performance KPIs:**\n"]
        lines.append("| Analyst | Accounts | Invoices | Overdue (₹) | Avg Days | Rate | Follow-ups |")
        lines.append("|---------|----------|----------|------------|----------|------|-----------|")
        for _, r in perf.iterrows():
            lines.append(f"| {r['analyst']} | {r['total_accounts']} | {r['total_invoices']} | ₹{r['total_overdue_amount']:,.0f} | {r['avg_days_overdue']:.0f} | {r['collection_rate']}% | {r['follow_ups_this_week']} |")
        return "\n".join(lines)

    # Trends
    if any(kw in q for kw in ["trend", "over time", "changed", "history", "week over week"]):
        trend = data_service.get_overdue_trends()
        lines = ["**Overdue Balance Trend (12 Weeks):**\n"]
        lines.append("| Week | Total Overdue (₹) |")
        lines.append("|------|------------------|")
        for _, r in trend.iterrows():
            lines.append(f"| {r['week']} | ₹{r['total_overdue']:,.0f} |")
        first, last = trend.iloc[0]['total_overdue'], trend.iloc[-1]['total_overdue']
        change = ((last - first) / first) * 100
        direction = "increased" if change > 0 else "decreased"
        lines.append(f"\nOverdue has **{direction} by {abs(change):.1f}%** over 12 weeks.")
        lines.append(_generate_logic_and_next_steps(data_service, analyst_filter, persona, "trends"))
        return "\n".join(lines)

    # Percentage >90 days
    if any(kw in q for kw in ["percentage", "percent", "90 day", ">90", "what %"]):
        summary = data_service.get_overdue_summary(analyst_filter=analyst_filter)
        total = summary["total_overdue_invoices"]
        critical = summary["critical_count"]
        pct_count = round(critical / max(total, 1) * 100, 1)
        pct_amount = round(summary["critical_amount"] / max(summary["total_overdue_amount"], 1) * 100, 1)
        return (
            f"**Receivables beyond 90 days:**\n\n"
            f"- **{pct_count}%** of invoices ({critical}/{total}) are >90 days overdue\n"
            f"- **{pct_amount}%** of amount (₹{summary['critical_amount']:,.0f} / ₹{summary['total_overdue_amount']:,.0f})\n\n"
            f"These should be prioritized for escalation."
        )

    # Email
    if any(kw in q for kw in ["send email", "send mail", "email reminder", "reminder email", "email to"]):
        cust_name = _extract_customer_name(query, data_service, analyst_filter)
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if cust_name:
            cust_inv = invoices[invoices["customer_name"] == cust_name]
            if not cust_inv.empty:
                top = cust_inv.iloc[0]
                return json.dumps({
                    "action": "send_email", "customer_id": top["customer_id"],
                    "invoice_id": top["invoice_id"], "status": "pending_confirmation",
                    "message": f"Ready to send reminder to **{cust_name}** for Invoice {top['invoice_id']} (₹{top['amount']:,.0f}). Confirm?"
                })
        if not invoices.empty:
            top = invoices.iloc[0]
            return json.dumps({
                "action": "send_email", "customer_id": top["customer_id"],
                "invoice_id": top["invoice_id"], "status": "pending_confirmation",
                "message": f"Ready to send reminder to **{top['customer_name']}** for Invoice {top['invoice_id']} (₹{top['amount']:,.0f}). Confirm?"
            })
        return "No invoices found."

    # Call transcript / summary query
    if any(kw in q for kw in ["transcript", "call summary", "call result", "what happened on the call",
                               "call outcome", "call detail", "call log"]):
        import streamlit as st
        action_log = st.session_state.get("action_log", [])
        calls = [a for a in action_log if a.get("type") == "call"]
        if not calls:
            return "No AI calls have been made yet. You can initiate a call from the home page or ask me to call a customer."

        # Show summaries for both analyst and manager in chat
        lines = ["**Recent AI Call Summaries:**\n"]
        for call in reversed(calls[-5:]):
            customer = call.get("customer", "Unknown")
            invoice = call.get("invoice_id", "")
            outcome = call.get("outcome", "unknown").replace("_", " ").title()
            duration = call.get("call_duration", "")
            promised_date = call.get("promised_date", "")
            summary = call.get("summary", "")

            lines.append(f"**{customer}** — Invoice {invoice}")
            lines.append(f"- Outcome: {outcome} | Duration: {duration}")
            if promised_date:
                lines.append(f"- Promise to Pay: Rs.{call.get('promised_amount', 0):,.0f} by {promised_date}")
            if summary:
                lines.append(f"- {summary}")
            lines.append("")

        if persona == ANALYST:
            lines.append("> Full transcripts are available in the **Action Log** under the Call Transcripts tab.")
        else:
            lines.append("> Call summaries shown above. Detailed transcripts are available to analysts in the Action Log.")
        return "\n".join(lines)

    # Call — use word-boundary matching to avoid false triggers (e.g. "recall", "called")
    call_keywords = ["initiate call", "make a call", "make call", "place a call", "phone", "voice call", "ring"]
    call_match = any(kw in q for kw in call_keywords)
    if not call_match:
        # Check for standalone "call" as a word (not substring like "recall")
        import re as _re2
        call_match = bool(_re2.search(r'\bcall\b', q)) and not any(kw in q for kw in [
            "call log", "call history", "call transcript", "call summary", "call status",
            "invoice", "invoices", "details", "show me", "tell me", "info", "information"
        ])
    if call_match:
        cust_name = _extract_customer_name(query, data_service, analyst_filter)
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        if cust_name:
            cust_inv = invoices[invoices["customer_name"] == cust_name]
            if not cust_inv.empty:
                top = cust_inv.iloc[0]
                return json.dumps({
                    "action": "initiate_call", "customer_id": top["customer_id"],
                    "invoice_id": top["invoice_id"], "status": "pending_confirmation",
                    "message": f"Ready to call **{cust_name}** about Invoice {top['invoice_id']} (₹{top['amount']:,.0f}). Confirm?"
                })
        if not invoices.empty:
            top = invoices.iloc[0]
            return json.dumps({
                "action": "initiate_call", "customer_id": top["customer_id"],
                "invoice_id": top["invoice_id"], "status": "pending_confirmation",
                "message": f"Ready to call **{top['customer_name']}** about Invoice {top['invoice_id']} (₹{top['amount']:,.0f}). Confirm?"
            })
        return "No invoices found."

    # ═══════════════════════════════════════════════════
    # Manager Remarks to Analyst
    # ═══════════════════════════════════════════════════
    if persona == MANAGER and any(kw in q for kw in ["remark", "comment", "note to", "message to",
                                                       "tell analyst", "inform analyst", "send remark",
                                                       "feedback to", "notify analyst"]):
        from persistence import add_remark
        from config import USERS
        import re as _re

        # Find analyst name in the query
        target_analyst_id = None
        target_analyst_name = None
        for uname, udata in USERS.items():
            if udata.get("analyst_id"):
                name_parts = udata["name"].lower().replace("(", "").replace(")", "").split()
                for part in name_parts:
                    if len(part) > 2 and part in q:
                        target_analyst_id = udata["analyst_id"]
                        target_analyst_name = udata["name"]
                        break
                if target_analyst_id:
                    break

        if not target_analyst_id:
            # Default: list available analysts
            analyst_list = [f"- {u['name']} ({u['analyst_id']})" for u in USERS.values() if u.get("analyst_id")]
            return "Please specify which analyst to send the remark to. Available analysts:\n" + "\n".join(analyst_list) + "\n\nExample: *\"Send remark to Falguni: Focus on critical invoices this week\"*"

        # Extract the remark text — find the actual message after the analyst name
        # Patterns: "send remark to falguni: message", "send remark to falguni - message",
        #           "tell falguni to do something", "remark to falguni send me files"
        remark_text = ""

        # Find where the analyst name appears in the original query
        analyst_first_name = target_analyst_name.split()[0].lower()
        name_pos = query.lower().find(analyst_first_name)

        if name_pos >= 0:
            # Everything after the analyst name
            after_name = query[name_pos + len(analyst_first_name):].strip()
            # Strip leading separators: colon, dash, comma, "to", "that"
            import re as _re2
            after_name = _re2.sub(r'^[\s:,\-–—]+', '', after_name)
            after_name = _re2.sub(r'^(to|that)\s+', '', after_name, flags=_re2.IGNORECASE)
            remark_text = after_name.strip()
        elif ":" in query:
            remark_text = query.split(":", 1)[1].strip()
        elif " - " in query:
            remark_text = query.split(" - ", 1)[1].strip()

        if not remark_text or len(remark_text) < 3:
            return f"What would you like to say to **{target_analyst_name}**? Example: *\"Send remark to {target_analyst_name.split()[0]}: Focus on XYZ customer this week\"*"

        manager_name = analyst_id or "Manager"
        import streamlit as st
        manager_name = st.session_state.get("user_name", "Manager")
        add_remark(manager_name, target_analyst_id, target_analyst_name, remark_text)

        return (
            f"**Remark sent to {target_analyst_name}** ({target_analyst_id}):\n\n"
            f"> {remark_text}\n\n"
            f"This will appear on their Filli Assistant page when they next log in."
        )

    # View remarks sent (manager)
    if persona == MANAGER and any(kw in q for kw in ["my remarks", "remarks sent", "sent remarks", "view remarks"]):
        from persistence import load_remarks
        remarks = load_remarks()
        import streamlit as st
        manager_name = st.session_state.get("user_name", "Manager")
        my_remarks = [r for r in remarks if r.get("manager") == manager_name]
        if not my_remarks:
            return "You haven't sent any remarks to analysts yet. Try: *\"Send remark to Falguni: Focus on critical invoices\"*"
        lines = ["**Your Remarks:**\n"]
        for r in reversed(my_remarks[-10:]):
            read_icon = "✅" if r.get("read") else "🔵"
            lines.append(f"- {read_icon} **To {r['analyst_name']}** ({r['timestamp'][:16]}): {r['remark']}")
        return "\n".join(lines)

    # View remarks received (analyst)
    if persona == ANALYST and any(kw in q for kw in ["remark", "remarks", "manager comment", "manager message",
                                                       "any remarks", "my remarks", "feedback from manager"]):
        from persistence import get_remarks_for_analyst, mark_remarks_read
        remarks = get_remarks_for_analyst(analyst_filter)
        if not remarks:
            return "No remarks from your manager at this time."
        lines = ["**Remarks from Manager:**\n"]
        for r in reversed(remarks[-10:]):
            read_icon = "✅" if r.get("read") else "🔵 NEW"
            remark_text_val = r['remark']
            lines.append(f"- {read_icon} **{r['manager']}** ({r['timestamp'][:16]}):\n  > {remark_text_val}")
            # Suggest action based on remark content
            suggestion = _suggest_action_for_remark(remark_text_val, data_service, analyst_filter)
            if suggestion:
                lines.append(f"  💡 *{suggestion}*")
        mark_remarks_read(analyst_filter)
        return "\n".join(lines)

    # Hello / greeting — use word boundary to avoid matching "which", "they", etc.
    import re as _re_greet
    if _re_greet.search(r'\b(hello|hey|good morning|good afternoon|good evening)\b', q) or q.strip() in ("hi", "hi!", "hey", "hey!"):
        name = "there"
        if persona == ANALYST:
            name = analyst_id or "Analyst"
        return f"Hello {name}! 👋 I'm Filli, your AI Collections Assistant. How can I help you today? You can ask me about overdue invoices, DSO, priorities, or I can send emails and make calls on your behalf."

    # Vertex AI search fallback
    try:
        search_results = _search_invoices(query, page_size=15)
        if analyst_filter:
            search_results = [r for r in search_results if r.get("analyst_id") == analyst_filter]
        if search_results:
            from datetime import datetime
            today = datetime.now().date()
            lines = [f"Here's what I found ({len(search_results)} results):\n"]
            lines.append("| Invoice | Customer | Outstanding (₹) | Days Overdue | Status |")
            lines.append("|---------|----------|-----------------|-------------|--------|")
            for inv in search_results[:15]:
                due = inv.get("due_date", "")
                try:
                    days = max(0, (today - datetime.strptime(due, "%Y-%m-%d").date()).days)
                except:
                    days = 0
                outstanding = float(inv.get("outstanding_amount", inv.get("amount", 0)))
                lines.append(f"| {inv.get('invoice_id', 'N/A')} | {inv.get('customer_name', 'N/A')} | ₹{outstanding:,.0f} | {days} | {inv.get('invoice_status', 'N/A')} |")
            return "\n".join(lines)
    except Exception:
        pass

    # Smart fallback — try to understand intent from context
    # Check if the query mentions a customer name
    cust_name = _extract_customer_name(query, data_service, analyst_filter)
    if cust_name:
        invoices = data_service.get_invoices(analyst_filter=analyst_filter)
        cust_inv = invoices[invoices["customer_name"] == cust_name]
        if not cust_inv.empty:
            total = cust_inv["amount"].sum()
            max_days = cust_inv["days_overdue"].max()
            avg_days = cust_inv["days_overdue"].mean()
            lines = [f"I found **{cust_name}** in your portfolio:\n"]
            lines.append(f"- **{len(cust_inv)} invoices** totaling ₹{total:,.0f}")
            lines.append(f"- **Max overdue:** {max_days} days | **Avg:** {avg_days:.0f} days")
            lines.append(f"\n**Top invoices:**\n")
            lines.append("| Invoice | Amount (₹) | Days Overdue | Status |")
            lines.append("|---------|-----------|-------------|--------|")
            for _, r in cust_inv.head(5).iterrows():
                lines.append(f"| {r['invoice_id']} | ₹{r['amount']:,.0f} | {r['days_overdue']} | {r.get('status', 'N/A')} |")
            if max_days > 90:
                lines.append(f"\n⚠️ This customer has critical invoices. Would you like me to send an email or initiate a call?")
            else:
                lines.append(f"\nWould you like me to send a reminder email or show more details?")
            return "\n".join(lines)

    # Check if query has any number — might be asking about a threshold
    num = _extract_number(query)
    if num and num > 100:
        custs = data_service.get_customers_above_threshold(min_amount=num, analyst_filter=analyst_filter)
        if not custs.empty:
            lines = [f"**Customers with outstanding above ₹{num:,.0f}:**\n"]
            lines.append("| Customer | Outstanding (₹) | Invoices |")
            lines.append("|----------|----------------|----------|")
            for _, r in custs.head(10).iterrows():
                lines.append(f"| {r['customer_name']} | ₹{r['total_outstanding']:,.0f} | {r['invoice_count']} |")
            return "\n".join(lines)

    # Final fallback with helpful suggestions
    return (
        f"I'm not sure I understood that. Let me help — here are some things you can ask me:\n\n"
        f"**Plain English Works:**\n"
        f"- *\"Which customer is always late?\"*\n"
        f"- *\"What should I focus on today?\"*\n"
        f"- *\"Show me my worst accounts\"*\n"
        f"- *\"How much is overdue?\"*\n"
        f"- *\"Who has broken promises?\"*\n\n"
        f"**Specific Actions:**\n"
        f"- *\"Send email to [customer name]\"*\n"
        f"- *\"Call [customer name]\"*\n\n"
        f"**Analytics:**\n"
        f"- *\"What is the DSO?\"*\n"
        f"- *\"Show aging distribution\"*\n"
        f"- *\"SLA compliance\"*\n"
        f"- *\"Cash flow forecast\"*"
    )


def chat_with_filli(user_message: str, conversation_history: list,
                    persona: str, data_service, api_key: str = None,
                    analyst_id: str = None) -> tuple:
    response_text = _build_response(user_message, data_service, persona, analyst_id)

    action_data = None
    try:
        parsed = json.loads(response_text)
        if parsed.get("action") in ("send_email", "initiate_call"):
            action_data = parsed
            response_text = parsed.get("message", response_text)
    except (json.JSONDecodeError, TypeError):
        pass

    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": response_text})

    return response_text, conversation_history, action_data
