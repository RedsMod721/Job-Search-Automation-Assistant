from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .constants import APPLICATION_COLUMNS, DEFAULT_DATABASE_PATH, LIST_FIELDS
from .database_migrations import run_migrations
from .normalization import canonicalize_url, content_hash, normalize_company_name, normalize_email
from .utils import (
    deserialize_list,
    generate_uuid,
    normalize_boolish,
    now_iso,
    resolve_path,
    serialize_list,
)

APPLICATION_DEFAULTS: dict[str, Any] = {
    "company_name": "",
    "company_size": "",
    "company_industry": "",
    "company_website": "",
    "company_linkedin": "",
    "career_page_url": "",
    "job_title": "",
    "job_domain": "",
    "seniority_level": "",
    "contract_type": "",
    "job_length": "",
    "salary": "",
    "location": "",
    "remote_policy": "",
    "relocation_required": "",
    "key_responsibilities": [],
    "required_skills": [],
    "preferred_qualifications": [],
    "detected_language": "",
    "raw_job_description": "",
    "source_platform": "",
    "application_channel": "",
    "job_url": "",
    "status": "Saved",
    "date_applied": "",
    "follow_up_date": "",
    "contact_person": "",
    "contact_url": "",
    "notes": "",
    "recommended_cv": "",
    "selected_cv": "",
    "cv_confidence_score": None,
    "cv_recommendation_reason": "",
    "cv_matched_keywords": [],
    "motivation_letter_required": None,
    "motivation_letter_language": "",
    "motivation_letter_file": "",
    "form_answers_file": "",
    "google_sheet_row_id": "",
    "normalized_company_name": "",
    "canonical_job_url": "",
    "external_job_id": "",
    "job_description_hash": "",
    "deleted_at": "",
    "tombstone_reason": "",
    "record_version": 1,
    "sync_status": "PENDING",
    "sync_pending": 1,
    "sync_hash": "",
    "sync_last_attempt_at": "",
    "sync_last_success_at": "",
    "sync_last_error": "",
    "sync_last_source": "",
    "archived": 0,
}


def _db_path(db_path: str | Path | None = None) -> Path:
    return resolve_path(db_path or DEFAULT_DATABASE_PATH)


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _db_path(db_path).resolve()
    uri = f"file:{path.as_posix()}?mode=rwc&nolock=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    # OneDrive-backed folders can reject SQLite delete-journal locking.
    connection.execute("PRAGMA journal_mode=TRUNCATE")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db(db_path: str | Path | None = None) -> Path:
    path = _db_path(db_path)
    existed_before = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        create_tables(connection)
    run_migrations(path, create_backup=existed_before)
    return path


