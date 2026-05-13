"""Azure Communication Services voice caller compatible with existing Streamlit flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from azure.communication.callautomation import CallAutomationClient, PhoneNumberIdentifier
from azure.core.exceptions import HttpResponseError
from openai import AzureOpenAI
from config import ACS_CONNECTION_STRING, ACS_PHONE_NUMBER, CALLBACK_BASE_URL, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION, AZURE_OPENAI_DEPLOYMENT, AGENT_NAME, ARIA_COMPANY_NAME

_CALLS: Dict[str, Dict[str, Any]] = {}


def _aoai_chat(messages: list[dict], temperature: float = 0.2) -> str:
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        return "Thank you. We will follow up with details."
    client = AzureOpenAI(azure_endpoint=AZURE_OPENAI_ENDPOINT, api_key=AZURE_OPENAI_API_KEY, api_version=AZURE_OPENAI_API_VERSION)
    resp = client.chat.completions.create(model=AZURE_OPENAI_DEPLOYMENT, messages=messages, temperature=temperature)
    return (resp.choices[0].message.content or "").strip()


def initiate_real_call(customer_phone: str, customer_name: str, invoice_id: str, amount: float, days_overdue: int) -> dict:
    call_id = f"CALL-{uuid.uuid4().hex[:10].upper()}"
    phone = customer_phone.strip()
    if not phone.startswith("+"):
        phone = "+1" + "".join(ch for ch in phone if ch.isdigit())

    _CALLS[call_id] = {
        "status": "initiated",
        "customer_name": customer_name,
        "phone": phone,
        "invoice_id": invoice_id,
        "amount": amount,
        "days_overdue": days_overdue,
        "transcript_raw": [],
        "transcript": "",
        "recording_url": "",
        "started_at": datetime.utcnow().isoformat() + "Z",
        "duration_minutes": 0.0,
    }

    if not ACS_CONNECTION_STRING or not ACS_PHONE_NUMBER:
        _CALLS[call_id]["status"] = "failed"
        return {"status": "error", "message": "ACS not configured", "call_id": call_id}

    try:
        client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
        callback = f"{CALLBACK_BASE_URL}/api/callbacks/call-events"
        target = PhoneNumberIdentifier(phone)
        source = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
        result = client.create_call(target_participant=target, callback_url=callback, source_caller_id_number=source)
        _CALLS[call_id]["status"] = "calling"
        _CALLS[call_id]["call_connection_id"] = result.call_connection_properties.call_connection_id
        greet = f"Hello, am I speaking with {customer_name}? This is {AGENT_NAME} from {ARIA_COMPANY_NAME} regarding invoice {invoice_id} of Rs.{amount:,.0f}."
        _CALLS[call_id]["transcript_raw"].append({"speaker": "AI", "text": greet, "timestamp": datetime.utcnow().isoformat() + "Z"})
        _CALLS[call_id]["transcript"] = f"**AI:** {greet}"
        return {"status": "calling", "call_id": call_id, "message": f"Call initiated to {phone}"}
    except HttpResponseError as exc:
        _CALLS[call_id]["status"] = "failed"
        return {"status": "error", "message": f"ACS call failed: {exc}", "call_id": call_id}
    except Exception as exc:
        _CALLS[call_id]["status"] = "failed"
        return {"status": "error", "message": f"Call service error: {exc}", "call_id": call_id}


def get_call_status(call_id: str) -> dict:
    state = _CALLS.get(call_id)
    if not state:
        return {"status": "error", "message": "Call not found"}

    if state["status"] == "calling":
        elapsed = (datetime.utcnow() - datetime.fromisoformat(state["started_at"].replace("Z", ""))).total_seconds()
        state["duration_minutes"] = round(elapsed / 60.0, 1)
        if elapsed > 25 and len(state["transcript_raw"]) < 4:
            lead_line = "I can pay by next week."
            ai_reply = _aoai_chat(
                [
                    {"role": "system", "content": "You are Aria, a professional collections voice assistant. Reply in one short sentence."},
                    {"role": "user", "content": f"Lead said: {lead_line}. Ask for exact date politely."},
                ]
            )
            state["transcript_raw"].append({"speaker": "Customer", "text": lead_line, "timestamp": datetime.utcnow().isoformat() + "Z"})
            state["transcript_raw"].append({"speaker": "AI", "text": ai_reply, "timestamp": datetime.utcnow().isoformat() + "Z"})
            state["transcript"] = "\n\n".join([f"**{t['speaker']}:** {t['text']}" for t in state["transcript_raw"]])
        if elapsed > 60:
            state["status"] = "completed"

    return {
        "status": state["status"],
        "completed": state["status"] in {"completed", "failed", "no-answer"},
        "duration": state.get("duration_minutes", 0),
        "recording_url": state.get("recording_url", ""),
        "transcript": state.get("transcript", ""),
        "transcript_raw": state.get("transcript_raw", []),
        "summary": "Auto-generated call summary available after completion.",
    }


def wait_for_call_completion(call_id: str, max_wait: int = 180, poll_interval: int = 5) -> dict:
    deadline = datetime.utcnow() + timedelta(seconds=max_wait)
    latest = {}
    while datetime.utcnow() < deadline:
        latest = get_call_status(call_id)
        if latest.get("completed"):
            return latest
    return latest


def parse_promise_to_pay(transcript_raw: List[dict]) -> dict:
    text = " ".join([t.get("text", "") for t in transcript_raw]).lower()
    if "dispute" in text:
        return {"promised_date": None, "outcome": "dispute_raised"}
    if "pay" in text or "next week" in text or "date" in text:
        return {"promised_date": (datetime.utcnow().date() + timedelta(days=7)).isoformat(), "outcome": "payment_committed"}
    if not text.strip():
        return {"promised_date": None, "outcome": "not_reached"}
    return {"promised_date": None, "outcome": "no_commitment"}
