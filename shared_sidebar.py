"""Shared sidebar — Streamlit native sidebar styled to auto-hide and show on hover."""

import streamlit as st
import base64
import os
from datetime import datetime
from config import EY_YELLOW, EY_DARK, ANALYST


@st.cache_data
def _get_ey_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "EY-LOGO-800X800-768x768.gif")
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_sidebar():
    """Native Streamlit sidebar with CSS hover-to-reveal behavior."""
    if not st.session_state.get("logged_in"):
        return

    user = st.session_state
    role_icon = "📊" if user.persona == ANALYST else "👔"
    portfolio_line = f'<div style="font-size: 10px; color: #6e7681; margin-top: 2px;">📁 {user.analyst_id}</div>' if user.analyst_id else ''
    logo_b64 = _get_ey_logo_b64()

    # CSS: force sidebar visible, make it hover-reveal
    st.markdown("""
    <style>
        /* Hide default page nav and header */
        [data-testid="stSidebarNav"] { display: none !important; }
        section[data-testid="stSidebar"] > div > div:first-child > ul { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }

        /* Force sidebar to exist and style it */
        [data-testid="stSidebar"] {
            display: flex !important;
            background: linear-gradient(180deg, #2E2E38 0%, #1a1a2e 50%, #0d1117 100%) !important;
            min-width: 230px !important;
            max-width: 230px !important;
            position: fixed !important;
            left: 0; top: 0;
            height: 100vh !important;
            z-index: 99990 !important;
            transform: translateX(-218px);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: none;
        }
        [data-testid="stSidebar"]:hover {
            transform: translateX(0) !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.5) !important;
        }
        [data-testid="stSidebar"] * {
            color: #e6edf3 !important;
            font-family: 'DM Sans', -apple-system, sans-serif !important;
        }

        /* Hide the collapse button */
        button[data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="stSidebarCollapseButton"] { display: none !important; }
        button[kind="headerNoPadding"] { display: none !important; }

        /* Tab handle visible on edge */
        [data-testid="stSidebar"]::after {
            content: '\\2630';
            position: absolute; top: 50%; right: -20px;
            transform: translateY(-50%);
            background: #2E2E38; color: #FFE600;
            padding: 14px 5px; border-radius: 0 8px 8px 0;
            font-size: 14px; cursor: pointer;
            box-shadow: 4px 0 12px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,230,0,0.15);
            border-left: none;
            z-index: 99991;
        }

        /* Page link styling */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a {
            padding: 9px 12px !important;
            border-radius: 8px !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
            margin: 2px 0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: rgba(255,230,0,0.1) !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink"] a p {
            font-size: 13px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(
            '<div style="text-align: center; padding: 12px 0 16px 0;">'
            '<img src="data:image/gif;base64,' + logo_b64 + '" '
            'style="width: 48px; height: 48px; border-radius: 10px; '
            'border: 1.5px solid rgba(255,230,0,0.15);" alt="EY">'
            '<h3 style="color: #FFE600 !important; margin: 8px 0 0 0; font-size: 18px; font-weight: 700;">Filli</h3>'
            '<p style="color: #8b949e !important; font-size: 10px; margin: 2px 0 0 0;">AI Collections Assistant</p>'
            '</div>',
            unsafe_allow_html=True
        )

        st.divider()

        st.markdown(
            '<div style="padding: 10px; background: rgba(255,230,0,0.06); border-radius: 8px; '
            'border-left: 3px solid #FFE600; margin-bottom: 8px;">'
            '<div style="font-size: 13px; font-weight: 600;">' + role_icon + ' ' + user.user_name + '</div>'
            '<div style="font-size: 11px; color: #8b949e !important; margin-top: 2px;">' + user.persona + '</div>'
            + portfolio_line +
            '</div>',
            unsafe_allow_html=True
        )

        st.divider()

        st.page_link("app.py", label="🏠 Home", use_container_width=True)
        st.page_link("pages/1_Dashboard.py", label="📊 Dashboard", use_container_width=True)
        st.page_link("pages/2_Assistant.py", label="🤖 Filli Assistant", use_container_width=True)
        st.page_link("pages/4_Invoices.py", label="📄 Invoices", use_container_width=True)
        st.page_link("pages/3_Actions.py", label="📋 Action Log", use_container_width=True)

        st.divider()

        if st.button("🚪 Sign Out", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.markdown(
            '<div style="font-size: 9px; color: #484f58 !important; text-align: center; margin-top: 16px;">'
            'Built for EY · ' + datetime.now().strftime('%Y') + '</div>',
            unsafe_allow_html=True
        )


def render_back_home_buttons():
    """Render back and home buttons at the top of every sub-page."""
    col_back, col_home, col_space = st.columns([1, 1, 8])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.markdown('<script>window.history.back();</script>', unsafe_allow_html=True)
            st.rerun()
    with col_home:
        st.page_link("app.py", label="🏠 Home", use_container_width=True)
