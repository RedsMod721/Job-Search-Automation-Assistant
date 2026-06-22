# Stage 4 Implementation Report

Date: 2026-06-19

## Objective

Stage 4 adds database safety before automatic synchronization work begins. The implementation introduces schema migrations, pre-migration backups, recovery tools, duplicate detection, audit events, normalized identifiers, and soft-delete tombstones.

## Implemented Changes

- Added schema migration framework:
  - `src/database_migrations.py`
  - schema version table: `schema_migrations`
  - current schema version: `1`
- Added backup and recovery helpers:
  - `src/database_backups.py`
  - `src/services/recovery_service.py`
- Added duplicate detection:
  - `src/services/deduplication_service.py`
- Added normalization helpers:
  - `src/normalization.py`
- Extended application domain model with Stage 4 fields:
  - normalized company name
  - canonical job URL
  - external job ID
  - job-description hash
  - deleted-at timestamp
  - tombstone reason
- Updated database writes to enrich normalized fields automatically.
- Added audit-event recording for application/company/contact creates and updates.
- Changed application delete behavior to soft-delete/tombstone.
- Added hard-delete API for explicit recovery/admin use.
- Added Settings-page database safety controls:
  - integrity check
  - manual database backup
  - recovery SQL export
  - duplicate scan
  - guarded restore from backup path
- Added Stage 4 tests:
  - `tests/test_stage4_database_safety.py`

## Real Database Migration

The local `database/applications.db` was migrated successfully.

- Before migration: schema version `0`, pending version `[1]`.
- After migration: schema version `1`, pending versions `[]`.
- SQLite integrity check: `ok`.
- Application count after migration: `7`.

Pre-migration backup created:

```text
database/backups/applications_pre_migration_2026-06-19T16-52-20.db
```

Recovery SQL export created:

```text
database/recovery_exports/applications_recovery_2026-06-19T16-52-41.sql
```

Both paths are local ignored artifacts.

## Schema Version 1 Additions

New tables:

- `schema_migrations`
- `audit_events`
- `backup_history`

New application columns:

- `normalized_company_name`
- `canonical_job_url`
- `external_job_id`
- `job_description_hash`
- `deleted_at`
- `tombstone_reason`

New company columns:

- `normalized_company_name`
- `canonical_company_website`
- `deleted_at`

New contact columns:

- `normalized_full_name`
- `normalized_email`
- `deleted_at`

Indexes were added for normalized company names, canonical URLs, external job IDs, job-description hashes, deleted timestamps, and contact email lookup.

## Acceptance Status

- Existing user database upgraded without deletion: passed.
- Pre-migration backup created: passed.
- Duplicate test cases detected: passed.
- Backup restore tested: passed.
- Failed migration restore tested: passed.
- Audit records identify important changes: passed.
- Settings-page backup/restore/integrity/dedupe controls added: passed.
- All local checks passed.

## Not Included

- Automatic Google Sheets sync remains Stage 5.
- Backup browsing UI is not implemented; restore uses a typed backup path.
- Historical audit events were not backfilled for records created before Stage 4.

