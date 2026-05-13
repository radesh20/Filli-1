"""JSON persistence layer for actions, remarks, escalations, and PTP tracking."""
from __future__ import annotations

import json
import os
from datetime import datetime
from filelock import FileLock

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ACTION_LOG_FILE = os.path.join(DATA_DIR, "action_log.json")
EMAIL_COUNTER_FILE = os.path.join(DATA_DIR, "email_counter.json")
REMARKS_FILE = os.path.join(DATA_DIR, "manager_remarks.json")
ESCALATION_FILE = os.path.join(DATA_DIR, "escalations.json")
PTP_FILE = os.path.join(DATA_DIR, "ptp_tracking.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, payload):
    _ensure_dir()
    lock = FileLock(f"{path}.lock")
    with lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)


def load_action_log(): return _load(ACTION_LOG_FILE, [])
def save_action_log(action_log): _save(ACTION_LOG_FILE, action_log)
def load_email_counter(): return _load(EMAIL_COUNTER_FILE, {})
def save_email_counter(counter): _save(EMAIL_COUNTER_FILE, counter)
def load_remarks(): return _load(REMARKS_FILE, [])
def save_remarks(remarks): _save(REMARKS_FILE, remarks)
def load_escalations(): return _load(ESCALATION_FILE, [])
def save_escalations(escalations): _save(ESCALATION_FILE, escalations)
def load_ptp_tracking(): return _load(PTP_FILE, [])
def save_ptp_tracking(ptp): _save(PTP_FILE, ptp)


def add_remark(manager_name, analyst_id, analyst_name, remark_text):
    remarks = load_remarks()
    remarks.append({"manager": manager_name, "analyst_id": analyst_id, "analyst_name": analyst_name, "remark": remark_text, "timestamp": datetime.now().isoformat(), "read": False})
    save_remarks(remarks)
    return remarks


def get_remarks_for_analyst(analyst_id):
    return [r for r in load_remarks() if r.get("analyst_id") == analyst_id]


def mark_remarks_read(analyst_id):
    remarks = load_remarks()
    for r in remarks:
        if r.get("analyst_id") == analyst_id:
            r["read"] = True
    save_remarks(remarks)
    return remarks


def add_escalation(analyst_name, analyst_id, customer_name, customer_id, invoice_id, amount, days_overdue, emails_sent, calls_made, broken_promises):
    escalations = load_escalations()
    entry = {
        "analyst": analyst_name,
        "analyst_id": analyst_id,
        "customer_name": customer_name,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "days_overdue": days_overdue,
        "emails_sent": emails_sent,
        "calls_made": calls_made,
        "broken_promises": broken_promises,
        "timestamp": datetime.now().isoformat(),
        "status": "open",
    }
    escalations.append(entry)
    save_escalations(escalations)
    return entry


def get_escalations(analyst_id=None, status=None):
    rows = load_escalations()
    if analyst_id:
        rows = [e for e in rows if e.get("analyst_id") == analyst_id]
    if status:
        rows = [e for e in rows if e.get("status") == status]
    return rows


def is_escalated(invoice_id):
    return any(e.get("invoice_id") == invoice_id and e.get("status") == "open" for e in load_escalations())


def get_customer_action_history(action_log, customer_name):
    emails = sum(1 for a in action_log if a.get("customer", "").lower() == customer_name.lower() and a.get("type") == "email")
    calls = sum(1 for a in action_log if a.get("customer", "").lower() == customer_name.lower() and a.get("type") == "call")
    return emails, calls