def create_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS applications (
            application_id TEXT PRIMARY KEY,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            company_name TEXT,
            company_size TEXT,
            company_industry TEXT,
            company_website TEXT,
            company_linkedin TEXT,
            career_page_url TEXT,

            job_title TEXT,
            job_domain TEXT,
            seniority_level TEXT,
            contract_type TEXT,
            job_length TEXT,
            salary TEXT,
            location TEXT,
            remote_policy TEXT,
            relocation_required TEXT,

            key_responsibilities TEXT,
            required_skills TEXT,
            preferred_qualifications TEXT,
            detected_language TEXT,
            raw_job_description TEXT,

            source_platform TEXT,
            application_channel TEXT,
            job_url TEXT,
            status TEXT,
            date_applied TEXT,
            follow_up_date TEXT,
            contact_person TEXT,
            contact_url TEXT,
            notes TEXT,

            recommended_cv TEXT,
            selected_cv TEXT,
            cv_confidence_score REAL,
            cv_recommendation_reason TEXT,
            cv_matched_keywords TEXT,

            motivation_letter_required INTEGER,
            motivation_letter_language TEXT,
            motivation_letter_file TEXT,

            form_answers_file TEXT,

            google_sheet_row_id TEXT,

            archived INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS companies (
            company_id TEXT PRIMARY KEY,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            company_name TEXT NOT NULL,
            company_size TEXT,
            company_industry TEXT,
            company_website TEXT,
            company_linkedin TEXT,
            career_page_url TEXT,

            country TEXT,
            city TEXT,

            source TEXT,
            source_url TEXT,

            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS contacts (
            contact_id TEXT PRIMARY KEY,
            company_id TEXT,

            date_created TEXT NOT NULL,
            date_updated TEXT NOT NULL,

            full_name TEXT,
            role_title TEXT,
            department TEXT,
            email TEXT,
            linkedin_url TEXT,

            source_type TEXT,
            source_url TEXT,
            manually_verified INTEGER DEFAULT 0,

            notes TEXT,

            FOREIGN KEY(company_id) REFERENCES companies(company_id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,

            document_type TEXT,
            domain TEXT,
            label TEXT,
            file_path TEXT,
            language TEXT,
            active INTEGER DEFAULT 1,
            version TEXT,
            notes TEXT
        );
        """
    )
    connection.commit()


def _prepare_application_record(application: dict[str, Any] | None = None) -> dict[str, Any]:
    application = application or {}
    timestamp = now_iso()
    record = dict(APPLICATION_DEFAULTS)
    record.update({key: application[key] for key in APPLICATION_DEFAULTS if key in application})
    record["application_id"] = application.get("application_id") or generate_uuid()
    record["date_created"] = application.get("date_created") or timestamp
    record["date_updated"] = application.get("date_updated") or timestamp
    _enrich_application_record(record)
    return _serialize_application(record)


def _enrich_application_record(record: dict[str, Any]) -> None:
    if "company_name" in record:
        record["normalized_company_name"] = normalize_company_name(str(record.get("company_name", "")))
    if "job_url" in record:
        record["canonical_job_url"] = canonicalize_url(str(record.get("job_url", "")))
    if "raw_job_description" in record:
        record["job_description_hash"] = content_hash(str(record.get("raw_job_description", "")))


def _serialize_application(record: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(record)
    for field in LIST_FIELDS:
        if field in serialized:
            serialized[field] = serialize_list(serialized[field])
    if "motivation_letter_required" in serialized:
        serialized["motivation_letter_required"] = normalize_boolish(serialized["motivation_letter_required"])
    if "archived" in serialized:
        serialized["archived"] = 1 if serialized["archived"] else 0
    return serialized


def _deserialize_application(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    record = dict(row)
    for field in LIST_FIELDS:
        if field in record:
            record[field] = deserialize_list(record[field])
    return record


def _json_payload(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, ensure_ascii=True, sort_keys=True, default=str)


def _record_audit_event(
    connection: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events (
            audit_event_id,
            date_created,
            entity_type,
            entity_id,
            action,
            actor,
            before_json,
            after_json,
            details_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            generate_uuid(),
            now_iso(),
            entity_type,
            entity_id,
            action,
            "local_app",
            _json_payload(before),
            _json_payload(after),
            _json_payload(details),
        ),
    )


def _application_by_id(
    connection: sqlite3.Connection,
    application_id: str,
    *,
    include_deleted: bool = False,
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT * FROM applications WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    if not row:
        return None
    application = _deserialize_application(row)
    if not include_deleted and application.get("deleted_at"):
        return None
    return application


def _next_record_version(before: dict[str, Any] | None) -> int:
    if before is None:
        return 1
    try:
        return int(before.get("record_version") or 0) + 1
    except (TypeError, ValueError):
        return 1


def _sync_operation_for_audit_action(audit_action: str | None) -> str:
    if audit_action in {"archive", "delete"}:
        return audit_action
    return "update"


def _record_sync_change(
    connection: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: str,
    operation: str,
    payload: dict[str, Any] | None,
) -> None:
    timestamp = now_iso()
    local_version = 1
    if payload is not None:
        try:
            local_version = int(payload.get("record_version") or 1)
        except (TypeError, ValueError):
            local_version = 1

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
        VALUES (?, ?, '', ?, NULL, '', '', '', 'PENDING')
        ON CONFLICT(entity_type, entity_id) DO UPDATE SET
            local_version = excluded.local_version,
            sync_status = 'PENDING'
        """,
        (entity_type, entity_id, local_version),
    )
    connection.execute(
        """
        INSERT INTO sync_outbox (
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
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, '', '', 'PENDING')
        """,
        (
            generate_uuid(),
            entity_type,
            entity_id,
            operation,
            _json_payload(payload),
            timestamp,
            timestamp,
        ),
    )


def add_application(application: dict[str, Any], db_path: str | Path | None = None) -> str:
    record = _prepare_application_record(application)
    columns = [column for column in APPLICATION_COLUMNS if column in record]
    placeholders = ", ".join("?" for _ in columns)
    column_sql = ", ".join(columns)
    values = [record[column] for column in columns]

    with _connect(db_path) as connection:
        connection.execute(
            f"INSERT INTO applications ({column_sql}) VALUES ({placeholders})",
            values,
        )
        stored = _application_by_id(connection, str(record["application_id"]), include_deleted=True)
        _record_audit_event(
            connection,
            entity_type="application",
            entity_id=str(record["application_id"]),
            action="create",
            after=stored,
        )
        _record_sync_change(
            connection,
            entity_type="application",
            entity_id=str(record["application_id"]),
            operation="create",
            payload=stored,
        )
        connection.commit()
    return str(record["application_id"])


def update_application(
    application_id: str,
    updates: dict[str, Any],
    db_path: str | Path | None = None,
    audit_action: str | None = "update",
    enqueue_sync: bool = True,
) -> None:
    allowed_updates = {
        key: value
        for key, value in updates.items()
        if key in APPLICATION_COLUMNS and key not in {"application_id", "date_created"}
    }
    if not allowed_updates:
        return
    _enrich_application_record(allowed_updates)
    with _connect(db_path) as connection:
        before = _application_by_id(connection, application_id, include_deleted=True)
        if before is None:
            return
        if enqueue_sync:
            allowed_updates["record_version"] = _next_record_version(before)
            allowed_updates["sync_pending"] = 1
            allowed_updates["sync_status"] = "PENDING"
            allowed_updates["sync_last_error"] = ""
        if enqueue_sync or audit_action is not None:
            allowed_updates["date_updated"] = now_iso()
        serialized = _serialize_application(allowed_updates)

        assignments = ", ".join(f"{key} = ?" for key in serialized)
        values = list(serialized.values()) + [application_id]
        connection.execute(
            f"UPDATE applications SET {assignments} WHERE application_id = ?",
            values,
        )
        after = _application_by_id(connection, application_id, include_deleted=True)
        if audit_action is not None:
            _record_audit_event(
                connection,
                entity_type="application",
                entity_id=application_id,
                action=audit_action,
                before=before,
                after=after,
                details={"updated_fields": sorted(serialized)},
            )
        if enqueue_sync:
            _record_sync_change(
                connection,
                entity_type="application",
                entity_id=application_id,
                operation=_sync_operation_for_audit_action(audit_action),
                payload=after,
            )
        connection.commit()


def get_application(
    application_id: str,
    db_path: str | Path | None = None,
    include_deleted: bool = False,
) -> dict[str, Any] | None:
    with _connect(db_path) as connection:
        return _application_by_id(connection, application_id, include_deleted=include_deleted)


def list_applications(
    filters: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    filters = filters or {}
    where_clauses: list[str] = []
    values: list[Any] = []
    for key, value in filters.items():
        if key in APPLICATION_COLUMNS and value not in (None, ""):
            where_clauses.append(f"{key} = ?")
            values.append(value)
    if not include_deleted:
        where_clauses.append("(deleted_at IS NULL OR deleted_at = '')")

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM applications{where_sql} ORDER BY date_created DESC",
            values,
        ).fetchall()
    return [_deserialize_application(row) for row in rows]


def archive_application(application_id: str, db_path: str | Path | None = None) -> None:
    update_application(application_id, {"status": "Archived", "archived": 1}, db_path, audit_action="archive")


def delete_application(application_id: str, db_path: str | Path | None = None) -> None:
    update_application(
        application_id,
        {
            "status": "Archived",
            "archived": 1,
            "deleted_at": now_iso(),
            "tombstone_reason": "manual_delete",
        },
        db_path,
        audit_action="delete",
    )


def upsert_company(company: dict[str, Any], db_path: str | Path | None = None) -> str:
    timestamp = now_iso()
    company_id = company.get("company_id") or generate_uuid()
    record = {
        "company_id": company_id,
        "date_created": company.get("date_created") or timestamp,
        "date_updated": timestamp,
        "company_name": company.get("company_name", ""),
        "company_size": company.get("company_size", ""),
        "company_industry": company.get("company_industry", ""),
        "company_website": company.get("company_website", ""),
        "company_linkedin": company.get("company_linkedin", ""),
        "career_page_url": company.get("career_page_url", ""),
        "country": company.get("country", ""),
        "city": company.get("city", ""),
        "source": company.get("source", ""),
        "source_url": company.get("source_url", ""),
        "notes": company.get("notes", ""),
        "normalized_company_name": normalize_company_name(str(company.get("company_name", ""))),
        "canonical_company_website": canonicalize_url(str(company.get("company_website", ""))),
        "deleted_at": company.get("deleted_at", ""),
    }
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}" for column in columns if column not in {"company_id", "date_created"}
    )
    with _connect(db_path) as connection:
        before_row = connection.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
        connection.execute(
            f"""
            INSERT INTO companies ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(company_id) DO UPDATE SET {updates}
            """,
            [record[column] for column in columns],
        )
        after_row = connection.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
        _record_audit_event(
            connection,
            entity_type="company",
            entity_id=str(company_id),
            action="update" if before_row else "create",
            before=dict(before_row) if before_row else None,
            after=dict(after_row) if after_row else None,
        )
        connection.commit()
    return str(company_id)


