# Stage 1 UI Workflows and Setup

Date: 2026-06-17

## Windows Setup Used for Baseline

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Validation environment:

```text
Python: 3.14.3
Streamlit: 1.58.0
pytest: 8.4.2
Ollama models present: qwen3:4b, llama3.2:latest
```

## Required Local Assets

Place the four real CV PDFs at these ignored local paths:

```text
documents/cvs/CV_Sebastian.Vazquez_Anglais-Marketing.pdf
documents/cvs/CV_Sebastian.Vazquez_Anglais-Consulting.pdf
documents/cvs/CV_Sebastian.Vazquez_Anglais-DataScience.pdf
documents/cvs/CV_Sebastian.Vazquez_Anglais-AI.pdf
```

Existing templates:

```text
documents/templates/motivation_letter_en.txt
documents/templates/motivation_letter_fr.txt
```

For Google Sheets validation:

```text
config/google_service_account.json
STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID=<dedicated test sheet id>
```

Do not commit credentials, private PDFs, local database backups, or generated exports.

## Current UI Workflows

Dashboard:

- Shows high-level tracker metrics and recent application state.
- Expected behavior: app should load without requiring Ollama or Google Sheets.

Add Job:

- Accepts raw job-post text.
- Runs structured extraction through Ollama when available.
- Shows extracted fields for review before saving.
- Expected behavior: missing fields remain blank rather than invented.

Application Tracker:

- Lists applications from SQLite.
- Supports filtering, editing status, archive, and confirmed delete.
- Supports Excel export.
- Expected behavior: SQLite remains the source of truth.

CV Matcher:

- Scores the current job against configured CV keyword sets.
- Shows warnings when configured CV files are missing.
- Allows manual review or override.

Motivation Letter:

- Generates English or French drafts.
- Falls back to templates when Ollama generation fails.
- Saves generated content under `generated/motivation_letters/`.

Form Helper:

- Generates personal information and reusable common answers.
- Uses local profile defaults and job context.
- Saves generated content under `generated/form_answers/`.

Company Search:

- Provides basic public lookup and career-page discovery.
- This is not yet the full Stage 13 discovery engine.

Settings:

- Shows editable runtime settings.
- Google Sheets sync is disabled by default.
- Credentials path defaults to `config/google_service_account.json`.

## macOS Validation Checklist

Run this checklist on the MacBook Pro before treating Stage 1 as accepted on the primary environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
streamlit run app.py
```

Record:

- macOS version.
- Python version.
- Streamlit version.
- pytest output.
- Ollama version and `ollama list`.
- Whether `qwen3:4b` is installed.
- Whether the app launches in the browser.
- Whether the four CV paths exist.
- Whether Google Sheets test sync succeeds or the exact blocker.

## Manual Acceptance Checklist

- App launches.
- Dashboard loads.
- Add Job accepts pasted text.
- Extraction preview appears and remains editable.
- Application can be saved.
- Tracker lists the saved application.
- Status can be changed.
- Archive workflow requires confirmation.
- CV recommendation appears and can be manually overridden.
- English motivation letter can be generated.
- French motivation letter can be generated.
- Form answers can be generated.
- Excel export creates a file.
- Google Sheets sync succeeds once or records a precise blocker.
