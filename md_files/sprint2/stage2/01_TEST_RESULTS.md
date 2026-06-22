# Stage 2 Test Results

Date: 2026-06-17

## Environment

```text
OS: Windows
uv: 0.11.21
Python used by uv environment: 3.12.10
pytest: 9.1.0
uv environment: .tmp/stage2-uv-venv
uv cache: .tmp/uv-cache
```

## Commands Run

```powershell
uv lock
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run mypy app.py src tests
uv run pytest
uv run bandit -c pyproject.toml -r app.py src
uv run pip-audit --cache-dir .tmp/pip-audit-cache
uv run python scripts/diagnostics.py --json
```

On this Windows workspace, `UV_CACHE_DIR=.tmp/uv-cache` and `UV_PROJECT_ENVIRONMENT=.tmp/stage2-uv-venv` were used to avoid protected user-cache and existing `.venv` permissions.

## Results

| Check | Result |
|---|---|
| `uv lock` | Pass |
| `uv sync --group dev` | Pass |
| `ruff format --check .` | Pass, 26 files already formatted |
| `ruff check .` | Pass |
| `mypy app.py src tests` | Pass, 22 source files checked |
| `pytest` | Pass, 61 passed |
| `bandit -c pyproject.toml -r app.py src` | Pass, no issues identified |
| `pip-audit --cache-dir .tmp/pip-audit-cache` | Pass, no known vulnerabilities found |
| `scripts/diagnostics.py --json` | Pass |

## Security Audit Note

The first dependency audit found:

```text
pytest 8.4.2 - CVE-2025-71176 - fixed in 9.0.3
```

Stage 2 updated the dev dependency range to `pytest>=9.0.3,<10` and regenerated `uv.lock`. Final audit result:

```text
No known vulnerabilities found
```

## Test Suite Detail

```text
platform win32 -- Python 3.12.10, pytest-9.1.0, pluggy-1.6.0
collected 61 items

tests\test_company_search.py ............................
tests\test_config_loading.py ......
tests\test_cv_matcher.py ....
tests\test_database_init.py ..
tests\test_diagnostics.py ..
tests\test_excel_exporter.py .
tests\test_extraction_review.py ........
tests\test_extractor.py ..
tests\test_generated_assets.py ..
tests\test_network.py .....
tests\test_sheets_sync.py .

61 passed in 3.89s
```

## Diagnostics Snapshot

```text
database exists: true
table counts: applications=7, companies=0, contacts=0, documents=0
settings local override exists: true
settings public safe: true
missing CVs: none reported
templates: English and French present
Ollama: available
configured model: qwen3:4b installed
Google Sheets: manual sync only, credentials missing, spreadsheet configured through local override
TLS verification: enabled
```

