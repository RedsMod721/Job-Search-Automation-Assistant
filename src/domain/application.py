from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApplicationRecord(BaseModel):
    """Typed view of an application row while preserving legacy extra fields."""

    model_config = ConfigDict(extra="allow")

    application_id: str = ""
    company_name: str = ""
    job_title: str = ""
    job_domain: str = ""
    location: str = ""
    source_platform: str = ""
    application_channel: str = ""
    status: str = "Saved"
    selected_cv: str = ""
    recommended_cv: str = ""
    raw_job_description: str = ""
    required_skills: list[str] = Field(default_factory=list)
    key_responsibilities: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    motivation_letter_required: bool | None = None
    google_sheet_row_id: str = ""
    normalized_company_name: str = ""
    canonical_job_url: str = ""
    external_job_id: str = ""
    job_description_hash: str = ""
    deleted_at: str = ""
    tombstone_reason: str = ""
    record_version: int = 1
    sync_status: str = "PENDING"
    sync_pending: int = 1
    sync_hash: str = ""
    sync_last_attempt_at: str = ""
    sync_last_success_at: str = ""
    sync_last_error: str = ""
    sync_last_source: str = ""
    archived: int = 0

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> ApplicationRecord:
        return cls.model_validate(value)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump()


class CompanyRecord(BaseModel):
    """Typed company search/save payload."""

    model_config = ConfigDict(extra="allow")

    company_id: str = ""
    company_name: str = ""
    company_size: str = ""
    company_industry: str = ""
    company_website: str = ""
    company_linkedin: str = ""
    career_page_url: str = ""
    source: str = ""
    source_url: str = ""
    notes: str = ""
