"""Risk analysis charts — vibrant and interactive."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from config import EY_YELLOW, EY_DARK

def _title_color():
    return "#e6edf3" if st.session_state.get("dark_mode", True) else EY_DARK


def risk_bubble_chart(invoices_df, customers_df):
    """Bubble chart: X=days overdue, Y=amount, color=risk level."""
    merged = invoices_df.merge(
        customers_df[["customer_id", "risk_level"]], on="customer_id", how="left"
    )
    if "risk_level" not in merged.columns:
        merged["risk_level"] = "Medium"

    colors = {"High": "#EE5A24", "Medium": "#FFE600", "Low": "#2ECC71"}

    fig = px.scatter(
        merged, x="days_overdue", y="amount",
        color="risk_level", size="amount",
        hover_data=["invoice_id", "customer_name", "status"],
        color_discrete_map=colors,
        labels={"days_overdue": "Days Overdue", "amount": "Amount (₹)", "risk_level": "Risk Level"},
    )

    fig.update_traces(marker=dict(line=dict(width=1, color="rgba(255,255,255,0.4)")))

    fig.update_layout(
        title=dict(text="Invoice Risk Map", font=dict(size=14, color=_title_color())),
        height=400,
        margin=dict(t=50, b=60, l=60, r=20),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
    )
    return fig


def risk_distribution_bar(customers_df):
    """Bar chart showing customer count by risk level."""
    if "risk_level" not in customers_df.columns:
        return go.Figure()

    risk_counts = customers_df["risk_level"].value_counts().reset_index()
    risk_counts.columns = ["risk_level", "count"]

    colors = {"High": "#EE5A24", "Medium": "#FFE600", "Low": "#2ECC71"}

    fig = px.bar(
        risk_counts, x="risk_level", y="count",
        color="risk_level", color_discrete_map=colors,
        labels={"risk_level": "Risk Level", "count": "Customer Count"},
        text="count",
    )
    fig.update_layout(
        title=dict(text="Customers by Risk Level", font=dict(size=14, color=_title_color())),
        showlegend=False,
        height=380,
        margin=dict(t=50, b=40, l=50, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
    )
    fig.update_traces(textposition="inside", textfont_size=11, marker_line=dict(width=1, color="rgba(255,255,255,0.3)"))
    return fig
