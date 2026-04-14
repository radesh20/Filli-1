"""Cash flow forecast charts — vibrant with confidence bands."""

import plotly.graph_objects as go
import streamlit as st
from config import EY_YELLOW, EY_DARK

def _title_color():
    return "#e6edf3" if st.session_state.get("dark_mode", True) else EY_DARK


def cashflow_forecast_chart(forecast_df):
    """Line chart with confidence bands for predicted cash inflow."""
    fig = go.Figure()

    # Confidence band
    fig.add_trace(go.Scatter(
        x=forecast_df["week"], y=forecast_df["optimistic"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df["week"], y=forecast_df["conservative"],
        mode="lines", line=dict(width=0), showlegend=False,
        fill="tonexty", fillcolor="rgba(255, 230, 0, 0.12)", hoverinfo="skip",
    ))

    # Expected line
    fig.add_trace(go.Scatter(
        x=forecast_df["week"], y=forecast_df["expected_inflow"],
        mode="lines+markers", name="Expected Inflow",
        line=dict(color=EY_YELLOW, width=3),
        marker=dict(size=7, color=EY_YELLOW, line=dict(width=1.5, color=EY_DARK)),
        hovertemplate="<b>Week: %{x}</b><br>Expected: ₹%{y:,.0f}<extra></extra>",
    ))

    # Optimistic
    fig.add_trace(go.Scatter(
        x=forecast_df["week"], y=forecast_df["optimistic"],
        mode="lines", name="Optimistic",
        line=dict(color="#2ECC71", width=1.5, dash="dash"),
    ))

    # Conservative
    fig.add_trace(go.Scatter(
        x=forecast_df["week"], y=forecast_df["conservative"],
        mode="lines", name="Conservative",
        line=dict(color="#EE5A24", width=1.5, dash="dash"),
    ))

    fig.update_layout(
        title=dict(text="Predicted Cash Inflow — Next 6 Weeks", font=dict(size=14, color=_title_color())),
        xaxis_title="Week", yaxis_title="Amount (₹)",
        height=400,
        margin=dict(t=50, b=60, l=60, r=20),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10), tickangle=-45),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
    )
    return fig
