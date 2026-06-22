# Job Search Automation Assistant

A local, user-controlled job search assistant for tracking applications, extracting job post data, recommending one of four fixed CVs, drafting motivation letters, preparing form answers, exporting Excel files, and optionally syncing to Google Sheets.

The app assists the user. It does not auto-submit applications, mass scrape LinkedIn, send messages, bypass CAPTCHA, or run hidden background application actions.

## Quick Start

Recommended development setup:

```powershell
uv sync --group dev
uv run streamlit run app.py
```

Fallback pip setup:

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

On first launch, the app creates the required local folders and initializes `database/applications.db`.

## Configuration

Active config lives in `config/`:

- `profile.yaml`: Sebastian's profile and preferences.
- `documents.yaml`: fixed CV metadata, paths, keywords, and letter template paths.
- `settings.yaml`: app, database, Ollama, export, Google Sheets, automation, and logging settings.
- `form_answers.yaml`: reusable form answer defaults.

Public-safe examples live in:

- `config/profile.example.yaml`
- `config/settings.example.yaml`

Local overrides are supported and ignored by Git:

- `config/profile.local.yaml`
- `config/settings.local.yaml`
- `config/documents.local.yaml`
- `config/form_answers.local.yaml`

Config precedence is base YAML, local YAML, then environment variables.

Do not commit credentials. Use `.env` for local overrides and keep Google service account credentials at `config/google_service_account.json`, which is ignored by Git.

## Optional Ollama Setup

Install Ollama, then pull the default local model:

```powershell
ollama pull qwen2.5:7b
```

If Ollama or the selected model is unavailable, the app stays usable for manual tracking, deterministic CV matching, template-based letters, and deterministic form answers.

## CV Files

The app expects the four fixed CV PDFs configured in `config/documents.yaml` to be placed in `documents/cvs/`. The app does not create or edit CV PDFs. If any configured file is missing, the CV Matcher and Settings pages show a warning while still allowing keyword-based recommendations and manual overrides.

## Optional Google Sheets Setup

Google Sheets sync is disabled by default in `config/settings.yaml`.

The app expects a standard Google Cloud service-account JSON key for Sheets access. The app itself does not require any paid Google Cloud feature to use the sync path documented here.

To enable it later:

1. Create a Google Cloud service account.
2. Save the credential JSON as `config/google_service_account.json`.
3. Share the target spreadsheet with the service account email.
4. Put local sync settings in `config/settings.local.yaml`.
5. Set `google_sheets.enabled: true`.
6. Fill `google_sheets.spreadsheet_id` with the real spreadsheet ID or an editable Google Sheets URL.
7. If you want to keep the sheet ID out of YAML, set `GOOGLE_SHEETS_SPREADSHEET_ID` locally instead.

The published `/pubhtml` link is not enough for sync. The app needs the underlying spreadsheet ID plus a sheet that the service account can edit.

SQLite remains the source of truth for V1, and sync is still manual through the UI button until the later bidirectional sync stage.

## Network Configuration

TLS verification is enabled by default. Corporate proxy or custom CA settings should be explicit in `config/settings.local.yaml`:

```yaml
network:
  verify_tls: true
  custom_ca_bundle: ""
  http_proxy: ""
  https_proxy: ""
  no_proxy: ""
  request_timeout_seconds: 30
```

Environment variables are also supported for local overrides:

- `JOB_SEARCH_VERIFY_TLS`
- `JOB_SEARCH_CA_BUNDLE`
- `JOB_SEARCH_HTTP_PROXY`
- `JOB_SEARCH_HTTPS_PROXY`
- `JOB_SEARCH_NO_PROXY`
- `JOB_SEARCH_REQUEST_TIMEOUT_SECONDS`

## Diagnostics

Run local diagnostics from the project root:

```powershell
uv run python scripts/diagnostics.py
uv run python scripts/diagnostics.py --json
```

The Settings tab also includes a health diagnostics panel.

## Current V1 Features

- Streamlit tabs for Dashboard, Add Job, Tracker, CV Matcher, Motivation Letter, Form Helper, Company Search, and Settings.
- Active YAML config loading and editable runtime settings.
- SQLite schema initialization for applications, companies, contacts, and documents.
- Manual application creation, extraction review, tracker editing, CV override, archive, and confirmed delete.
- Local Ollama job extraction with schema normalization and editable review before saving.
- Deterministic CV recommendation using configured keywords and missing-file validation.
- Editable motivation letters and form answers, saved locally and linked back to application records.
- Excel export from the tracker.
- Google Sheets sync with header creation, row updates, duplicate avoidance, and stored sheet row IDs.
- Basic public company/career-page search with save-to-company and create-application flows.
- Pytest coverage for config loading, database operations, extraction, CV matching, generated assets, Excel export, Google Sheets sync, and company search.
