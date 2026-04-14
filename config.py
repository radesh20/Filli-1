"""Centralized configuration for the Collections Assistant PoC."""

# EY Branding Colors
EY_YELLOW = "#FFE600"
EY_DARK = "#2E2E38"
EY_GRAY = "#7D7D8A"
EY_LIGHT_GRAY = "#C4C4CD"
EY_BG = "#F6F6FA"
EY_WHITE = "#FFFFFF"

# Dark mode colors
DARK_BG = "#1a1a2e"
DARK_CARD = "#16213e"
DARK_TEXT = "#e0e0e0"

# Chart color palette
CHART_COLORS = [EY_YELLOW, EY_DARK, EY_GRAY, "#4B8BBE", "#E74C3C", "#2ECC71", "#9B59B6"]

# Aging bucket thresholds
AGING_CRITICAL = 90
AGING_HIGH = 60
AGING_MEDIUM = 30

# Priority scoring weights
PRIORITY_SCORES = {
    "critical": 100,
    "high": 75,
    "medium": 50,
    "low": 25,
}
BROKEN_PROMISE_UPLIFT = 30
HIGH_RISK_UPLIFT = 20
VALUE_WEIGHT = 15

# BigQuery settings
BQ_PROJECT = "project-899e2ec5-c891-4b57-9bb"
BQ_DATASET = "ar_collections"

# Email endpoint
EMAIL_ENDPOINT = "https://send-collection-email-972191003940.us-central1.run.app"

# Gemini model (free tier) - fallback chain
GEMINI_MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]

# Personas
ANALYST = "Collections Analyst"
MANAGER = "Collections Manager"

# Demo analyst assignment
DEMO_ANALYST = "A101"

# Predefined users (analyst_ids match BigQuery: A101=FS, A102=AS)
USERS = {
    "falguni.sharma": {"password": "analyst123", "role": ANALYST, "name": "Falguni Sharma (FS)", "analyst_id": "A101"},
    "arjun.singh": {"password": "analyst123", "role": ANALYST, "name": "Arjun Singh (AS)", "analyst_id": "A102"},
    "deepa.menon": {"password": "manager123", "role": MANAGER, "name": "Deepa Menon", "analyst_id": None},
    "vikram.singh": {"password": "manager123", "role": MANAGER, "name": "Vikram Singh", "analyst_id": None},
}
