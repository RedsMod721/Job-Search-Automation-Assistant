# Stage 4 Known Bugs and Friction

Date: 2026-06-19

## Current Data Friction

1. Duplicate scan found one application duplicate group in the current local database.
   - Summary: `application_groups=1`, `company_groups=0`, `contact_groups=0`.
   - This is not a schema blocker, but the user should review the duplicate before heavy Stage 5 sync work.

2. Audit events start from Stage 4 writes.
   - Existing historical records were not backfilled into `audit_events`.
   - The current local database has `audit_events=0` immediately after migration.

## UI Friction

1. Restore uses a typed backup path.
   - There is no file picker.
   - The restore action is guarded by a confirmation checkbox.

2. Duplicate scan displays raw JSON.
   - This is sufficient for Stage 4 validation.
   - A richer dedupe review/merge workflow can come later.

3. Backup history table exists, but the UI does not yet show a history table view.
   - The local backup files are still created and restorable.

## Behavior Changes

1. Tracker delete is now a soft-delete.
   - Normal app reads hide tombstoned applications.
   - `include_deleted=True` can still recover tombstones through the database/repository layer.
   - A hard-delete API exists for explicit admin/recovery use.

2. Stage 5 sync should treat tombstoned records deliberately.
   - Do not blindly delete Google Sheets rows until Stage 5 defines sync tombstone behavior.

## Validation Friction

1. Mac validation was not run during Stage 4.
   - Windows validation passed.

2. `pip-audit` requires network access.
   - The sandboxed run failed through a refused local proxy.
   - The approved normal-network run passed.

## Intentional Deferrals

1. Automatic Google Sheets startup sync remains Stage 5.
2. Timed Google Sheets sync remains Stage 5.
3. Change-triggered sync remains Stage 5.
4. Duplicate merge actions are not implemented yet.

