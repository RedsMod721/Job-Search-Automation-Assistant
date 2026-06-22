# Stage 2 Implementation Report

Date: 2026-06-17

## Overall Status

Stage 2 repository and environment stabilization is implemented on Windows.

The project now has:

- `pyproject.toml` with runtime dependencies, dev dependency group, Ruff, mypy, and Bandit config.
- `uv.lock` as the canonical lock file.
- Python support declared as `>=3.12,<3.15`.
- GitHub Actions CI for Windows and macOS across Python 3.12, 3.13, and 3.14.
- Optional pre-commit hooks.
- Runtime/dev dependency separation.
- Public-safe tracked settings with ignored local overrides.
- TLS verification enabled by default.
- Workspace diagnostics command and Settings-page diagnostics panel.
- Stage 2 report set.

Google Sheets remains manual UI-button sync until Stage 5.

## Important Implementation Notes

- The real Google Sheet URL was moved out of tracked `config/settings.yaml` and into ignored `config/settings.local.yaml`.
- `config/settings.yaml` now uses an empty `google_sheets.spreadsheet_id` and `google_sheets.enabled: false`.
- Local config precedence is now base YAML, local YAML, then environment variables.
- Company search no longer disables TLS globally and no longer sets `session.verify = False`.
- Settings saves now write to `config/settings.local.yaml` so user-specific values do not re-enter tracked config.
- The Stage 2 uv environment used for verification is `.tmp/stage2-uv-venv`.

## Files and Areas Added

- Tooling and CI:
  - `pyproject.toml`
  - `uv.lock`
  - `requirements-dev.txt`
  - `.python-version`
  - `.pre-commit-config.yaml`
  - `.github/workflows/ci.yml`
- Configuration:
  - `config/profile.example.yaml`
  - `config/settings.example.yaml`
  - ignored `config/settings.local.yaml`
- Runtime support:
  - `src/network.py`
  - `src/diagnostics.py`
  - `scripts/diagnostics.py`
- Tests:
  - `tests/test_network.py`
  - `tests/test_diagnostics.py`
  - expanded config and company-search tests.

## Acceptance Gate Status

| Gate | Status |
|---|---|
| Clean clone install path documented | Pass |
| Dependency lock strategy exists | Pass |
| Runtime/dev dependencies separated | Pass |
| Formatter, linter, type check configured | Pass |
| Security scanning configured | Pass |
| CI workflow added | Pass |
| TLS verification enabled by default | Pass |
| Custom CA/proxy settings available | Pass |
| Global TLS disabling removed | Pass |
| Secrets and local config ignored | Pass |
| Diagnostics command and UI panel added | Pass |
| Manual Google Sheets sync preserved | Pass |
| Remote GitHub Actions run observed | Not run locally |
| Mac validation | Pending user run |

