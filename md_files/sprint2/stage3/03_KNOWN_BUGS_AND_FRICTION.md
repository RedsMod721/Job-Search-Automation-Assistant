# Stage 3 Known Bugs and Friction

Date: 2026-06-17

## Google Sheets Sync Status

1. `config/google_service_account.json` now exists locally.
   - The file remains ignored and must not be committed.
   - A redacted validation confirmed the JSON has service-account shape.

2. Google Sheets is enabled in merged local settings.
   - Diagnostics show a spreadsheet is configured locally.
   - Diagnostics show credentials exist.

3. A zero-row manual sync setup check passed on 2026-06-18.
   - Result: no warnings and no errors.
   - This confirms the configured credentials can open and prepare the target worksheet.

## Stage 3 Intentional Deferrals

1. Timed Google Sheets sync is not implemented.
   - The roadmap assigns timer sync to Stage 5.

2. Startup Google Sheets sync is not implemented.
   - The roadmap assigns startup sync to Stage 5.

3. Change-triggered sync after application create/update/delete is not implemented.
   - The roadmap assigns this to Stage 5.

4. Offline sync queue, retry/backoff state, and sync audit log are not implemented.
   - These belong with Stage 5 automatic sync.

## Architecture Friction

1. The top-level `pages/` modules are thin entrypoints.
   - They reuse render functions from `app.py`.
   - This preserves behavior now but does not fully move every UI form into its own module yet.

2. Prompt bodies are still embedded in generator modules.
   - Stage 3 added a prompt registry and versions.
   - A future cleanup can move prompt templates into separate prompt files.

3. `src.database` remains the low-level persistence implementation.
   - Stage 3 added repository wrappers.
   - Stage 4 should put migrations, backups, deduplication, and audit logging behind those wrappers.

4. The worktree remains intentionally dirty from Sprint 1/2 documentation relocation and Stage 2/3 work.
   - Review file moves and deleted root docs before making a final sprint commit.

## Validation Friction

1. Mac validation was not run in this pass.
   - The Stage 1 Mac test result is still expected from the user.

2. `pip-audit` requires network access.
   - The sandboxed run failed through a refused local proxy.
   - The approved normal-network run passed.

3. A full live non-empty application push was not re-run during the 2026-06-18 readiness check.
   - The zero-row setup check passed.
   - Existing automated fake-client sync tests cover create/update row behavior.
