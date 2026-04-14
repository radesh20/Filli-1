"""KPI and manager-level charts — vibrant and interactive."""

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from config import EY_YELLOW, EY_DARK

def _title_color():
    return "#e6edf3" if st.session_state.get("dark_mode", True) else EY_DARK


def overdue_trend_chart(trend_df):
    """Line chart showing overdue balance trend over 12 weeks."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=trend_df["week"], y=trend_df["total_overdue"],
        mode="lines+markers",
        line=dict(color=EY_YELLOW, width=3),
        marker=dict(size=6, color=EY_YELLOW, line=dict(color=EY_DARK, width=1.5)),
        fill="tozeroy", fillcolor="rgba(255, 230, 0, 0.08)",
        hovertemplate="<b>%{x}</b><br>Overdue: ₹%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Overdue Balance Trend (12 Weeks)", font=dict(size=14, color=_title_color())),
        xaxis_title="Week", yaxis_title="Total Overdue (₹)",
        height=380,
        margin=dict(t=50, b=60, l=60, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=9), tickangle=-45),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=10)),
    )
    return fig


def team_performance_chart(perf_df):
    """Grouped bar chart for analyst performance."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=perf_df["analyst"], y=perf_df["total_overdue_amount"],
        name="Overdue Amount (₹)",
        marker_color=EY_YELLOW,
        marker_line=dict(width=1, color="rgba(255,255,255,0.3)"),
        yaxis="y",
    ))

    fig.add_trace(go.Scatter(
        x=perf_df["analyst"], y=perf_df["collection_rate"],
        name="Collection Rate (%)",
        mode="lines+markers+text",
        text=[f"{v}%" for v in perf_df["collection_rate"]],
        textposition="top center", textfont=dict(size=10, color="#EE5A24"),
        line=dict(color="#EE5A24", width=3),
        marker=dict(size=8, color="#EE5A24", line=dict(width=1.5, color="white")),
        yaxis="y2",
    ))

    fig.update_layout(
        title=dict(text="Team Performance Overview", font=dict(size=14, color=_title_color())),
        yaxis=dict(title="Overdue Amount (₹)", side="left", gridcolor="rgba(128,128,128,0.15)"),
        yaxis2=dict(title="Collection Rate (%)", overlaying="y", side="right", range=[0, 120]),
        height=420,
        margin=dict(t=50, b=60, l=60, r=60),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def workload_distribution_chart(perf_df):
    """Donut chart showing workload distribution across analysts."""
    colors = [EY_YELLOW, "#FF9F43", "#3498DB", "#2ECC71", "#9B59B6"]

    fig = go.Figure(data=[go.Pie(
        labels=perf_df["analyst"],
        values=perf_df["total_invoices"],
        hole=0.5,
        marker_colors=colors[:len(perf_df)],
        textinfo="percent",
        textposition="inside",
        textfont=dict(size=10, color="white"),
        pull=[0.02] * len(perf_df),
        hovertemplate="<b>%{label}</b><br>Invoices: %{value}<br>Share: %{percent}<extra></extra>",
    )])

    fig.update_layout(
        title=dict(text="Workload Distribution", font=dict(size=14, color=_title_color())),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font=dict(size=10)),
        height=380,
        margin=dict(t=50, b=50, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uniformtext_minsize=8, uniformtext_mode="hide",
        annotations=[dict(text="<b>Load</b>", x=0.5, y=0.5, font_size=13, showarrow=False, font_color=_title_color())],
    )
    return fig
