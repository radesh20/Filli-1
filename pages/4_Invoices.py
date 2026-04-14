"""Invoices page — grouped by customer with expandable invoice details."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from config import ANALYST, MANAGER, EY_YELLOW, EY_DARK


def _apply_page_styles():
    st.markdown("""
    <style>
        .invoice-header {
            font-size: 22px; font-weight: 600; color: inherit;
            margin: 0 0 4px 0; letter-spacing: -0.3px;
            border-bottom: 2px solid """ + EY_YELLOW + """;
            display: inline-block; padding-bottom: 6px;
        }
        .customer-card {
            padding: 16px 20px; border-radius: 12px; margin-bottom: 8px;
            border: 1px solid rgba(255,255,255,0.08);
            background: #161b22;
            border-left: 4px solid """ + EY_YELLOW + """;
        }
        .customer-card .cust-name {
            font-size: 16px; font-weight: 600; color: #e6edf3;
        }
        .customer-card .cust-detail {
            font-size: 13px; color: #8b949e; margin-top: 4px; line-height: 1.6;
        }
        .inv-sub-card {
            padding: 12px 18px; border-radius: 8px; margin: 4px 0;
            border: 1px solid rgba(255,255,255,0.05);
            background: #0d1117;
        }
        .urgency-critical { border-left: 5px solid #E74C3C; }
        .urgency-high { border-left: 5px solid #E67E22; }
        .urgency-medium { border-left: 5px solid #F1C40F; }
        .urgency-low { border-left: 5px solid #2ECC71; }
        .stMetric {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            border: 1px solid rgba(0,0,0,0.06); border-radius: 8px;
        }
        .stMetric:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
    </style>
    """, unsafe_allow_html=True)


def _get_urgency_class(days):
    if days > 90:
        return "urgency-critical"
    elif days > 60:
        return "urgency-high"
    elif days > 30:
        return "urgency-medium"
    return "urgency-low"


def _get_urgency_label(days):
    if days > 90:
        return "🔴 Critical"
    elif days > 60:
        return "🟠 High"
    elif days > 30:
        return "🟡 Medium"
    return "🟢 Low"


def _get_risk_color(risk):
    if risk == "High":
        return "#E74C3C"
    elif risk == "Medium":
        return "#E67E22"
    elif risk == "Low":
        return "#2ECC71"
    return "#8b949e"


def render_invoices():
    st.markdown("""<style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
    </style>""", unsafe_allow_html=True)

    if not st.session_state.get("logged_in"):
        st.warning("Please sign in from the main page.")
        st.page_link("app.py", label="<- Go to Login")
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
    analyst_id = st.session_state.get("analyst_id")
    user_name = st.session_state.get("user_name", "User")

    st.markdown("### 📄 Invoices")
    st.caption(f"Viewing as: **{user_name}** ({persona})")

    # Fetch invoices
    invoices = data_service.get_invoices(analyst_filter=analyst_id)
    customers = data_service.get_customers(analyst_filter=analyst_id)

    if invoices.empty:
        st.info("No invoices found.")
        return

    # Merge risk level from customers if available
    if "risk_level" not in invoices.columns and not customers.empty and "risk_level" in customers.columns:
        invoices = invoices.merge(
            customers[["customer_id", "risk_level"]],
            on="customer_id", how="left"
        )

    # Summary KPIs
    total_amount = invoices["amount"].sum()
    total_count = len(invoices)
    unique_customers = invoices["customer_name"].nunique()
    critical_count = len(invoices[invoices["days_overdue"] > 90])
    avg_days = invoices["days_overdue"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("👥 Customers", unique_customers)
    with col2:
        st.metric("📄 Total Invoices", total_count)
    with col3:
        st.metric("💰 Total Amount", f"₹{total_amount:,.0f}")
    with col4:
        st.metric("🔴 Critical (>90d)", critical_count)
    with col5:
        st.metric("📅 Avg Days Overdue", f"{avg_days:.0f}")

    st.divider()

    # Filters
    st.markdown("**Filters**")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    with col_f1:
        customer_names = ["All"] + sorted(invoices["customer_name"].unique().tolist())
        selected_customer = st.selectbox("Customer", customer_names)

    with col_f2:
        aging_options = ["All", "0-30 days", "31-60 days", "61-90 days", ">90 days"]
        selected_aging = st.selectbox("Aging Bucket", aging_options)

    with col_f3:
        if "status" in invoices.columns:
            status_options = ["All"] + sorted(invoices["status"].dropna().unique().tolist())
        else:
            status_options = ["All"]
        selected_status = st.selectbox("Status", status_options)

    with col_f4:
        if "risk_level" in invoices.columns:
            risk_options = ["All"] + sorted(invoices["risk_level"].dropna().unique().tolist())
        else:
            risk_options = ["All"]
        selected_risk = st.selectbox("Risk Level", risk_options)

    # Apply filters
    filtered = invoices.copy()
    if selected_customer != "All":
        filtered = filtered[filtered["customer_name"] == selected_customer]
    if selected_aging != "All":
        if selected_aging == "0-30 days":
            filtered = filtered[filtered["days_overdue"] <= 30]
        elif selected_aging == "31-60 days":
            filtered = filtered[(filtered["days_overdue"] > 30) & (filtered["days_overdue"] <= 60)]
        elif selected_aging == "61-90 days":
            filtered = filtered[(filtered["days_overdue"] > 60) & (filtered["days_overdue"] <= 90)]
        elif selected_aging == ">90 days":
            filtered = filtered[filtered["days_overdue"] > 90]
    if selected_status != "All" and "status" in filtered.columns:
        filtered = filtered[filtered["status"] == selected_status]
    if selected_risk != "All" and "risk_level" in filtered.columns:
        filtered = filtered[filtered["risk_level"] == selected_risk]

    cust_count = filtered["customer_name"].nunique()
    st.markdown(f"**Showing {len(filtered)} invoices across {cust_count} customers**")

    st.divider()

    # --- Customer-grouped view ---
    _render_customer_grouped_view(filtered, data_service, customers)


def _render_customer_grouped_view(filtered, data_service, customers_df):
    """Render invoices grouped by customer with expandable sections."""
    if filtered.empty:
        st.info("No invoices match the current filters.")
        return

    # Group by customer
    grouped = filtered.groupby("customer_name").agg(
        total_amount=("amount", "sum"),
        invoice_count=("amount", "count"),
        max_days=("days_overdue", "max"),
        avg_days=("days_overdue", "mean"),
        customer_id=("customer_id", "first"),
    ).sort_values("total_amount", ascending=False).reset_index()

    # Add risk level
    if "risk_level" in filtered.columns:
        risk_map = filtered.groupby("customer_name")["risk_level"].first()
        grouped["risk_level"] = grouped["customer_name"].map(risk_map)
    else:
        grouped["risk_level"] = "N/A"

    for _, cust_row in grouped.iterrows():
        cust_name = cust_row["customer_name"]
        total = cust_row["total_amount"]
        count = cust_row["invoice_count"]
        max_days = cust_row["max_days"]
        risk = cust_row.get("risk_level", "N/A")
        risk_color = _get_risk_color(risk)
        urgency = _get_urgency_label(max_days)
        urgency_class = _get_urgency_class(max_days)

        # Customer header as expander
        with st.expander(
            f"**{cust_name}** — {count} invoice{'s' if count > 1 else ''} · ₹{total:,.0f} · Max {max_days}d overdue · {urgency}",
            expanded=False
        ):
            # Customer summary row
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Outstanding", f"₹{total:,.0f}")
            with c2:
                st.metric("Invoices", int(count))
            with c3:
                st.metric("Max Days Overdue", int(max_days))
            with c4:
                st.markdown(f"**Risk Level**")
                st.markdown(f"<span style='color:{risk_color}; font-size: 20px; font-weight: 700;'>{risk}</span>", unsafe_allow_html=True)

            # Customer contact info
            cust_id = cust_row["customer_id"]
            if not customers_df.empty:
                cust_info = customers_df[customers_df["customer_id"] == cust_id]
                if not cust_info.empty:
                    ci = cust_info.iloc[0]
                    cc1, cc2, cc3 = st.columns(3)
                    with cc1:
                        st.caption(f"📧 {ci.get('email', 'N/A')}")
                    with cc2:
                        st.caption(f"📞 {ci.get('phone', 'N/A')}")
                    with cc3:
                        st.caption(f"💳 {ci.get('payment_behavior', 'N/A')}")

            st.markdown("---")

            # Individual invoices for this customer
            cust_invoices = filtered[filtered["customer_name"] == cust_name].sort_values("days_overdue", ascending=False)

            for idx, (_, inv) in enumerate(cust_invoices.iterrows()):
                days = inv.get("days_overdue", 0)
                urgency_lbl = _get_urgency_label(days)
                status = inv.get("status", "N/A")
                due_date = inv.get("due_date", "N/A")

                col_inv, col_action = st.columns([5, 1])
                with col_inv:
                    st.markdown(f"""
                    <div class="inv-sub-card {_get_urgency_class(days)}">
                        <div style="font-size: 14px; font-weight: 600; color: #e6edf3;">
                            {inv['invoice_id']}
                        </div>
                        <div style="font-size: 12px; color: #8b949e; margin-top: 4px;">
                            💰 ₹{inv['amount']:,.0f} · 📅 {days} days overdue · {urgency_lbl} · Status: {status} · Due: {due_date}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_action:
                    # Show recommended action based on aging
                    safe_key = f"inv_action_{inv['invoice_id']}_{cust_name}".replace(" ", "_")
                    if days > 90:
                        if st.button("🚨 Escalate", key=safe_key, use_container_width=True):
                            st.warning(f"Escalation flagged for {inv['invoice_id']} — notify your manager.")
                    elif days > 60:
                        if st.button("📞 Call", key=safe_key, use_container_width=True):
                            st.session_state.pending_call = {"customer_id": cust_id, "invoice_id": inv["invoice_id"]}
                            st.info(f"Go to Filli Assistant to initiate call for {inv['invoice_id']}")
                    else:
                        if st.button("📧 Email", key=safe_key, use_container_width=True):
                            st.session_state.pending_email = {"customer_id": cust_id, "invoice_id": inv["invoice_id"]}
                            st.info(f"Go to Filli Assistant to send email for {inv['invoice_id']}")

            # Promise-to-pay history for this customer
            promises = data_service.get_promises(customer_id=cust_id)
            if not promises.empty:
                st.markdown("---")
                st.markdown("**Promise-to-Pay History**")
                for _, p in promises.iterrows():
                    kept_icon = "✅" if p.get("promise_kept") == "Yes" else "❌"
                    st.markdown(
                        f"- {kept_icon} **{p.get('invoice_id', '')}** — Promised: ₹{p.get('promise_amount', 0):,.0f} "
                        f"by {p.get('promised_date', 'N/A')} — Kept: {p.get('promise_kept', 'N/A')}"
                    )


render_invoices()
