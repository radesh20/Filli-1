from __future__ import annotations

import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow running this file directly from `backend/` via `python main.py`
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import USERS, ANALYST
from data.bigquery_client import DataService
from assistant.chat_engine import chat_with_filli
from actions.email_sender import send_collection_email
from actions.voice_caller import initiate_real_call, get_call_status, parse_promise_to_pay
from persistence import load_action_log, save_action_log, load_email_counter, save_email_counter


app = FastAPI(title="Filli API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_service = DataService()
token_store: dict[str, dict[str, Any]] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)


class SendEmailRequest(BaseModel):
    customer_id: str
    invoice_id: str | None = None
    custom_message: str | None = None


class CallRequest(BaseModel):
    customer_id: str
    invoice_id: str | None = None


def _build_user_payload(username: str) -> dict[str, Any]:
    u = USERS[username]
    return {"username": username, "name": u["name"], "role": u["role"], "analyst_id": u["analyst_id"]}


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    user = token_store.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def _analyst_filter(user: dict[str, Any]) -> str | None:
    return user["analyst_id"] if user["role"] == ANALYST else None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    user = USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = secrets.token_urlsafe(32)
    payload = _build_user_payload(body.username)
    token_store[token] = payload
    return {"access_token": token, "token_type": "bearer", "user": payload}


@app.post("/api/auth/logout")
async def logout(current_user: dict[str, Any] = Depends(get_current_user), authorization: str | None = Header(default=None)) -> dict[str, str]:
    token = authorization.split(" ", 1)[1].strip()
    token_store.pop(token, None)
    return {"message": "Logged out"}


@app.get("/api/auth/me")
async def me(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return current_user


@app.get("/api/dashboard/summary")
async def dashboard_summary(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    af = _analyst_filter(current_user)
    overdue = data_service.get_overdue_summary(analyst_filter=af)
    inv = data_service.get_invoices(analyst_filter=af)
    return {
        "overdue": overdue,
        "total_invoices": int(len(inv)),
        "customers_count": int(data_service.get_customers(analyst_filter=af).shape[0]),
    }


@app.get("/api/invoices")
async def list_invoices(
    status: str | None = Query(default=None),
    min_days_overdue: int | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    af = _analyst_filter(current_user)
    df = data_service.get_invoices(
        analyst_filter=af,
        status=status,
        min_days_overdue=min_days_overdue,
        customer_id=customer_id,
        min_amount=min_amount,
    )
    return df.to_dict(orient="records")


@app.get("/api/customers")
async def list_customers(risk_level: str | None = None, current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    af = _analyst_filter(current_user)
    df = data_service.get_customers(risk_level=risk_level, analyst_filter=af)
    return df.to_dict(orient="records")


@app.post("/api/assistant/chat")
async def assistant_chat(body: ChatRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    response_text, history, action_data = chat_with_filli(
        user_message=body.message,
        conversation_history=body.history,
        persona=current_user["role"],
        data_service=data_service,
        analyst_id=current_user["analyst_id"],
    )
    return {"reply": response_text, "history": history, "action": action_data}


@app.post("/api/actions/email")
async def trigger_email(body: SendEmailRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    customers = data_service.get_customers(analyst_filter=_analyst_filter(current_user))
    cust = customers[customers["customer_id"] == body.customer_id]
    if cust.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer = cust.iloc[0]
    invoices = data_service.get_invoices(customer_id=body.customer_id, analyst_filter=_analyst_filter(current_user))
    if invoices.empty:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if body.invoice_id:
        chosen = invoices[invoices["invoice_id"] == body.invoice_id]
        invoice = chosen.iloc[0] if not chosen.empty else invoices.iloc[0]
    else:
        invoice = invoices.iloc[0]

    result = send_collection_email(
        customer_email=customer["email"],
        customer_name=customer["customer_name"],
        invoice_id=invoice["invoice_id"],
        amount=float(invoice["amount"]),
        days_overdue=int(invoice["days_overdue"]),
        custom_message=body.custom_message,
    )

    action_log = load_action_log()
    action_log.append(
        {
            "type": "email",
            "customer": customer["customer_name"],
            "customer_id": body.customer_id,
            "invoice_id": invoice["invoice_id"],
            "amount": float(invoice["amount"]),
            "email": customer["email"],
            "result": result.get("status", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "triggered_by": current_user["username"],
        }
    )
    save_action_log(action_log)

    counter = load_email_counter()
    counter[body.customer_id] = counter.get(body.customer_id, 0) + 1
    save_email_counter(counter)

    return {"result": result, "email_count_for_customer": counter[body.customer_id]}


@app.post("/api/actions/call")
async def trigger_call(body: CallRequest, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    customers = data_service.get_customers(analyst_filter=_analyst_filter(current_user))
    cust = customers[customers["customer_id"] == body.customer_id]
    if cust.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer = cust.iloc[0]
    invoices = data_service.get_invoices(customer_id=body.customer_id, analyst_filter=_analyst_filter(current_user))
    if invoices.empty:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if body.invoice_id:
        chosen = invoices[invoices["invoice_id"] == body.invoice_id]
        invoice = chosen.iloc[0] if not chosen.empty else invoices.iloc[0]
    else:
        invoice = invoices.iloc[0]

    result = initiate_real_call(
        customer_phone=customer["phone"],
        customer_name=customer["customer_name"],
        invoice_id=invoice["invoice_id"],
        amount=float(invoice["amount"]),
        days_overdue=int(invoice["days_overdue"]),
    )
    return {"result": result}


@app.get("/api/actions/call/{call_id}/status")
async def call_status(call_id: str, current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    status = get_call_status(call_id)
    transcript_raw = status.get("transcript_raw", [])
    if status.get("completed") and transcript_raw:
        parsed = parse_promise_to_pay(transcript_raw)
        status["parsed_outcome"] = parsed
    return status


@app.get("/api/actions/log")
async def action_log(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    rows = load_action_log()
    if current_user["role"] == ANALYST:
        return [r for r in rows if r.get("triggered_by") in (None, current_user["username"])]
    return rows


@app.get("/api/analytics/trends")
async def trends(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    return data_service.get_overdue_trends().to_dict(orient="records")


@app.get("/api/analytics/risk")
async def risk(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    df = data_service.get_customers(analyst_filter=_analyst_filter(current_user))
    out = df.groupby("risk_level").size().reset_index(name="count")
    return out.to_dict(orient="records")


@app.get("/api/analytics/cashflow")
async def cashflow(current_user: dict[str, Any] = Depends(get_current_user), weeks: int = 6) -> list[dict[str, Any]]:
    return data_service.get_cash_flow_forecast(weeks=weeks).to_dict(orient="records")


@app.get("/api/analytics/team")
async def team(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    return data_service.get_analyst_performance().to_dict(orient="records")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
