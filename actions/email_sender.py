"""Azure Communication Services email sender with GPT-4o drafting."""
from __future__ import annotations

from azure.communication.email import EmailClient
from openai import AzureOpenAI
from config import (
    AZURE_EMAIL_SENDER,
    ACS_CONNECTION_STRING,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT,
    COMPANY_NAME,
)


def _draft_body(customer_name: str, invoice_id: str, amount: float, days_overdue: int, custom_message: str | None = None) -> str:
    if custom_message:
        return custom_message
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        return f"Dear {customer_name},\n\nThis is a reminder for invoice {invoice_id} with outstanding amount Rs.{amount:,.0f}, overdue by {days_overdue} days. Please arrange payment within 3 business days.\n\nRegards,\n{COMPANY_NAME}"
    client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY, api_version=AZURE_OPENAI_API_VERSION)
    completion = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Draft a professional AR reminder email in plain text. Keep concise."},
            {"role": "user", "content": f"Customer: {customer_name}; invoice: {invoice_id}; amount: Rs.{amount:,.0f}; overdue days: {days_overdue}"},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content.strip()


def send_collection_email(customer_email: str, customer_name: str, invoice_id: str, amount: float, days_overdue: int, custom_message: str = None) -> dict:
    if not ACS_CONNECTION_STRING or not AZURE_EMAIL_SENDER:
        return {"status": "error", "message": "ACS email is not configured. Set ACS_CONNECTION_STRING and AZURE_EMAIL_SENDER."}
    body_text = _draft_body(customer_name, invoice_id, amount, days_overdue, custom_message)
    html_body = f"""<div style='font-family:Arial,sans-serif;max-width:620px;margin:0 auto;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;'>
      <div style='background:#2E2E38;color:#FFE600;padding:16px 20px;font-size:20px;font-weight:700;'>{COMPANY_NAME} Collections</div>
      <div style='padding:20px;color:#1f2937;white-space:pre-wrap'>{body_text}</div>
      <div style='background:#f9fafb;color:#6b7280;padding:12px 20px;font-size:12px'>Automated notice from Filli.</div>
    </div>"""
    try:
        client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)
        poller = client.begin_send(
            {
                "senderAddress": AZURE_EMAIL_SENDER,
                "content": {"subject": f"Payment Reminder - {invoice_id}", "plainText": body_text, "html": html_body},
                "recipients": {"to": [{"address": customer_email, "displayName": customer_name}]},
            }
        )
        result = poller.result()
        return {"status": "success", "message_id": result.get("id", ""), "message": f"Email sent to {customer_email}"}
    except Exception as exc:
        return {"status": "error", "message": f"Email send failed: {exc}"}


def send_escalation_email(manager_name: str, analyst_name: str, customer_name: str, invoice_id: str, amount: float, days_overdue: int, emails_sent: int, calls_made: int, broken_promises: int) -> dict:
    summary = (
        f"Escalation for {customer_name} ({invoice_id})\n"
        f"Amount: Rs.{amount:,.0f}, Overdue: {days_overdue} days\n"
        f"Follow-ups: {emails_sent} emails, {calls_made} calls, {broken_promises} broken promises\n"
        f"Escalated by: {analyst_name}"
    )
    return send_collection_email(
        customer_email="collections.manager@eyfinance.example",
        customer_name=manager_name,
        invoice_id=invoice_id,
        amount=amount,
        days_overdue=days_overdue,
        custom_message=summary,
    )
