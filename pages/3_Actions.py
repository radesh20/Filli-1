"""Action log page with tabs: Actions, Call Transcripts."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from config import ANALYST, MANAGER, EY_YELLOW, EY_DARK


def _apply_page_styles():
    """Apply professional styling for the action log page."""
    st.markdown("""
    <style>
        .actions-header {
            font-size: 22px; font-weight: 600; color: inherit;
            margin: 0 0 4px 0; letter-spacing: -0.3px;
            border-bottom: 2px solid """ + EY_YELLOW + """;
            display: inline-block; padding-bottom: 6px;
        }
        .actions-caption {
            font-size: 12px; color: #7D7D8A; margin-bottom: 20px;
        }
        .stMetric {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 8px;
        }
        .stMetric:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .log-card {
            padding: 14px 18px; border-radius: 8px; margin-bottom: 8px;
            border-left: 4px solid #3498DB;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .log-card:hover {
            transform: translateX(3px);
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }
        .log-card.email-success {
            background: rgba(46, 204, 113, 0.08);
            border-left-color: #2ECC71;
        }
        .log-card.email-queued {
            background: rgba(230, 126, 34, 0.08);
            border-left-color: #E67E22;
        }
        .log-card.call-committed {
            background: rgba(46, 204, 113, 0.08);
            border-left-color: #2ECC71;
        }
        .log-card.call-dispute {
            background: rgba(231, 76, 60, 0.08);
            border-left-color: #E74C3C;
        }
        .log-card.call-default {
            background: rgba(52, 152, 219, 0.08);
            border-left-color: #3498DB;
        }
        .log-card .log-title {
            font-size: 14px; font-weight: 600; color: #e0e0e0;
        }
        .log-card .log-detail {
            font-size: 12px; color: #a0a0a0; margin-top: 4px;
        }
        .log-card .log-promise {
            font-size: 13px; color: #2ECC71; margin-top: 6px; font-weight: 600;
        }
        .log-card .log-summary {
            font-size: 12px; color: #b0b0b0; margin-top: 4px;
        }
        .log-card .log-timestamp {
            font-size: 11px; color: #606070; margin-top: 4px;
        }
        .log-card .log-recording a {
            font-size: 12px; color: #3498DB; text-decoration: none;
        }
        .log-card .log-recording a:hover {
            text-decoration: underline;
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


def render_action_log():
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

    _apply_page_styles()

    persona = st.session_state.get("persona", ANALYST)
    user_name = st.session_state.get("user_name", "User")

    st.markdown("### 📋 Action Log")
    st.caption(f"Viewing as: **{user_name}** ({persona})")

    # Load persisted action log if not in session
    if "action_log" not in st.session_state:
        from persistence import load_action_log
        st.session_state.action_log = load_action_log()
    action_log = st.session_state.get("action_log", [])

    if not action_log:
        st.info("No actions taken yet. Use the AI Assistant or home page to send emails or initiate calls.")
        return

    df = pd.DataFrame(action_log)
    emails = df[df["type"] == "email"] if "type" in df.columns else pd.DataFrame()
    calls = df[df["type"] == "call"] if "type" in df.columns else pd.DataFrame()

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📧 Emails Sent", len(emails))
    with col2:
        st.metric("📞 Calls Made", len(calls))
    with col3:
        committed = len(calls[calls["outcome"] == "payment_committed"]) if "outcome" in calls.columns else 0
        st.metric("✅ Payments Committed", committed)
    with col4:
        total_promised = pd.to_numeric(calls["promised_amount"], errors="coerce").sum() if "promised_amount" in calls.columns else 0
        total_promised = total_promised if pd.notna(total_promised) else 0
        st.metric("💰 Promised Amount", f"₹{total_promised:,.0f}")

    st.divider()

    # --- Tabs: Actions | Call Transcripts ---
    tab_actions, tab_transcripts = st.tabs(["Actions", "Call Transcripts"])

    with tab_actions:
        _render_actions_tab(df, emails, calls)

    with tab_transcripts:
        _render_transcripts_tab(calls)

    st.divider()
    if st.button("Clear All Logs"):
        st.session_state.action_log = []
        from persistence import save_action_log
        save_action_log([])
        st.rerun()


def _render_actions_tab(df, emails, calls):
    """Render the actions list."""
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        action_type = row.get("type", "unknown")
        customer = row.get("customer", "Unknown")
        timestamp = row.get("timestamp", "")

        if action_type == "email":
            result = row.get("result", "unknown")
            invoice = row.get("invoice_id", "")
            amount = row.get("amount", 0)
            email_addr = row.get("email", "")
            status_text = "Sent Successfully" if result == "success" else "Queued"
            card_class = "email-success" if result == "success" else "email-queued"
            status_dot_color = "#2ECC71" if result == "success" else "#E67E22"

            st.markdown(f"""
            <div class="log-card {card_class}">
                <div class="log-title">
                    <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{status_dot_color};margin-right:8px;vertical-align:middle;"></span>
                    Email to {customer} -- {status_text}
                </div>
                <div class="log-detail">
                    {'Invoice: ' + str(invoice) + ' | ' if invoice else ''}{'Rs.' + f'{amount:,.0f}' + ' | ' if amount else ''}{email_addr}
                </div>
                <div class="log-timestamp">{timestamp}</div>
            </div>
            """, unsafe_allow_html=True)

        elif action_type == "call":
            outcome = row.get("outcome", "unknown")
            promised_date = row.get("promised_date", "")
            promised_amount = row.get("promised_amount", 0)
            call_duration = row.get("call_duration", "")
            summary = row.get("summary", "")
            invoice = row.get("invoice_id", "")
            amount = row.get("amount", 0)
            phone = row.get("phone", "")
            recording_url = row.get("recording_url", "")
            call_id = row.get("call_id", "")

            outcome_color = {"payment_committed": "#2ECC71", "partial_payment": "#E67E22",
                             "dispute_raised": "#E74C3C", "no_commitment": "#95A5A6"}
            color = outcome_color.get(outcome, "#3498DB")

            if outcome == "payment_committed":
                card_class = "call-committed"
            elif outcome == "dispute_raised":
                card_class = "call-dispute"
            else:
                card_class = "call-default"

            promise_line = ""
            if promised_date:
                promise_line = f'<div class="log-promise">Promise to Pay: Rs.{promised_amount:,.0f} by {promised_date}</div>'

            recording_line = ""
            if recording_url:
                recording_line = f'<div class="log-recording"><a href="{recording_url}" target="_blank">Listen to Recording</a></div>'

            summary_line = ""
            if summary:
                summary_line = f'<div class="log-summary">{summary}</div>'

            st.markdown(f"""
            <div class="log-card {card_class}">
                <div class="log-title">
                    <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-right:8px;vertical-align:middle;"></span>
                    Call to {customer} -- {outcome.replace('_', ' ').title()} ({call_duration})
                </div>
                <div class="log-detail">
                    {'Invoice: ' + str(invoice) + ' | ' if invoice else ''}{'Rs.' + f'{amount:,.0f}' + ' | ' if amount else ''}{phone}
                </div>
                {promise_line}
                {summary_line}
                {recording_line}
                <div class="log-timestamp">
                    {timestamp}{'  |  Call ID: ' + str(call_id) if call_id else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)


def _render_transcripts_tab(calls):
    """Render call transcripts in detail.
    Analysts see full transcripts. Managers see only call summaries.
    """
    persona = st.session_state.get("persona", ANALYST)

    if calls.empty or "transcript" not in calls.columns:
        st.info("No call transcripts available yet. Initiate a call from the AI Assistant to see transcripts here.")
        return

    calls_with_transcript = calls[calls["transcript"].notna() & (calls["transcript"] != "")]
    if calls_with_transcript.empty:
        st.info("No transcripts recorded yet.")
        return

    for i in range(len(calls_with_transcript) - 1, -1, -1):
        row = calls_with_transcript.iloc[i]
        customer = row.get("customer", "Unknown")
        invoice = row.get("invoice_id", "")
        timestamp = row.get("timestamp", "")
        outcome = row.get("outcome", "unknown")
        duration = row.get("call_duration", "")
        transcript = row.get("transcript", "")
        recording_url = row.get("recording_url", "")
        promised_date = row.get("promised_date", "")
        promised_amount = row.get("promised_amount", 0)
        summary = row.get("summary", "")

        outcome_labels = {"payment_committed": "[Committed]", "partial_payment": "[Partial]",
                          "dispute_raised": "[Dispute]", "no_commitment": "[No Commitment]"}
        label = outcome_labels.get(outcome, "[Call]")

        with st.expander(f"{label} {customer} -- {invoice} ({timestamp})", expanded=(i == len(calls_with_transcript) - 1)):
            # Call info header
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Customer:** {customer}")
                st.markdown(f"**Invoice:** {invoice}")
            with col2:
                st.markdown(f"**Duration:** {duration}")
                st.markdown(f"**Outcome:** {outcome.replace('_', ' ').title()}")
            with col3:
                if promised_date:
                    st.markdown(f"**Promise Date:** {promised_date}")
                    st.markdown(f"**Promised:** Rs.{promised_amount:,.0f}")

            if recording_url:
                st.markdown(f"[Listen to Recording]({recording_url})")

            st.divider()

            if persona == MANAGER:
                # Managers see only the call summary, not the full transcript
                st.markdown("**Call Summary:**")
                if summary:
                    st.markdown(summary)
                else:
                    st.markdown(f"Call to {customer} regarding Invoice {invoice} — Outcome: {outcome.replace('_', ' ').title()}"
                                + (f". Promise to pay Rs.{promised_amount:,.0f} by {promised_date}." if promised_date else "."))
            else:
                # Analysts see full transcript
                st.markdown("**Full Transcript:**")
                st.markdown(transcript if transcript else "No transcript available.")


render_action_log()
