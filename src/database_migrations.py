from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.database_backups import create_sqlite_backup, restore_sqlite_backup
from src.normalization import canonicalize_url, content_hash, normalize_company_name, normalize_email
from src.utils import now_iso, resolve_path

CURRENT_SCHEMA_VERSION = 2


class MigrationError(RuntimeError):
    def __init__(self, message: str, backup_path: Path | None = None) -> None:
        super().__init__(message)
        self.backup_path = backup_path


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class MigrationReport:
    db_path: Path
    applied_versions: tuple[int, ...]
    backup_path: Path | None
    current_version: int


def ensure_schema_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _connect(path: str | Path) -> sqlite3.Connection:
    resolved = resolve_path(path).resolve()
    uri = f"file:{resolved.as_posix()}?mode=rwc&nolock=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=TRUNCATE")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def applied_versions(connection: sqlite3.Connection) -> set[int]:
    ensure_schema_migrations_table(connection)
    return {int(row[0]) for row in connection.execute("SELECT version FROM schema_migrations").fetchall()}


def current_schema_version(db_path: str | Path) -> int:
    path = resolve_path(db_path)
    if not path.exists():
        return 0
    with _connect(path) as connection:
        ensure_schema_migrations_table(connection)
        row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return int(row[0] or 0)


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}  # nosec B608


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name not in _column_names(connection, table_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")  # nosec B608


def _create_stage4_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            audit_event_id TEXT PRIMARY KEY,
            date_created TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT,
            before_json TEXT,
            after_json TEXT,
            details_json TEXT
        );

        CREATE TABLE IF NOT EXISTS backup_history (
            backup_id TEXT PRIMARY KEY,
            date_created TEXT NOT NULL,
            backup_type TEXT NOT NULL,
            source_path TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_audit_events_entity
            ON audit_events(entity_type, entity_id, date_created);

        CREATE INDEX IF NOT EXISTS idx_audit_events_action
            ON audit_events(action, date_created);
        """
    )


def _add_stage4_columns(connection: sqlite3.Connection) -> None:
    for column, definition in {
        "normalized_company_name": "TEXT DEFAULT ''",
        "canonical_job_url": "TEXT DEFAULT ''",
        "external_job_id": "TEXT DEFAULT ''",
        "job_description_hash": "TEXT DEFAULT ''",
        "deleted_at": "TEXT DEFAULT ''",
        "tombstone_reason": "TEXT DEFAULT ''",
    }.items():
        _add_column_if_missing(connection, "applications", column, definition)

    for column, definition in {
        "normalized_company_name": "TEXT DEFAULT ''",
        "canonical_company_website": "TEXT DEFAULT ''",
        "deleted_at": "TEXT DEFAULT ''",
    }.items():
        _add_column_if_missing(connection, "companies", column, definition)

    for column, definition in {
        "normalized_full_name": "TEXT DEFAULT ''",
        "normalized_email": "TEXT DEFAULT ''",
        "deleted_at": "TEXT DEFAULT ''",
    }.items():
        _add_column_if_missing(connection, "contacts", column, definition)


def _backfill_stage4_fields(connection: sqlite3.Connection) -> None:
    for row in connection.execute(
        """
        SELECT application_id, company_name, job_url, raw_job_description
        FROM applications
        """
    ).fetchall():
        connection.execute(
            """
            UPDATE applications
            SET normalized_company_name = ?,
                canonical_job_url = ?,
                job_description_hash = ?
            WHERE application_id = ?
            """,
            (
                normalize_company_name(row[1]),
                canonicalize_url(row[2]),
                content_hash(row[3]),
                row[0],
            ),
        )

    for row in connection.execute("SELECT company_id, company_name, company_website FROM companies").fetchall():
        connection.execute(
            """
            UPDATE companies
            SET normalized_company_name = ?,
                canonical_company_website = ?
            WHERE company_id = ?
            """,
            (normalize_company_name(row[1]), canonicalize_url(row[2]), row[0]),
        )

    for row in connection.execute("SELECT contact_id, full_name, email FROM contacts").fetchall():
        connection.execute(
            """
            UPDATE contacts
            SET normalized_full_name = ?,
                normalized_email = ?
            WHERE contact_id = ?
            """,
            (normalize_company_name(row[1]), normalize_email(row[2]), row[0]),
        )


def _create_stage4_indexes(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_applications_canonical_job_url
            ON applications(canonical_job_url);
        CREATE INDEX IF NOT EXISTS idx_applications_external_job_id
            ON applications(external_job_id);
        CREATE INDEX IF NOT EXISTS idx_applications_job_description_hash
            ON applications(job_description_hash);
        CREATE INDEX IF NOT EXISTS idx_applications_normalized_company_name
            ON applications(normalized_company_name);
        CREATE INDEX IF NOT EXISTS idx_applications_deleted_at
            ON applications(deleted_at);
        CREATE INDEX IF NOT EXISTS idx_companies_normalized_company_name
            ON companies(normalized_company_name);
        CREATE INDEX IF NOT EXISTS idx_companies_canonical_company_website
            ON companies(canonical_company_website);
        CREATE INDEX IF NOT EXISTS idx_contacts_normalized_email
            ON contacts(normalized_email);
        """
    )


def apply_stage4_migration(connection: sqlite3.Connection) -> None:
    _create_stage4_tables(connection)
    _add_stage4_columns(connection)
    _backfill_stage4_fields(connection)
    _create_stage4_indexes(connection)