def upsert_contact(contact: dict[str, Any], db_path: str | Path | None = None) -> str:
    timestamp = now_iso()
    contact_id = contact.get("contact_id") or generate_uuid()
    record = {
        "contact_id": contact_id,
        "company_id": contact.get("company_id", ""),
        "date_created": contact.get("date_created") or timestamp,
        "date_updated": timestamp,
        "full_name": contact.get("full_name", ""),
        "role_title": contact.get("role_title", ""),
        "department": contact.get("department", ""),
        "email": contact.get("email", ""),
        "linkedin_url": contact.get("linkedin_url", ""),
        "source_type": contact.get("source_type", ""),
        "source_url": contact.get("source_url", ""),
        "manually_verified": 1 if contact.get("manually_verified") else 0,
        "notes": contact.get("notes", ""),
        "normalized_full_name": normalize_company_name(str(contact.get("full_name", ""))),
        "normalized_email": normalize_email(str(contact.get("email", ""))),
        "deleted_at": contact.get("deleted_at", ""),
    }
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}" for column in columns if column not in {"contact_id", "date_created"}
    )
    with _connect(db_path) as connection:
        before_row = connection.execute("SELECT * FROM contacts WHERE contact_id = ?", (contact_id,)).fetchone()
        connection.execute(
            f"""
            INSERT INTO contacts ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(contact_id) DO UPDATE SET {updates}
            """,
            [record[column] for column in columns],
        )
        after_row = connection.execute("SELECT * FROM contacts WHERE contact_id = ?", (contact_id,)).fetchone()
        _record_audit_event(
            connection,
            entity_type="contact",
            entity_id=str(contact_id),
            action="update" if before_row else "create",
            before=dict(before_row) if before_row else None,
            after=dict(after_row) if after_row else None,
        )
        connection.commit()
    return str(contact_id)


