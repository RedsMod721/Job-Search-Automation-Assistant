from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from src import database
from src.constants import PROJECT_ROOT
from src.database_migrations import CURRENT_SCHEMA_VERSION, Migration, MigrationError, run_migrations, schema_status
from src.services import deduplication_service, recovery_service


def _test_dir() -> Path:
    path = PROJECT_ROOT / ".tmp" / f"stage4-tests-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _create_legacy_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        database.create_tables(connection)


def _column_names(path: Path, table_name: str) -> set[str]:
    with sqlite3.connect(path) as connection:
        return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}  # nosec B608


def test_init_db_runs_stage4_migration() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "applications.db"

    database.init_db(db_path)

    assert schema_status(db_path)["current_version"] == CURRENT_SCHEMA_VERSION
    assert {
        "normalized_company_name",
        "canonical_job_url",
        "external_job_id",
        "job_description_hash",
        "deleted_at",
        "tombstone_reason",
    }.issubset(_column_names(db_path, "applications"))

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
    assert {"schema_migrations", "audit_events", "backup_history"}.issubset(tables)


def test_existing_database_migrates_with_backup() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "legacy.db"
    backup_dir = test_dir / "backups"
    _create_legacy_db(db_path)

    report = run_migrations(db_path, backup_dir=backup_dir, create_backup=True)

    assert report.applied_versions == tuple(range(1, CURRENT_SCHEMA_VERSION + 1))
    assert report.backup_path is not None
    assert report.backup_path.exists()
    assert schema_status(db_path)["current_version"] == CURRENT_SCHEMA_VERSION


def test_failed_migration_restores_backup() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "restore-on-failure.db"
    backup_dir = test_dir / "backups"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE sentinel (value TEXT)")
        connection.execute("INSERT INTO sentinel (value) VALUES ('original')")
        connection.commit()

    def bad_migration(connection: sqlite3.Connection) -> None:
        connection.execute("UPDATE sentinel SET value = 'mutated'")
        connection.commit()
        raise RuntimeError("boom")

    with pytest.raises(MigrationError) as error:
        run_migrations(
            db_path,
            migrations=(Migration(99, "bad_migration", bad_migration),),
            backup_dir=backup_dir,
            create_backup=True,
        )

    assert error.value.backup_path is not None
    assert error.value.backup_path.exists()
    with sqlite3.connect(db_path) as connection:
        value = connection.execute("SELECT value FROM sentinel").fetchone()[0]
    assert value == "original"


def test_backup_restore_and_recovery_export() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "backup-restore.db"
    backup_dir = test_dir / "backups"
    export_dir = test_dir / "exports"
    database.init_db(db_path)
    application_id = database.add_application(
        {
            "company_name": "Backup Co",
            "job_title": "Analyst",
            "status": "Saved",
        },
        db_path=db_path,
    )
    backup_path = recovery_service.create_backup(db_path, backup_dir=backup_dir, label="test")

    database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
    recovery_service.restore_backup(backup_path, db_path, pre_restore_backup_dir=backup_dir)

    restored = database.get_application(application_id, db_path=db_path)
    assert restored is not None
    assert restored["status"] == "Saved"

    export_path = recovery_service.create_recovery_export(db_path, export_dir=export_dir)
    assert export_path.exists()
    assert "CREATE TABLE applications" in export_path.read_text(encoding="utf-8")


def test_duplicate_detection_for_applications_companies_and_contacts() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "duplicates.db"
    database.init_db(db_path)
    database.add_application(
        {
            "company_name": "Acme Inc.",
            "job_title": "AI Analyst",
            "location": "Paris",
            "job_url": "https://www.example.com/jobs/ai-analyst?utm_source=newsletter",
            "raw_job_description": "Build AI dashboards",
        },
        db_path=db_path,
    )
    database.add_application(
        {
            "company_name": "Acme",
            "job_title": "AI Analyst",
            "location": "Paris",
            "job_url": "example.com/jobs/ai-analyst",
            "raw_job_description": "Build AI dashboards",
        },
        db_path=db_path,
    )
    company_id = database.upsert_company(
        {
            "company_name": "Example SAS",
            "company_website": "https://www.example.com/",
        },
        db_path=db_path,
    )
    database.upsert_company(
        {
            "company_name": "Example",
            "company_website": "example.com",
        },
        db_path=db_path,
    )
    database.upsert_contact(
        {
            "company_id": company_id,
            "full_name": "Jane Example",
            "email": "Jane@example.com",
        },
        db_path=db_path,
    )
    database.upsert_contact(
        {
            "company_id": company_id,
            "full_name": "Jane E.",
            "email": "jane@example.com",
        },
        db_path=db_path,
    )

    duplicates = deduplication_service.find_all_duplicates(db_path)

    assert duplicates["summary"]["application_groups"] >= 1
    assert duplicates["summary"]["company_groups"] >= 1
    assert duplicates["summary"]["contact_groups"] >= 1
    assert any(group["reason"] == "same canonical job url" for group in duplicates["applications"])


def test_audit_events_and_soft_delete_tombstone() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "audit.db"
    database.init_db(db_path)
    application_id = database.add_application(
        {
            "company_name": "Audit Co",
            "job_title": "Engineer",
            "status": "Saved",
        },
        db_path=db_path,
    )

    database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
    database.archive_application(application_id, db_path=db_path)
    database.delete_application(application_id, db_path=db_path)

    assert database.get_application(application_id, db_path=db_path) is None
    tombstone = database.get_application(application_id, db_path=db_path, include_deleted=True)
    assert tombstone is not None
    assert tombstone["deleted_at"]
    assert tombstone["tombstone_reason"] == "manual_delete"

    audit_events = database.list_audit_events(db_path=db_path, entity_type="application", entity_id=application_id)
    actions = {event["action"] for event in audit_events}
    assert {"create", "update", "archive", "delete"}.issubset(actions)


def test_integrity_check_reports_ok() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "integrity.db"
    database.init_db(db_path)

    report = recovery_service.run_integrity_check(db_path)

    assert report["ok"] is True
    assert report["schema"]["current_version"] == CURRENT_SCHEMA_VERSION
