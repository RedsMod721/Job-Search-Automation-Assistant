# Stage 4 Test Results

Date: 2026-06-19

## Environment

- OS: Windows
- Python: 3.12.10
- Tool environment: `uv` with `.tmp/stage2-uv-venv`

## Validation Commands

| Command | Result |
| --- | --- |
| `uv run ruff format --check .` | Passed, 57 files already formatted |
| `uv run ruff check .` | Passed |
| `uv run mypy app.py src tests` | Passed, no issues in 42 source files |
| `uv run pytest` | Passed, 77 tests |
| `uv run bandit -c pyproject.toml -r app.py src` | Passed, no issues |
| `uv run python scripts/diagnostics.py --json` | Passed |
| `uv run python -m compileall -q app.py src pages scripts tests` | Passed |
| `uv run pip-audit --cache-dir .tmp/pip-audit-cache` | Passed after approved network access |

## Pytest Summary

`77 passed in 4.25s`

New Stage 4 tests cover:

- `init_db` runs the Stage 4 migration.
- Existing legacy database migrates with backup.
- Failed migration restores from backup.
- Manual backup restore succeeds.
- Recovery SQL export is created.
- Application/company/contact duplicate detection works.
- Audit events are written.
- Soft-delete tombstones are hidden from normal reads but recoverable.
- Integrity check reports OK.

## Diagnostics After Migration

Important diagnostic results:

- Database exists: yes.
- Schema version: `1`.
- Target schema version: `1`.
- Pending migrations: none.
- SQLite integrity: `ok`.
- Application count: `7`.
- Audit event count: `0`.
- CV files: all configured files present.
- Google Sheets: enabled, spreadsheet configured, credentials present.
- Ollama: available, configured model installed.

## Dependency Audit Note

The sandboxed `pip-audit` run failed through a refused local proxy. The audit was rerun with approved normal network access and passed with no known vulnerabilities.

