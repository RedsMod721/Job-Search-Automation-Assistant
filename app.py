from __future__ import annotations

from typing import Any

import streamlit as st

from src import (
    company_search,
    cv_matcher,
    database,
    excel_exporter,
    extractor,
    form_helper,
    letter_generator,
    sheets_sync,
)
from src.constants import (
    APPLICATION_CHANNEL_VALUES,
    CONFIG_FILES,
    CONTRACT_TYPE_VALUES,
    CV_KEYS,
    EXTRACTION_LIST_FIELDS,
    EXTRACTION_SCHEMA_KEYS,
    SOURCE_PLATFORM_VALUES,
    STATUS_VALUES,
)
from src.utils import configure_logging, ensure_directories, load_app_config, resolve_path, write_yaml

COMPANY_SEARCH_RESULT_FIELDS = (
    "company_name",
    "company_size",
    "company_industry",
    "company_website",
    "company_linkedin",
    "career_page_url",
)
PENDING_REVIEW_STATE_KEY = "pending_job_extraction_review_state"


def bootstrap() -> dict[str, dict[str, Any]]:
    ensure_directories()
    configs = load_app_config()
    configure_logging(configs.get("settings", {}))
    db_path = configs["settings"].get("database", {}).get("path", "database/applications.db")
    database.init_db(db_path)
    return configs


def _db_path_from_configs(configs: dict[str, dict[str, Any]]) -> str:
    return configs["settings"].get("database", {}).get("path", "database/applications.db")


def load_applications(configs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return database.list_applications(db_path=_db_path_from_configs(configs))


def _parse_review_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]

    lines = []
    for line in str(value or "").splitlines():
        cleaned = line.strip().lstrip("-* ").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _list_to_review_text(value: Any) -> str:
    return "\n".join(_parse_review_list(value))


def _coerce_motivation_letter_required(value: Any) -> bool | None:
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
            application[key] = _parse_review_list(value)
        elif key == "motivation_letter_required":
            application[key] = _coerce_motivation_letter_required(value)
        else:
            application[key] = "" if value is None else str(value).strip()

    application["raw_job_description"] = raw_job_description.strip()
    application["status"] = status or "To Apply"
    application["notes"] = notes.strip()
    return application


def _store_pending_extraction(extraction: dict[str, Any], raw_text: str) -> None:
    st.session_state["pending_job_extraction"] = extraction
    st.session_state["pending_job_extraction_raw_text"] = raw_text
    st.session_state["pending_job_extraction_version"] = (
        st.session_state.get("pending_job_extraction_version", 0) + 1
    )


def _clear_pending_extraction() -> None:
    for key in (
        "pending_job_extraction",
        "pending_job_extraction_raw_text",
        "pending_job_extraction_version",
    ):
        st.session_state.pop(key, None)


def _set_extraction_notice(level: str, message: str) -> None:
    st.session_state["job_extraction_notice"] = {"level": level, "message": message}


def _review_text(pending_extraction: dict[str, Any], key: str) -> str:
    value = pending_extraction.get(key, "")
    return "" if value is None else str(value)


def _run_extraction(raw_text: str, settings: dict[str, Any]) -> None:
    llm_settings = settings.get("llm", {})
    extraction = extractor.extract_job_post(
        raw_text,
        model=llm_settings.get("model", "qwen2.5:7b"),
        fallback_models=list(llm_settings.get("fallback_models", [])),
        timeout_seconds=int(llm_settings.get("timeout_seconds", 120)),
        temperature=float(llm_settings.get("temperature", 0.2)),
    )
    _store_pending_extraction(extraction, raw_text)


