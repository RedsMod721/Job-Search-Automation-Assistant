# Stage 2 Known Bugs and Friction

Date: 2026-06-17

## Remaining Friction

### Blocking

1. Google Sheets sync inputs are still missing:
   - `config/google_service_account.json`
   - A real spreadsheet ID or editable Google Sheets URL
   - The spreadsheet must be shared with the service-account email as an Editor
2. macOS validation is still pending the user run planned after Stage 1.

### Should Have

1. Remote GitHub Actions CI has been added but not observed running from this local workspace.
2. `uv sync` could not use the existing `.venv` because of local permission friction, so Stage 2 validation used `.tmp/stage2-uv-venv`.
3. `uv` and `pip-audit` needed workspace-local caches because Windows user-cache paths were not writable in this environment.
4. Networked commands required approval due restricted network access.

### Nice To Have

1. Ruff formatting touched existing source and test files mechanically; behavioral changes were limited to Stage 2 stabilization work.
2. The app is still a monolithic Streamlit file. That is expected until Stage 3.

## Product Notes

1. Google Sheets sync is still a V1 manual push workflow.
2. No automatic push timer, startup sync, change-triggered sync, conflict queue, outbox, or background worker was added in Stage 2.
3. Diagnostics report `credentials_exists: false` until `config/google_service_account.json` is added locally.
4. The local settings file contains the real Sheet URL and is ignored by Git.
5. Corporate proxy variables are detected as configured in diagnostics because this Windows environment exposes proxy-related environment variables.

## Fixed During Stage 2

1. Global TLS warning suppression was removed from company search.
2. `session.verify = False` was removed from company search.
3. Public tracked settings no longer contain the real Google Sheet URL.
4. Settings UI saves to ignored local config instead of tracked base config.
5. Pytest was upgraded from 8.4.2 to 9.1.0 after pip-audit identified `CVE-2025-71176`.
6. Test imports and temp-path behavior are now reproducible under the uv environment.

