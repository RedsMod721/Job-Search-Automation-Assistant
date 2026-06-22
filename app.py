from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import streamlit as st

from src import (
    company_search,
    cv_matcher,
    diagnostics,
    excel_exporter,
    form_helper,
    letter_generator,
)
from src.constants import (
    APPLICATION_CHANNEL_VALUES,
    CONFIG_FILES,
    CONTRACT_TYPE_VALUES,
    CV_KEYS,
    SOURCE_PLATFORM_VALUES,
    STATUS_VALUES,
)
from src.repositories.applications import ApplicationRepository, application_repository_from_settings
from src.repositories.companies import CompanyRepository
from src.services import deduplication_service, recovery_service
from src.services.application_service import (
    application_label as _application_label,
)
from src.services.application_service import (
    application_matches_filters as _application_matches_filters,
)
from src.services.application_service import (
    build_application_from_company_search_result,
    build_application_from_reviewed_extraction,
)
from src.services.application_service import (
    build_company_search_request as _build_company_search_request,
)
from src.services.application_service import (
    build_review_refresh_state as _build_review_refresh_state,
)
from src.services.application_service import (
    company_fields_changed as _company_fields_changed,
)
from src.services.application_service import (
    has_company_search_input as _has_company_search_input,
)
from src.services.application_service import (
    list_to_review_text as _list_to_review_text,
)
from src.services.application_service import (
    merge_company_search_result as _merge_company_search_result,
)
from src.services.application_service import (
    parse_review_list as _parse_review_list,
)
from src.services.application_service import (
    review_refresh_defaults as _review_refresh_defaults,
)
from src.services.application_service import (
    selected_cv_value as _selected_cv_value,
)
from src.services.extraction_service import run_extraction
from src.services.sync_service import (
    change_triggered_sync,
    manual_sync_applications,
    startup_sync,
    sync_mode_summary,
    sync_status_summary,
    timer_sync,
)
from src.utils import (
    apply_runtime_config_overrides,
    configure_logging,
    ensure_directories,
    load_app_config,
    local_config_path,
    resolve_path,
    write_yaml,
)

PENDING_REVIEW_STATE_KEY = "pending_job_extraction_review_state"


def bootstrap() -> dict[str, dict[str, Any]]:
    ensure_directories()
    configs = apply_runtime_config_overrides(load_app_config())
    configure_logging(configs.get("settings", {}))
    application_repository_from_settings(configs["settings"]).init()
    return configs


def _db_path_from_configs(configs: dict[str, dict[str, Any]]) -> str:
    return configs["settings"].get("database", {}).get("path", "database/applications.db")


