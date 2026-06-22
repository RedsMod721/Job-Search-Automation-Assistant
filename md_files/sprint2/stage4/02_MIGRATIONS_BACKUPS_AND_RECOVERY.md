# Stage 4 Migrations, Backups, and Recovery

Date: 2026-06-19

## Migration Framework

Migration code lives in `src/database_migrations.py`.

Current version:

```text
1
```

The migration runner:

- creates `schema_migrations`
- checks applied versions
- creates a pre-migration backup for existing databases
- applies pending migrations in version order
- records applied migrations
- restores from backup if a migration fails after making changes

## Backup Behavior

Low-level backup helpers live in `src/database_backups.py`.

Service functions live in `src/services/recovery_service.py`:

- `create_backup(db_path, backup_dir=None, label="manual")`
- `restore_backup(backup_path, db_path, pre_restore_backup_dir=None)`
- `create_recovery_export(db_path, export_dir=None, label="recovery")`
- `run_integrity_check(db_path)`
- `list_backups(backup_dir=None)`

Generated local artifacts are ignored:

- `database/backups/`
- `database/recovery_exports/`

## Real Local Artifacts

Pre-migration backup:

```text
database/backups/applications_pre_migration_2026-06-19T16-52-20.db
```

Recovery SQL export:

```text
database/recovery_exports/applications_recovery_2026-06-19T16-52-41.sql
```

## Settings Page Controls

Settings now exposes:

- Run integrity check.
- Create database backup.
- Export recovery SQL.
- Scan duplicates.
- Restore database backup after typing a backup path and confirming restore.

## Restore Safety

Restore creates a pre-restore backup of the current database before copying the selected backup into place.

Failed migration restore is tested by forcing a committed mutation inside a failing migration and verifying the original data is restored.