def list_audit_events(
    db_path: str | Path | None = None,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    where_clauses: list[str] = []
    values: list[Any] = []
    if entity_type:
        where_clauses.append("entity_type = ?")
        values.append(entity_type)
    if entity_id:
        where_clauses.append("entity_id = ?")
        values.append(entity_id)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    values.append(limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM audit_events
            {where_sql}
            ORDER BY date_created DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def hard_delete_application(application_id: str, db_path: str | Path | None = None) -> None:
    with _connect(db_path) as connection:
        before = _application_by_id(connection, application_id, include_deleted=True)
        connection.execute(
            "DELETE FROM applications WHERE application_id = ?",
            (application_id,),
        )
        if before is not None:
            _record_audit_event(
                connection,
                entity_type="application",
                entity_id=application_id,
                action="hard_delete",
                before=before,
            )
        connection.commit()


def enqueue_application_sync(
    application_id: str,
    *,
    operation: str = "manual",
    db_path: str | Path | None = None,
) -> None:
    with _connect(db_path) as connection:
        application = _application_by_id(connection, application_id, include_deleted=True)
        if application is None:
            return
        connection.execute(
            """
            UPDATE applications
            SET sync_pending = 1,
                sync_status = 'PENDING',
                sync_last_error = ''
            WHERE application_id = ?
            """,
            (application_id,),
        )
        application = _application_by_id(connection, application_id, include_deleted=True)
        _record_sync_change(
            connection,
            entity_type="application",
            entity_id=application_id,
            operation=operation,
            payload=application,
        )
        connection.commit()


def enqueue_all_applications_sync(
    *,
    operation: str = "manual",
    db_path: str | Path | None = None,
    include_deleted: bool = True,
) -> int:
    applications = list_applications(db_path=db_path, include_deleted=include_deleted)
    for application in applications:
        enqueue_application_sync(str(application["application_id"]), operation=operation, db_path=db_path)
    return len(applications)


def list_due_sync_outbox(
    db_path: str | Path | None = None,
    *,
    limit: int = 50,
    force: bool = False,
) -> list[dict[str, Any]]:
    timestamp = now_iso()
    values: list[Any] = ["PENDING", "RETRY"]
    due_clause = ""
    if not force:
        due_clause = "AND (next_attempt_at IS NULL OR next_attempt_at = '' OR next_attempt_at <= ?)"
        values.append(timestamp)
    values.append(limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM sync_outbox
            WHERE status IN (?, ?)
            {due_clause}
            ORDER BY created_at ASC
            LIMIT ?
            """,
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def mark_sync_outbox_processing(
    outbox_ids: list[str],
    *,
    db_path: str | Path | None = None,
) -> None:
    if not outbox_ids:
        return
    timestamp = now_iso()
    with _connect(db_path) as connection:
        for outbox_id in outbox_ids:
            connection.execute(
                """
                UPDATE sync_outbox
                SET status = 'PROCESSING',
                    updated_at = ?
                WHERE outbox_id = ?
                """,
                (timestamp, outbox_id),
            )
        connection.commit()


def mark_sync_outbox_completed(
    outbox_ids: list[str],
    *,
    db_path: str | Path | None = None,
) -> None:
    if not outbox_ids:
        return
    timestamp = now_iso()
    with _connect(db_path) as connection:
        for outbox_id in outbox_ids:
            connection.execute(
                """
                UPDATE sync_outbox
                SET status = 'COMPLETED',
                    updated_at = ?,
                    last_error = ''
                WHERE outbox_id = ?
                """,
                (timestamp, outbox_id),
            )
        connection.commit()


def mark_sync_outbox_retry(
    outbox_ids: list[str],
    error: str,
    *,
    db_path: str | Path | None = None,
    max_attempts: int = 5,
    backoff_seconds: int = 60,
) -> None:
    if not outbox_ids:
        return
    from datetime import datetime, timedelta

    timestamp = now_iso()
    with _connect(db_path) as connection:
        for outbox_id in outbox_ids:
            row = connection.execute(
                "SELECT attempt_count FROM sync_outbox WHERE outbox_id = ?",
                (outbox_id,),
            ).fetchone()
            attempts = int(row["attempt_count"] if row else 0) + 1
            status = "DEAD_LETTER" if attempts >= max_attempts else "RETRY"
            delay_seconds = max(backoff_seconds, 1) * attempts
            next_attempt_at = (datetime.now().replace(microsecond=0) + timedelta(seconds=delay_seconds)).isoformat()
            connection.execute(
                """
                UPDATE sync_outbox
                SET status = ?,
                    attempt_count = ?,
                    next_attempt_at = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE outbox_id = ?
                """,
                (status, attempts, next_attempt_at, error, timestamp, outbox_id),
            )
        connection.commit()


def update_application_sync_success(
    application_id: str,
    *,
    row_id: str,
    sync_hash: str,
    source: str,
    db_path: str | Path | None = None,
) -> None:
    timestamp = now_iso()
    update_application(
        application_id,
        {
            "google_sheet_row_id": row_id,
            "sync_pending": 0,
            "sync_status": "SYNCED",
            "sync_hash": sync_hash,
            "sync_last_attempt_at": timestamp,
            "sync_last_success_at": timestamp,
            "sync_last_error": "",
            "sync_last_source": source,
        },
        db_path=db_path,
        audit_action=None,
        enqueue_sync=False,
    )
    with _connect(db_path) as connection:
        application = _application_by_id(connection, application_id, include_deleted=True)
        local_version = int(application.get("record_version") or 1) if application else 1
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
            VALUES ('application', ?, ?, ?, ?, ?, ?, ?, 'SYNCED')
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                remote_row_key = excluded.remote_row_key,
                local_version = excluded.local_version,
                remote_version = excluded.remote_version,
                last_synced_hash = excluded.last_synced_hash,
                last_synced_at = excluded.last_synced_at,
                last_sync_source = excluded.last_sync_source,
                sync_status = excluded.sync_status
            """,
            (application_id, row_id, local_version, local_version, sync_hash, timestamp, source),
        )
        connection.commit()


def update_application_sync_failure(
    application_id: str,
    error: str,
    *,
    db_path: str | Path | None = None,
) -> None:
    update_application(
        application_id,
        {
            "sync_pending": 1,
            "sync_status": "ERROR",
            "sync_last_attempt_at": now_iso(),
            "sync_last_error": error,
        },
        db_path=db_path,
        audit_action=None,
        enqueue_sync=False,
    )


def record_sync_run(
    *,
    mode: str,
    status: str,
    synced: int = 0,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    db_path: str | Path | None = None,
) -> str:
    timestamp = now_iso()
    sync_run_id = generate_uuid()
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO sync_runs (
                sync_run_id,
                started_at,
                finished_at,
                mode,
                status,
                synced,
                created,
                updated,
                skipped,
                warnings_json,
                errors_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sync_run_id,
                timestamp,
                timestamp,
                mode,
                status,
                synced,
                created,
                updated,
                skipped,
                json.dumps(warnings or [], ensure_ascii=True),
                json.dumps(errors or [], ensure_ascii=True),
            ),
        )
        connection.commit()
    return sync_run_id


def sync_status_summary(db_path: str | Path | None = None) -> dict[str, Any]:
    with _connect(db_path) as connection:
        table_names = {
            str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "sync_outbox" not in table_names or "sync_runs" not in table_names:
            return {
                "outbox": {},
                "applications": {},
                "last_run": None,
                "pending_migration": True,
            }
        outbox_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                "SELECT status, COUNT(*) FROM sync_outbox GROUP BY status ORDER BY status"
            ).fetchall()
        }
        application_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                """
                SELECT COALESCE(NULLIF(sync_status, ''), 'UNKNOWN'), COUNT(*)
                FROM applications
                WHERE deleted_at IS NULL OR deleted_at = ''
                GROUP BY COALESCE(NULLIF(sync_status, ''), 'UNKNOWN')
                """
            ).fetchall()
        }
        last_run = connection.execute(
            """
            SELECT *
            FROM sync_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "outbox": outbox_counts,
        "applications": application_counts,
        "last_run": dict(last_run) if last_run else None,
    }


def record_extraction_corrections(
    corrections: list[dict[str, Any]],
    db_path: str | Path | None = None,
) -> int:
    if not corrections:
        return 0
    timestamp = now_iso()
    with _connect(db_path) as connection:
        for correction in corrections:
            connection.execute(
                """
                INSERT INTO extraction_corrections (
                    correction_id,
                    date_created,
                    application_id,
                    fixture_id,
                    raw_text_hash,
                    field_name,
                    original_value_json,
                    corrected_value_json,
                    prompt_version,
                    model_name,
                    model_parameters_json,
                    source,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    correction.get("correction_id") or generate_uuid(),
                    correction.get("date_created") or timestamp,
                    correction.get("application_id", ""),
                    correction.get("fixture_id", ""),
                    correction.get("raw_text_hash", ""),
                    correction.get("field_name", ""),
                    json.dumps(correction.get("original_value"), ensure_ascii=True, default=str),
                    json.dumps(correction.get("corrected_value"), ensure_ascii=True, default=str),
                    correction.get("prompt_version", ""),
                    correction.get("model_name", ""),
                    _json_payload(correction.get("model_parameters")),
                    correction.get("source", "review_form"),
                    correction.get("notes", ""),
                ),
            )
        connection.commit()
    return len(corrections)


