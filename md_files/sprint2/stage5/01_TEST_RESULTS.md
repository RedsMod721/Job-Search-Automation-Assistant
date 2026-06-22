# Stage 5 Test Results

Date: 2026-06-19

## Environment

- OS: Windows
- Python: 3.12.10
- Tool environment: `uv` with `.tmp/stage2-uv-venv`

## Validation Commands

| Command | Result |
| --- | --- |
| `uv run ruff format --check .` | Passed, 58 files already formatted |
| `uv run ruff check .` | Passed |
| `uv run mypy app.py src tests` | Passed, no issues in 43 source files |
| `uv run pytest` | Passed, 82 tests |
| `uv run bandit -c pyproject.toml -r app.py src` | Passed, no issues |
| `uv run python scripts/diagnostics.py --json` | Passed |
| `uv run python -m compileall -q app.py src pages scripts tests` | Passed |
| `uv run pip-audit --cache-dir .tmp/pip-audit-cache` | Passed after approved network access |

## Pytest Summary

`82 passed in 6.04s`

New Stage 5 tests cover:

- application writes queue outbox items and increment record version
- change-triggered sync creates then updates without duplicate rows
- offline failures move outbox items to retry
- manual force sync processes retry items before retry delay
- startup sync queues and processes existing records

## Diagnostics Snapshot

Important diagnostic results:

- Schema version: `2`.
- Target schema version: `2`.
- Pending migrations: none.
- SQLite integrity: `ok`.
- Applications: `7`.
- Sync state rows: `7`.
- Sync outbox rows: `14`.
- Sync runs: `1`.
- Google Sheets automatic push enabled: yes.
- Startup sync enabled: yes.
- Timer sync enabled: yes.
- Change-triggered sync enabled: yes.
- Applications synced: `7`.

## Dependency Audit Note

The sandboxed `pip-audit` run failed through a refused local proxy. The audit was rerun with approved normal network access and passed with no known vulnerabilities.