def _add_stage5_columns(connection: sqlite3.Connection) -> None:
    for column, definition in {
        "record_version": "INTEGER DEFAULT 1",
        "sync_status": "TEXT DEFAULT 'PENDING'",
        "sync_pending": "INTEGER DEFAULT 1",
        "sync_hash": "TEXT DEFAULT ''",
        "sync_last_attempt_at": "TEXT DEFAULT ''",
        "sync_last_success_at": "TEXT DEFAULT ''",
        "sync_last_error": "TEXT DEFAULT ''",
        "sync_last_source": "TEXT DEFAULT ''",
    }.items():
        _add_column_if_missing(connection, "applications", column, definition)


def _create_stage5_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS sync_outbox (
            outbox_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            payload_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            attempt_count INTEGER DEFAULT 0,
            next_attempt_at TEXT,
            last_error TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_state (
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            remote_row_key TEXT,
            local_version INTEGER NOT NULL,
            remote_version INTEGER,
            last_synced_hash TEXT,
            last_synced_at TEXT,
            last_sync_source TEXT,
            sync_status TEXT,
            PRIMARY KEY(entity_type, entity_id)
        );

        CREATE TABLE IF NOT EXISTS sync_conflicts (
            conflict_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            field_name TEXT NOT NULL,
            base_value TEXT,
            local_value TEXT,
            remote_value TEXT,
            detected_at TEXT NOT NULL,
            resolved_at TEXT,
            resolution TEXT,
            resolved_value TEXT,
            status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sync_runs (
            sync_run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            synced INTEGER DEFAULT 0,
            created INTEGER DEFAULT 0,
            updated INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            warnings_json TEXT,
            errors_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sync_outbox_status_due
            ON sync_outbox(status, next_attempt_at, created_at);
        CREATE INDEX IF NOT EXISTS idx_sync_outbox_entity
            ON sync_outbox(entity_type, entity_id, status);
        CREATE INDEX IF NOT EXISTS idx_sync_runs_started_at
            ON sync_runs(started_at);
        """
    )


def _backfill_stage5_sync_state(connection: sqlite3.Connection) -> None:
    timestamp = now_iso()
    rows = connection.execute(
        """
        SELECT application_id, record_version
        FROM applications
        WHERE deleted_at IS NULL OR deleted_at = ''
        """
    ).fetchall()
    for row in rows:
        connection.execute(
            """
            INSERT INTO sync_state (
                entity_type,
                entity_id,
                remote_row_key,
                local_version,
                remote_version,
                last_synced_hash,
                last_synced_at,
                last_sync_source,
                sync_status
            )
            VALUES ('application', ?, '', COALESCE(?, 1), NULL, '', '', '', 'PENDING')
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                local_version = excluded.local_version,
                sync_status = excluded.sync_status
            """,
            (row[0], row[1]),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO sync_outbox (
                outbox_id,
                entity_type,
                entity_id,
                operation,
                payload_json,
                created_at,
                updated_at,
                attempt_count,
                next_attempt_at,
                last_error,
                status
            )
            VALUES (?, 'application', ?, 'migration_backfill', '', ?, ?, 0, '', '', 'PENDING')
            """,
            (f"migration-{row[0]}", row[0], timestamp, timestamp),
        )


def apply_stage5_migration(connection: sqlite3.Connection) -> None:
    _add_stage5_columns(connection)
    _create_stage5_tables(connection)
    _backfill_stage5_sync_state(connection)


MIGRATIONS: tuple[Migration, ...] = (
    Migration(1, "stage4_database_safety", apply_stage4_migration),
    Migration(2, "stage5_google_sheets_sync", apply_stage5_migration),
)


def run_migrations(
    db_path: str | Path,
    *,
    migrations: Sequence[Migration] = MIGRATIONS,
    create_backup: bool = True,
    backup_dir: str | Path | None = None,
) -> MigrationReport:
    path = resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = None

    with _connect(path) as connection:
        ensure_schema_migrations_table(connection)
        pending = [migration for migration in migrations if migration.version not in applied_versions(connection)]

    if not pending:
        return MigrationReport(path, (), None, current_schema_version(path))

    if create_backup and path.exists():
        backup_path = create_sqlite_backup(path, backup_dir=backup_dir, label="pre_migration")

    applied: list[int] = []
    try:
        with _connect(path) as connection:
            ensure_schema_migrations_table(connection)
            for migration in pending:
                with connection:
                    migration.apply(connection)
                    connection.execute(
                        """
                        INSERT INTO schema_migrations (version, name, applied_at)
                        VALUES (?, ?, ?)
                        """,
                        (migration.version, migration.name, now_iso()),
                    )
                applied.append(migration.version)
    except Exception as exc:
        if backup_path is not None:
            restore_sqlite_backup(backup_path, path, pre_restore_backup_dir=backup_dir)
        raise MigrationError(f"Database migration failed: {exc}", backup_path=backup_path) from exc

    return MigrationReport(path, tuple(applied), backup_path, current_schema_version(path))


def schema_status(db_path: str | Path) -> dict[str, Any]:
    path = resolve_path(db_path)
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "current_version": 0,
            "target_version": CURRENT_SCHEMA_VERSION,
            "pending_versions": list(range(1, CURRENT_SCHEMA_VERSION + 1)),
        }

    with _connect(path) as connection:
        versions = applied_versions(connection)
    return {
        "path": str(path),
        "exists": True,
        "current_version": max(versions) if versions else 0,
        "target_version": CURRENT_SCHEMA_VERSION,
        "pending_versions": [migration.version for migration in MIGRATIONS if migration.version not in versions],
    }
