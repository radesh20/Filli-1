"""Tool definitions for Claude's tool-use (function calling)."""

import json
from config import ANALYST, MANAGER, DEMO_ANALYST

# --- Tool schemas for Claude API ---

QUERY_INVOICES = {
    "name": "query_invoices",
    "description": "Fetch invoices with optional filters. Returns a list of invoices with details like invoice_id, customer_name, amount, due_date, days_overdue, status.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter by status: Open, Partially Paid, Promised, Escalated", "enum": ["Open", "Partially Paid", "Promised", "Escalated"]},
            "min_days_overdue": {"type": "integer", "description": "Minimum days overdue to filter"},
            "customer_id": {"type": "string", "description": "Filter by specific customer ID (e.g., CUST-001)"},
            "min_amount": {"type": "number", "description": "Minimum invoice amount to filter"},
        },
        "required": [],
    },
}

GET_PRIORITY_LIST = {
    "name": "get_priority_list",
    "description": "Get prioritized list of invoices ranked by priority score. Considers aging, broken promises, customer risk level, and invoice value. Returns top N invoices with scores and priority labels.",
    "input_schema": {
        "type": "object",
        "properties": {
            "top_n": {"type": "integer", "description": "Number of top priority invoices to return (default 15)", "default": 15},
        },
        "required": [],
    },
}

QUERY_AGING_DISTRIBUTION = {
    "name": "query_aging_distribution",
    "description": "Get aging bucket summary showing total amounts and invoice counts distributed across 0-30, 31-60, 61-90, and >90 day buckets.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Optional: filter for a specific customer"},
        },
        "required": [],
    },
}

GET_CUSTOMER_RISK_PROFILE = {
    "name": "get_customer_risk_profile",
    "description": "Get customer risk profiles including risk level, payment behavior, and contact details. Can filter by risk level.",
    "input_schema": {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "description": "Filter by risk level", "enum": ["High", "Medium", "Low"]},
        },
        "required": [],
    },
}

GET_PROMISE_STATUS = {
    "name": "get_promise_to_pay_status",
    "description": "Get promise-to-pay records. Shows promised dates, whether promises were kept, and amounts. Can filter to show only broken promises.",
    "input_schema": {
        "type": "object",
        "properties": {
            "broken_only": {"type": "boolean", "description": "If true, show only broken promises", "default": False},
            "customer_id": {"type": "string", "description": "Filter by customer ID"},
        },
        "required": [],
    },
}

GET_OVERDUE_SUMMARY = {
    "name": "get_overdue_summary",
    "description": "Get summary of total overdue amounts and invoice counts, broken down by aging buckets (critical >90, high 61-90, medium 31-60, low 0-30 days).",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_CUSTOMERS_ABOVE_THRESHOLD = {
    "name": "get_customers_above_threshold",
    "description": "Get list of customers whose total outstanding invoice amount exceeds a specified threshold.",
    "input_schema": {
        "type": "object",
        "properties": {
            "min_amount": {"type": "number", "description": "Minimum total outstanding amount threshold"},
        },
        "required": ["min_amount"],
    },
}

SEND_COLLECTION_EMAIL = {
    "name": "send_collection_email",
    "description": "Send a payment reminder email to a customer. Requires customer_id. The email will include overdue invoice details and payment instructions. ALWAYS confirm with the analyst before sending.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID to send the email to"},
            "invoice_id": {"type": "string", "description": "Specific invoice ID to reference in the email"},
            "custom_message": {"type": "string", "description": "Optional custom message to include in the email"},
        },
        "required": ["customer_id"],
    },
}

INITIATE_VOICE_CALL = {
    "name": "initiate_voice_call",
    "description": "Initiate an AI voice call to a customer for payment follow-up. The call will remind the customer about overdue invoices and record their payment commitment. ALWAYS confirm with the analyst before initiating.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID to call"},
            "invoice_id": {"type": "string", "description": "Primary invoice to discuss on the call"},
        },
        "required": ["customer_id"],
    },
}

