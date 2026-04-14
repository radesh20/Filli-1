"""Real AI Voice Calling via Bland.ai API + transcript retrieval."""

import time
import requests
import json
from datetime import datetime, timedelta

BLAND_API_KEY = "org_11056ccbe069ca4e0b415fd480c4e5ffd1c15fd1af4412af3bd2452b84b5a8969d1128eeb29d48937cea69"
BLAND_API_URL = "https://api.bland.ai/v1"
DEFAULT_PHONE = "+918000596098"


def initiate_real_call(customer_phone: str, customer_name: str,
                       invoice_id: str, amount: float,
                       days_overdue: int) -> dict:
    """
    Make a REAL AI phone call via Bland.ai.
    Returns call_id to track status and retrieve transcript.
    """
    headers = {"Authorization": BLAND_API_KEY, "Content-Type": "application/json"}

    # Format phone number
    phone = customer_phone.strip()
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")

    task = f"""You are a polite and professional collections assistant calling from EY Finance Operations department.

You are calling {customer_name} regarding an overdue invoice.

Invoice Details:
- Invoice ID: {invoice_id}
- Outstanding Amount: {amount:,.0f} rupees
- Days Overdue: {days_overdue} days

Your conversation flow:
1. Greet warmly and introduce yourself as calling from EY Collections department
2. Mention the specific invoice ID {invoice_id} and the outstanding amount of {amount:,.0f} rupees
3. Mention it is {days_overdue} days overdue
4. Politely ask when they expect to process the payment - ask for a specific date
5. If they provide a date, confirm the promise-to-pay date and amount, then thank them
6. If they mention any dispute or concern, acknowledge it empathetically and say the collections analyst will follow up
7. Thank them and end the call professionally

Important rules:
- Be professional, empathetic, and concise
- Speak in English
- Do NOT be aggressive or threatening
- If they ask who you are, say you are an AI assistant from EY Collections
- Always try to get a specific payment commitment date
"""

    payload = {
        "phone_number": phone,
        "task": task,
        "voice": "maya",
        "first_sentence": f"Hello, this is the EY Collections department. Am I speaking with someone from {customer_name}?",
        "wait_for_greeting": True,
        "max_duration": 3,
        "language": "en",
        "record": True,
        "answered_by_enabled": True,
    }

    try:
        resp = requests.post(f"{BLAND_API_URL}/calls", headers=headers,
                             json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "success":
            return {
                "status": "calling",
                "call_id": data["call_id"],
                "message": f"Call initiated to {phone}",
                "customer_name": customer_name,
                "invoice_id": invoice_id,
                "amount": amount,
                "phone": phone,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to initiate call: {data}",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Call service error: {str(e)}",
        }


def get_call_status(call_id: str) -> dict:
    """Check the status of an ongoing call."""
    headers = {"Authorization": BLAND_API_KEY}
    try:
        resp = requests.get(f"{BLAND_API_URL}/calls/{call_id}",
                            headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        transcripts = data.get("transcripts", [])
        transcript_text = ""
        for t in transcripts:
            speaker = "AI" if t.get("user") == "assistant" else "Customer"
            transcript_text += f"**{speaker}:** {t.get('text', '')}\n\n"

        return {
            "status": data.get("status", "unknown"),
            "completed": data.get("completed", False),
            "duration": data.get("call_length", 0),
            "recording_url": data.get("recording_url", ""),
            "transcript": transcript_text.strip(),
            "transcript_raw": transcripts,
            "summary": data.get("summary", ""),
            "end_at": data.get("end_at", ""),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def wait_for_call_completion(call_id: str, max_wait: int = 180, poll_interval: int = 5) -> dict:
    """
    Poll until the call completes. Returns full call result.
    max_wait: maximum seconds to wait
    poll_interval: seconds between polls
    """
    elapsed = 0
    while elapsed < max_wait:
        status = get_call_status(call_id)

        if status.get("status") in ("completed", "failed", "error", "no-answer"):
            return status

        # Also check if call_length > 0 and we have transcripts
        if status.get("duration", 0) > 0 and status.get("transcript"):
            return status

        time.sleep(poll_interval)
        elapsed += poll_interval

    # Timeout - return whatever we have
    return get_call_status(call_id)


def parse_promise_to_pay(transcript_raw: list) -> dict:
    """Extract promise-to-pay info from transcript."""
    full_text = " ".join([t.get("text", "") for t in transcript_raw]).lower()

    # Look for date patterns
    promise_date = None
    today = datetime.now().date()

    date_keywords = {
        "tomorrow": today + timedelta(days=1),
        "day after tomorrow": today + timedelta(days=2),
        "next week": today + timedelta(days=7),
        "this week": today + timedelta(days=3),
        "friday": today + timedelta(days=(4 - today.weekday()) % 7 or 7),
        "monday": today + timedelta(days=(0 - today.weekday()) % 7 or 7),
        "end of week": today + timedelta(days=(4 - today.weekday()) % 7 or 7),
        "within a week": today + timedelta(days=7),
        "two days": today + timedelta(days=2),
        "three days": today + timedelta(days=3),
        "five days": today + timedelta(days=5),
    }

    for keyword, date in date_keywords.items():
        if keyword in full_text:
            promise_date = date.strftime("%B %d, %Y")
            break

    if not promise_date:
        # Default to 7 days if payment was discussed
        payment_words = ["pay", "payment", "process", "transfer", "settle"]
        if any(w in full_text for w in payment_words):
            promise_date = (today + timedelta(days=7)).strftime("%B %d, %Y")

    # Determine outcome
    dispute_words = ["dispute", "concern", "issue", "wrong", "incorrect", "doesn't match", "query"]
    if any(w in full_text for w in dispute_words):
        outcome = "dispute_raised"
    elif promise_date:
        outcome = "payment_committed"
    else:
        outcome = "no_commitment"

    return {
        "promised_date": promise_date,
        "outcome": outcome,
    }
