"""Dashboard page with charts, analyst profiles (manager), and dynamic graph generation."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config import ANALYST, MANAGER, EY_YELLOW, EY_DARK


# Common chart layout defaults — legend on vertical right, DM Sans font
CHART_LAYOUT = dict(
    font=dict(family="DM Sans, sans-serif", size=13),
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
    margin=dict(t=50, b=40, l=50, r=120),
)


def render_dashboard():
    st.markdown("""<style>
        [data-testid="stSidebarNav"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
    </style>""", unsafe_allow_html=True)

    if not st.session_state.get("logged_in"):
        st.warning("Please sign in from the main page.")
        st.page_link("app.py", label="← Go to Login")
        return

    from shared_sidebar import render_sidebar, render_back_home_buttons
    render_sidebar()
    render_back_home_buttons()

    data_service = st.session_state.get("data_service")
    if not data_service:
        st.error("Data service not initialized. Please go to the main page first.")
        return

    persona = st.session_state.get("persona", ANALYST)
    analyst_filter = st.session_state.get("analyst_id")
    user_name = st.session_state.get("user_name", "User")

    st.markdown(f"### 📊 Collections Dashboard")
    st.caption(f"Viewing as: **{user_name}** ({persona})")

    # KPI Cards
    summary = data_service.get_overdue_summary(analyst_filter=analyst_filter)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        label = "💰 My Overdue" if persona == ANALYST else "💰 Total Overdue"
        st.metric(label, f"₹{summary['total_overdue_amount']:,.0f}")
    with col2:
        st.metric("📄 Overdue Invoices", summary["total_overdue_invoices"])
    with col3:
        st.metric("🔴 Critical (>90d)", summary["critical_count"])
    with col4:
        st.metric("🟠 High (61-90d)", summary["high_count"])

    st.divider()

    # Charts Row 1: Aging & Risk
    from charts.aging_charts import aging_donut_chart, aging_bar_chart
    from charts.risk_charts import risk_bubble_chart

    aging = data_service.get_aging_summary(analyst_filter=analyst_filter)
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)
    customers = data_service.get_customers(analyst_filter=analyst_filter)

    col_left, col_right = st.columns(2)
    with col_left:
        with st.container(border=True):
            st.markdown("**Aging Distribution** &nbsp; ℹ️ _Overdue amounts by aging bucket_")
            fig = aging_donut_chart(aging)
            fig.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
    with col_right:
        with st.container(border=True):
            st.markdown("**Invoice Risk Map** &nbsp; ℹ️ _Bubble = invoice, size = amount, color = risk_")
            fig = risk_bubble_chart(invoices, customers)
            fig.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

    with st.container(border=True):
        st.markdown("**Aging by Customer** &nbsp; ℹ️ _Stacked bars by aging bucket per customer_")
        fig = aging_bar_chart(aging)
        fig.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    # Cash Flow Forecast
    from charts.cashflow_charts import cashflow_forecast_chart
    forecast = data_service.get_cash_flow_forecast()
    with st.container(border=True):
        st.markdown("**Cash Flow Forecast** &nbsp; ℹ️ _Predicted inflow: yellow=expected, green=optimistic, red=conservative_")
        fig = cashflow_forecast_chart(forecast)
        fig.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)

    # ─── Manager Only: Analyst Profiles + Insights + Graph Generator ───
    if persona == MANAGER:
        st.divider()

        # ── Analyst Team Overview ──
        st.markdown("### 👥 Team — Analyst Profiles")

        perf = data_service.get_analyst_performance()
        all_invoices = data_service.get_invoices()

        for _, analyst in perf.iterrows():
            analyst_id = analyst["analyst"]
            analyst_inv = all_invoices[all_invoices["assigned_analyst"] == analyst_id]

            from config import USERS
            analyst_name = analyst_id
            for uname, udata in USERS.items():
                if udata.get("analyst_id") == analyst_id:
                    analyst_name = udata["name"]
                    break

            total_customers = analyst_inv["customer_id"].nunique()
            total_invoices = len(analyst_inv)
            total_overdue = analyst_inv["amount"].sum()
            critical = len(analyst_inv[analyst_inv["days_overdue"] > 90])
            high = len(analyst_inv[(analyst_inv["days_overdue"] > 60) & (analyst_inv["days_overdue"] <= 90)])
            avg_days = analyst_inv["days_overdue"].mean() if len(analyst_inv) > 0 else 0
            collection_rate = analyst["collection_rate"]
            follow_ups = analyst["follow_ups_this_week"]

            top_cust = analyst_inv.groupby("customer_name")["amount"].sum().sort_values(ascending=False)
            top_customer = top_cust.index[0] if len(top_cust) > 0 else "N/A"
            top_amount = top_cust.iloc[0] if len(top_cust) > 0 else 0

            with st.expander(f"📊 {analyst_name} ({analyst_id})", expanded=False):
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("🏢 Customers", total_customers)
                with col_b:
                    st.metric("📄 Invoices", total_invoices)
                with col_c:
                    st.metric("💰 Overdue Amount", f"₹{total_overdue:,.0f}")
                with col_d:
                    st.metric("📈 Collection Rate", f"{collection_rate}%")

                col_e, col_f, col_g, col_h = st.columns(4)
                with col_e:
                    st.metric("🔴 Critical", critical)
                with col_f:
                    st.metric("🟠 High", high)
                with col_g:
                    st.metric("📅 Avg Days Overdue", f"{avg_days:.0f}")
                with col_h:
                    st.metric("📞 Follow-ups/Week", follow_ups)

                st.markdown(f"**🏆 Top Overdue Customer:** {top_customer} — ₹{top_amount:,.0f}")

                analyst_aging = data_service.get_aging_summary(analyst_filter=analyst_id)
                if not analyst_aging.empty:
                    bucket_summary = analyst_aging.groupby("aging_bucket")["total_amount"].sum().reset_index()
                    fig = px.bar(
                        bucket_summary, x="aging_bucket", y="total_amount",
                        color="aging_bucket",
                        color_discrete_map={"0-30": "#2ECC71", "31-60": "#F1C40F", "61-90": "#E67E22", ">90": "#E74C3C"},
                        labels={"aging_bucket": "Aging Bucket", "total_amount": "Amount (₹)"},
                    )
                    fig.update_layout(
                        height=250, showlegend=False, margin=dict(t=20, b=30, l=40, r=20),
                        xaxis_title="", yaxis_title="Amount (₹)",
                        font=dict(family="DM Sans, sans-serif"),
                    )
                    fig.update_traces(
                        hovertemplate="<b>%{x}</b><br>Amount: ₹%{y:,.0f}<extra></extra>",
                        texttemplate="₹%{y:,.0f}", textposition="outside",
                    )
                    st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ── Manager Insights Charts ──
        st.markdown("### 📈 Manager Insights")
        from charts.kpi_charts import overdue_trend_chart, team_performance_chart, workload_distribution_chart

        trend = data_service.get_overdue_trends()
        with st.container(border=True):
            st.markdown("**Overdue Trend**")
            fig = overdue_trend_chart(trend)
            fig.update_layout(**CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)

        col_perf, col_work = st.columns([2, 1])
        with col_perf:
            with st.container(border=True):
                st.markdown("**Team Performance**")
                fig = team_performance_chart(perf)
                fig.update_layout(**CHART_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)
        with col_work:
            with st.container(border=True):
                st.markdown("**Workload Distribution**")
                fig = workload_distribution_chart(perf)
                fig.update_layout(**CHART_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        # ── Analyst Comparison Charts ──
        st.divider()
        st.markdown("### 📊 Analyst Comparison")

        col_comp1, col_comp2 = st.columns(2)

        with col_comp1:
            with st.container(border=True):
                st.markdown("**Overdue by Analyst & Aging**")
                fig_comp = go.Figure()
                for _, a in perf.iterrows():
                    a_inv = all_invoices[all_invoices["assigned_analyst"] == a["analyst"]]
                    critical_amt = a_inv[a_inv["days_overdue"] > 90]["amount"].sum()
                    high_amt = a_inv[(a_inv["days_overdue"] > 60) & (a_inv["days_overdue"] <= 90)]["amount"].sum()
                    medium_amt = a_inv[(a_inv["days_overdue"] > 30) & (a_inv["days_overdue"] <= 60)]["amount"].sum()
                    low_amt = a_inv[a_inv["days_overdue"] <= 30]["amount"].sum()
                    for bucket, amt, color in [
                        (">90d", critical_amt, "#E74C3C"), ("61-90d", high_amt, "#E67E22"),
                        ("31-60d", medium_amt, "#F1C40F"), ("0-30d", low_amt, "#2ECC71")
                    ]:
                        fig_comp.add_trace(go.Bar(
                            x=[a["analyst"]], y=[amt], name=bucket, marker_color=color,
                            hovertemplate=f"<b>{a['analyst']}</b><br>{bucket}: ₹%{{y:,.0f}}<extra></extra>",
                        ))
                fig_comp.update_layout(
                    barmode="stack", height=350,
                    yaxis_title="Amount (₹)", showlegend=True,
                    **CHART_LAYOUT,
                )
                st.plotly_chart(fig_comp, use_container_width=True)

        with col_comp2:
            with st.container(border=True):
                st.markdown("**Collection Efficiency**")
                fig_scatter = px.scatter(
                    perf, x="avg_days_overdue", y="collection_rate",
                    size="total_overdue_amount", color="analyst",
                    labels={"avg_days_overdue": "Avg Days Overdue", "collection_rate": "Collection Rate (%)", "analyst": "Analyst"},
                    color_discrete_map={"A101": EY_YELLOW, "A102": "#3498DB"},
                    size_max=50,
                )
                fig_scatter.update_layout(
                    height=350, **CHART_LAYOUT,
                )
                fig_scatter.update_traces(
                    hovertemplate="<b>%{customdata[0]}</b><br>Avg Days: %{x:.0f}<br>Rate: %{y:.1f}%<extra></extra>",
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

        st.divider()

        # ── Dynamic Graph Generator ──
        st.markdown("### 🛠️ Generate Custom Graph")
        st.caption("Build custom visualizations from your collections data")

        col_options, col_preview = st.columns([1, 2])

        with col_options:
            chart_type = st.selectbox("📈 Chart Type", [
                "Bar Chart", "Pie Chart", "Line Chart", "Scatter Plot", "Heatmap"
            ])

            metric_options = [
                "Outstanding Amount by Customer",
                "Invoice Count by Aging Bucket",
                "Overdue Amount by Analyst",
                "Customer Risk Distribution",
                "Payment Status Distribution",
                "Top 10 Overdue Customers",
                "Days Overdue Distribution",
                "Amount vs Days Overdue",
                "Industry-wise Overdue",
            ]
            selected_metric = st.selectbox("📊 Data Metric", metric_options)

            color_scheme = st.selectbox("🎨 Color Scheme", [
                "EY Brand", "Viridis", "Blues", "Reds", "Rainbow"
            ])

            show_values = st.checkbox("Show Values on Chart", value=True)

        with col_preview:
            fig = _generate_custom_chart(
                data_service, all_invoices, chart_type, selected_metric, color_scheme, show_values
            )
            if fig:
                st.plotly_chart(fig, use_container_width=True)


def _generate_custom_chart(data_service, invoices, chart_type, metric, color_scheme, show_values):
    """Generate dynamic charts based on user selection."""
    color_map = {
        "EY Brand": [EY_YELLOW, EY_DARK, "#7D7D8A", "#4B8BBE", "#E74C3C", "#2ECC71"],
        "Viridis": px.colors.sequential.Viridis,
        "Blues": px.colors.sequential.Blues,
        "Reds": px.colors.sequential.Reds,
        "Rainbow": px.colors.qualitative.Set1,
    }
    colors = color_map.get(color_scheme, color_map["EY Brand"])

    try:
        if metric == "Outstanding Amount by Customer":
            df = invoices.groupby("customer_name")["amount"].sum().sort_values(ascending=False).reset_index()
            if chart_type == "Bar Chart":
                fig = px.bar(df, x="customer_name", y="amount", color_discrete_sequence=colors,
                             text="amount" if show_values else None)
                if show_values:
                    fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            elif chart_type == "Pie Chart":
                fig = px.pie(df, names="customer_name", values="amount", color_discrete_sequence=colors)
            elif chart_type == "Line Chart":
                fig = px.line(df, x="customer_name", y="amount", markers=True, color_discrete_sequence=colors)
            else:
                fig = px.bar(df, x="customer_name", y="amount", color_discrete_sequence=colors)
            fig.update_layout(title="Outstanding Amount by Customer", xaxis_title="", yaxis_title="Amount (₹)")

        elif metric == "Invoice Count by Aging Bucket":
            df = invoices.copy()
            df["bucket"] = df["days_overdue"].apply(
                lambda d: "0-30" if d <= 30 else "31-60" if d <= 60 else "61-90" if d <= 90 else ">90"
            )
            bucket_df = df["bucket"].value_counts().reset_index()
            bucket_df.columns = ["bucket", "count"]
            if chart_type in ("Pie Chart",):
                fig = px.pie(bucket_df, names="bucket", values="count", color_discrete_sequence=colors)
            else:
                fig = px.bar(bucket_df, x="bucket", y="count", color="bucket",
                             color_discrete_map={"0-30": "#2ECC71", "31-60": "#F1C40F", "61-90": "#E67E22", ">90": "#E74C3C"},
                             text="count" if show_values else None)
                if show_values:
                    fig.update_traces(textposition="outside")
            fig.update_layout(title="Invoice Count by Aging Bucket", showlegend=True)

        elif metric == "Overdue Amount by Analyst":
            df = invoices.groupby("assigned_analyst")["amount"].sum().reset_index()
            if chart_type == "Pie Chart":
                fig = px.pie(df, names="assigned_analyst", values="amount", color_discrete_sequence=colors)
            else:
                fig = px.bar(df, x="assigned_analyst", y="amount", color="assigned_analyst",
                             color_discrete_sequence=colors,
                             text="amount" if show_values else None)
                if show_values:
                    fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(title="Overdue Amount by Analyst")

        elif metric == "Customer Risk Distribution":
            cust = data_service.get_customers()
            risk_df = cust["risk_level"].value_counts().reset_index()
            risk_df.columns = ["risk_level", "count"]
            color_map_risk = {"High": "#E74C3C", "Medium": "#E67E22", "Low": "#2ECC71"}
            if chart_type == "Pie Chart":
                fig = px.pie(risk_df, names="risk_level", values="count",
                             color="risk_level", color_discrete_map=color_map_risk)
            else:
                fig = px.bar(risk_df, x="risk_level", y="count", color="risk_level",
                             color_discrete_map=color_map_risk,
                             text="count" if show_values else None)
                if show_values:
                    fig.update_traces(textposition="outside")
            fig.update_layout(title="Customer Risk Distribution")

        elif metric == "Payment Status Distribution":
            status_df = invoices["status"].value_counts().reset_index()
            status_df.columns = ["status", "count"]
            if chart_type == "Pie Chart":
                fig = px.pie(status_df, names="status", values="count", color_discrete_sequence=colors)
            else:
                fig = px.bar(status_df, x="status", y="count", color_discrete_sequence=colors,
                             text="count" if show_values else None)
                if show_values:
                    fig.update_traces(textposition="outside")
            fig.update_layout(title="Payment Status Distribution")

        elif metric == "Top 10 Overdue Customers":
            df = invoices.groupby("customer_name").agg(
                total=("amount", "sum"), max_days=("days_overdue", "max")
            ).sort_values("total", ascending=True).tail(10).reset_index()
            fig = px.bar(df, y="customer_name", x="total", orientation="h", color="max_days",
                         color_continuous_scale="RdYlGn_r",
                         text="total" if show_values else None)
            if show_values:
                fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig.update_layout(title="Top 10 Overdue Customers", yaxis_title="", xaxis_title="Amount (₹)")

        elif metric == "Days Overdue Distribution":
            fig = px.histogram(invoices, x="days_overdue", nbins=20, color_discrete_sequence=[EY_YELLOW])
            fig.update_layout(title="Days Overdue Distribution", xaxis_title="Days Overdue", yaxis_title="Count")

        elif metric == "Amount vs Days Overdue":
            fig = px.scatter(invoices, x="days_overdue", y="amount", color="customer_name",
                             size="amount", hover_data=["invoice_id"],
                             color_discrete_sequence=colors)
            fig.update_layout(title="Amount vs Days Overdue", xaxis_title="Days Overdue", yaxis_title="Amount (₹)")

        elif metric == "Industry-wise Overdue":
            if "industry" in invoices.columns:
                df = invoices.groupby("industry")["amount"].sum().sort_values(ascending=False).reset_index()
                if chart_type == "Pie Chart":
                    fig = px.pie(df, names="industry", values="amount", color_discrete_sequence=colors)
                else:
                    fig = px.bar(df, x="industry", y="amount", color_discrete_sequence=colors,
                                 text="amount" if show_values else None)
                    if show_values:
                        fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
                fig.update_layout(title="Industry-wise Overdue")
            else:
                return None
        else:
            return None

        fig.update_layout(
            height=420,
            font=dict(family="DM Sans, sans-serif", size=13),
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02),
            margin=dict(t=50, b=40, l=50, r=120),
        )
        return fig

    except Exception:
        return None


render_dashboard()