# Manager-only tools
GET_OVERDUE_TRENDS = {
    "name": "get_overdue_trends",
    "description": "Get historical overdue balance trends over the past 12 weeks. Shows how total overdue amounts have changed over time.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_TEAM_PERFORMANCE = {
    "name": "get_team_performance",
    "description": "Get collections team performance KPIs including total accounts, invoices, overdue amounts, collection rates, and follow-up counts per analyst.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_CASH_FLOW_FORECAST = {
    "name": "get_cash_flow_forecast",
    "description": "Get predicted cash inflow forecast for the next 6 weeks based on aging probabilities and promise-to-pay data. Shows expected, optimistic, and conservative scenarios.",
    "input_schema": {
        "type": "object",
        "properties": {
            "weeks": {"type": "integer", "description": "Number of weeks to forecast (default 6)", "default": 6},
        },
        "required": [],
    },
}


def get_tools_for_persona(persona: str) -> list:
    """Return the list of tools available for a given persona."""
    common_tools = [
        QUERY_INVOICES, GET_PRIORITY_LIST, QUERY_AGING_DISTRIBUTION,
        GET_CUSTOMER_RISK_PROFILE, GET_PROMISE_STATUS, GET_OVERDUE_SUMMARY,
        GET_CUSTOMERS_ABOVE_THRESHOLD, GET_CASH_FLOW_FORECAST,
    ]
    if persona == ANALYST:
        return common_tools + [SEND_COLLECTION_EMAIL, INITIATE_VOICE_CALL]
    elif persona == MANAGER:
        return common_tools + [GET_OVERDUE_TRENDS, GET_TEAM_PERFORMANCE]
    return common_tools


def execute_tool(tool_name: str, tool_input: dict, data_service, persona: str,
                  analyst_id: str = None) -> str:
    """Execute a tool and return JSON result."""
    analyst_filter = analyst_id if persona == ANALYST else None

    if tool_name == "query_invoices":
        df = data_service.get_invoices(
            analyst_filter=analyst_filter,
            status=tool_input.get("status"),
            min_days_overdue=tool_input.get("min_days_overdue"),
            customer_id=tool_input.get("customer_id"),
            min_amount=tool_input.get("min_amount"),
        )
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_priority_list":
        df = data_service.get_priority_invoices(
            analyst_filter=analyst_filter,
            top_n=tool_input.get("top_n", 15),
        )
        cols = ["invoice_id", "customer_name", "amount", "days_overdue", "status",
                "risk_level", "broken_promises", "priority_score", "priority"]
        return df[cols].to_json(orient="records", indent=2)

    elif tool_name == "query_aging_distribution":
        df = data_service.get_aging_summary(
            customer_id=tool_input.get("customer_id"),
            analyst_filter=analyst_filter,
        )
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_customer_risk_profile":
        df = data_service.get_customers(
            risk_level=tool_input.get("risk_level"),
            analyst_filter=analyst_filter,
        )
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_promise_to_pay_status":
        df = data_service.get_promises(
            broken_only=tool_input.get("broken_only", False),
            customer_id=tool_input.get("customer_id"),
            analyst_filter=analyst_filter,
        )
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_overdue_summary":
        summary = data_service.get_overdue_summary(analyst_filter=analyst_filter)
        return json.dumps(summary, indent=2)

    elif tool_name == "get_customers_above_threshold":
        df = data_service.get_customers_above_threshold(
            min_amount=tool_input["min_amount"],
            analyst_filter=analyst_filter,
        )
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_cash_flow_forecast":
        df = data_service.get_cash_flow_forecast(weeks=tool_input.get("weeks", 6))
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_overdue_trends":
        df = data_service.get_overdue_trends()
        return df.to_json(orient="records", indent=2)

    elif tool_name == "get_team_performance":
        df = data_service.get_analyst_performance()
        return df.to_json(orient="records", indent=2)

    elif tool_name == "send_collection_email":
        return json.dumps({
            "action": "send_email",
            "customer_id": tool_input["customer_id"],
            "invoice_id": tool_input.get("invoice_id"),
            "status": "pending_confirmation",
            "message": "Email draft ready. Awaiting analyst confirmation to send."
        })

    elif tool_name == "initiate_voice_call":
        return json.dumps({
            "action": "initiate_call",
            "customer_id": tool_input["customer_id"],
            "invoice_id": tool_input.get("invoice_id"),
            "status": "pending_confirmation",
            "message": "Voice call ready to initiate. Awaiting analyst confirmation."
        })

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