def list_extraction_corrections(
    db_path: str | Path | None = None,
    *,
    application_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    where_clauses: list[str] = []
    values: list[Any] = []
    if application_id:
        where_clauses.append("application_id = ?")
        values.append(application_id)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    values.append(limit)
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM extraction_corrections
            {where_sql}
            ORDER BY date_created DESC
            LIMIT ?
            """,
            values,
        ).fetchall()
    return [dict(row) for row in rows]


def record_extraction_evaluation_run(
    run: dict[str, Any],
    fixture_results: list[dict[str, Any]],
    db_path: str | Path | None = None,
) -> str:
    evaluation_run_id = str(run.get("evaluation_run_id") or generate_uuid())
    with _connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO extraction_evaluation_runs (
                evaluation_run_id,
                dataset_version,
                prompt_version,
                model_name,
                model_parameters_json,
                started_at,
                completed_at,
                runner,
                status,
                aggregate_metrics_json,
                output_path,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evaluation_run_id,
                run.get("dataset_version", ""),
                run.get("prompt_version", ""),
                run.get("model_name", ""),
                _json_payload(run.get("model_parameters")),
                run.get("started_at", now_iso()),
                run.get("completed_at", ""),
                run.get("runner", ""),
                run.get("status", ""),
                _json_payload(run.get("aggregate_metrics")),
                run.get("output_path", ""),
                run.get("notes", ""),
            ),
        )
        connection.execute(
            "DELETE FROM extraction_evaluation_results WHERE evaluation_run_id = ?",
            (evaluation_run_id,),
        )
        for result in fixture_results:
            aggregate = result.get("aggregate", {})
            connection.execute(
                """
                INSERT INTO extraction_evaluation_results (
                    result_id,
                    evaluation_run_id,
                    fixture_id,
                    role_family,
                    language,
                    source_platform,
                    ats_source,
                    json_valid,
                    latency_seconds,
                    aggregate_metrics_json,
                    validation_issues_json,
                    field_results_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    generate_uuid(),
                    evaluation_run_id,
                    result.get("fixture_id", ""),
                    result.get("role_family", ""),
                    result.get("language", ""),
                    result.get("source_platform", ""),
                    result.get("ats_source", ""),
                    1 if aggregate.get("json_valid", True) else 0,
                    float(aggregate.get("latency_seconds", 0.0) or 0.0),
                    _json_payload(aggregate),
                    json.dumps(result.get("validation_issues", []), ensure_ascii=True, default=str),
                    _json_payload(result.get("field_results")),
                ),
            )
        connection.commit()
    return evaluation_run_id


def extraction_quality_summary(db_path: str | Path | None = None) -> dict[str, Any]:
    with _connect(db_path) as connection:
        table_names = {
            str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        if "extraction_corrections" not in table_names or "extraction_evaluation_runs" not in table_names:
            return {"pending_migration": True, "corrections": {}, "latest_evaluation": None}
        correction_counts = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                """
                SELECT field_name, COUNT(*)
                FROM extraction_corrections
                GROUP BY field_name
                ORDER BY COUNT(*) DESC, field_name
                """
            ).fetchall()
        }
        latest_run = connection.execute(
            """
            SELECT *
            FROM extraction_evaluation_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
    latest_evaluation = dict(latest_run) if latest_run else None
    if latest_evaluation:
        try:
            latest_evaluation["aggregate_metrics"] = json.loads(
                str(latest_evaluation.pop("aggregate_metrics_json") or "{}")
            )
        except json.JSONDecodeError:
            latest_evaluation["aggregate_metrics"] = {}
    return {
        "pending_migration": False,
        "corrections": correction_counts,
        "latest_evaluation": latest_evaluation,
    }
