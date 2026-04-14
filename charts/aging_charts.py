"""Aging distribution charts — vibrant, interactive, with explanations."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config import EY_YELLOW, EY_DARK

def _title_color():
    return "#e6edf3" if st.session_state.get("dark_mode", True) else EY_DARK

AGING_COLORS = ["#2ECC71", "#FFE600", "#FF9F43", "#EE5A24"]
BUCKET_ORDER = ["0-30", "31-60", "61-90", ">90"]


def aging_donut_chart(aging_df):
    """Donut chart showing overdue distribution across aging buckets."""
    bucket_summary = aging_df.groupby("aging_bucket").agg(
        total_amount=("total_amount", "sum"),
        invoice_count=("invoice_count", "sum"),
    ).reset_index()

    bucket_summary["aging_bucket"] = bucket_summary["aging_bucket"].astype("category")
    bucket_summary["aging_bucket"] = bucket_summary["aging_bucket"].cat.set_categories(BUCKET_ORDER, ordered=True)
    bucket_summary = bucket_summary.sort_values("aging_bucket")

    fig = go.Figure(data=[go.Pie(
        labels=bucket_summary["aging_bucket"],
        values=bucket_summary["total_amount"],
        hole=0.55,
        marker_colors=AGING_COLORS,
        textinfo="percent",
        textposition="inside",
        textfont_size=11,
        textfont_color="white",
        pull=[0, 0, 0.03, 0.06],
        hovertemplate="<b>%{label} days</b><br>Amount: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>",
    )])

    fig.update_layout(
        title=dict(text="Overdue by Aging Bucket", font=dict(size=14, color=_title_color())),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        height=400,
        margin=dict(t=50, b=50, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uniformtext_minsize=8, uniformtext_mode="hide",
        annotations=[dict(text="<b>Aging</b>", x=0.5, y=0.5, font_size=13, showarrow=False, font_color=_title_color())],
    )
    return fig


def aging_bar_chart(aging_df, top_n=10):
    """Horizontal stacked bar chart showing aging by customer."""
    cust_totals = aging_df.groupby("customer_name")["total_amount"].sum().nlargest(top_n)
    top_customers = cust_totals.index.tolist()
    filtered = aging_df[aging_df["customer_name"].isin(top_customers)]

    color_map = {"0-30": "#2ECC71", "31-60": "#FFE600", "61-90": "#FF9F43", ">90": "#EE5A24"}

    fig = go.Figure()
    for bucket in BUCKET_ORDER:
        bucket_data = filtered[filtered["aging_bucket"] == bucket]
        fig.add_trace(go.Bar(
            y=bucket_data["customer_name"],
            x=bucket_data["total_amount"],
            name=f"{bucket} days",
            orientation="h",
            marker_color=color_map[bucket],
            marker_line=dict(width=0.5, color="rgba(255,255,255,0.3)"),
            hovertemplate="<b>%{y}</b><br>Bucket: " + bucket + " days<br>Amount: ₹%{x:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=f"Top {top_n} Customers — Aging Breakdown", font=dict(size=16, color=_title_color())),
        barmode="stack",
        xaxis_title="Amount (₹)",
        yaxis=dict(autorange="reversed"),
        height=420,
        margin=dict(t=60, b=50, l=150, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
    )
    return fig


def render_chart_with_info(chart_func, data, info_text, key_suffix=""):
    """Render a chart with an info (i) button that shows explanation."""
    col_chart, col_info = st.columns([20, 1])
    with col_info:
        with st.popover("ℹ️"):
            st.markdown(info_text)
    with col_chart:
        fig = chart_func(data) if not isinstance(data, tuple) else chart_func(*data)
        st.plotly_chart(fig, use_container_width=True)
