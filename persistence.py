"""Simple JSON file persistence for action logs and email counters."""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ACTION_LOG_FILE = os.path.join(DATA_DIR, "action_log.json")
EMAIL_COUNTER_FILE = os.path.join(DATA_DIR, "email_counter.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_action_log():
    """Load action log from disk."""
    try:
        with open(ACTION_LOG_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_action_log(action_log):
    """Save action log to disk."""
    _ensure_dir()
    with open(ACTION_LOG_FILE, "w") as f:
        json.dump(action_log, f, indent=2, default=str)


def load_email_counter():
    """Load email counter from disk."""
    try:
        with open(EMAIL_COUNTER_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_email_counter(counter):
    """Save email counter to disk."""
    _ensure_dir()
    with open(EMAIL_COUNTER_FILE, "w") as f:
        json.dump(counter, f, indent=2)


# ── Manager Remarks ──
REMARKS_FILE = os.path.join(DATA_DIR, "manager_remarks.json")


def load_remarks():
    """Load manager remarks from disk."""
    try:
        with open(REMARKS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_remarks(remarks):
    """Save manager remarks to disk."""
    _ensure_dir()
    with open(REMARKS_FILE, "w") as f:
        json.dump(remarks, f, indent=2, default=str)


def add_remark(manager_name, analyst_id, analyst_name, remark_text):
    """Add a remark from manager to analyst."""
    from datetime import datetime
    remarks = load_remarks()
    remarks.append({
        "manager": manager_name,
        "analyst_id": analyst_id,
        "analyst_name": analyst_name,
        "remark": remark_text,
        "timestamp": datetime.now().isoformat(),
        "read": False,
    })
    save_remarks(remarks)
    return remarks


def get_remarks_for_analyst(analyst_id):
    """Get all remarks for a specific analyst."""
    remarks = load_remarks()
    return [r for r in remarks if r.get("analyst_id") == analyst_id]


def mark_remarks_read(analyst_id):
    """Mark all remarks for an analyst as read."""
    remarks = load_remarks()
    for r in remarks:
        if r.get("analyst_id") == analyst_id:
            r["read"] = True
    save_remarks(remarks)
    return remarks


# ── Escalations ──
ESCALATION_FILE = os.path.join(DATA_DIR, "escalations.json")


def load_escalations():
    """Load escalations from disk."""
    try:
        with open(ESCALATION_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_escalations(escalations):
    """Save escalations to disk."""
    _ensure_dir()
    with open(ESCALATION_FILE, "w") as f:
        json.dump(escalations, f, indent=2, default=str)


def add_escalation(analyst_name, analyst_id, customer_name, customer_id,
                   invoice_id, amount, days_overdue, emails_sent, calls_made, broken_promises):
    """Log an escalation and return the entry."""
    from datetime import datetime
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
    """Get escalations, optionally filtered."""
    escalations = load_escalations()
    if analyst_id:
        escalations = [e for e in escalations if e.get("analyst_id") == analyst_id]
    if status:
        escalations = [e for e in escalations if e.get("status") == status]
    return escalations


def is_escalated(invoice_id):
    """Check if an invoice is already escalated."""
    escalations = load_escalations()
    return any(e.get("invoice_id") == invoice_id and e.get("status") == "open" for e in escalations)


def get_customer_action_history(action_log, customer_name):
    """Count emails and calls for a customer from the action log."""
    emails = 0
    calls = 0
    for a in action_log:
        if a.get("customer", "").lower() == customer_name.lower():
            if a.get("type") == "email":
                emails += 1
            elif a.get("type") == "call":
                calls += 1
    return emails, calls
