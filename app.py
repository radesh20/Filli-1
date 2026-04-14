"""
Filli - AI Collections Assistant for EY
Main entry point with login, dark/light mode, and role-based routing.
"""

import streamlit as st
import sys
import os
import base64
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ANALYST, MANAGER, USERS, EY_YELLOW, EY_DARK, EY_BG, EY_WHITE,
    DARK_BG, DARK_CARD, DARK_TEXT
)
from persistence import load_action_log, save_action_log, load_email_counter, save_email_counter

st.set_page_config(
    page_title="Filli — Collections Assistant | EY",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def _get_ey_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "EY-LOGO-800X800-768x768.gif")
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def get_theme():
    return st.session_state.get("theme", "dark")

def get_colors():
    if get_theme() == "dark":
        return {
            "bg": "#0a1628", "card": "#112240", "text": "#e6edf3",
            "sidebar_bg": "#0a1628", "accent": EY_YELLOW,
            "card_shadow": "rgba(0,0,0,0.5)", "metric_bg": "#112240",
            "text_muted": "#8b949e", "border": "rgba(255,255,255,0.08)",
            "hover_card": "#1a3358", "gradient_start": "#0a1628", "gradient_end": "#112240",
            "input_bg": "#0d1b30", "success": "#2ea043", "danger": "#f85149",
            "warning": "#d29922", "info": "#58a6ff",
        }
    return {
        "bg": "#f6f8fa", "card": "#ffffff", "text": "#1f2328",
        "sidebar_bg": EY_DARK, "accent": EY_YELLOW,
        "card_shadow": "rgba(0,0,0,0.06)", "metric_bg": "#ffffff",
        "text_muted": "#656d76", "border": "rgba(0,0,0,0.1)",
        "hover_card": "#f0f3f6", "gradient_start": "#ffffff", "gradient_end": "#f6f8fa",
        "input_bg": "#ffffff", "success": "#1a7f37", "danger": "#cf222e",
        "warning": "#9a6700", "info": "#0969da",
    }


