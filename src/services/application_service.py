from __future__ import annotations

from typing import Any

from src.constants import CV_KEYS, EXTRACTION_LIST_FIELDS, EXTRACTION_SCHEMA_KEYS, STATUS_VALUES

COMPANY_SEARCH_RESULT_FIELDS = (
    "company_name",
    "company_size",
    "company_industry",
    "company_website",
    "company_linkedin",
    "career_page_url",
)


def parse_review_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]

    lines = []
    for line in str(value or "").splitlines():
        cleaned = line.strip().lstrip("-* ").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def list_to_review_text(value: Any) -> str:
    return "\n".join(parse_review_list(value))


def coerce_motivation_letter_required(value: Any) -> bool | None:
    if value is True:
        return True
    if value is False:
        return False
    if value is None:
        return None

    normalized = str(value or "").strip().lower()
    if normalized in {"yes", "true", "required"}:
        return True
    if normalized in {"no", "false", "not required"}:
        return False
    return None


def build_application_from_reviewed_extraction(
    reviewed_extraction: dict[str, Any],
    raw_job_description: str,
    status: str = "To Apply",
    notes: str = "",
) -> dict[str, Any]:
    application: dict[str, Any] = {}
    for key in EXTRACTION_SCHEMA_KEYS:
        value = reviewed_extraction.get(key, "")
        if key in EXTRACTION_LIST_FIELDS:
            application[key] = parse_review_list(value)
        elif key == "motivation_letter_required":
            application[key] = coerce_motivation_letter_required(value)
        else:
            application[key] = "" if value is None else str(value).strip()

    application["raw_job_description"] = raw_job_description.strip()
    application["status"] = status or "To Apply"
    application["notes"] = notes.strip()
    return application


def compact_review_keywords(values: list[Any]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidates = parse_review_list(value)
        if not candidates and str(value or "").strip():
            candidates = [str(value).strip()]
        for candidate in candidates:
            normalized = candidate.strip()
            lookup_key = normalized.lower()
            if normalized and lookup_key not in seen:
                seen.add(lookup_key)
                keywords.append(normalized)
    return keywords


def build_company_search_request(reviewed_extraction: dict[str, Any]) -> dict[str, Any]:
    sector = next(
        (
            str(reviewed_extraction.get(key, "")).strip()
            for key in ("company_industry", "job_domain", "job_title")
            if str(reviewed_extraction.get(key, "")).strip()
        ),
        "",
    )
    location = str(reviewed_extraction.get("location", "")).strip()
    keywords = compact_review_keywords(
        [
            reviewed_extraction.get("company_name", ""),
            reviewed_extraction.get("company_website", ""),
            reviewed_extraction.get("company_linkedin", ""),
            reviewed_extraction.get("career_page_url", ""),
            reviewed_extraction.get("job_title", ""),
            reviewed_extraction.get("job_url", ""),
            reviewed_extraction.get("required_skills", ""),
            reviewed_extraction.get("preferred_qualifications", ""),
        ]
    )
    return {"sector": sector, "location": location, "keywords": keywords}


def has_company_search_input(search_request: dict[str, Any]) -> bool:
    return bool(search_request.get("sector") or search_request.get("location") or search_request.get("keywords"))


def merge_company_search_result(
    reviewed_extraction: dict[str, Any],
    company_result: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(reviewed_extraction)
    for field in COMPANY_SEARCH_RESULT_FIELDS:
        value = company_result.get(field)
        if value is None:
            continue
        cleaned_value = str(value).strip()
        if cleaned_value:
            merged[field] = cleaned_value
    return merged


def company_fields_changed(
    before: dict[str, Any],
    after: dict[str, Any],
) -> bool:
    return any(
        str(before.get(field, "")).strip() != str(after.get(field, "")).strip()
        for field in COMPANY_SEARCH_RESULT_FIELDS
    )


def application_label(item: dict[str, Any]) -> str:
    company = item.get("company_name") or "Unknown company"
    role = item.get("job_title") or "Unknown role"
    application_id = str(item.get("application_id", ""))
    short_id = application_id[:8] if application_id else "no-id"
    return f"{company} - {role} ({short_id})"


def selected_cv_value(value: Any) -> str:
    cv_value = str(value or "").strip()
    return cv_value if cv_value in CV_KEYS else CV_KEYS[-1]


def application_matches_filters(
    application: dict[str, Any],
    *,
    status_filter: str = "All",
    company_query: str = "",
    domain_query: str = "",
    source_filter: str = "All",
    cv_filter: str = "All",
    location_query: str = "",
    include_archived: bool = False,
) -> bool:
    if not include_archived and application.get("archived"):
        return False
    if status_filter != "All" and application.get("status") != status_filter:
        return False
    if source_filter != "All" and application.get("source_platform") != source_filter:
        return False
    if cv_filter != "All" and application.get("selected_cv") != cv_filter:
        return False
    searchable = {
        "company": str(application.get("company_name", "")).lower(),
        "domain": str(application.get("job_domain", "")).lower(),
        "location": str(application.get("location", "")).lower(),
    }
    if company_query and company_query.lower() not in searchable["company"]:
        return False
    if domain_query and domain_query.lower() not in searchable["domain"]:
        return False
    if location_query and location_query.lower() not in searchable["location"]:
        return False
    return True


def build_application_from_company_search_result(
    company_result: dict[str, Any],
    job_title: str = "",
    job_url: str = "",
    status: str = "Saved",
    notes: str = "",
) -> dict[str, Any]:
    company_name = str(company_result.get("company_name", "")).strip()
    source_url = str(company_result.get("source_url", "") or company_result.get("source", "")).strip()
    provenance_notes = [
        "Created from Company Search.",
        f"Source: {source_url}" if source_url else "",
        notes.strip(),
    ]
    return {
        "company_name": company_name,
        "company_size": str(company_result.get("company_size", "") or "").strip(),
        "company_industry": str(company_result.get("company_industry", "") or "").strip(),
        "company_website": str(company_result.get("company_website", "") or "").strip(),
        "company_linkedin": str(company_result.get("company_linkedin", "") or "").strip(),
        "career_page_url": str(company_result.get("career_page_url", "") or "").strip(),
        "job_title": job_title.strip(),
        "job_url": job_url.strip(),
        "status": status if status in STATUS_VALUES else "Saved",
        "source_platform": "Company Website",
        "application_channel": "Company Career Page",
        "notes": "\n".join(part for part in provenance_notes if part),
    }


def build_review_refresh_state(status: str, notes: str) -> dict[str, str]:
    return {"status": status, "notes": notes}


def review_refresh_defaults(state: dict[str, Any] | None) -> tuple[str, str]:
    state = state or {}
    status = str(state.get("status", "To Apply")).strip() or "To Apply"
    if status not in STATUS_VALUES:
        status = "To Apply"
    notes = str(state.get("notes", ""))
    return status, notes