def _compact_review_keywords(values: list[Any]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidates = _parse_review_list(value)
        if not candidates and str(value or "").strip():
            candidates = [str(value).strip()]
        for candidate in candidates:
            normalized = candidate.strip()
            lookup_key = normalized.lower()
            if normalized and lookup_key not in seen:
                seen.add(lookup_key)
                keywords.append(normalized)
    return keywords


def _build_company_search_request(reviewed_extraction: dict[str, Any]) -> dict[str, Any]:
    sector = next(
        (
            str(reviewed_extraction.get(key, "")).strip()
            for key in ("company_industry", "job_domain", "job_title")
            if str(reviewed_extraction.get(key, "")).strip()
        ),
        "",
    )
    location = str(reviewed_extraction.get("location", "")).strip()
    keywords = _compact_review_keywords(
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


def _has_company_search_input(search_request: dict[str, Any]) -> bool:
    return bool(
        search_request.get("sector")
        or search_request.get("location")
        or search_request.get("keywords")
    )


def _merge_company_search_result(
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


def _company_fields_changed(
    before: dict[str, Any],
    after: dict[str, Any],
) -> bool:
    return any(
        str(before.get(field, "")).strip() != str(after.get(field, "")).strip()
        for field in COMPANY_SEARCH_RESULT_FIELDS
    )


def _application_label(item: dict[str, Any]) -> str:
    company = item.get("company_name") or "Unknown company"
    role = item.get("job_title") or "Unknown role"
    application_id = str(item.get("application_id", ""))
    short_id = application_id[:8] if application_id else "no-id"
    return f"{company} - {role} ({short_id})"


def _selected_cv_value(value: Any) -> str:
    cv_value = str(value or "").strip()
    return cv_value if cv_value in CV_KEYS else CV_KEYS[-1]


def _application_matches_filters(
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


def _build_review_refresh_state(status: str, notes: str) -> dict[str, str]:
    return {"status": status, "notes": notes}


def _review_refresh_defaults(state: dict[str, Any] | None) -> tuple[str, str]:
    state = state or {}
    status = str(state.get("status", "To Apply")).strip() or "To Apply"
    if status not in STATUS_VALUES:
        status = "To Apply"
    notes = str(state.get("notes", ""))
    return status, notes


def _store_review_refresh_state(status: str, notes: str) -> None:
    st.session_state[PENDING_REVIEW_STATE_KEY] = _build_review_refresh_state(status, notes)


def render_dashboard(configs: dict[str, dict[str, Any]]) -> None:
    applications = load_applications(configs)
    active_applications = [item for item in applications if not item.get("archived")]

    cols = st.columns(4)
    cols[0].metric("Total", len(applications))
    cols[1].metric("Active", len(active_applications))
    cols[2].metric(
        "Applied",
        len([item for item in applications if item.get("status") == "Applied"]),
    )
    cols[3].metric(
        "Interviews",
        len([item for item in applications if item.get("status") == "Interview"]),
    )

    if not applications:
        st.info("No applications saved yet.")
        return

    status_counts: dict[str, int] = {}
    cv_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    upcoming_follow_ups: list[dict[str, Any]] = []
    for item in active_applications:
        status = item.get("status") or "Unknown"
        selected_cv = item.get("selected_cv") or "Unselected"
        source = item.get("source_platform") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1
        cv_counts[selected_cv] = cv_counts.get(selected_cv, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
        if item.get("follow_up_date"):
            upcoming_follow_ups.append(item)

    metric_cols = st.columns(3)
    metric_cols[0].dataframe(
        [{"Status": key, "Count": value} for key, value in sorted(status_counts.items())],
        width="stretch",
        hide_index=True,
    )
    metric_cols[1].dataframe(
        [{"CV": key, "Count": value} for key, value in sorted(cv_counts.items())],
        width="stretch",
        hide_index=True,
    )
    metric_cols[2].dataframe(
        [{"Source": key, "Count": value} for key, value in sorted(source_counts.items())],
        width="stretch",
        hide_index=True,
    )

    if upcoming_follow_ups:
        st.subheader("Upcoming follow-ups")
        follow_up_rows = [
            {
                "Company": item.get("company_name", ""),
                "Role": item.get("job_title", ""),
                "Follow-up": item.get("follow_up_date", ""),
                "Status": item.get("status", ""),
            }
            for item in sorted(upcoming_follow_ups, key=lambda value: value.get("follow_up_date") or "")[:8]
        ]
        st.dataframe(follow_up_rows, width="stretch", hide_index=True)

    st.subheader("Recent applications")
    recent_rows = [
        {
            "Company": item.get("company_name", ""),
            "Role": item.get("job_title", ""),
            "Status": item.get("status", ""),
            "Selected CV": item.get("selected_cv", ""),
            "Updated": item.get("date_updated", ""),
        }
        for item in applications[:10]
    ]
    st.dataframe(recent_rows, width="stretch", hide_index=True)


def render_add_job(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = settings.get("database", {}).get("path", "database/applications.db")

    with st.form("add_application_form", clear_on_submit=False):
        company_name = st.text_input("Company name")
        job_title = st.text_input("Job title")
        location = st.text_input("Location")
        col_a, col_b = st.columns(2)
        source_platform = col_a.selectbox("Source platform", SOURCE_PLATFORM_VALUES)
        application_channel = col_b.selectbox("Application channel", APPLICATION_CHANNEL_VALUES)
        col_c, col_d = st.columns(2)
        contract_type = col_c.selectbox("Contract type", CONTRACT_TYPE_VALUES)
        status = col_d.selectbox("Status", STATUS_VALUES, index=1)
        job_url = st.text_input("Job URL")
        raw_job_description = st.text_area("Raw job description", height=220)
        notes = st.text_area("Notes", height=100)
        submitted = st.form_submit_button("Save application")

    if submitted:
        application = {
            "company_name": company_name,
            "job_title": job_title,
            "location": location,
            "source_platform": source_platform,
            "application_channel": application_channel,
            "contract_type": contract_type,
            "status": status,
            "job_url": job_url,
            "raw_job_description": raw_job_description,
            "notes": notes,
        }
        recommendation = cv_matcher.recommend_cv(application, configs["documents"])
        application.update(
            {
                "recommended_cv": recommendation["recommended_cv"],
                "selected_cv": recommendation["recommended_cv"],
                "cv_confidence_score": recommendation["confidence_score"],
                "cv_recommendation_reason": recommendation["reason"],
                "cv_matched_keywords": recommendation["matched_keywords"],
            }
        )
        application_id = database.add_application(application, db_path=db_path)
        st.success(f"Application saved: {application_id}")

    st.divider()
    st.subheader("Job post extraction")
    notice = st.session_state.pop("job_extraction_notice", None)
    if notice:
        getattr(st, notice["level"])(notice["message"])

    raw_text = st.text_area(
        "Paste a job post for local extraction",
        height=180,
        key="job_extraction_raw_text",
    )
    if st.button("Analyze with local model"):
        try:
            _run_extraction(raw_text, settings)
        except (RuntimeError, ValueError) as exc:
            st.warning(str(exc))

    pending_extraction = st.session_state.get("pending_job_extraction")
    if pending_extraction:
        render_extraction_review(configs, pending_extraction, db_path, settings)


def render_extraction_review(
    configs: dict[str, dict[str, Any]],
    pending_extraction: dict[str, Any],
    db_path: str,
    settings: dict[str, Any],
) -> None:
    version = st.session_state.get("pending_job_extraction_version", 0)
    raw_job_description = st.session_state.get("pending_job_extraction_raw_text", "")
    restored_status, restored_notes = _review_refresh_defaults(
        st.session_state.pop(PENDING_REVIEW_STATE_KEY, None)
    )

    st.subheader("Review extracted job")
    with st.form(f"extraction_review_form_{version}", clear_on_submit=False):
        company_col, role_col = st.columns(2)
        company_name = company_col.text_input(
            "Company name",
            value=_review_text(pending_extraction, "company_name"),
            key=f"review_company_name_{version}",
        )
        job_title = role_col.text_input(
            "Job title",
            value=_review_text(pending_extraction, "job_title"),
            key=f"review_job_title_{version}",
        )

        company_size = company_col.text_input(
            "Company size",
            value=_review_text(pending_extraction, "company_size"),
            key=f"review_company_size_{version}",
        )
        job_domain = role_col.text_input(
            "Job domain",
            value=_review_text(pending_extraction, "job_domain"),
            key=f"review_job_domain_{version}",
        )

        company_industry = company_col.text_input(
            "Company industry",
            value=_review_text(pending_extraction, "company_industry"),
            key=f"review_company_industry_{version}",
        )
        seniority_level = role_col.text_input(
            "Seniority level",
            value=_review_text(pending_extraction, "seniority_level"),
            key=f"review_seniority_level_{version}",
        )

        company_website = company_col.text_input(
            "Company website",
            value=_review_text(pending_extraction, "company_website"),
            key=f"review_company_website_{version}",
        )
        contract_type = role_col.text_input(
            "Contract type",
            value=_review_text(pending_extraction, "contract_type"),
            key=f"review_contract_type_{version}",
        )

        company_linkedin = company_col.text_input(
            "Company LinkedIn",
            value=_review_text(pending_extraction, "company_linkedin"),
            key=f"review_company_linkedin_{version}",
        )
        job_length = role_col.text_input(
            "Job length",
            value=_review_text(pending_extraction, "job_length"),
            key=f"review_job_length_{version}",
        )

        career_page_url = company_col.text_input(
            "Career page URL",
            value=_review_text(pending_extraction, "career_page_url"),
            key=f"review_career_page_url_{version}",
        )
        salary = role_col.text_input(
            "Salary",
            value=_review_text(pending_extraction, "salary"),
            key=f"review_salary_{version}",
        )

        location_col, tracking_col = st.columns(2)
        location = location_col.text_input(
            "Location",
            value=_review_text(pending_extraction, "location"),
            key=f"review_location_{version}",
        )
        source_platform = tracking_col.text_input(
            "Source platform",
            value=_review_text(pending_extraction, "source_platform"),
            key=f"review_source_platform_{version}",
        )
        remote_policy = location_col.text_input(
            "Remote policy",
            value=_review_text(pending_extraction, "remote_policy"),
            key=f"review_remote_policy_{version}",
        )
        application_channel = tracking_col.text_input(
            "Application channel",
            value=_review_text(pending_extraction, "application_channel"),
            key=f"review_application_channel_{version}",
        )
        relocation_required = location_col.text_input(
            "Relocation required",
            value=_review_text(pending_extraction, "relocation_required"),
            key=f"review_relocation_required_{version}",
        )
        job_url = tracking_col.text_input(
            "Job URL",
            value=_review_text(pending_extraction, "job_url"),
            key=f"review_job_url_{version}",
        )

        detected_language = st.text_input(
            "Detected language",
            value=_review_text(pending_extraction, "detected_language"),
            key=f"review_detected_language_{version}",
        )
        motivation_options = {
            "Unknown": None,
            "Yes": True,
            "No": False,
        }
        motivation_value = pending_extraction.get("motivation_letter_required")
        motivation_label = next(
            (
                label
                for label, option_value in motivation_options.items()
                if option_value is motivation_value
            ),
            "Unknown",
        )
        motivation_letter_required = st.selectbox(
            "Motivation letter required",
            tuple(motivation_options),
            index=tuple(motivation_options).index(motivation_label),
            key=f"review_motivation_letter_required_{version}",
        )

        key_responsibilities = st.text_area(
            "Key responsibilities",
            value=_list_to_review_text(pending_extraction.get("key_responsibilities", [])),
            height=120,
            key=f"review_key_responsibilities_{version}",
        )
        required_skills = st.text_area(
            "Required skills",
            value=_list_to_review_text(pending_extraction.get("required_skills", [])),
            height=100,
            key=f"review_required_skills_{version}",
        )
        preferred_qualifications = st.text_area(
            "Preferred qualifications",
            value=_list_to_review_text(pending_extraction.get("preferred_qualifications", [])),
            height=100,
            key=f"review_preferred_qualifications_{version}",
        )
        reviewed_raw_job_description = st.text_area(
            "Raw job description",
            value=raw_job_description,
            height=220,
            key=f"review_raw_job_description_{version}",
        )
        notes = st.text_area(
            "Notes",
            value=restored_notes,
            height=100,
            key=f"review_notes_{version}",
        )

        status = st.selectbox(
            "Status",
            STATUS_VALUES,
            index=STATUS_VALUES.index(restored_status),
            key=f"review_status_{version}",
        )

        create_col, company_search_col, retry_col, cancel_col = st.columns(4)
        create_clicked = create_col.form_submit_button("Create application")
        company_search_clicked = company_search_col.form_submit_button(
            "Launch company search and fill fields"
        )
        retry_clicked = retry_col.form_submit_button("Retry extraction")
        cancel_clicked = cancel_col.form_submit_button("Cancel")

    reviewed_extraction = {
        "company_name": company_name,
        "company_size": company_size,
        "company_industry": company_industry,
        "company_website": company_website,
        "company_linkedin": company_linkedin,
        "career_page_url": career_page_url,
        "job_title": job_title,
        "job_domain": job_domain,
        "seniority_level": seniority_level,
        "contract_type": contract_type,
        "job_length": job_length,
        "salary": salary,
        "location": location,
        "remote_policy": remote_policy,
        "relocation_required": relocation_required,
        "key_responsibilities": key_responsibilities,
        "required_skills": required_skills,
        "preferred_qualifications": preferred_qualifications,
        "detected_language": detected_language,
        "source_platform": source_platform,
        "application_channel": application_channel,
        "job_url": job_url,
        "motivation_letter_required": motivation_options[motivation_letter_required],
    }

    if cancel_clicked:
        _clear_pending_extraction()
        _set_extraction_notice("info", "Extraction discarded.")
        st.rerun()
        return

    if retry_clicked:
        try:
            _run_extraction(reviewed_raw_job_description, settings)
            _set_extraction_notice("success", "Extraction refreshed.")
            st.rerun()
        except (RuntimeError, ValueError) as exc:
            st.warning(str(exc))
        return

    if company_search_clicked:
        search_request = _build_company_search_request(reviewed_extraction)
        if not _has_company_search_input(search_request):
            _store_review_refresh_state(status, notes)
            _set_extraction_notice(
                "warning",
                "Add a company name, industry, website, or job/domain context before launching company search.",
            )
            st.rerun()
            return

        try:
            company_results = company_search.search_companies(
                search_request["sector"],
                search_request["location"],
                search_request["keywords"],
            )
            if not company_results:
                _store_review_refresh_state(status, notes)
                _set_extraction_notice(
                    "info",
                    "Company search finished, but no company details were found.",
                )
                st.rerun()
                return

            company_result = dict(company_results[0] or {})
            if not str(company_result.get("career_page_url", "")).strip():
                career_page_url_result = company_search.find_career_page(
                    str(
                        company_result.get("company_name")
                        or reviewed_extraction.get("company_name")
                        or ""
                    ).strip(),
                    str(
                        company_result.get("company_website")
                        or reviewed_extraction.get("company_website")
                        or ""
                    ).strip()
                    or None,
                )
                if career_page_url_result:
                    company_result["career_page_url"] = career_page_url_result

            merged_extraction = _merge_company_search_result(reviewed_extraction, company_result)
            _store_review_refresh_state(status, notes)
            _store_pending_extraction(merged_extraction, reviewed_raw_job_description)
            if _company_fields_changed(reviewed_extraction, merged_extraction):
                _set_extraction_notice("success", "Company search completed. Fields refreshed.")
            else:
                _set_extraction_notice(
                    "info",
                    "Company search completed, but no new company details were found.",
                )
            st.rerun()
        except (RuntimeError, ValueError) as exc:
            st.warning(str(exc))
        return

    if not create_clicked:
        return

    application = build_application_from_reviewed_extraction(
        reviewed_extraction,
        raw_job_description=reviewed_raw_job_description,
        status=status,
        notes=notes,
    )
    recommendation = cv_matcher.recommend_cv(application, configs["documents"])
    application.update(
        {
            "recommended_cv": recommendation["recommended_cv"],
            "selected_cv": recommendation["recommended_cv"],
            "cv_confidence_score": recommendation["confidence_score"],
            "cv_recommendation_reason": recommendation["reason"],
            "cv_matched_keywords": recommendation["matched_keywords"],
        }
    )
    application_id = database.add_application(application, db_path=db_path)
    _clear_pending_extraction()
    _set_extraction_notice("success", f"Application created from extraction: {application_id}")
    st.rerun()


def render_tracker(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = _db_path_from_configs(configs)
    applications = load_applications(configs)

    filter_cols = st.columns(4)
    status_filter = filter_cols[0].selectbox("Status", ("All",) + STATUS_VALUES)
    source_filter = filter_cols[1].selectbox("Source", ("All",) + SOURCE_PLATFORM_VALUES)
    cv_filter = filter_cols[2].selectbox("Selected CV", ("All",) + CV_KEYS)
    include_archived = filter_cols[3].checkbox("Include archived", value=False)
    query_cols = st.columns(3)
    company_query = query_cols[0].text_input("Company contains")
    domain_query = query_cols[1].text_input("Domain contains")
    location_query = query_cols[2].text_input("Location contains")

    filtered_applications = [
        item
        for item in applications
        if _application_matches_filters(
            item,
            status_filter=status_filter,
            company_query=company_query,
            domain_query=domain_query,
            source_filter=source_filter,
            cv_filter=cv_filter,
            location_query=location_query,
            include_archived=include_archived,
        )
    ]

    action_cols = st.columns(2)
    if action_cols[0].button("Export filtered applications to Excel"):
        export_dir = settings.get("exports", {}).get("export_folder", "exports/excel")
        try:
            output_path = excel_exporter.export_applications_to_excel(filtered_applications, export_dir)
            st.success(f"Excel export created: {output_path}")
        except Exception as exc:
            st.error(f"Excel export failed: {exc}")

    if action_cols[1].button("Sync all applications to Google Sheets"):
        result = sheets_sync.sync_applications_to_sheet(applications, settings, db_path=db_path)
        if result.get("errors"):
            st.error("; ".join(result["errors"]))
        elif result.get("warnings"):
            st.warning("; ".join(result["warnings"]))
        else:
            st.success(
                f"Google Sheets sync complete: {result['synced']} synced, "
                f"{result['created']} created, {result['updated']} updated."
            )

    if not filtered_applications:
        st.info("No matching applications.")
        return

    rows = [
        {
            "ID": item.get("application_id", ""),
            "Company": item.get("company_name", ""),
            "Role": item.get("job_title", ""),
            "Location": item.get("location", ""),
            "Status": item.get("status", ""),
            "Selected CV": item.get("selected_cv", ""),
            "Source": item.get("source_platform", ""),
            "Follow-up": item.get("follow_up_date", ""),
            "Updated": item.get("date_updated", ""),
        }
        for item in filtered_applications
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("Inspect and edit")
    options = {_application_label(item): item["application_id"] for item in filtered_applications}
    selected_label = st.selectbox("Application", list(options), key="tracker_application")
    selected = next(item for item in filtered_applications if item["application_id"] == options[selected_label])

    with st.form(f"tracker_edit_{selected['application_id']}", clear_on_submit=False):
        company_col, role_col = st.columns(2)
        company_name = company_col.text_input("Company name", value=selected.get("company_name", ""))
        job_title = role_col.text_input("Job title", value=selected.get("job_title", ""))
        company_size = company_col.text_input("Company size", value=selected.get("company_size", ""))
        job_domain = role_col.text_input("Job domain", value=selected.get("job_domain", ""))
        company_industry = company_col.text_input(
            "Company industry",
            value=selected.get("company_industry", ""),
        )
        seniority_level = role_col.text_input("Seniority level", value=selected.get("seniority_level", ""))
        company_website = company_col.text_input("Company website", value=selected.get("company_website", ""))
        contract_type = role_col.selectbox(
            "Contract type",
            CONTRACT_TYPE_VALUES,
            index=CONTRACT_TYPE_VALUES.index(selected.get("contract_type"))
            if selected.get("contract_type") in CONTRACT_TYPE_VALUES
            else len(CONTRACT_TYPE_VALUES) - 1,
        )
        company_linkedin = company_col.text_input("Company LinkedIn", value=selected.get("company_linkedin", ""))
        job_length = role_col.text_input("Job length", value=selected.get("job_length", ""))
        career_page_url = company_col.text_input("Career page URL", value=selected.get("career_page_url", ""))
        salary = role_col.text_input("Salary", value=selected.get("salary", ""))

        location_col, tracking_col = st.columns(2)
        location = location_col.text_input("Location", value=selected.get("location", ""))
        source_platform = tracking_col.selectbox(
            "Source platform",
            SOURCE_PLATFORM_VALUES,
            index=SOURCE_PLATFORM_VALUES.index(selected.get("source_platform"))
            if selected.get("source_platform") in SOURCE_PLATFORM_VALUES
            else len(SOURCE_PLATFORM_VALUES) - 1,
        )
        remote_policy = location_col.text_input("Remote policy", value=selected.get("remote_policy", ""))
        application_channel = tracking_col.selectbox(
            "Application channel",
            APPLICATION_CHANNEL_VALUES,
            index=APPLICATION_CHANNEL_VALUES.index(selected.get("application_channel"))
            if selected.get("application_channel") in APPLICATION_CHANNEL_VALUES
            else len(APPLICATION_CHANNEL_VALUES) - 1,
        )
        relocation_required = location_col.text_input(
            "Relocation required",
            value=selected.get("relocation_required", ""),
        )
        job_url = tracking_col.text_input("Job URL", value=selected.get("job_url", ""))

        status_col, cv_col = st.columns(2)
        status = status_col.selectbox(
            "Status",
            STATUS_VALUES,
            index=STATUS_VALUES.index(selected.get("status"))
            if selected.get("status") in STATUS_VALUES
            else 0,
        )
        selected_cv = cv_col.selectbox(
            "Selected CV override",
            CV_KEYS,
            index=CV_KEYS.index(_selected_cv_value(selected.get("selected_cv") or selected.get("recommended_cv"))),
        )
        date_applied = status_col.text_input("Date applied", value=selected.get("date_applied", ""))
        follow_up_date = cv_col.text_input("Follow-up date", value=selected.get("follow_up_date", ""))
        contact_person = status_col.text_input("Contact person", value=selected.get("contact_person", ""))
        contact_url = cv_col.text_input("Contact URL", value=selected.get("contact_url", ""))

        key_responsibilities = st.text_area(
            "Key responsibilities",
            value=_list_to_review_text(selected.get("key_responsibilities", [])),
            height=100,
        )
        required_skills = st.text_area(
            "Required skills",
            value=_list_to_review_text(selected.get("required_skills", [])),
            height=100,
        )
        preferred_qualifications = st.text_area(
            "Preferred qualifications",
            value=_list_to_review_text(selected.get("preferred_qualifications", [])),
            height=100,
        )
        raw_job_description = st.text_area(
            "Raw job description",
            value=selected.get("raw_job_description", ""),
            height=160,
        )
        notes = st.text_area("Notes", value=selected.get("notes", ""), height=120)
        save_changes = st.form_submit_button("Save tracker changes")

    if save_changes:
        database.update_application(
            selected["application_id"],
            {
                "company_name": company_name,
                "company_size": company_size,
                "company_industry": company_industry,
                "company_website": company_website,
                "company_linkedin": company_linkedin,
                "career_page_url": career_page_url,
                "job_title": job_title,
                "job_domain": job_domain,
                "seniority_level": seniority_level,
                "contract_type": contract_type,
                "job_length": job_length,
                "salary": salary,
                "location": location,
                "remote_policy": remote_policy,
                "relocation_required": relocation_required,
                "source_platform": source_platform,
                "application_channel": application_channel,
                "job_url": job_url,
                "status": status,
                "date_applied": date_applied,
                "follow_up_date": follow_up_date,
                "contact_person": contact_person,
                "contact_url": contact_url,
                "selected_cv": selected_cv,
                "key_responsibilities": _parse_review_list(key_responsibilities),
                "required_skills": _parse_review_list(required_skills),
                "preferred_qualifications": _parse_review_list(preferred_qualifications),
                "raw_job_description": raw_job_description,
                "notes": notes,
                "archived": 1 if status == "Archived" else selected.get("archived", 0),
            },
            db_path=db_path,
        )
        st.success("Application updated.")
        st.rerun()

    destructive_cols = st.columns(2)
    if destructive_cols[0].button("Archive selected application"):
        database.archive_application(selected["application_id"], db_path=db_path)
        st.success("Application archived.")
        st.rerun()
    confirm_delete = destructive_cols[1].checkbox("Confirm permanent delete")
    if destructive_cols[1].button("Delete selected application", disabled=not confirm_delete):
        database.delete_application(selected["application_id"], db_path=db_path)
        st.success("Application deleted.")
        st.rerun()


def render_cv_matcher(configs: dict[str, dict[str, Any]]) -> None:
    db_path = _db_path_from_configs(configs)
    applications = load_applications(configs)
    missing_cv_files = cv_matcher.validate_cv_files(configs["documents"])
    if missing_cv_files:
        st.warning(
            "Missing configured CV files: "
            + "; ".join(f"{cv_key}: {path}" for cv_key, path in missing_cv_files.items())
        )

    if applications:
        st.subheader("Application recommendation")
        options = _application_options(applications)
        selected_label = st.selectbox("Application", list(options), key="cv_matcher_application")
        selected = next(item for item in applications if item["application_id"] == options[selected_label])
        recommendation = cv_matcher.recommend_cv(selected, configs["documents"])
        st.json(recommendation)
        selected_cv = st.selectbox(
            "Selected CV",
            CV_KEYS,
            index=CV_KEYS.index(_selected_cv_value(selected.get("selected_cv") or recommendation["recommended_cv"])),
            key=f"cv_override_{selected['application_id']}",
        )
        if st.button("Save CV recommendation and override"):
            database.update_application(
                selected["application_id"],
                {
                    "recommended_cv": recommendation["recommended_cv"],
                    "selected_cv": selected_cv,
                    "cv_confidence_score": recommendation["confidence_score"],
                    "cv_recommendation_reason": recommendation["reason"],
                    "cv_matched_keywords": recommendation["matched_keywords"],
                },
                db_path=db_path,
            )
            st.success("CV recommendation saved.")
            st.rerun()

    st.divider()
    st.subheader("Ad-hoc recommendation")
    job_title = st.text_input("Job title", key="cv_job_title")
    job_domain = st.text_input("Job domain", key="cv_job_domain")
    required_skills = st.text_area("Required skills", key="cv_required_skills")
    raw_description = st.text_area("Raw description", key="cv_raw_description", height=180)

    if st.button("Recommend CV"):
        application = {
            "job_title": job_title,
            "job_domain": job_domain,
            "required_skills": [item.strip() for item in required_skills.split(",") if item.strip()],
            "raw_job_description": raw_description,
        }
        recommendation = cv_matcher.recommend_cv(application, configs["documents"])
        st.json(recommendation)


def _application_options(applications: list[dict[str, Any]]) -> dict[str, str]:
    return {_application_label(item): item["application_id"] for item in applications}


def render_motivation_letter(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = _db_path_from_configs(configs)
    applications = load_applications(configs)
    if not applications:
        st.info("No applications available.")
        return

    options = _application_options(applications)
    selected_label = st.selectbox("Application", list(options))
    selected = next(item for item in applications if item["application_id"] == options[selected_label])
    language = st.selectbox("Language", ("auto", "English", "French"))
    user_notes = st.text_area("Optional notes")
    draft_key = f"letter_draft_{selected['application_id']}"
    result_key = f"letter_result_{selected['application_id']}"

    if st.button("Generate draft"):
        result = letter_generator.generate_letter(
            selected,
            selected.get("selected_cv") or selected.get("recommended_cv") or "ai",
            language=language,
            profile=configs["profile"],
            user_notes=user_notes,
            documents_config=configs["documents"],
            llm_settings=settings.get("llm", {}),
        )
        st.session_state[draft_key] = result["letter_text"]
        st.session_state[result_key] = result

    result = st.session_state.get(result_key)
    if result:
        if result.get("warnings"):
            st.warning("; ".join(result["warnings"]))
        st.caption(f"Language: {result['language']} | Words: {result['word_count']}")

    draft = st.text_area("Draft", key=draft_key, height=260)
    if draft and st.button("Save letter locally and link to application"):
        saved_language = (result or {}).get("language") or letter_generator.select_letter_language(selected, language)
        file_path = letter_generator.save_letter(selected["application_id"], draft, saved_language)
        database.update_application(
            selected["application_id"],
            {
                "motivation_letter_file": file_path,
                "motivation_letter_language": saved_language,
            },
            db_path=db_path,
        )
        st.success(f"Letter saved: {file_path}")
        st.rerun()


def render_form_helper(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = _db_path_from_configs(configs)
    applications = load_applications(configs)
    if not applications:
        st.info("No applications available.")
        return

    options = _application_options(applications)
    selected_label = st.selectbox("Application", list(options), key="form_application")
    selected = next(item for item in applications if item["application_id"] == options[selected_label])
    platforms = configs["settings"].get("form_helper", {}).get("supported_platforms", ["Other"])
    platform = st.selectbox("Platform", platforms)
    result_key = f"form_answers_result_{selected['application_id']}"

    if st.button("Generate answers"):
        result = form_helper.generate_common_answers(
            selected,
            configs["profile"],
            platform,
            configs["form_answers"],
            llm_settings=settings.get("llm", {}),
        )
        st.session_state[result_key] = result

    result = st.session_state.get(result_key)
    if not result:
        return

    if result.get("warnings"):
        st.warning("; ".join(result["warnings"]))

    answers = result.get("answers", {})
    personal_information = dict(answers.get("personal_information", {}))
    common_questions = dict(answers.get("common_questions", {}))
    with st.form(f"form_answers_edit_{selected['application_id']}", clear_on_submit=False):
        st.subheader("Personal information")
        edited_personal = {
            key: st.text_input(key.replace("_", " ").title(), value=str(value or ""))
            for key, value in personal_information.items()
        }
        st.subheader("Common answers")
        edited_common = {
            key: st.text_area(key.replace("_", " ").title(), value=str(value or ""), height=90)
            for key, value in common_questions.items()
        }
        save_answers = st.form_submit_button("Save form answers locally and link to application")

    if save_answers:
        payload = {
            "application_id": selected["application_id"],
            "platform": platform,
            "answers": {
                "personal_information": edited_personal,
                "common_questions": edited_common,
            },
            "file_path": "",
            "warnings": result.get("warnings", []),
        }
        file_path = form_helper.save_form_answers(selected["application_id"], payload)
        database.update_application(
            selected["application_id"],
            {"form_answers_file": file_path},
            db_path=db_path,
        )
        st.success(f"Form answers saved: {file_path}")
        st.rerun()


def render_company_search(configs: dict[str, dict[str, Any]]) -> None:
    db_path = _db_path_from_configs(configs)
    with st.form("company_search_form", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        sector = col_a.text_input("Sector", value="AI consulting")
        location = col_b.text_input("Location", value="Geneva")
        keywords_text = st.text_area(
            "Keywords",
            value="junior\nanalyst\nAI product\nbusiness analyst",
            height=110,
        )
        search_clicked = st.form_submit_button("Search public company sources")

    if search_clicked:
        keywords = _parse_review_list(keywords_text)
        try:
            results = company_search.search_companies(sector, location, keywords)
            enriched_results: list[dict[str, Any]] = []
            for result in results:
                enriched = dict(result)
                enriched.setdefault("source", "Public company search")
                enriched.setdefault("source_url", "")
                if not enriched.get("career_page_url"):
                    career_page_url = company_search.find_career_page(
                        enriched.get("company_name", "") or sector,
                        enriched.get("company_website"),
                    )
                    if career_page_url:
                        enriched["career_page_url"] = career_page_url
                enriched_results.append(enriched)
            st.session_state["company_search_results"] = enriched_results
        except Exception as exc:
            st.error(f"Company search failed: {exc}")

    results = st.session_state.get("company_search_results", [])
    if not results:
        st.info("No company search results yet.")
        return

    st.dataframe(results, width="stretch", hide_index=True)
    result_options = {
        f"{item.get('company_name') or 'Unknown company'} ({index + 1})": index
        for index, item in enumerate(results)
    }
    selected_label = st.selectbox("Result", list(result_options), key="company_search_result")
    selected_result = results[result_options[selected_label]]

    action_cols = st.columns(2)
    if action_cols[0].button("Save company"):
        company_id = database.upsert_company(selected_result, db_path=db_path)
        st.success(f"Company saved: {company_id}")

    with st.form("company_search_create_application", clear_on_submit=False):
        st.subheader("Create tracker record")
        job_title = st.text_input("Job title", value="")
        job_url = st.text_input(
            "Job URL",
            value=selected_result.get("career_page_url") or selected_result.get("company_website") or "",
        )
        status = st.selectbox("Status", STATUS_VALUES, index=0)
        notes = st.text_area("Notes", value="", height=90)
        create_clicked = st.form_submit_button("Create application from result")

    if create_clicked:
        application = build_application_from_company_search_result(
            selected_result,
            job_title=job_title,
            job_url=job_url,
            status=status,
            notes=notes,
        )
        recommendation = cv_matcher.recommend_cv(application, configs["documents"])
        application.update(
            {
                "recommended_cv": recommendation["recommended_cv"],
                "selected_cv": recommendation["recommended_cv"],
                "cv_confidence_score": recommendation["confidence_score"],
                "cv_recommendation_reason": recommendation["reason"],
                "cv_matched_keywords": recommendation["matched_keywords"],
            }
        )
        application_id = database.add_application(application, db_path=db_path)
        st.success(f"Application created: {application_id}")
        st.rerun()


def render_settings(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = resolve_path(settings.get("database", {}).get("path", "database/applications.db"))
    missing_cv_files = cv_matcher.validate_cv_files(configs["documents"])
    st.write(
        {
            "database": str(db_path),
            "llm_model": settings.get("llm", {}).get("model"),
            "google_sheets_enabled": settings.get("google_sheets", {}).get("enabled"),
            "automation": settings.get("automation", {}),
            "cv_keys": list(CV_KEYS),
        }
    )
    if missing_cv_files:
        st.warning(
            "Missing configured CV files: "
            + "; ".join(f"{cv_key}: {path}" for cv_key, path in missing_cv_files.items())
        )

    llm_settings = settings.get("llm", {})
    sheets_settings = settings.get("google_sheets", {})
    export_settings = settings.get("exports", {})

    with st.form("settings_form", clear_on_submit=False):
        st.subheader("Local model")
        llm_model = st.text_input("Ollama model", value=llm_settings.get("model", "qwen2.5:7b"))
        fallback_models_text = st.text_area(
            "Fallback models",
            value="\n".join(llm_settings.get("fallback_models", [])),
            height=90,
        )
        timeout_seconds = st.number_input(
            "Timeout seconds",
            min_value=10,
            max_value=600,
            value=int(llm_settings.get("timeout_seconds", 120)),
            step=10,
        )
        temperature = st.number_input(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(llm_settings.get("temperature", 0.2)),
            step=0.05,
        )

        st.subheader("Google Sheets")
        sheets_enabled = st.checkbox("Enable Google Sheets sync", value=bool(sheets_settings.get("enabled", False)))
        spreadsheet_id = st.text_input("Spreadsheet ID or URL", value=sheets_settings.get("spreadsheet_id", ""))
        worksheet_name = st.text_input("Worksheet name", value=sheets_settings.get("worksheet_name", "Applications"))
        credentials_path = st.text_input(
            "Credentials path",
            value=sheets_settings.get("credentials_path", "config/google_service_account.json"),
        )

        st.subheader("Exports")
        export_folder = st.text_input("Excel export folder", value=export_settings.get("export_folder", "exports/excel"))
        save_settings = st.form_submit_button("Save settings")

    if save_settings:
        updated_settings = dict(settings)
        updated_settings["llm"] = dict(llm_settings)
        updated_settings["llm"].update(
            {
                "provider": llm_settings.get("provider", "ollama"),
                "model": llm_model.strip() or "qwen2.5:7b",
                "fallback_models": _parse_review_list(fallback_models_text),
                "timeout_seconds": int(timeout_seconds),
                "temperature": float(temperature),
            }
        )
        updated_settings["google_sheets"] = dict(sheets_settings)
        updated_settings["google_sheets"].update(
            {
                "enabled": bool(sheets_enabled),
                "spreadsheet_id": spreadsheet_id.strip(),
                "worksheet_name": worksheet_name.strip() or "Applications",
                "credentials_path": credentials_path.strip() or "config/google_service_account.json",
                "sqlite_is_source_of_truth": True,
            }
        )
        updated_settings["exports"] = dict(export_settings)
        updated_settings["exports"].update(
            {
                "excel_enabled": True,
                "export_folder": export_folder.strip() or "exports/excel",
                "timestamp_filenames": True,
            }
        )
        write_yaml(CONFIG_FILES["settings"], updated_settings)
        st.success("Settings saved. Reloading app configuration.")
        st.rerun()

    credentials_exists = resolve_path(sheets_settings.get("credentials_path", "config/google_service_account.json")).exists()
    if sheets_settings.get("enabled") and not credentials_exists:
        st.warning("Google Sheets is enabled, but the credentials file is missing.")
    if st.button("Check Google Sheets sync setup"):
        result = sheets_sync.sync_applications_to_sheet([], settings)
        st.json(result)


def main() -> None:
    st.set_page_config(page_title="Job Search Automation Assistant", layout="wide")
    configs = bootstrap()
    st.title("Job Search Automation Assistant")

    tabs = st.tabs(
        [
            "Dashboard",
            "Add Job",
            "Tracker",
            "CV Matcher",
            "Motivation Letter",
            "Form Helper",
            "Company Search",
            "Settings",
        ]
    )
    with tabs[0]:
        render_dashboard(configs)
    with tabs[1]:
        render_add_job(configs)
    with tabs[2]:
        render_tracker(configs)
    with tabs[3]:
        render_cv_matcher(configs)
    with tabs[4]:
        render_motivation_letter(configs)
    with tabs[5]:
        render_form_helper(configs)
    with tabs[6]:
        render_company_search(configs)
    with tabs[7]:
        render_settings(configs)


if __name__ == "__main__":
    main()
