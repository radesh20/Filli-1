# Filli — AI Collections Assistant

Filli is an AI-powered Accounts Receivable (AR) Collections Assistant built for EY Finance Operations. It helps collections analysts and managers prioritize overdue invoice follow-ups, send reminder emails, initiate AI voice calls, track promise-to-pay commitments, and forecast cash inflow.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration — What You Need to Change](#configuration--what-you-need-to-change)
- [Running the App](#running-the-app)
- [Project Structure](#project-structure)
- [Demo Credentials](#demo-credentials)
- [Documentation](#documentation)

---

## Features

| Feature | Description |
|---------|-------------|
| **Role-Based Login** | Analyst (sees own portfolio) vs Manager (sees all + team analytics) |
| **Dashboard** | Aging donut, risk bubble map, cash flow forecast, overdue trends, team performance charts |
| **AI Chat (Filli Assistant)** | Natural language queries: priority ranking, DSO, CEI, aging analysis, customer lookup |
| **Invoice Management** | Browse invoices grouped by customer with filters (aging, status, risk). Action buttons per invoice |
| **Email Reminders** | Real EY-branded HTML emails sent via Gmail SMTP with urgency-coded headers |
| **AI Voice Calls** | Automated phone calls via Bland.ai with live transcripts and promise-to-pay extraction |
| **Auto-Escalation** | After 2 failed emails, system suggests AI call. After failed call, suggests manager escalation |
| **Action Log** | Full audit trail: emails sent, call transcripts, outcomes, promise-to-pay tracking |
| **Manager Remarks** | Manager can post remarks to analysts, shown as alerts with AI-suggested actions |
| **Priority Scoring** | Weighted formula: aging (25-100) + broken promises (30) + customer risk (20) + value (15) |
| **Insight Generator** | Auto root-cause analysis and recommended next steps appended to every AI response |
| **Custom Graph Generator** | Manager can build ad-hoc charts: pick chart type, metric, color scheme |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit >= 1.32.0 | Multi-page web app, session management, chat UI |
| Charts | Plotly >= 5.18.0 | Interactive donut, bar, scatter, line charts |
| Data | Pandas >= 2.1.0 | DataFrame operations, filtering, aggregation |
| AI Chat | Custom keyword engine | Intent detection, response building, insight generation |
| LLM Fallback | Google Gemini 2.0 Flash | For complex queries the keyword engine can't handle |
| Tool Calling | Anthropic SDK >= 0.25.0 | Function-calling schema definitions |
| Primary Data | Vertex AI Agent Builder | Discovery Engine API for natural language invoice search |
| Database | Google BigQuery >= 3.17.0 | AR collections dataset (invoices, customers) |
| Fallback Data | Mock Data (Pandas) | 25 Indian companies, ~100 invoices, aging, promises |
| Email | Gmail SMTP SSL | Real email delivery with EY-branded HTML templates |
| Voice Calls | Bland.ai REST API | AI phone calls with live transcripts |
| Serverless | GCP Cloud Run | Backup email delivery endpoint |
| Auth | Google ADC | Service account for BigQuery + Vertex AI |

---

## Prerequisites

- Python 3.10+
- A Google Cloud Platform project (for Vertex AI and BigQuery — optional, app works with mock data)
- A Gmail account with an App Password (for sending emails)
- A Bland.ai API key (for AI voice calls — optional, app works without it)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Falgunisharma72/Filli.git
cd Filli

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration — What You Need to Change

### 1. Gmail Credentials (Required for email feature)

File: `actions/email_sender.py`

```python
GMAIL_USER = "your-email@gmail.com"          # Your Gmail address
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password (not your regular password)
```

**How to get a Gmail App Password:**
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### 2. Bland.ai API Key (Required for voice calls)

File: `actions/voice_caller.py`

```python
BLAND_API_KEY = "your_bland_api_key_here"
DEFAULT_PHONE = "+91XXXXXXXXXX"  # Default phone for testing
```

Sign up at https://bland.ai to get an API key.

### 3. Google Cloud (Optional — app works with mock data)

File: `config.py`

```python
BQ_PROJECT = "your-gcp-project-id"
BQ_DATASET = "your-bigquery-dataset"
```

File: `data/vertex_agent.py`

```python
PROJECT_NUM = "your-project-number"
PROJECT_ID = "your-project-id"
ENGINE_ID = "your-discovery-engine-id"
DATA_STORE_ID = "your-datastore-id"
```

If GCP is not configured, the app automatically falls back to mock data — no changes needed to run locally.

### 4. Users and Personas

File: `config.py`

```python
USERS = {
    "username": {
        "password": "password",
        "role": ANALYST,  # or MANAGER
        "name": "Display Name",
        "analyst_id": "A101",  # None for managers
    },
}
```

Add, remove, or modify users as needed.

### 5. Priority Scoring Weights

File: `config.py`

```python
PRIORITY_SCORES = {"critical": 100, "high": 75, "medium": 50, "low": 25}
BROKEN_PROMISE_UPLIFT = 30
HIGH_RISK_UPLIFT = 20
VALUE_WEIGHT = 15
```

Adjust weights to change how invoices are prioritized.

### 6. Customer Email for Testing

File: `data/mock_data.py`

All mock customers have `email` set to a test address. Change this to your email to receive test reminder emails:

```python
"email": "your-test-email@gmail.com"
```

---

## Running the App

```bash
# Start the app
streamlit run app.py

# Or specify a port
streamlit run app.py --server.port 8502

# For headless mode (no browser auto-open)
streamlit run app.py --server.port 8502 --server.headless true
```

The app will be available at `http://localhost:8501` (or your specified port).

---

## Project Structure

```
Filli/
|-- app.py                      # Main entry point, login, home page, theme
|-- config.py                   # EY colors, thresholds, weights, users, personas
|-- shared_sidebar.py           # Sidebar navigation, role display, sign out
|-- persistence.py              # JSON read/write: action logs, remarks, escalations
|-- requirements.txt            # Python dependencies
|
|-- pages/
|   |-- 1_Dashboard.py          # Charts, KPIs, manager analytics, graph generator
|   |-- 2_Assistant.py          # AI chat UI, proactive alerts, action confirmations
|   |-- 3_Actions.py            # Action log + call transcripts
|   |-- 4_Invoices.py           # Invoice browse, filters, customer grouping
|
|-- assistant/
|   |-- chat_engine.py          # Intent detection, response builder, insight generator
|   |-- prompts.py              # Analyst + Manager system prompts
|   |-- tools.py                # Function-calling tool schemas + execution router
|
|-- charts/
|   |-- aging_charts.py         # Aging donut + stacked bar charts
|   |-- risk_charts.py          # Risk bubble chart + distribution bar
|   |-- cashflow_charts.py      # Cash flow forecast with confidence bands
|   |-- kpi_charts.py           # Overdue trend, team performance, workload donut
|
|-- data/
|   |-- mock_data.py            # 25 companies, invoices, aging, promises, trends
|   |-- bigquery_client.py      # DataService class + Vertex AI connector
|   |-- vertex_agent.py         # Vertex AI Agent Builder Discovery Engine client
|
|-- actions/
|   |-- email_sender.py         # Gmail SMTP: reminder + escalation emails
|   |-- voice_caller.py         # Bland.ai: initiate call, poll status, parse PTP
|
|-- assets/                     # EY logo files (gif, png, svg)
|-- docs/                       # SRS/SDS architecture document
|-- data/*.json                 # Persisted action logs, counters, remarks
```

---

## Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Collections Analyst | `falguni.sharma` | `analyst123` |
| Collections Analyst | `arjun.singh` | `analyst123` |
| Collections Manager | `deepa.menon` | `manager123` |
| Collections Manager | `vikram.singh` | `manager123` |

---

## Documentation

The `docs/` folder contains the full SRS/SDS document:

- **Filli_SRS_SDS_Document.docx** — System architecture (4-layer diagram, data flow, user workflow flowchart), complete tech stack table, and feature-by-feature coverage with implementation details for all 11 features.

---

## Notes

- The app works fully with mock data out of the box — no GCP setup needed for a demo
- Email sending requires valid Gmail credentials with an App Password
- Voice calls require a Bland.ai API key and credits
- All action logs are stored as JSON files in the `data/` directory
- The app is designed for the Indian market: INR currency, Indian company names, Indian phone formats