def load_applications(configs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return ApplicationRepository(_db_path_from_configs(configs)).list()


def _store_pending_extraction(extraction: dict[str, Any], raw_text: str) -> None:
    st.session_state["pending_job_extraction"] = extraction
    st.session_state["pending_job_extraction_raw_text"] = raw_text
    st.session_state["pending_job_extraction_version"] = st.session_state.get("pending_job_extraction_version", 0) + 1


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
    _store_pending_extraction(run_extraction(raw_text, settings), raw_text)


def _google_sync_enabled(settings: dict[str, Any]) -> bool:
    return bool(settings.get("google_sheets", {}).get("enabled", False))


def _store_sync_notice(mode: str, result: Any) -> None:
    if result is None:
        return
    st.session_state["google_sheets_sync_notice"] = {
        "mode": mode,
        "synced": getattr(result, "synced", 0),
        "created": getattr(result, "created", 0),
        "updated": getattr(result, "updated", 0),
        "skipped": getattr(result, "skipped", 0),
        "warnings": list(getattr(result, "warnings", [])),
        "errors": list(getattr(result, "errors", [])),
    }


def _show_sync_notice() -> None:
    notice = st.session_state.get("google_sheets_sync_notice")
    if not notice:
        return
    if notice.get("errors"):
        st.warning(f"Google Sheets sync {notice['mode']} failed: {'; '.join(notice['errors'])}")
        return
    if notice.get("warnings"):
        st.caption(f"Google Sheets sync {notice['mode']}: {'; '.join(notice['warnings'])}")
        return
    if notice.get("synced"):
        st.caption(
            f"Google Sheets sync {notice['mode']}: {notice['synced']} synced, "
            f"{notice['created']} created, {notice['updated']} updated."
        )


def _run_change_triggered_sync(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    if not _google_sync_enabled(settings):
        return
    try:
        _store_sync_notice("change-triggered", change_triggered_sync(settings, db_path=_db_path_from_configs(configs)))
    except Exception as exc:
        st.session_state["google_sheets_sync_notice"] = {
            "mode": "change-triggered",
            "synced": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "warnings": [],
            "errors": [str(exc)],
        }


def _run_automatic_sync(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    if not _google_sync_enabled(settings):
        return
    db_path = _db_path_from_configs(configs)
    sheet_settings = settings.get("google_sheets", {})
    now = datetime.now().replace(microsecond=0)

    if sheet_settings.get("startup_sync_enabled", True) and not st.session_state.get("google_sheets_startup_sync_done"):
        try:
            _store_sync_notice("startup", startup_sync(settings, db_path=db_path))
        except Exception as exc:
            st.session_state["google_sheets_sync_notice"] = {
                "mode": "startup",
                "synced": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "warnings": [],
                "errors": [str(exc)],
            }
        st.session_state["google_sheets_startup_sync_done"] = True

    if sheet_settings.get("timer_sync_enabled", True):
        interval_seconds = int(sheet_settings.get("timer_interval_seconds", 60) or 60)
        last_timer_sync = st.session_state.get("google_sheets_last_timer_sync_at")
        due = not isinstance(last_timer_sync, datetime) or now - last_timer_sync >= timedelta(seconds=interval_seconds)
        if due:
            try:
                _store_sync_notice("timer", timer_sync(settings, db_path=db_path))
            except Exception as exc:
                st.session_state["google_sheets_sync_notice"] = {
                    "mode": "timer",
                    "synced": 0,
                    "created": 0,
                    "updated": 0,
                    "skipped": 0,
                    "warnings": [],
                    "errors": [str(exc)],
                }
            st.session_state["google_sheets_last_timer_sync_at"] = now
        st.markdown(f"<meta http-equiv='refresh' content='{max(interval_seconds, 10)}'>", unsafe_allow_html=True)


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
    application_repository = ApplicationRepository(db_path)

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
        application_id = application_repository.add(application)
        _run_change_triggered_sync(configs)
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
    restored_status, restored_notes = _review_refresh_defaults(st.session_state.pop(PENDING_REVIEW_STATE_KEY, None))

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
            (label for label, option_value in motivation_options.items() if option_value is motivation_value),
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
        company_search_clicked = company_search_col.form_submit_button("Launch company search and fill fields")
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
                    str(company_result.get("company_name") or reviewed_extraction.get("company_name") or "").strip(),
                    str(
                        company_result.get("company_website") or reviewed_extraction.get("company_website") or ""
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
    application_id = ApplicationRepository(db_path).add(application)
    _run_change_triggered_sync(configs)
    _clear_pending_extraction()
    _set_extraction_notice("success", f"Application created from extraction: {application_id}")
    st.rerun()


def render_tracker(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = _db_path_from_configs(configs)
    application_repository = ApplicationRepository(db_path)
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
        result = manual_sync_applications(applications, settings, db_path=db_path)
        if result.errors:
            st.error("; ".join(result.errors))
        elif result.warnings:
            st.warning("; ".join(result.warnings))
        else:
            st.success(
                f"Google Sheets sync complete: {result.synced} synced, "
                f"{result.created} created, {result.updated} updated."
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
            index=STATUS_VALUES.index(selected.get("status")) if selected.get("status") in STATUS_VALUES else 0,
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
        application_repository.update(
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
        )
        _run_change_triggered_sync(configs)
        st.success("Application updated.")
        st.rerun()

    destructive_cols = st.columns(2)
    if destructive_cols[0].button("Archive selected application"):
        application_repository.archive(selected["application_id"])
        _run_change_triggered_sync(configs)
        st.success("Application archived.")
        st.rerun()
    confirm_delete = destructive_cols[1].checkbox("Confirm soft delete")
    if destructive_cols[1].button("Soft-delete selected application", disabled=not confirm_delete):
        application_repository.delete(selected["application_id"])
        _run_change_triggered_sync(configs)
        st.success("Application soft-deleted.")
        st.rerun()


def render_cv_matcher(configs: dict[str, dict[str, Any]]) -> None:
    db_path = _db_path_from_configs(configs)
    application_repository = ApplicationRepository(db_path)
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
            application_repository.update(
                selected["application_id"],
                {
                    "recommended_cv": recommendation["recommended_cv"],
                    "selected_cv": selected_cv,
                    "cv_confidence_score": recommendation["confidence_score"],
                    "cv_recommendation_reason": recommendation["reason"],
                    "cv_matched_keywords": recommendation["matched_keywords"],
                },
            )
            _run_change_triggered_sync(configs)
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
    application_repository = ApplicationRepository(db_path)
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

    stored_letter_result = st.session_state.get(result_key)
    if stored_letter_result:
        if stored_letter_result.get("warnings"):
            st.warning("; ".join(stored_letter_result["warnings"]))
        st.caption(f"Language: {stored_letter_result['language']} | Words: {stored_letter_result['word_count']}")

    draft = st.text_area("Draft", key=draft_key, height=260)
    if draft and st.button("Save letter locally and link to application"):
        saved_language = (stored_letter_result or {}).get("language") or letter_generator.select_letter_language(
            selected, language
        )
        file_path = letter_generator.save_letter(selected["application_id"], draft, saved_language)
        application_repository.update(
            selected["application_id"],
            {
                "motivation_letter_file": file_path,
                "motivation_letter_language": saved_language,
            },
        )
        _run_change_triggered_sync(configs)
        st.success(f"Letter saved: {file_path}")
        st.rerun()


def render_form_helper(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = _db_path_from_configs(configs)
    application_repository = ApplicationRepository(db_path)
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

    stored_answers_result = st.session_state.get(result_key)
    if not stored_answers_result:
        return

    if stored_answers_result.get("warnings"):
        st.warning("; ".join(stored_answers_result["warnings"]))

    answers = stored_answers_result.get("answers", {})
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
            "warnings": stored_answers_result.get("warnings", []),
        }
        file_path = form_helper.save_form_answers(selected["application_id"], payload)
        application_repository.update(
            selected["application_id"],
            {"form_answers_file": file_path},
        )
        _run_change_triggered_sync(configs)
        st.success(f"Form answers saved: {file_path}")
        st.rerun()


def render_company_search(configs: dict[str, dict[str, Any]]) -> None:
    network_settings = configs["settings"].get("network", {})
    db_path = _db_path_from_configs(configs)
    application_repository = ApplicationRepository(db_path)
    company_repository = CompanyRepository(db_path)
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
            results = company_search.search_companies(sector, location, keywords, network_settings=network_settings)
            enriched_results: list[dict[str, Any]] = []
            for result in results:
                enriched = dict(result)
                enriched.setdefault("source", "Public company search")
                enriched.setdefault("source_url", "")
                if not enriched.get("career_page_url"):
                    career_page_url = company_search.find_career_page(
                        enriched.get("company_name", "") or sector,
                        enriched.get("company_website"),
                        network_settings=network_settings,
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
        f"{item.get('company_name') or 'Unknown company'} ({index + 1})": index for index, item in enumerate(results)
    }
    selected_label = st.selectbox("Result", list(result_options), key="company_search_result")
    selected_result = results[result_options[selected_label]]

    action_cols = st.columns(2)
    if action_cols[0].button("Save company"):
        company_id = company_repository.upsert(selected_result)
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
        application_id = application_repository.add(application)
        _run_change_triggered_sync(configs)
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

    st.subheader("Health diagnostics")
    diagnostic_report = diagnostics.collect_diagnostics(configs)
    sheet_sync_summary = sync_mode_summary(settings)
    sheet_status_summary = sync_status_summary(db_path)
    st.write(diagnostics.diagnostics_summary(diagnostic_report))
    with st.expander("Detailed diagnostics"):
        st.json(
            {
                "diagnostics": diagnostic_report,
                "google_sheets_sync_modes": sheet_sync_summary.model_dump(),
                "google_sheets_sync_status": sheet_status_summary,
            }
        )

    st.subheader("Google Sheets sync status")
    st.json(sheet_status_summary)

    st.subheader("Database safety")
    safety_cols = st.columns(4)
    if safety_cols[0].button("Run integrity check"):
        st.json(recovery_service.run_integrity_check(db_path))
    if safety_cols[1].button("Create database backup"):
        try:
            backup_path = recovery_service.create_backup(db_path)
            st.success(f"Backup created: {backup_path}")
        except Exception as exc:
            st.error(f"Backup failed: {exc}")
    if safety_cols[2].button("Export recovery SQL"):
        try:
            export_path = recovery_service.create_recovery_export(db_path)
            st.success(f"Recovery export created: {export_path}")
        except Exception as exc:
            st.error(f"Recovery export failed: {exc}")
    if safety_cols[3].button("Scan duplicates"):
        st.json(deduplication_service.find_all_duplicates(db_path))

    restore_path = st.text_input("Backup path to restore", value="", key="restore_backup_path")
    confirm_restore = st.checkbox("Confirm database restore", value=False)
    if st.button("Restore database backup", disabled=not (restore_path and confirm_restore)):
        try:
            pre_restore_backup = recovery_service.restore_backup(restore_path, db_path)
            st.success(f"Database restored. Pre-restore backup: {pre_restore_backup}")
            st.rerun()
        except Exception as exc:
            st.error(f"Restore failed: {exc}")

    llm_settings = settings.get("llm", {})
    sheets_settings = settings.get("google_sheets", {})
    export_settings = settings.get("exports", {})
    network_settings = settings.get("network", {})

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
        startup_sync_enabled = st.checkbox(
            "Sync on app startup",
            value=bool(sheets_settings.get("startup_sync_enabled", True)),
        )
        timer_sync_enabled = st.checkbox(
            "Sync on timer",
            value=bool(sheets_settings.get("timer_sync_enabled", True)),
        )
        change_triggered_sync_enabled = st.checkbox(
            "Sync after local changes",
            value=bool(sheets_settings.get("change_triggered_sync_enabled", True)),
        )
        timer_interval_seconds = st.number_input(
            "Timer sync interval seconds",
            min_value=10,
            max_value=3600,
            value=int(sheets_settings.get("timer_interval_seconds", 60)),
            step=10,
        )
        max_retry_attempts = st.number_input(
            "Max sync retry attempts",
            min_value=1,
            max_value=20,
            value=int(sheets_settings.get("max_retry_attempts", 5)),
            step=1,
        )
        retry_backoff_seconds = st.number_input(
            "Retry backoff seconds",
            min_value=10,
            max_value=3600,
            value=int(sheets_settings.get("retry_backoff_seconds", 60)),
            step=10,
        )

        st.subheader("Network")
        verify_tls = st.checkbox("Verify TLS certificates", value=bool(network_settings.get("verify_tls", True)))
        custom_ca_bundle = st.text_input(
            "Custom CA bundle",
            value=network_settings.get("custom_ca_bundle", ""),
        )
        http_proxy = st.text_input("HTTP proxy", value=network_settings.get("http_proxy", ""))
        https_proxy = st.text_input("HTTPS proxy", value=network_settings.get("https_proxy", ""))
        request_timeout_seconds = st.number_input(
            "Network timeout seconds",
            min_value=3,
            max_value=180,
            value=int(network_settings.get("request_timeout_seconds", 30)),
            step=1,
        )

        st.subheader("Exports")
        export_folder = st.text_input(
            "Excel export folder", value=export_settings.get("export_folder", "exports/excel")
        )
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
                "startup_sync_enabled": bool(startup_sync_enabled),
                "timer_sync_enabled": bool(timer_sync_enabled),
                "change_triggered_sync_enabled": bool(change_triggered_sync_enabled),
                "timer_interval_seconds": int(timer_interval_seconds),
                "max_retry_attempts": int(max_retry_attempts),
                "retry_backoff_seconds": int(retry_backoff_seconds),
            }
        )
        updated_settings["network"] = dict(network_settings)
        updated_settings["network"].update(
            {
                "verify_tls": bool(verify_tls),
                "custom_ca_bundle": custom_ca_bundle.strip(),
                "http_proxy": http_proxy.strip(),
                "https_proxy": https_proxy.strip(),
                "request_timeout_seconds": int(request_timeout_seconds),
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
        write_yaml(local_config_path(CONFIG_FILES["settings"]), updated_settings)
        st.success("Local settings saved. Reloading app configuration.")
        st.rerun()

    credentials_exists = resolve_path(
        sheets_settings.get("credentials_path", "config/google_service_account.json")
    ).exists()
    if sheets_settings.get("enabled") and not credentials_exists:
        st.warning("Google Sheets is enabled, but the credentials file is missing.")
    if st.button("Check Google Sheets sync setup"):
        result = manual_sync_applications([], settings)
        st.json(result.model_dump())
    if st.button("Force sync all applications now"):
        applications = load_applications(configs)
        result = manual_sync_applications(applications, settings, db_path=db_path)
        st.json(result.model_dump())


def main() -> None:
    st.set_page_config(page_title="Job Search Automation Assistant", layout="wide")
    configs = bootstrap()
    st.title("Job Search Automation Assistant")
    _run_automatic_sync(configs)
    _show_sync_notice()

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
