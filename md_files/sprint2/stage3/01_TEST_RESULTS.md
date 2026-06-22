# Stage 3 Test Results

Date: 2026-06-17

## Environment

- OS: Windows
- Python: 3.12.10
- Tool environment: `uv` with `.tmp/stage2-uv-venv`

## Validation Commands

| Command | Result |
| --- | --- |
| `uv run ruff format --check .` | Passed, 51 files already formatted |
| `uv run ruff check .` | Passed |
| `uv run mypy app.py src tests` | Passed, no issues in 39 source files |
| `uv run pytest` | Passed, 67 tests |
| `uv run bandit -c pyproject.toml -r app.py src` | Passed, no issues |
| `uv run pip-audit --cache-dir .tmp/pip-audit-cache` | Passed, no known vulnerabilities |
| `uv run python scripts/diagnostics.py --json` | Passed |
| `uv run python -m compileall -q app.py src pages scripts tests` | Passed |
| `uv run python -c "import app; ..."` | Passed, `IMPORT_SMOKE=OK` |

## Pytest Summary

`67 passed in 4.28s`

New Stage 3 tests cover:

- Service modules do not import Streamlit.
- Application repository lifecycle against SQLite.
- Domain model compatibility with legacy extra fields.
- Google Sheets automatic modes remain disabled in Stage 3.
- Manual sync service returns a typed result.
- Prompt registry versions the core LLM prompt families.

## Dependency Audit Note

The first sandboxed `pip-audit` attempt failed because the environment pointed HTTPS traffic at a refused local proxy. The audit was rerun with approved normal network access and passed with no known vulnerabilities.

## Diagnostics Snapshot

Important diagnostic results:

- Database exists: yes.
- Application count: 7.
- CV files: all configured files present.
- Templates: English and French templates present.
- Ollama: available.
- Configured Ollama model: `qwen3:4b`.
- Google Sheets: manual sync only.
- Spreadsheet configured locally: yes.
- Google credentials file exists: no.
- Tracked settings remain public-safe: yes.

## Mac Validation

Mac validation was not run during this Stage 3 implementation pass. The Stage 1 Mac result remains pending until the user runs it on the MacBook.

## Readiness Recheck - 2026-06-18

| Command | Result |
| --- | --- |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 51 files already formatted |
| `uv run mypy app.py src tests` | Passed, no issues in 39 source files |
| `uv run pytest` | Passed, 70 tests |
| `uv run bandit -c pyproject.toml -r app.py src` | Passed, no issues |
| `uv run python scripts/diagnostics.py --json` | Passed |
| Zero-row `manual_sync_applications([], settings)` | Passed, no warnings or errors |

Current Google Sheets state:

- `config/google_service_account.json` exists locally.
- Credential JSON has service-account shape: project ID, client email, private key, and token URI are present.
- Google Sheets is enabled in merged local settings.
- Spreadsheet is configured.
- Manual setup check returned `{"synced":0,"updated":0,"created":0,"warnings":[],"errors":[]}`.

