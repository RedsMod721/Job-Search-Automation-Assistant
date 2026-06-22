# Stage 2 Setup and Diagnostics

Date: 2026-06-17

## Recommended Setup

```powershell
uv sync --group dev
uv run streamlit run app.py
```

If the default uv cache or environment is blocked on Windows:

```powershell
$env:UV_CACHE_DIR='.tmp/uv-cache'
$env:UV_PROJECT_ENVIRONMENT='.tmp/stage2-uv-venv'
uv sync --group dev
uv run streamlit run app.py
```

## Pip Fallback

Runtime:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Development:

```powershell
pip install -r requirements-dev.txt
python -m pytest
```

## Diagnostics

Human-readable:

```powershell
uv run python scripts/diagnostics.py
```

JSON:

```powershell
uv run python scripts/diagnostics.py --json
```

The Settings page also shows the diagnostics summary and full JSON details.

## Local Google Sheets Setup

Use ignored local config:

```yaml
google_sheets:
  enabled: true
  spreadsheet_id: "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
  worksheet_name: "Applications"
  credentials_path: "config/google_service_account.json"
```

The service-account credentials file remains:

```text
config/google_service_account.json
```

This file is ignored by Git.

## Local Network Setup

Use ignored local config for corporate network settings:

```yaml
network:
  verify_tls: true
  custom_ca_bundle: "config/corporate-ca.pem"
  http_proxy: ""
  https_proxy: ""
  no_proxy: ""
  request_timeout_seconds: 30
```

Do not disable TLS globally. If TLS verification must be disabled temporarily for troubleshooting, use `verify_tls: false` only in local config and record the reason.

