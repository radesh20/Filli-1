"""Chat engine powered by Azure OpenAI GPT-4o with deterministic data tools."""
from __future__ import annotations

import json
from openai import AzureOpenAI
from config import ANALYST, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT
from assistant.prompts import ANALYST_SYSTEM_PROMPT, MANAGER_SYSTEM_PROMPT


def _suggest_action_for_remark(remark_text, data_service, analyst_filter=None):
    """Return a short actionable suggestion for manager remarks."""
    r = (remark_text or "").lower()
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    if invoices.empty:
        return "No invoices in scope. Ask your manager for a specific account."

    customer_names = invoices["customer_name"].dropna().unique().tolist()
    for name in customer_names:
        if name.lower() in r:
            cust = invoices[invoices["customer_name"] == name]
            total = float(cust["amount"].sum())
            max_days = int(cust["days_overdue"].max())
            return f"Review {name}: {len(cust)} invoice(s), Rs.{total:,.0f} outstanding, max {max_days} days overdue."

    if any(k in r for k in ["priorit", "urgent", "critical", "immediate"]):
        return "Ask: 'Which invoices should I prioritize today?' and start with >90-day invoices."
    if any(k in r for k in ["email", "reminder", "follow up", "follow-up"]):
        return "Ask: 'Send reminder email to top overdue customer' to queue action."
    if any(k in r for k in ["call", "contact", "phone"]):
        return "Ask: 'Call <customer name>' to initiate an AI call after confirmation."
    if any(k in r for k in ["escalat", "manager", "approve"]):
        return "Prepare escalation candidates from critical invoices and broken promises."
    if any(k in r for k in ["dso", "kpi", "performance", "trend"]):
        return "Open dashboard KPIs and ask for overdue trend and recovery snapshot."

    return "Use this remark as today’s action focus and ask me for the exact customer/action list."


def _extract_customer_name(query, data_service, analyst_filter=None):
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    q = query.lower()
    for name in invoices["customer_name"].dropna().unique().tolist():
        if name.lower() in q:
            return name
    return None


def _build_response(query, data_service, persona, analyst_id=None):
    q = query.lower().strip()
    analyst_filter = analyst_id if persona == ANALYST else None
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)

    if "overdue" in q and "total" in q:
        total = float(invoices[invoices["amount"] > 0]["amount"].sum())
        return f"Total overdue in your scope is Rs.{total:,.0f} across {len(invoices[invoices['amount']>0])} invoices."

    if any(k in q for k in ["priority", "focus", "critical"]):
        p = data_service.get_priority_invoices(analyst_filter=analyst_filter, top_n=10)
        if p.empty:
            return "No priority invoices found right now."
        lines = ["Top priority invoices:", "| Invoice | Customer | Amount | Days | Priority |", "|---|---|---:|---:|---|"]
        for _, r in p.head(5).iterrows():
            lines.append(f"| {r['invoice_id']} | {r['customer_name']} | Rs.{r['amount']:,.0f} | {int(r['days_overdue'])} | {r['priority']} |")
        return "\n".join(lines)

    if any(k in q for k in ["call", "phone", "voice"]):
        name = _extract_customer_name(query, data_service, analyst_filter)
        if name:
            inv = invoices[invoices["customer_name"] == name].iloc[0]
            return json.dumps({"action": "initiate_call", "customer_id": inv["customer_id"], "invoice_id": inv["invoice_id"], "status": "pending_confirmation", "message": f"Ready to call {name} about invoice {inv['invoice_id']} (Rs.{inv['amount']:,.0f}). Confirm?"})

    if any(k in q for k in ["email", "reminder", "mail"]):
        name = _extract_customer_name(query, data_service, analyst_filter)
        if name:
            inv = invoices[invoices["customer_name"] == name].iloc[0]
            return json.dumps({"action": "send_email", "customer_id": inv["customer_id"], "invoice_id": inv["invoice_id"], "status": "pending_confirmation", "message": f"Ready to send reminder email to {name} for {inv['invoice_id']} (Rs.{inv['amount']:,.0f}). Confirm?"})

    return "Ask me for priorities, overdue totals, customer risk, aging buckets, or to call/email a customer."


def _polish_with_gpt(query: str, draft: str, persona: str) -> str:
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        return draft
    try:
        client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY, api_version=AZURE_OPENAI_API_VERSION)
        system_prompt = ANALYST_SYSTEM_PROMPT if persona == ANALYST else MANAGER_SYSTEM_PROMPT
        completion = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User asked: {query}\nDraft response: {draft}\nRewrite clearly while preserving facts and numbers."},
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content.strip() or draft
    except Exception:
        return draft


def chat_with_filli(user_message, conversation_history, persona, data_service, api_key=None, analyst_id=None):
    response_text = _build_response(user_message, data_service, persona, analyst_id)
    action_data = None
    try:
        parsed = json.loads(response_text)
        if parsed.get("action") in ("send_email", "initiate_call"):
            action_data = parsed
            response_text = parsed.get("message", response_text)
    except (json.JSONDecodeError, TypeError):
        response_text = _polish_with_gpt(user_message, response_text, persona)

    conversation_history.append({"role": "user", "content": user_message})
    conversation_history.append({"role": "assistant", "content": response_text})
    return response_text, conversation_history, action_data
