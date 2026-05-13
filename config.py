"""Centralized configuration for Filli with Azure services."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

EY_YELLOW = "#FFE600"
EY_DARK = "#2E2E38"
EY_GRAY = "#7D7D8A"
EY_LIGHT_GRAY = "#C4C4CD"
EY_BG = "#F6F6FA"
EY_WHITE = "#FFFFFF"
DARK_BG = "#1a1a2e"
DARK_CARD = "#16213e"
DARK_TEXT = "#e0e0e0"
CHART_COLORS = [EY_YELLOW, EY_DARK, EY_GRAY, "#4B8BBE", "#E74C3C", "#2ECC71", "#9B59B6"]

AGING_CRITICAL = 90
AGING_HIGH = 60
AGING_MEDIUM = 30

PRIORITY_SCORES = {"critical": 100, "high": 75, "medium": 50, "low": 25}
BROKEN_PROMISE_UPLIFT = 30
HIGH_RISK_UPLIFT = 20
VALUE_WEIGHT = 15

ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
ACS_PHONE_NUMBER = os.getenv("ACS_PHONE_NUMBER", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
AZURE_EMAIL_SENDER = os.getenv("AZURE_EMAIL_SENDER", "")
CALLBACK_BASE_URL = os.getenv("CALLBACK_BASE_URL", "http://localhost:8000")
LEADS_JSON_PATH = os.getenv("LEADS_JSON_PATH", "data/mock_data.json")
AGENT_NAME = os.getenv("AGENT_NAME", "Aria")
COMPANY_NAME = os.getenv("COMPANY_NAME", "EY Finance")
ARIA_COMPANY_NAME = os.getenv("ARIA_COMPANY_NAME", "EY Finance")
ARIA_VOICE = os.getenv("ARIA_VOICE", "en-US-AriaNeural")

ANALYST = "Collections Analyst"
MANAGER = "Collections Manager"
DEMO_ANALYST = "A101"

USERS = {
    "falguni.sharma": {"password": "analyst123", "role": ANALYST, "name": "Falguni Sharma (FS)", "analyst_id": "A101"},
    "arjun.singh": {"password": "analyst123", "role": ANALYST, "name": "Arjun Singh (AS)", "analyst_id": "A102"},
    "deepa.menon": {"password": "manager123", "role": MANAGER, "name": "Deepa Menon", "analyst_id": None},
    "vikram.singh": {"password": "manager123", "role": MANAGER, "name": "Vikram Singh", "analyst_id": None},
}
