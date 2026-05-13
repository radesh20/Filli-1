# Filli (Azure + JSON Edition)

Filli is a Streamlit AI-powered AR Collections Assistant for EY Finance Operations with Analyst/Manager views, portfolio dashboards, chat assistant, reminder actions, and action logs.

## Migration summary
- Bland.ai voice calling replaced with Azure Communication Services Call Automation.
- Gemini/Anthropic replaced with Azure OpenAI (`gpt-4o` deployment).
- Gmail SMTP replaced with Azure Communication Services Email.
- BigQuery/Vertex removed and replaced by local JSON mock data (`data/mock_data.json`).

## Prerequisites
- Python 3.10+
- Azure Communication Services resource and PSTN number
- Azure OpenAI resource + deployed `gpt-4o`
- Azure Speech resource
- ngrok (for callback URL testing)

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```
2. Copy `.env.example` to `.env` and fill all Azure values.
3. Start Streamlit app:
```bash
streamlit run app.py
```

## New React + FastAPI app
Backend:
```bash
uvicorn backend.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Azure configuration notes
1. ACS: create communication resource, copy connection string, purchase/assign a phone number.
2. Azure OpenAI: deploy `gpt-4o`, set endpoint/key/deployment name.
3. Speech: create speech resource and set key/region.
4. ACS Email: configure sender domain and set `AZURE_EMAIL_SENDER`.
5. ngrok: expose callback host and set `CALLBACK_BASE_URL` to public URL.

## Data model
- Main data source: `data/mock_data.json`
- Includes 25 companies and 110 invoices, plus promises, trends, and analyst KPIs.
- Persistence files remain local JSON under `data/`:
  - `action_log.json`
  - `email_counter.json`
  - `manager_remarks.json`
  - `escalations.json`
  - `ptp_tracking.json`

## Run checks
- Confirm `.env` values
- Launch Streamlit
- Use Analyst login flow in `app.py`
- Trigger email and call from Assistant page
- Review outcomes in Action Log page
