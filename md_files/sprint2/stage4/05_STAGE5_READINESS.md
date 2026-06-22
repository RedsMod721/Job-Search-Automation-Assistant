# Stage 5 Readiness

Date: 2026-06-19

## Stage 5 Target

Stage 5 is automatic Google Sheets push synchronization.

The Stage 4 schema now gives Stage 5 the database primitives it needs:

- schema versioning
- backups before risky changes
- normalized application/company fields
- external job ID
- job-description hash
- tombstones
- audit events
- recovery exports

## Ready Inputs

- Manual Google Sheets sync still works through `sync_service`.
- Google Sheets credentials are present locally.
- Google Sheets is enabled in local settings.
- Zero-row manual setup check passed during Stage 3 readiness.
- Local database is migrated to schema version `1`.
- Integrity check is OK.
- Pre-migration backup exists.
- Recovery SQL export exists.

## Recommended Stage 5 Plan

1. Add sync state/outbox table with a Stage 5 migration.
2. Add dirty flags or pending sync operations for application create/update/archive/delete/tombstone events.
3. Decide how tombstones map to Google Sheets rows.
4. Keep the manual sync button.
5. Add startup sync after `bootstrap`.
6. Add post-write sync triggers behind repository/service methods.
7. Add configurable timer sync, defaulting to one minute.
8. Add retry/backoff and offline queue.
9. Add visible sync status in Settings or Tracker.
10. Add live integration tests against the dedicated test spreadsheet.

## Guardrails

- Do not hard-delete local records as part of sync.
- Do not delete Google Sheets rows for tombstones until the conflict/tombstone rule is explicit.
- Keep SQLite as source of truth unless the Stage 5 sync spec changes.
- Keep generated backups and recovery exports ignored.
- Keep `config/google_service_account.json` ignored.

