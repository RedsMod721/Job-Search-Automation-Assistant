from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src import database
from src.normalization import canonicalize_url, content_hash, normalize_company_name, normalize_email
from src.utils import resolve_path


class DuplicateGroup(BaseModel):
    entity_type: str
    reason: str
    match_key: str
    record_ids: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)


def _group_records(
    records: list[dict[str, Any]],
    *,
    entity_type: str,
    reason: str,
    key_field: str,
    id_field: str,
    label_fields: tuple[str, ...],
) -> list[DuplicateGroup]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = str(record.get(key_field, "") or "").strip()
        if key:
            grouped.setdefault(key, []).append(record)

    duplicate_groups: list[DuplicateGroup] = []
    for key, values in grouped.items():
        if len(values) < 2:
            continue
        duplicate_groups.append(
            DuplicateGroup(
                entity_type=entity_type,
                reason=reason,
                match_key=key,
                record_ids=[str(item.get(id_field, "")) for item in values],
                labels=[
                    " - ".join(str(item.get(field, "") or "").strip() for field in label_fields).strip(" -")
                    for item in values
                ],
            )
        )
    return duplicate_groups


def find_duplicate_applications(db_path: str | Path | None = None) -> list[DuplicateGroup]:
    applications = database.list_applications(db_path=db_path, include_deleted=False)
    normalized_records: list[dict[str, Any]] = []
    for application in applications:
        normalized = dict(application)
        normalized["normalized_company_name"] = normalized.get("normalized_company_name") or normalize_company_name(
            str(application.get("company_name", ""))
        )
        normalized["canonical_job_url"] = normalized.get("canonical_job_url") or canonicalize_url(
            str(application.get("job_url", ""))
        )
        normalized["job_description_hash"] = normalized.get("job_description_hash") or content_hash(
            str(application.get("raw_job_description", ""))
        )
        normalized["company_role_key"] = "::".join(
            [
                str(normalized.get("normalized_company_name", "")),
                str(application.get("job_title", "")).strip().lower(),
                str(application.get("location", "")).strip().lower(),
            ]
        )
        normalized_records.append(normalized)

    duplicate_groups: list[DuplicateGroup] = []
    duplicate_groups.extend(
        _group_records(
            normalized_records,
            entity_type="application",
            reason="same external job id",
            key_field="external_job_id",
            id_field="application_id",
            label_fields=("company_name", "job_title"),
        )
    )
    duplicate_groups.extend(
        _group_records(
            normalized_records,
            entity_type="application",
            reason="same canonical job url",
            key_field="canonical_job_url",
            id_field="application_id",
            label_fields=("company_name", "job_title"),
        )
    )
    duplicate_groups.extend(
        _group_records(
            normalized_records,
            entity_type="application",
            reason="same job description hash",
            key_field="job_description_hash",
            id_field="application_id",
            label_fields=("company_name", "job_title"),
        )
    )
    duplicate_groups.extend(
        _group_records(
            normalized_records,
            entity_type="application",
            reason="same company, role, and location",
            key_field="company_role_key",
            id_field="application_id",
            label_fields=("company_name", "job_title", "location"),
        )
    )
    return duplicate_groups


def _fetch_table(db_path: str | Path | None, table_name: str) -> list[dict[str, Any]]:
    path = resolve_path(db_path or "database/applications.db")
    if not path.exists():
        return []
    uri = f"file:{path.resolve().as_posix()}?mode=rw&nolock=1"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=TRUNCATE")
        connection.execute("PRAGMA foreign_keys=ON")
        rows = connection.execute(
            f"SELECT * FROM {table_name} WHERE deleted_at IS NULL OR deleted_at = ''"  # nosec B608
        ).fetchall()
    return [dict(row) for row in rows]


def find_duplicate_companies(db_path: str | Path | None = None) -> list[DuplicateGroup]:
    companies = _fetch_table(db_path, "companies")
    for company in companies:
        company["normalized_company_name"] = company.get("normalized_company_name") or normalize_company_name(
            str(company.get("company_name", ""))
        )
        company["canonical_company_website"] = company.get("canonical_company_website") or canonicalize_url(
            str(company.get("company_website", ""))
        )
    return [
        *_group_records(
            companies,
            entity_type="company",
            reason="same normalized company name",
            key_field="normalized_company_name",
            id_field="company_id",
            label_fields=("company_name",),
        ),
        *_group_records(
            companies,
            entity_type="company",
            reason="same canonical company website",
            key_field="canonical_company_website",
            id_field="company_id",
            label_fields=("company_name", "company_website"),
        ),
    ]


def find_duplicate_contacts(db_path: str | Path | None = None) -> list[DuplicateGroup]:
    contacts = _fetch_table(db_path, "contacts")
    for contact in contacts:
        contact["normalized_full_name"] = contact.get("normalized_full_name") or normalize_company_name(
            str(contact.get("full_name", ""))
        )
        contact["normalized_email"] = contact.get("normalized_email") or normalize_email(str(contact.get("email", "")))
        contact["company_email_key"] = (
            "::".join([str(contact.get("company_id", "")), str(contact.get("normalized_email", ""))])
            if contact.get("normalized_email")
            else ""
        )
        contact["canonical_linkedin_url"] = canonicalize_url(str(contact.get("linkedin_url", "")))
    return [
        *_group_records(
            contacts,
            entity_type="contact",
            reason="same company and email",
            key_field="company_email_key",
            id_field="contact_id",
            label_fields=("full_name", "email"),
        ),
        *_group_records(
            contacts,
            entity_type="contact",
            reason="same linkedin url",
            key_field="canonical_linkedin_url",
            id_field="contact_id",
            label_fields=("full_name", "linkedin_url"),
        ),
    ]


def find_all_duplicates(db_path: str | Path | None = None) -> dict[str, Any]:
    applications = find_duplicate_applications(db_path)
    companies = find_duplicate_companies(db_path)
    contacts = find_duplicate_contacts(db_path)
    return {
        "applications": [group.model_dump() for group in applications],
        "companies": [group.model_dump() for group in companies],
        "contacts": [group.model_dump() for group in contacts],
        "summary": {
            "application_groups": len(applications),
            "company_groups": len(companies),
            "contact_groups": len(contacts),
            "total_groups": len(applications) + len(companies) + len(contacts),
        },
    }
