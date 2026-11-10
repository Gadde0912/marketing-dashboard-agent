# Marketing Dashboard Monitoring Agent POC

A Streamlit prototype for marketing KPI monitoring using synthetic data. It includes interactive filters, KPI cards, trend charts, channel performance, a simple ROAS monitoring rule, and a placeholder chat panel.

**All data is synthetic. Do not upload client or confidential data to a public repository.**

## Run locally

```bash
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\activate
```

Install dependencies:
```bash
python -m pip install -r requirements.txt
```

Run:
```bash
streamlit run dashboard/app.py
```

## Deploy from GitHub

1. Push this repository to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Select **Create app** and choose this GitHub repository.
4. Set the main file path to `dashboard/app.py`.
5. Deploy.

## Planned next phase

- Load curated data from Databricks SQL.
- Create a Databricks Genie Space over approved tables.
- Add a secure backend for Genie Conversation API calls.
- Pass selected dashboard filters to the backend as query context.
- Add scheduled KPI checks and alert delivery.

Never place Databricks tokens, passwords, or client credentials in source code or GitHub.
