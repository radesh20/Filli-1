"""Tool metadata and local execution helpers for Filli."""
from __future__ import annotations
import json
from config import ANALYST


def get_tools_for_persona(persona: str) -> list:
    common = ["query_invoices", "get_priority_list", "query_aging_distribution", "get_customer_risk_profile", "get_promise_to_pay_status", "get_overdue_summary", "get_customers_above_threshold", "get_cash_flow_forecast"]
    return common + (["send_collection_email", "initiate_voice_call"] if persona == ANALYST else ["get_overdue_trends", "get_team_performance"])


def execute_tool(tool_name: str, tool_input: dict, data_service, persona: str, analyst_id: str = None) -> str:
    analyst_filter = analyst_id if persona == ANALYST else None
    if tool_name == "query_invoices":
        return data_service.get_invoices(analyst_filter=analyst_filter, status=tool_input.get("status"), min_days_overdue=tool_input.get("min_days_overdue"), customer_id=tool_input.get("customer_id"), min_amount=tool_input.get("min_amount")).to_json(orient="records", indent=2)
    if tool_name == "get_priority_list":
        return data_service.get_priority_invoices(analyst_filter=analyst_filter, top_n=tool_input.get("top_n", 15)).to_json(orient="records", indent=2)
    if tool_name == "query_aging_distribution":
        return data_service.get_aging_summary(customer_id=tool_input.get("customer_id"), analyst_filter=analyst_filter).to_json(orient="records", indent=2)
    if tool_name == "get_customer_risk_profile":
        return data_service.get_customers(risk_level=tool_input.get("risk_level"), analyst_filter=analyst_filter).to_json(orient="records", indent=2)
    if tool_name == "get_promise_to_pay_status":
        return data_service.get_promises(broken_only=tool_input.get("broken_only", False), customer_id=tool_input.get("customer_id"), analyst_filter=analyst_filter).to_json(orient="records", indent=2)
    if tool_name == "get_overdue_summary":
        return json.dumps(data_service.get_overdue_summary(analyst_filter=analyst_filter), indent=2)
    if tool_name == "get_customers_above_threshold":
        return data_service.get_customers_above_threshold(min_amount=tool_input["min_amount"], analyst_filter=analyst_filter).to_json(orient="records", indent=2)
    if tool_name == "get_cash_flow_forecast":
        return data_service.get_cash_flow_forecast(weeks=tool_input.get("weeks", 6)).to_json(orient="records", indent=2)
    if tool_name == "get_overdue_trends":
        return data_service.get_overdue_trends().to_json(orient="records", indent=2)
    if tool_name == "get_team_performance":
        return data_service.get_analyst_performance().to_json(orient="records", indent=2)
    if tool_name == "send_collection_email":
        return json.dumps({"action": "send_email", "customer_id": tool_input["customer_id"], "invoice_id": tool_input.get("invoice_id"), "status": "pending_confirmation", "message": "Email draft ready. Awaiting analyst confirmation."})
    if tool_name == "initiate_voice_call":
        return json.dumps({"action": "initiate_call", "customer_id": tool_input["customer_id"], "invoice_id": tool_input.get("invoice_id"), "status": "pending_confirmation", "message": "Voice call ready. Awaiting analyst confirmation."})
    return json.dumps({"error": f"Unknown tool: {tool_name}"})
