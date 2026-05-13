"""AI Assistant (Filli) chat page with proactive email alerts and toast notifications."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import json
from datetime import datetime
from config import ANALYST, MANAGER, EY_YELLOW, EY_DARK
from assistant.chat_engine import chat_with_filli
from actions.email_sender import send_collection_email
from actions.voice_caller import initiate_real_call, get_call_status, wait_for_call_completion, parse_promise_to_pay
from persistence import save_action_log, save_email_counter


def _apply_page_styles():
    """Apply professional styling for the assistant page."""
    st.markdown("""
    <style>
        .assist-header {
            font-size: 22px; font-weight: 600; color: inherit;
            margin: 0 0 4px 0; letter-spacing: -0.3px;
            border-bottom: 2px solid """ + EY_YELLOW + """;
            display: inline-block; padding-bottom: 6px;
        }
        .assist-caption {
            font-size: 12px; color: #7D7D8A; margin-bottom: 16px;
        }
        .alert-box {
            background: linear-gradient(135deg, #16213e 0%, #1a2a3e 100%);
            border: 1px solid rgba(255,230,0,0.15);
            border-left: 4px solid """ + EY_YELLOW + """;
            border-radius: 8px; padding: 16px 20px; margin-bottom: 16px;
        }
        .alert-box p {
            color: #e0e0e0; font-size: 13px; margin: 0; line-height: 1.6;
        }
        .alert-box .alert-label {
            font-size: 11px; font-weight: 600; color: """ + EY_YELLOW + """;
            text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
        }
        .call-panel {
            background: #16213e; border: 1px solid #2ECC71; border-radius: 10px;
            padding: 20px; margin: 12px 0;
        }
        .call-panel-title {
            text-align: center; color: #e0e0e0; font-size: 16px; font-weight: 600;
            margin-bottom: 8px;
        }
        .call-panel-detail {
            text-align: center; color: #8a8a9a; font-size: 12px;
        }
        .call-panel-id {
            text-align: center; color: #2ECC71; font-size: 11px; margin-top: 6px;
        }
        .stButton > button {
            border-radius: 6px; font-weight: 500; font-size: 13px;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
    </style>
    """, unsafe_allow_html=True)


def get_suggested_questions(persona):
    if persona == ANALYST:
        return [
            "Which invoices should I prioritize for follow-up today?",
            "What is the total overdue amount across my assigned customers?",
            "Show me the aging bucket distribution for my portfolio",
            "Which customers consistently delay payments?",
            "List customers with total outstanding above Rs.50,000",
            "Send a reminder email to the top overdue customer",
            "What is the expected cash inflow from overdue invoices?",
        ]
    return [
        "What is the total overdue balance across all customers?",
        "Which customer accounts require escalation this period?",
        "What percentage of receivables is overdue beyond 90 days?",
        "How has the overdue amount changed over time?",
        "Which customers contribute most to high-risk overdue balances?",
        "Show me the predicted cash inflow for the next 6 weeks",
        "How is the collections team performing against KPIs?",
    ]


def _show_toast(message, toast_type="success"):
    colors = {"success": "#2ECC71", "warning": "#E67E22", "error": "#E74C3C"}
    bg = colors.get(toast_type, "#2ECC71")
    st.markdown(f"""
    <div style="position: fixed; top: 20px; right: 20px; z-index: 9999;
         background: {bg}; color: white; padding: 16px 24px;
         border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.25);
         animation: slideIn 0.4s ease, fadeOut 0.5s ease 4s forwards;
         font-size: 13px; max-width: 380px;
         font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">
        {message}
    </div>
    <style>
        @keyframes slideIn {{ from {{ transform: translateX(100%); opacity: 0; }} to {{ transform: translateX(0); opacity: 1; }} }}
        @keyframes fadeOut {{ from {{ opacity: 1; }} to {{ opacity: 0; }} }}
    </style>
    """, unsafe_allow_html=True)


def render_assistant():
    st.markdown("""<style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
    </style>""", unsafe_allow_html=True)

    if not st.session_state.get("logged_in"):
        st.warning("Please sign in from the main page.")
        st.page_link("app.py", label="Go to Login")
        return

    from shared_sidebar import render_sidebar, render_back_home_buttons
    render_sidebar()
    render_back_home_buttons()

    data_service = st.session_state.get("data_service")
    if not data_service:
        st.error("Data service not initialized. Please go to the main page first.")
        return

    _apply_page_styles()

    persona = st.session_state.get("persona", ANALYST)
    user_name = st.session_state.get("user_name", "User")
    analyst_id = st.session_state.get("analyst_id")

    # Show toast if email was just sent
    if st.session_state.get("email_toast"):
        _show_toast(st.session_state.email_toast, "success")
        st.session_state.email_toast = None

    # Header
    st.markdown("### 🤖 Filli — AI Collections Assistant")
    portfolio_text = f" | 📁 Portfolio: {analyst_id}" if analyst_id else ""
    st.caption(f"Logged in as: **{user_name}** ({persona}){portfolio_text}")

    # Initialize state — load persisted data if needed
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "action_queue" not in st.session_state:
        st.session_state.action_queue = []
    if "action_log" not in st.session_state:
        from persistence import load_action_log
        st.session_state.action_log = load_action_log()
    if "email_counter" not in st.session_state:
        from persistence import load_email_counter
        st.session_state.email_counter = load_email_counter()

    # --- Manager remarks for analyst ---
    if persona == ANALYST and analyst_id:
        from persistence import get_remarks_for_analyst, mark_remarks_read
        from assistant.chat_engine import _suggest_action_for_remark
        remarks = get_remarks_for_analyst(analyst_id)
        unread = [r for r in remarks if not r.get("read")]
        if unread:
            st.markdown(f"""
            <div class="alert-box" style="border-left-color: #3498DB;">
                <div class="alert-label" style="color: #3498DB;">📋 Manager Remarks ({len(unread)} new)</div>
            </div>
            """, unsafe_allow_html=True)
            for r in reversed(unread[-5:]):
                st.info(f"**{r['manager']}** ({r['timestamp'][:16]}):\n> {r['remark']}")
                suggestion = _suggest_action_for_remark(r['remark'], data_service, analyst_id)
                if suggestion:
                    st.caption(f"💡 **Suggested action:** {suggestion}")
            if st.button("✅ Mark all as read", key="mark_remarks_read"):
                mark_remarks_read(analyst_id)
                st.rerun()

    # --- Proactive alert: near-due invoices ---
    if persona == ANALYST and len(st.session_state.messages) == 0:
        invoices = data_service.get_invoices(analyst_filter=analyst_id)
        critical = invoices[invoices["days_overdue"] > 60].sort_values("days_overdue", ascending=False)
        if len(critical) > 0:
            top = critical.iloc[0]
            st.markdown(f"""
            <div class="alert-box">
                <div class="alert-label">Filli Alert</div>
                <p><strong>{top['customer_name']}</strong> has an invoice ({top['invoice_id']})
                overdue by <strong>{top['days_overdue']} days</strong> (Rs.{top['amount']:,.0f}).
                Would you like to send a reminder email?</p>
            </div>
            """, unsafe_allow_html=True)
            col_yes, col_no, col_space = st.columns([1, 1, 3])
            with col_yes:
                if st.button("Yes, Send Email", key="proactive_email", type="primary"):
                    _send_email_and_notify(
                        data_service, top["customer_id"], top["invoice_id"],
                        top["customer_name"], top["amount"], top["days_overdue"]
                    )
            with col_no:
                if st.button("Later", key="proactive_skip"):
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Noted. I will remind you about {top['customer_name']} later. How else can I help?"
                    })
                    st.rerun()

    # Suggested questions
    with st.expander("Suggested Questions", expanded=len(st.session_state.messages) == 0):
        questions = get_suggested_questions(persona)
        cols = st.columns(2)
        for i, q in enumerate(questions):
            with cols[i % 2]:
                if st.button(q, key=f"sq_{i}", use_container_width=True):
                    st.session_state.pending_question = q
                    st.rerun()

    # Chat history display
    for msg in st.session_state.messages:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Handle pending actions
    if st.session_state.action_queue:
        action = st.session_state.action_queue[-1]
        _handle_action_confirmation(action, data_service, persona)

    # Chat input
    pending = st.session_state.pop("pending_question", None)
    user_input = st.chat_input("Ask Filli anything about collections...")
    prompt = pending or user_input

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Filli is analyzing..."):
                try:
                    response_text, updated_history, action_data = chat_with_filli(
                        user_message=prompt,
                        conversation_history=st.session_state.chat_history,
                        persona=persona,
                        data_service=data_service,
                        analyst_id=analyst_id,
                    )
                    st.session_state.chat_history = updated_history
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})

                    if action_data:
                        st.session_state.action_queue.append(action_data)
                        st.rerun()

                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


def _send_email_and_notify(data_service, customer_id, invoice_id, customer_name, amount, days_overdue):
    """Send email, log it, track count, and auto-prompt call after 2 emails."""
    customers = data_service.get_customers()
    cust = customers[customers["customer_id"] == customer_id]
    email = cust.iloc[0]["email"] if len(cust) > 0 else "collections@eyfinance.example"

    result = send_collection_email(
        customer_email=email,
        customer_name=customer_name,
        invoice_id=invoice_id,
        amount=amount,
        days_overdue=days_overdue,
    )

    if "action_log" not in st.session_state:
        st.session_state.action_log = []
    st.session_state.action_log.append({
        "type": "email", "customer": customer_name,
        "invoice_id": invoice_id, "amount": amount,
        "email": email, "result": result["status"],
        "timestamp": datetime.now().isoformat(),
    })
    save_action_log(st.session_state.action_log)

    # Track email count per customer
    if "email_counter" not in st.session_state:
        st.session_state.email_counter = {}
    st.session_state.email_counter[customer_id] = st.session_state.email_counter.get(customer_id, 0) + 1
    save_email_counter(st.session_state.email_counter)
    email_count = st.session_state.email_counter[customer_id]

    if result["status"] == "success":
        st.session_state.email_toast = f"Email sent to {customer_name} ({email})"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**Email sent successfully** to {customer_name} ({email}) for Invoice {invoice_id} (Rs.{amount:,.0f}).\n\nThe action has been logged. You can view it in the Action Log."
        })
    else:
        st.session_state.email_toast = f"Reminder queued for {customer_name} -- {invoice_id}"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Email reminder for {customer_name} has been queued. Invoice {invoice_id} (Rs.{amount:,.0f})."
        })

    # After 2 emails to same customer, auto-prompt a call
    if email_count >= 2:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📞 **Call Recommended:** {email_count} reminder emails have been sent to **{customer_name}** with no response. "
                       f"Would you like to initiate an AI call for Invoice {invoice_id} (Rs.{amount:,.0f})?"
        })
        st.session_state.action_queue.append({
            "action": "initiate_call",
            "customer_id": customer_id,
            "invoice_id": invoice_id,
        })

    st.rerun()


def _handle_action_confirmation(action, data_service, persona):
    """Handle email/call action confirmations."""
    action_type = action.get("action")
    customer_id = action.get("customer_id")
    invoice_id = action.get("invoice_id")

    customers = data_service.get_customers()
    cust = customers[customers["customer_id"] == customer_id]
    if len(cust) == 0:
        st.warning(f"Customer {customer_id} not found.")
        st.session_state.action_queue.pop()
        return

    cust = cust.iloc[0]

    if action_type == "send_email":
        st.warning(f"**Send email to {cust['customer_name']}** ({cust['email']})?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Send", key="confirm_email", type="primary"):
                invoices = data_service.get_invoices(customer_id=customer_id)
                inv = invoices.iloc[0] if len(invoices) > 0 else None
                if inv is not None:
                    _send_email_and_notify(
                        data_service, customer_id,
                        invoice_id or inv["invoice_id"],
                        cust["customer_name"], inv["amount"], inv["days_overdue"]
                    )
                st.session_state.action_queue.pop()
                st.rerun()
        with col2:
            if st.button("Cancel", key="cancel_email"):
                st.session_state.action_queue.pop()
                st.session_state.messages.append({"role": "assistant", "content": "Email cancelled."})
                st.rerun()

    elif action_type == "initiate_call":
        st.warning(f"**Initiate AI call to {cust['customer_name']}** ({cust['phone']})?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Call", key="confirm_call", type="primary"):
                invoices = data_service.get_invoices(customer_id=customer_id)
                inv = invoices.iloc[0] if len(invoices) > 0 else None
                if inv is not None:
                    _run_live_call(
                        cust, inv, invoice_id or inv["invoice_id"]
                    )
                st.session_state.action_queue.pop()
                st.rerun()
        with col2:
            if st.button("Cancel", key="cancel_call"):
                st.session_state.action_queue.pop()
                st.session_state.messages.append({"role": "assistant", "content": "Call cancelled."})
                st.rerun()


def _run_live_call(cust, inv, invoice_id):
    """Make a real AI phone call via Azure Communication Services with live status updates."""
    import time

    customer_name = cust["customer_name"]
    phone = cust.get("phone", "+12013034001")
    amount = inv["amount"]
    days_overdue = inv["days_overdue"]

    # Initiate real call
    call_result = initiate_real_call(phone, customer_name, invoice_id, amount, days_overdue)

    if call_result.get("status") == "error":
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Failed to initiate call: {call_result.get('message')}"
        })
        return

    call_id = call_result["call_id"]

    # Live call UI (will be cleared after call completes)
    call_panel_container = st.empty()
    call_panel_container.markdown(f"""
    <div class="call-panel">
        <div class="call-panel-title">AI Call in Progress -- {customer_name}</div>
        <div class="call-panel-detail">
            Calling {phone} | Invoice {invoice_id} | Rs.{amount:,.0f}
        </div>
        <div class="call-panel-id">Call ID: {call_id}</div>
    </div>
    """, unsafe_allow_html=True)

    # Poll for status with live transcript updates (shown temporarily)
    status_container = st.empty()
    transcript_container = st.empty()
    prev_transcript = ""

    for i in range(60):  # Poll for up to 5 minutes (60 * 5s)
        time.sleep(5)
        status = get_call_status(call_id)

        call_status = status.get("status", "unknown")
        duration = status.get("duration") or 0
        transcript = status.get("transcript", "")

        # Update status
        dur_str = f"{float(duration):.1f}" if duration else "0.0"
        if call_status in ("completed", "failed", "no-answer"):
            status_container.markdown(f"**Status:** {call_status.upper()} | Duration: {dur_str} min")
            break
        else:
            status_container.markdown(f"**Status:** 🔴 LIVE | Duration: {dur_str} min | Polling... ({i+1})")

        # Show live transcript (will be cleared after call ends)
        if transcript and transcript != prev_transcript:
            transcript_container.markdown(f"""
---
**Live Transcript:**

{transcript}
---
            """)
            prev_transcript = transcript

    # Clear all live call UI — transcript disappears, only summary will remain in chat
    call_panel_container.empty()
    status_container.empty()
    transcript_container.empty()

    # Final status check
    final = get_call_status(call_id)
    transcript = final.get("transcript", "No transcript available.") or "No transcript available."
    duration = final.get("duration") or 0
    recording_url = final.get("recording_url", "") or ""

    # Parse promise-to-pay from transcript
    promise_info = parse_promise_to_pay(final.get("transcript_raw") or [])
    outcome = promise_info.get("outcome", "completed")
    promised_date = promise_info.get("promised_date")

    # Build summary for chat (no full transcript — transcript lives in Action Log only)
    outcome_labels = {"payment_committed": "[Committed]", "dispute_raised": "[Dispute]", "no_commitment": "[No Commitment]"}
    outcome_label = outcome_labels.get(outcome, "[Completed]")
    dur_final = f"{float(duration):.1f}" if duration else "0.0"

    call_summary = f"""{outcome_label} **Call Completed** -- {dur_final} minutes

**Customer:** {customer_name}
**Phone:** {phone}
**Invoice:** {invoice_id} | Rs.{amount:,.0f}
**Outcome:** {outcome.replace('_', ' ').title()}
"""
    if promised_date:
        call_summary += f"\n**Promise to Pay:** Rs.{amount:,.0f} by **{promised_date}**"

    if recording_url:
        call_summary += f"\n\n**Recording:** [Listen]({recording_url})"

    call_summary += "\n\n> Full transcript is available in the **Action Log** under Call Transcripts."

    st.session_state.messages.append({"role": "assistant", "content": call_summary})

    # Log with full details
    log_entry = {
        "type": "call",
        "customer": customer_name,
        "invoice_id": invoice_id,
        "amount": amount,
        "phone": phone,
        "outcome": outcome,
        "call_duration": f"{dur_final} min",
        "call_id": call_id,
        "recording_url": recording_url,
        "transcript": transcript,
        "timestamp": datetime.now().isoformat(),
    }
    # Always store a summary for the Action Log
    if promised_date:
        log_entry["promised_date"] = promised_date
        log_entry["promised_amount"] = amount
        log_entry["summary"] = f"Customer committed to pay Rs.{amount:,.0f} by {promised_date}"
    else:
        log_entry["summary"] = f"Call to {customer_name} regarding Invoice {invoice_id} (Rs.{amount:,.0f}) — Outcome: {outcome.replace('_', ' ').title()}"

    if "action_log" not in st.session_state:
        st.session_state.action_log = []
    st.session_state.action_log.append(log_entry)
    save_action_log(st.session_state.action_log)

    # Toast
    st.session_state.email_toast = f"Call completed with {customer_name} -- {outcome.replace('_', ' ').title()}"


render_assistant()
