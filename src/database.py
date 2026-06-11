from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .constants import APPLICATION_COLUMNS, DEFAULT_DATABASE_PATH, LIST_FIELDS
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as connection:
        create_tables(connection)
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
    return _serialize_application(record)


def _serialize_application(record: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(record)
    for field in LIST_FIELDS:
        if field in serialized:
            serialized[field] = serialize_list(serialized[field])
    if "motivation_letter_required" in serialized:
        serialized["motivation_letter_required"] = normalize_boolish(
            serialized["motivation_letter_required"]
        )
    if "archived" in serialized:
        serialized["archived"] = 1 if serialized["archived"] else 0
    return serialized


def _deserialize_application(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    record = dict(row)
    for field in LIST_FIELDS:
        if field in record:
            record[field] = deserialize_list(record[field])
    return record


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
        connection.commit()
    return str(record["application_id"])


def update_application(
    application_id: str,
    updates: dict[str, Any],
    db_path: str | Path | None = None,
) -> None:
    allowed_updates = {
        key: value
        for key, value in updates.items()
        if key in APPLICATION_COLUMNS and key not in {"application_id", "date_created"}
    }
    if not allowed_updates:
        return
    allowed_updates["date_updated"] = now_iso()
    serialized = _serialize_application(allowed_updates)

    assignments = ", ".join(f"{key} = ?" for key in serialized)
    values = list(serialized.values()) + [application_id]
    with _connect(db_path) as connection:
        connection.execute(
            f"UPDATE applications SET {assignments} WHERE application_id = ?",
            values,
        )
        connection.commit()


def get_application(
    application_id: str,
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM applications WHERE application_id = ?",
            (application_id,),
        ).fetchone()
    return _deserialize_application(row) if row else None


def list_applications(
    filters: dict[str, Any] | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    filters = filters or {}
    where_clauses: list[str] = []
    values: list[Any] = []
    for key, value in filters.items():
        if key in APPLICATION_COLUMNS and value not in (None, ""):
            where_clauses.append(f"{key} = ?")
            values.append(value)

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    with _connect(db_path) as connection:
        rows = connection.execute(
            f"SELECT * FROM applications{where_sql} ORDER BY date_created DESC",
            values,
        ).fetchall()
    return [_deserialize_application(row) for row in rows]


def archive_application(application_id: str, db_path: str | Path | None = None) -> None:
    update_application(application_id, {"status": "Archived", "archived": 1}, db_path)


def delete_application(application_id: str, db_path: str | Path | None = None) -> None:
    with _connect(db_path) as connection:
        connection.execute(
            "DELETE FROM applications WHERE application_id = ?",
            (application_id,),
        )
        connection.commit()


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
    }
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"company_id", "date_created"}
    )
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO companies ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(company_id) DO UPDATE SET {updates}
            """,
            [record[column] for column in columns],
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
    }
    columns = list(record)
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"contact_id", "date_created"}
    )
    with _connect(db_path) as connection:
        connection.execute(
            f"""
            INSERT INTO contacts ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(contact_id) DO UPDATE SET {updates}
            """,
            [record[column] for column in columns],
        )
        connection.commit()
    return str(contact_id)