def apply_theme():
    c = get_colors()
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

        /* === Global === */
        .stApp {{ background-color: {c['bg']}; font-family: 'DM Sans', -apple-system, sans-serif; }}
        [data-testid="stSidebar"] {{ background: linear-gradient(180deg, {c['sidebar_bg']} 0%, #1a1a2e 100%); }}
        [data-testid="stSidebar"] * {{ color: #e6edf3 !important; }}

        /* === Hide Streamlit default page nav === */
        [data-testid="stSidebarNav"] {{ display: none !important; }}
        section[data-testid="stSidebar"] > div > div:first-child > ul {{ display: none !important; }}
        header[data-testid="stHeader"] {{ display: none !important; }}
        p, span, div, label {{ font-family: 'DM Sans', -apple-system, sans-serif; color: {c['text']}; font-size: 15px; }}
        h1, h2, h3, h4, h5, h6 {{ font-family: 'DM Sans', -apple-system, sans-serif; color: {c['text']} !important; }}

        /* === Light mode input fix === */
        .stTextInput input, .stSelectbox select, .stTextArea textarea {{
            background-color: {c['input_bg']} !important;
            color: {c['text']} !important;
            border: 1px solid {c['border']} !important;
        }}
        .stTextInput input::placeholder {{ color: {c['text_muted']} !important; }}
        [data-testid="stTextInput"] input {{
            background-color: {c['input_bg']} !important;
            color: {c['text']} !important;
        }}
        [data-baseweb="input"] {{
            background-color: {c['input_bg']} !important;
        }}
        [data-baseweb="input"] input {{
            background-color: {c['input_bg']} !important;
            color: {c['text']} !important;
        }}
        [data-baseweb="base-input"] {{
            background-color: {c['input_bg']} !important;
        }}
        [data-baseweb="select"] {{
            background-color: {c['input_bg']} !important;
        }}
        .stSelectbox [data-baseweb="select"] > div {{
            background-color: {c['input_bg']} !important;
            color: {c['text']} !important;
        }}

        /* === Hero Header === */
        .hero-header {{
            background: linear-gradient(135deg, #2E2E38 0%, #1a1a2e 60%, #0d1117 100%);
            padding: 28px 36px; border-radius: 16px; margin-bottom: 28px;
            border: 1px solid rgba(255,230,0,0.15);
            position: relative; overflow: hidden;
        }}
        .hero-header::before {{
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
            background: linear-gradient(90deg, {EY_YELLOW}, #e6cf00, {EY_YELLOW});
        }}
        .hero-header h1 {{
            color: {EY_YELLOW} !important; margin: 0; font-size: 24px; font-weight: 700;
            letter-spacing: -0.5px;
        }}
        .hero-header p {{ color: #9ca3af !important; margin: 8px 0 0 0; font-size: 13px; }}

        /* === Metric Cards === */
        .stMetric {{
            background: {c['metric_bg']}; padding: 18px 20px;
            border-radius: 12px; box-shadow: 0 1px 3px {c['card_shadow']};
            border: 1px solid {c['border']};
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .stMetric:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px {c['card_shadow']};
            border-color: rgba(255,230,0,0.3);
        }}

        /* === Navigation Cards === */
        .nav-card {{
            background: {c['card']}; padding: 28px; border-radius: 14px;
            box-shadow: 0 2px 8px {c['card_shadow']}; min-height: 170px;
            border: 1px solid {c['border']};
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative; overflow: hidden;
        }}
        .nav-card::before {{
            content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
            background: {EY_YELLOW}; transition: width 0.3s ease;
        }}
        .nav-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 16px 40px {c['card_shadow']};
            border-color: rgba(255,230,0,0.25);
        }}
        .nav-card:hover::before {{ width: 6px; }}
        .nav-card h4 {{ color: {c['text']} !important; margin: 0 0 10px 0; font-size: 17px; font-weight: 600; }}
        .nav-card p {{ color: {c['text_muted']} !important; font-size: 13px; line-height: 1.6; }}
        .nav-card .nav-icon {{ font-size: 28px; margin-bottom: 12px; display: block; }}

        /* === Action Cards === */
        .action-card {{
            background: {c['card']}; padding: 18px 22px; border-radius: 12px;
            box-shadow: 0 1px 4px {c['card_shadow']}; margin-bottom: 10px;
            border: 1px solid {c['border']}; border-left: 5px solid #E74C3C;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .action-card:hover {{
            transform: translateX(6px);
            box-shadow: 0 6px 20px {c['card_shadow']};
        }}
        .action-card.upcoming {{ border-left-color: #E67E22; }}
        .action-card.low-urgency {{ border-left-color: #2ECC71; }}
        .action-card h5 {{ color: {c['text']} !important; margin: 0 0 6px 0; font-size: 15px; font-weight: 600; }}
        .action-card p {{ color: {c['text_muted']} !important; font-size: 13px; margin: 2px 0; }}

        /* === Section Header === */
        .section-header {{
            font-size: 19px; font-weight: 700; color: {c['text']} !important;
            margin: 12px 0 18px 0; padding-bottom: 10px;
            border-bottom: 3px solid {EY_YELLOW}; display: inline-block;
        }}

        /* === Buttons === */
        .stButton > button {{
            border-radius: 8px; font-weight: 600; font-size: 13px;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            letter-spacing: 0.3px; padding: 8px 20px;
        }}
        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }}

        /* === Toast === */
        .toast-notification {{
            position: fixed; top: 24px; right: 24px; z-index: 9999;
            color: white; padding: 18px 28px;
            border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: slideIn 0.5s cubic-bezier(0.4, 0, 0.2, 1), fadeOut 0.5s ease 4s forwards;
            font-size: 14px; max-width: 400px; font-weight: 500;
            backdrop-filter: blur(10px);
        }}
        @keyframes slideIn {{
            from {{ transform: translateX(120%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        @keyframes fadeOut {{ from {{ opacity: 1; }} to {{ opacity: 0; }} }}

        /* === Quick Stats === */
        .quick-stat {{
            background: {c['card']}; border-radius: 12px; padding: 16px 20px;
            border: 1px solid {c['border']}; text-align: center;
            transition: all 0.3s ease;
        }}
        .quick-stat:hover {{ transform: scale(1.02); box-shadow: 0 8px 24px {c['card_shadow']}; }}
        .quick-stat .stat-value {{ font-size: 28px; font-weight: 700; color: {c['text']}; }}
        .quick-stat .stat-label {{ font-size: 12px; color: {c['text_muted']}; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
    </style>
    """, unsafe_allow_html=True)


def chart_with_info(fig, info_title, info_text, key):
    """Render a Plotly chart with an info (i) popover button."""
    col_chart, col_info = st.columns([20, 1])
    with col_info:
        with st.popover("ℹ️", use_container_width=True):
            st.markdown(f"**{info_title}**")
            st.markdown(info_text)
    with col_chart:
        st.plotly_chart(fig, use_container_width=True, key=key)


def show_toast(message: str, toast_type: str = "success"):
    colors = {"success": "#059669", "warning": "#d97706", "error": "#dc2626", "info": "#2563eb"}
    bg = colors.get(toast_type, "#059669")
    st.markdown(f'<div class="toast-notification" style="background: {bg};">{message}</div>', unsafe_allow_html=True)


# ─── Login Page ───
def render_login():
    apply_theme()
    c = get_colors()

    # Hide sidebar on login, constrain width
    st.markdown(f"""
    <style>
        [data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="stMainBlockContainer"] {{
            max-width: 440px !important;
            margin: 0 auto !important;
        }}
        .theme-pill {{
            display: inline-block; padding: 6px 16px; border-radius: 20px;
            background: {c['card']}; border: 1px solid {c['border']};
            font-size: 13px; color: {c['text_muted']}; cursor: pointer;
            margin-top: 8px;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: center; margin-top: 60px;">
        <img src="data:image/gif;base64,{_get_ey_logo_b64()}"
             style="width: 80px; height: 80px; border-radius: 16px; margin-bottom: 12px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    border: 2px solid rgba(255,230,0,0.2);" alt="EY">
        <h1 style="color: {EY_YELLOW} !important; font-size: 44px; margin: 0; font-weight: 800; letter-spacing: 0.5px;">
            Filli
        </h1>
        <p style="color: {c['text_muted']}; font-size: 14px; margin-top: 6px; font-weight: 400;">
            AI-Powered Collections Assistant &nbsp;·&nbsp; EY Finance Operations
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: {c['card']}; padding: 28px 24px 8px 24px; border-radius: 14px;
         box-shadow: 0 4px 24px {c['card_shadow']};
         border: 1px solid {c['border']}; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 0; right: 0; height: 3px;
             background: linear-gradient(90deg, {EY_YELLOW}, #e6cf00, {EY_YELLOW});"></div>
        <h3 style="color: {c['text']} !important; text-align: center; margin-bottom: 2px; font-size: 18px; font-weight: 700;">
            Sign In
        </h3>
        <p style="color: {c['text_muted']}; text-align: center; font-size: 12px; margin-bottom: 16px;">
            Access the collections management portal
        </p>
    </div>
    """, unsafe_allow_html=True)

    username = st.text_input("Username", placeholder="Enter your username")
    password = st.text_input("Password", type="password", placeholder="Enter password")

    if st.button("Sign In", use_container_width=True, type="primary"):
        if username in USERS and USERS[username]["password"] == password:
            user = USERS[username]
            st.session_state.logged_in = True
            st.session_state.show_splash = True
            st.session_state.username = username
            st.session_state.user_name = user["name"]
            st.session_state.persona = user["role"]
            st.session_state.analyst_id = user["analyst_id"]
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.session_state.action_queue = []
            st.session_state.action_log = load_action_log()
            st.session_state.email_toast = None
            st.session_state.email_counter = load_email_counter()
            st.rerun()
        else:
            st.error("Invalid credentials. Please try again.")

    # Theme toggle — clean centered pill below the form
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    icon = "☀️ Light Mode" if get_theme() == "dark" else "🌙 Dark Mode"
    if st.button(icon, use_container_width=True):
        st.session_state.theme = "light" if get_theme() == "dark" else "dark"
        st.rerun()


# ─── Sidebar ───
def render_sidebar():
    """Delegate to shared sidebar."""
    from shared_sidebar import render_sidebar as _shared_render_sidebar
    _shared_render_sidebar()


# ─── Get upcoming actions ───
def get_upcoming_actions(data_service, analyst_filter):
    invoices = data_service.get_invoices(analyst_filter=analyst_filter)

    # Only show invoices that actually need action
    # Exclude: Closed, Paid, Written Off, Settled (case-insensitive)
    exclude_statuses = {"closed", "paid", "written off", "settled"}
    actions = []
    for _, inv in invoices.iterrows():
        status = str(inv.get("status", inv.get("invoice_status", "Open")))
        if status.strip().lower() in exclude_statuses:
            continue
        outstanding = inv.get("outstanding_amount", inv.get("amount", 0))
        if outstanding <= 0:
            continue

        days = inv.get("days_overdue", 0)
        if days > 90:
            urgency, label, icon = "critical", "🔴 CRITICAL — Escalation needed", "🚨"
        elif days > 60:
            urgency, label, icon = "high", "🟠 HIGH — Immediate follow-up", "⚠️"
        elif days > 30:
            urgency, label, icon = "medium", "🟡 MEDIUM — Send reminder", "📧"
        elif days > 7:
            urgency, label, icon = "low", "🟢 DUE SOON — Proactive reminder", "📋"
        else:
            continue
        actions.append({
            "invoice_id": inv.get("invoice_id", "N/A"),
            "customer_name": inv.get("customer_name", "Unknown"),
            "customer_id": inv.get("customer_id", ""),
            "amount": outstanding,
            "days_overdue": days,
            "status": status,
            "industry": inv.get("industry", ""),
            "urgency": urgency, "label": label, "icon": icon,
        })
    actions.sort(key=lambda x: x["days_overdue"], reverse=True)
    return actions


# ─── Splash Screen ───
def render_splash():
    """EY splash screen — completely standalone, nothing else renders."""
    c = get_colors()
    logo_b64 = _get_ey_logo_b64()
    user_name = st.session_state.get("user_name", "")
    bg = c['bg']
    muted = c['text_muted']
    text = c['text']

    # Inject one single HTML block — CSS + splash + auto-redirect JS
    splash_html = (
        '<style>'
        '  [data-testid="stSidebar"] { display: none !important; }'
        '  [data-testid="stSidebarNav"] { display: none !important; }'
        '  header[data-testid="stHeader"] { display: none !important; }'
        '  button[data-testid="stSidebarCollapsedControl"] { display: none !important; }'
        '  [data-testid="stMainBlockContainer"] { max-width: 100% !important; padding: 0 !important; margin: 0 !important; }'
        '  @keyframes logoIn { 0% { transform: scale(0.3) rotate(-10deg); opacity: 0; } 50% { transform: scale(1.1) rotate(2deg); opacity: 1; } 100% { transform: scale(1) rotate(0deg); opacity: 1; } }'
        '  @keyframes textIn { 0% { opacity: 0; transform: translateY(30px); letter-spacing: 20px; } 100% { opacity: 1; transform: translateY(0); letter-spacing: -2px; } }'
        '  @keyframes subtitleIn { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }'
        '  @keyframes lineGrow { 0% { width: 0; } 100% { width: 120px; } }'
        '  .splash-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;'
        '    background: ' + bg + '; z-index: 99999;'
        '    display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }'
        '  .splash-logo { width: 110px; height: 110px; border-radius: 22px;'
        '    box-shadow: 0 16px 48px rgba(255,230,0,0.25); border: 2px solid rgba(255,230,0,0.3);'
        '    animation: logoIn 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; }'
        '  .splash-title { color: #FFE600; font-size: 72px; font-weight: 800;'
        '    margin: 24px 0 0 0; opacity: 0; font-family: "DM Sans", sans-serif;'
        '    animation: textIn 0.7s cubic-bezier(0.16, 1, 0.3, 1) 0.4s forwards; }'
        '  .splash-line { height: 3px; background: linear-gradient(90deg, transparent, #FFE600, transparent);'
        '    margin: 14px auto; animation: lineGrow 0.6s ease 0.8s forwards; width: 0; }'
        '  .splash-subtitle { color: ' + muted + '; font-size: 17px; font-weight: 400; opacity: 0;'
        '    font-family: "DM Sans", sans-serif; animation: subtitleIn 0.5s ease 1s forwards; }'
        '  .splash-welcome { color: ' + text + '; font-size: 20px; font-weight: 500; opacity: 0;'
        '    font-family: "DM Sans", sans-serif; animation: subtitleIn 0.5s ease 1.3s forwards; margin-top: 28px; }'
        '</style>'
        '<div class="splash-overlay">'
        '  <img src="data:image/gif;base64,' + logo_b64 + '" class="splash-logo" alt="EY">'
        '  <div class="splash-title">Filli</div>'
        '  <div class="splash-line"></div>'
        '  <div class="splash-subtitle">AI-Powered Collections Assistant</div>'
        '  <div class="splash-welcome">Welcome, ' + user_name + '</div>'
        '</div>'
    )
    st.markdown(splash_html, unsafe_allow_html=True)

    # Hidden button — JS will auto-click it after 3 seconds
    if st.button("Continue", key="splash_continue"):
        st.session_state.show_splash = False
        st.rerun()

    # Hide the button and auto-click via st.components
    st.markdown("""
    <style>
        div[data-testid="stButton"] { position: fixed; top: -9999px; }
    </style>
    """, unsafe_allow_html=True)

    import streamlit.components.v1 as components
    components.html("""
    <script>
        setTimeout(function() {
            const btns = window.parent.document.querySelectorAll('button');
            for (let b of btns) {
                if (b.innerText.includes('Continue')) { b.click(); break; }
            }
        }, 3200);
    </script>
    """, height=0)


# ─── Main App ───
def render_main_app():
    apply_theme()
    render_sidebar()

    if st.session_state.get("email_toast"):
        show_toast(st.session_state.email_toast, "success")
        st.session_state.email_toast = None

    # Load persisted data if not already in session
    if "action_log" not in st.session_state:
        st.session_state.action_log = load_action_log()
    if "email_counter" not in st.session_state:
        st.session_state.email_counter = load_email_counter()

    if "data_service" not in st.session_state:
        from data.bigquery_client import DataService
        st.session_state.data_service = DataService()

    data_service = st.session_state.data_service
    persona = st.session_state.persona
    analyst_filter = st.session_state.analyst_id
    c = get_colors()

    # Hero Header
    st.markdown(f"""
    <div class="hero-header" style="display: flex; align-items: center; gap: 24px;">
        <img src="data:image/gif;base64,{_get_ey_logo_b64()}"
             style="width: 52px; height: 52px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" alt="EY">
        <div>
            <h1 style="color: {EY_YELLOW} !important;">⚡ Filli — AI Collections Assistant</h1>
            <p>Welcome back, {st.session_state.user_name} · {persona} · Accounts Receivable</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI Cards
    summary = data_service.get_overdue_summary(analyst_filter=analyst_filter)

    if persona == ANALYST:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 My Overdue", f"₹{summary['total_overdue_amount']:,.0f}")
        with col2:
            st.metric("📄 My Invoices", summary["total_overdue_invoices"])
        with col3:
            st.metric("🔴 Critical (>90d)", summary["critical_count"])
        with col4:
            st.metric("🟠 High (61-90d)", summary["high_count"])
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Total Overdue", f"₹{summary['total_overdue_amount']:,.0f}")
        with col2:
            st.metric("📄 Total Invoices", summary["total_overdue_invoices"])
        with col3:
            pct = round(summary["critical_count"] / max(summary["total_overdue_invoices"], 1) * 100, 1)
            st.metric("🔴 Critical %", f"{pct}%")
        with col4:
            high_risk = data_service.get_customers(risk_level="High")
            st.metric("⚠️ High-Risk", len(high_risk))

    st.divider()

    if persona == ANALYST:
        _render_analyst_home(data_service, analyst_filter, c)
    else:
        _render_manager_home(data_service, c)


def _render_analyst_home(data_service, analyst_filter, c):
    """Analyst home: action items with email/call buttons + portfolio health."""

    # ── Manager Remarks (live, no re-login needed) ──
    from persistence import get_remarks_for_analyst, mark_remarks_read
    remarks = get_remarks_for_analyst(analyst_filter)
    unread = [r for r in remarks if not r.get("read")]
    if unread:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1a2a3e 0%, #16213e 100%);
             border: 1px solid rgba(52,152,219,0.3); border-left: 4px solid #3498DB;
             border-radius: 10px; padding: 16px 20px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 600; color: #3498DB;
                 text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                📋 Manager Remarks ({len(unread)} new)
            </div>
        </div>
        """, unsafe_allow_html=True)
        for r in reversed(unread[:3]):
            st.info(f"**{r['manager']}** ({r['timestamp'][:16]}):\n> {r['remark']}")
        col_mark, col_view, _ = st.columns([1, 1, 3])
        with col_mark:
            if st.button("✅ Mark read", key="home_mark_read", use_container_width=True):
                mark_remarks_read(analyst_filter)
                st.rerun()
        with col_view:
            if st.button("💬 View all in Filli", key="home_view_remarks", use_container_width=True):
                st.switch_page("pages/2_Assistant.py")

    st.markdown('<div class="section-header">📌 What\'s Next — Actions Required</div>', unsafe_allow_html=True)

    actions = get_upcoming_actions(data_service, analyst_filter)

    if not actions:
        st.success("✅ All caught up! No immediate actions required.")
    else:
        # Counts
        critical_count = len([a for a in actions if a["urgency"] == "critical"])
        high_count = len([a for a in actions if a["urgency"] == "high"])
        medium_count = len([a for a in actions if a["urgency"] == "medium"])
        low_count = len([a for a in actions if a["urgency"] == "low"])
        total_action_amt = sum(a["amount"] for a in actions)

        # Filter buttons
        col_all, col_crit, col_high, col_med, col_low, col_val = st.columns(6)
        with col_all:
            if st.button(f"All ({len(actions)})", key="filter_all", use_container_width=True):
                st.session_state.action_filter = "all"
        with col_crit:
            if st.button(f"🚨 Critical ({critical_count})", key="filter_critical", use_container_width=True):
                st.session_state.action_filter = "critical"
        with col_high:
            if st.button(f"⚠️ High ({high_count})", key="filter_high", use_container_width=True):
                st.session_state.action_filter = "high"
        with col_med:
            if st.button(f"📧 Medium ({medium_count})", key="filter_medium", use_container_width=True):
                st.session_state.action_filter = "medium"
        with col_low:
            if st.button(f"📋 Low ({low_count})", key="filter_low", use_container_width=True):
                st.session_state.action_filter = "low"
        with col_val:
            st.metric("💰 Action Value", f"₹{total_action_amt:,.0f}")

        # Apply filter
        active_filter = st.session_state.get("action_filter", "all")
        if active_filter != "all":
            filtered_actions = [a for a in actions if a["urgency"] == active_filter]
        else:
            filtered_actions = actions

        if not filtered_actions:
            st.info(f"No {active_filter} priority actions.")
        else:
            st.caption(f"Showing: **{active_filter.upper() if active_filter != 'all' else 'ALL'}** — {len(filtered_actions)} items")

            from persistence import (load_action_log, get_customer_action_history,
                                     is_escalated, add_escalation, add_remark)
            action_log = load_action_log()

            for i, action in enumerate(filtered_actions[:15]):
                days = action["days_overdue"]
                cust_name = action["customer_name"]
                invoice_id = action["invoice_id"]

                # Get real history for this customer
                emails_sent, calls_made = get_customer_action_history(action_log, cust_name)

                # Count broken promises
                broken_promises = 0
                try:
                    promises = data_service.get_promises(broken_only=True, analyst_filter=analyst_filter)
                    if not promises.empty:
                        broken_promises = len(promises[promises["customer_name"] == cust_name])
                except Exception:
                    pass

                already_escalated = is_escalated(invoice_id)

                # Smart recommended action logic
                # Escalate only when: enough follow-ups done AND still unresolved
                escalation_ready = (
                    not already_escalated
                    and days > 60
                    and (
                        (emails_sent >= 2 and calls_made >= 1)
                        or (broken_promises >= 2)
                        or (emails_sent >= 3)
                        or (calls_made >= 2 and emails_sent >= 1)
                    )
                )

                if already_escalated:
                    rec_label, rec_icon = "Escalated", "✅"
                    rec_reason = "Already escalated to manager — awaiting resolution"
                elif escalation_ready:
                    rec_label, rec_icon = "Escalate", "🚨"
                    rec_reason = f"Escalation ready — {emails_sent} emails, {calls_made} calls, {broken_promises} broken promises"
                elif days > 60 and calls_made == 0 and emails_sent >= 1:
                    # Sent emails but never called — next step is call
                    rec_label, rec_icon = "Call", "📞"
                    rec_reason = f"{emails_sent} email(s) sent, no calls yet — call recommended"
                elif days > 60 and emails_sent == 0:
                    # Never contacted — start with email
                    rec_label, rec_icon = "Email", "📧"
                    rec_reason = f"No contact made yet — send first reminder"
                elif days > 60:
                    # Has done some emails and calls but not enough to escalate
                    rec_label, rec_icon = "Call", "📞"
                    rec_reason = f"{emails_sent} emails, {calls_made} calls — follow up again before escalation"
                elif days > 30:
                    rec_label, rec_icon = "Email", "📧"
                    rec_reason = "Medium — send payment reminder"
                else:
                    rec_label, rec_icon = "Email", "📧"
                    rec_reason = "Low — gentle reminder"

                # History tag for the card
                history_tag = f" · 📧×{emails_sent} 📞×{calls_made}"
                if broken_promises > 0:
                    history_tag += f" ❌×{broken_promises} broken PTP"

                col_info, col_rec, col_other = st.columns([5, 1.2, 1])
                with col_info:
                    uc = "upcoming" if action["urgency"] == "medium" else "low-urgency" if action["urgency"] == "low" else ""
                    industry_tag = f' · 🏢 {action["industry"]}' if action.get("industry") else ""
                    status_tag = f' · 📌 {action["status"]}' if action.get("status") else ""
                    st.markdown(f"""
                    <div class="action-card {uc}">
                        <h5>{action['icon']} {cust_name} — {invoice_id}</h5>
                        <p>₹{action['amount']:,.0f} · {days} days overdue{history_tag}{industry_tag}{status_tag}</p>
                        <p style="font-size: 11px; color: #6e7681; margin-top: 2px;">{action['label']}</p>
                        <p style="font-size: 10px; color: #FFE600; margin-top: 2px;">⚡ {rec_reason}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_rec:
                    st.write("")
                    if already_escalated:
                        st.button(f"{rec_icon} {rec_label}", key=f"home_rec_{i}", use_container_width=True, disabled=True)
                    elif rec_label == "Escalate":
                        if st.button(f"{rec_icon} {rec_label}", key=f"home_rec_{i}", use_container_width=True, type="primary"):
                            _handle_escalation(action, data_service, analyst_filter,
                                               emails_sent, calls_made, broken_promises)
                    elif rec_label == "Call":
                        if st.button(f"{rec_icon} {rec_label}", key=f"home_rec_{i}", use_container_width=True, type="primary"):
                            _initiate_proactive_call(action, data_service)
                    else:
                        if st.button(f"{rec_icon} {rec_label}", key=f"home_rec_{i}", use_container_width=True, type="primary"):
                            _send_proactive_email(action, data_service)
                with col_other:
                    # Show the opposite action — if recommended is Email, show Call and vice versa
                    st.write("")
                    if rec_label in ("Email", "Escalated"):
                        if st.button("📞 Call", key=f"home_call_{i}", use_container_width=True):
                            _initiate_proactive_call(action, data_service)
                    else:
                        if st.button("📧 Email", key=f"home_email_{i}", use_container_width=True):
                            _send_proactive_email(action, data_service)

        if critical_count > 0 or high_count > 0:
            st.warning(
                f"⚡ **{critical_count} critical** and **{high_count} high-priority** invoices need attention. "
                f"Use the buttons above or ask Filli in the AI Assistant."
            )

    # Analyst portfolio health
    st.divider()
    st.markdown('<div class="section-header">📈 Portfolio Health</div>', unsafe_allow_html=True)

    # Row 1: Aging donut + Risk bar (2 columns)
    col_a, col_b = st.columns(2)
    with col_a:
        from charts.aging_charts import aging_donut_chart
        aging = data_service.get_aging_summary(analyst_filter=analyst_filter)
        if not aging.empty:
            chart_with_info(
                aging_donut_chart(aging),
                "Overdue by Aging Bucket",
                "Shows how overdue receivables are distributed across aging buckets (0-30, 31-60, 61-90, >90 days). "
                "Larger slices indicate higher concentration of overdue amounts in that period. "
                "Focus on reducing the >90 day bucket first.",
                key="aging_donut_home"
            )
    with col_b:
        from charts.risk_charts import risk_distribution_bar
        customers = data_service.get_customers(analyst_filter=analyst_filter)
        chart_with_info(
            risk_distribution_bar(customers),
            "Customers by Risk Level",
            "Shows customer count by risk category (High, Medium, Low). "
            "Risk is calculated from payment history, days overdue, and outstanding amounts. "
            "High-risk customers need immediate collection attention.",
            key="risk_bar_home"
        )

    # Row 2: Cash flow forecast (full width)
    from charts.cashflow_charts import cashflow_forecast_chart
    forecast = data_service.get_cash_flow_forecast()
    chart_with_info(
        cashflow_forecast_chart(forecast),
        "Predicted Cash Inflow",
        "Forecasts expected cash collections over the next 6 weeks. "
        "Yellow line = expected inflow, green dashed = optimistic, red dashed = conservative. "
        "The shaded band shows the confidence range. Use this to plan cash flow.",
        key="cashflow_home"
    )


def _render_manager_home(data_service, c):
    """Manager home: strategic overview based on the document —
    - Monitor overall overdue balances and collection trends
    - Review aging buckets and risk exposure across customer portfolios
    - Identify high-risk or chronically delinquent accounts
    - Review escalated cases and unresolved issues
    - Evaluate team performance and workload distribution
    """
    from charts.aging_charts import aging_donut_chart
    from charts.kpi_charts import overdue_trend_chart, team_performance_chart, workload_distribution_chart
    from charts.cashflow_charts import cashflow_forecast_chart

    # ── 0. Analyst Escalations (live) ──
    from persistence import load_remarks, get_escalations
    escalation_remarks = [r for r in load_remarks() if r.get("type") == "escalation" and not r.get("read")]
    open_escalations = get_escalations(status="open")

    if escalation_remarks or open_escalations:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #2a1a1a 0%, #1a1a2e 100%);
             border: 1px solid rgba(231,76,60,0.3); border-left: 4px solid #E74C3C;
             border-radius: 10px; padding: 16px 20px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 600; color: #E74C3C;
                 text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">
                🚨 Analyst Escalations ({len(open_escalations)} open)
            </div>
        </div>
        """, unsafe_allow_html=True)

        for esc in open_escalations[-5:]:
            st.error(
                f"**{esc['customer_name']}** — Invoice {esc['invoice_id']} "
                f"(₹{esc['amount']:,.0f}, {esc['days_overdue']}d overdue)\n\n"
                f"Escalated by **{esc['analyst']}** · "
                f"📧 {esc['emails_sent']} emails · 📞 {esc['calls_made']} calls · "
                f"❌ {esc['broken_promises']} broken PTP · "
                f"_{esc['timestamp'][:16]}_"
            )

        # Mark escalation remarks as read
        if escalation_remarks:
            from persistence import save_remarks
            all_remarks = load_remarks()
            for r in all_remarks:
                if r.get("type") == "escalation":
                    r["read"] = True
            save_remarks(all_remarks)

        st.divider()

    # ── 1. Overdue Trends & Aging Overview ──
    st.markdown('<div class="section-header">📈 Overdue Trends & Aging Overview</div>', unsafe_allow_html=True)

    col_trend, col_aging = st.columns(2)
    with col_trend:
        trend = data_service.get_overdue_trends()
        chart_with_info(
            overdue_trend_chart(trend),
            "Overdue Balance Trend",
            "Tracks total overdue balance week-over-week over 12 weeks. "
            "Upward trend = growing risk. Downward = improving collections. "
            "Use this to assess whether collection efforts are working.",
            key="trend_mgr"
        )
    with col_aging:
        aging = data_service.get_aging_summary()
        if not aging.empty:
            chart_with_info(
                aging_donut_chart(aging),
                "Overdue by Aging Bucket",
                "Distribution of overdue receivables across aging buckets (0-30, 31-60, 61-90, >90 days). "
                "Larger slices in >90 days indicate severe collection delays requiring escalation.",
                key="aging_mgr"
            )

    st.divider()

    # ── 2. High-Risk & Escalation Accounts ──
    st.markdown('<div class="section-header">🚨 Accounts Requiring Escalation</div>', unsafe_allow_html=True)
    st.caption("Accounts stuck in higher aging buckets despite repeated follow-ups — requires management intervention")

    priority = data_service.get_priority_invoices(top_n=20)
    critical = priority[priority["priority"] == "Critical"]

    if len(critical) > 0:
        summary = data_service.get_overdue_summary()
        pct_critical = round(summary["critical_amount"] / max(summary["total_overdue_amount"], 1) * 100, 1)
        col_esc1, col_esc2, col_esc3 = st.columns(3)
        with col_esc1:
            st.metric("🔴 Critical Accounts", len(critical))
        with col_esc2:
            st.metric("💰 Critical Exposure", f"₹{summary['critical_amount']:,.0f}")
        with col_esc3:
            st.metric("📊 % of Total Overdue", f"{pct_critical}%")

        for _, row in critical.head(5).iterrows():
            risk = row.get("risk_level", "N/A")
            risk_color = "#E74C3C" if risk == "High" else "#E67E22" if risk == "Medium" else "#2ECC71"
            st.markdown(f"""
            <div class="action-card" style="border-left-color: {risk_color};">
                <h5>🚨 {row['customer_name']} — {row['invoice_id']}</h5>
                <p>₹{row['amount']:,.0f} · {row['days_overdue']} days overdue · Risk: <strong style="color:{risk_color}">{risk}</strong> · Score: {row['priority_score']:.0f}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No critical escalations at this time.")

    st.divider()

    # ── 3. Team Performance & Workload ──
    st.markdown('<div class="section-header">👥 Team Performance & Workload</div>', unsafe_allow_html=True)
    st.caption("Evaluate collections team performance and workload distribution across analysts")

    perf = data_service.get_analyst_performance()

    # Analyst summary cards
    from config import USERS
    cols = st.columns(len(perf))
    for idx, (_, analyst) in enumerate(perf.iterrows()):
        analyst_id = analyst["analyst"]
        analyst_name = analyst_id
        for uname, udata in USERS.items():
            if udata.get("analyst_id") == analyst_id:
                analyst_name = udata["name"]
                break

        rate_color = "#2ECC71" if analyst["collection_rate"] >= 70 else "#E67E22" if analyst["collection_rate"] >= 50 else "#E74C3C"

        with cols[idx]:
            st.markdown(f"""
            <div style="background: {c.get('card', '#161b22')}; padding: 20px; border-radius: 12px;
                 border: 1px solid {c.get('border', 'rgba(255,255,255,0.08)')};
                 border-top: 4px solid {EY_YELLOW}; text-align: center;">
                <div style="font-size: 15px; font-weight: 700; color: {c.get('text', '#e6edf3')}; margin-bottom: 4px;">
                    👤 {analyst_name}
                </div>
                <div style="font-size: 11px; color: {c.get('text_muted', '#8b949e')}; margin-bottom: 14px;">{analyst_id}</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Accounts</span>
                    <span style="font-size: 13px; font-weight: 600; color: {c.get('text', '#e6edf3')};">{analyst['total_accounts']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Invoices</span>
                    <span style="font-size: 13px; font-weight: 600; color: {c.get('text', '#e6edf3')};">{analyst['total_invoices']}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Overdue</span>
                    <span style="font-size: 13px; font-weight: 600; color: {c.get('text', '#e6edf3')};">₹{analyst['total_overdue_amount']:,.0f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Avg Days</span>
                    <span style="font-size: 13px; font-weight: 600; color: {c.get('text', '#e6edf3')};">{analyst['avg_days_overdue']:.0f}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Collection Rate</span>
                    <span style="font-size: 14px; font-weight: 700; color: {rate_color};">{analyst['collection_rate']}%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 12px; color: {c.get('text_muted', '#8b949e')};">Follow-ups/wk</span>
                    <span style="font-size: 13px; font-weight: 600; color: {c.get('text', '#e6edf3')};">{analyst['follow_ups_this_week']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Team charts
    col_perf, col_work = st.columns([2, 1])
    with col_perf:
        chart_with_info(
            team_performance_chart(perf),
            "Team Performance",
            "Compares analysts by overdue amount (yellow bars) and collection rate (red line). "
            "Higher bars = more exposure. Higher red line = better efficiency. "
            "Use this to identify underperformers and rebalance workload.",
            key="team_perf_mgr"
        )
    with col_work:
        chart_with_info(
            workload_distribution_chart(perf),
            "Workload Distribution",
            "Shows how invoices are split across analysts. "
            "Balanced distribution prevents burnout. Large slices = overloaded analyst.",
            key="workload_mgr"
        )

    st.divider()

    # ── 4. Risk Exposure & Cash Flow ──
    st.markdown('<div class="section-header">💰 Risk Exposure & Cash Flow Forecast</div>', unsafe_allow_html=True)
    st.caption("Monitor risk concentration and predicted cash inflow across the portfolio")

    col_risk, col_cash = st.columns(2)
    with col_risk:
        from charts.risk_charts import risk_bubble_chart
        invoices = data_service.get_invoices()
        customers = data_service.get_customers()
        chart_with_info(
            risk_bubble_chart(invoices, customers),
            "Invoice Risk Map",
            "Each bubble = one invoice. X-axis = days overdue, Y-axis = amount. "
            "Size = invoice value. Color: red = high risk, yellow = medium, green = low. "
            "Top-right corner = most critical invoices.",
            key="risk_bubble_mgr"
        )
    with col_cash:
        forecast = data_service.get_cash_flow_forecast()
        chart_with_info(
            cashflow_forecast_chart(forecast),
            "Cash Flow Forecast",
            "Predicts cash collections over the next 6 weeks. "
            "Yellow = expected, green dashed = optimistic, red dashed = conservative. "
            "Shaded area = confidence range.",
            key="cashflow_mgr"
        )

    # Key risk customers
    st.markdown("**🏢 Top Risk Contributors**")
    high_risk_custs = data_service.get_customers(risk_level="High")
    if not high_risk_custs.empty and "total_outstanding" in high_risk_custs.columns:
        for _, cust in high_risk_custs.head(5).iterrows():
            st.markdown(f"""
            <div class="action-card" style="border-left-color: #E74C3C;">
                <h5>⚠️ {cust['customer_name']}</h5>
                <p>Outstanding: ₹{cust.get('total_outstanding', 0):,.0f} · {cust.get('invoice_count', 0)} invoices · Max {cust.get('max_days_overdue', 0):.0f} days overdue</p>
            </div>
            """, unsafe_allow_html=True)
    elif not high_risk_custs.empty:
        for _, cust in high_risk_custs.head(5).iterrows():
            st.markdown(f"- **{cust['customer_name']}** — Risk: {cust['risk_level']}")


def _get_email_count(customer_id):
    """Get the number of emails sent to a customer."""
    counter = st.session_state.get("email_counter", {})
    return counter.get(customer_id, 0)


def _increment_email_count(customer_id):
    """Increment email counter for a customer and persist."""
    if "email_counter" not in st.session_state:
        st.session_state.email_counter = load_email_counter()
    st.session_state.email_counter[customer_id] = st.session_state.email_counter.get(customer_id, 0) + 1
    save_email_counter(st.session_state.email_counter)
    return st.session_state.email_counter[customer_id]


def _send_proactive_email(action, data_service):
    from actions.email_sender import send_collection_email
    customers = data_service.get_customers()
    cust = customers[customers["customer_id"] == action["customer_id"]]
    email = cust.iloc[0]["email"] if len(cust) > 0 else "faaalguniii10@gmail.com"
    result = send_collection_email(
        customer_email=email, customer_name=action["customer_name"],
        invoice_id=action["invoice_id"], amount=action["amount"], days_overdue=action["days_overdue"],
    )
    if "action_log" not in st.session_state:
        st.session_state.action_log = load_action_log()
    st.session_state.action_log.append({
        "type": "email", "customer": action["customer_name"],
        "invoice_id": action["invoice_id"], "amount": action["amount"],
        "email": email, "result": result["status"], "timestamp": datetime.now().isoformat(),
    })
    save_action_log(st.session_state.action_log)

    # Track email count per customer
    count = _increment_email_count(action["customer_id"])

    if result["status"] == "success":
        st.session_state.email_toast = f"✅ Email sent to {action['customer_name']} ({email})"
    else:
        st.session_state.email_toast = f"📧 Reminder queued for {action['customer_name']}"

    # After 2 emails, queue a call prompt in the assistant chat
    if count >= 2:
        if "messages" not in st.session_state:
            st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"📞 **Call Recommended:** {count} reminder emails have been sent to **{action['customer_name']}** with no response. "
                       f"I recommend initiating an AI call for Invoice {action['invoice_id']} (Rs.{action['amount']:,.0f}).\n\n"
                       f"Go to **Filli Assistant** to confirm the call."
        })
        st.session_state.action_queue = st.session_state.get("action_queue", [])
        st.session_state.action_queue.append({
            "action": "initiate_call",
            "customer_id": action["customer_id"],
            "invoice_id": action["invoice_id"],
        })
    st.rerun()


def _handle_escalation(action, data_service, analyst_filter, emails_sent, calls_made, broken_promises):
    """Escalate an invoice: persist escalation, send remark to all managers."""
    from persistence import add_escalation, add_remark
    from config import USERS

    analyst_name = st.session_state.get("user_name", "Analyst")
    analyst_id = st.session_state.get("analyst_id", analyst_filter)

    # Save escalation
    add_escalation(
        analyst_name=analyst_name,
        analyst_id=analyst_id,
        customer_name=action["customer_name"],
        customer_id=action["customer_id"],
        invoice_id=action["invoice_id"],
        amount=action["amount"],
        days_overdue=action["days_overdue"],
        emails_sent=emails_sent,
        calls_made=calls_made,
        broken_promises=broken_promises,
    )

    # ── 1. Store escalation remark so manager sees it on their dashboard ──
    from persistence import load_remarks, save_remarks
    from datetime import datetime as _dt

    remark_text = (
        f"🚨 ESCALATION from {analyst_name}: {action['customer_name']} — Invoice {action['invoice_id']} "
        f"(₹{action['amount']:,.0f}, {action['days_overdue']}d overdue). "
        f"Follow-up done: {emails_sent} emails, {calls_made} calls, {broken_promises} broken PTP. "
        f"Requesting management intervention."
    )

    remarks = load_remarks()
    remarks.append({
        "manager": "ALL_MANAGERS",
        "analyst_id": "ESCALATION",
        "analyst_name": analyst_name,
        "remark": remark_text,
        "timestamp": _dt.now().isoformat(),
        "read": False,
        "type": "escalation",
        "invoice_id": action["invoice_id"],
        "customer_name": action["customer_name"],
    })
    save_remarks(remarks)

    # ── 2. Send a real escalation email to all managers ──
    from actions.email_sender import send_escalation_email
    for uname, udata in USERS.items():
        if udata["role"] == "Collections Manager":
            send_escalation_email(
                manager_name=udata["name"],
                analyst_name=analyst_name,
                customer_name=action["customer_name"],
                invoice_id=action["invoice_id"],
                amount=action["amount"],
                days_overdue=action["days_overdue"],
                emails_sent=emails_sent,
                calls_made=calls_made,
                broken_promises=broken_promises,
            )

    # ── 3. Notify the analyst ──
    st.session_state.email_toast = f"🚨 Escalation sent — managers notified via email & dashboard"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"🚨 **Escalation Submitted**\n\n"
                   f"**Customer:** {action['customer_name']}\n"
                   f"**Invoice:** {action['invoice_id']} — ₹{action['amount']:,.0f}\n"
                   f"**Days Overdue:** {action['days_overdue']}\n"
                   f"**Follow-up History:** {emails_sent} emails, {calls_made} calls, {broken_promises} broken PTP\n\n"
                   f"**What happens now:**\n"
                   f"1. Your managers have been emailed with full details\n"
                   f"2. This appears as a red alert on their dashboard\n"
                   f"3. Manager will review and decide on: credit hold, legal notice, direct negotiation, or settlement plan\n\n"
                   f"You don't need to follow up further on this invoice until the manager responds."
    })
    st.rerun()


def _initiate_proactive_call(action, data_service):
    """Queue a call action for the assistant page."""
    st.session_state.action_queue = st.session_state.get("action_queue", [])
    st.session_state.action_queue.append({
        "action": "initiate_call",
        "customer_id": action["customer_id"],
        "invoice_id": action["invoice_id"],
    })
    st.session_state.email_toast = f"📞 Call queued for {action['customer_name']} — Go to AI Assistant to confirm"
    st.rerun()


# ─── Router ───
if st.session_state.get("logged_in") and st.session_state.get("show_splash"):
    render_splash()
elif st.session_state.get("logged_in"):
    render_main_app()
else:
    render_login()
