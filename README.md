# Job Search Automation Assistant

A local, user-controlled job search assistant for tracking applications, extracting job post data, recommending one of four fixed CVs, drafting motivation letters, preparing form answers, and later syncing to Google Sheets.

The app assists the user. It does not auto-submit applications, mass scrape LinkedIn, send messages, bypass CAPTCHA, or run hidden background application actions.

## Quick Start

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

Do not commit credentials. Use `.env` for local overrides and keep Google service account credentials at `config/google_service_account.json`, which is ignored by Git.

## Optional Ollama Setup

Install Ollama, then pull the default local model:

```powershell
ollama pull qwen2.5:7b
```

If Ollama or the selected model is unavailable, the app should stay usable for manual tracking and deterministic CV matching.

## Optional Google Sheets Setup

Google Sheets sync is scaffolded but disabled by default in `config/settings.yaml`.

To enable it later:

1. Create a Google Cloud service account.
2. Save the credential JSON as `config/google_service_account.json`.
3. Share the target spreadsheet with the service account email.
4. Set `google_sheets.enabled: true`.
5. Fill `google_sheets.spreadsheet_id`.

SQLite remains the source of truth for V1.

## Current Foundation

This skeleton includes:

- Streamlit tabs for Dashboard, Add Job, Tracker, CV Matcher, Motivation Letter, Form Helper, and Settings.
- Active YAML config loading.
- SQLite schema initialization for applications, companies, contacts, and documents.
- Manual application save flow.
- Deterministic CV recommendation using configured keywords.
- Safe placeholder modules for local extraction, letters, form answers, Excel export, Google Sheets sync, and company search.
- Pytest coverage for config loading, database initialization, module imports, and CV matching.
