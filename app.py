from __future__ import annotations

from typing import Any

import streamlit as st

from src import cv_matcher, database, extractor, form_helper, letter_generator, sheets_sync
from src.constants import (
    APPLICATION_CHANNEL_VALUES,
    CONTRACT_TYPE_VALUES,
    CV_KEYS,
    EXTRACTION_LIST_FIELDS,
    EXTRACTION_SCHEMA_KEYS,
    SOURCE_PLATFORM_VALUES,
    STATUS_VALUES,
)
from src.utils import configure_logging, ensure_directories, load_app_config, resolve_path


def bootstrap() -> dict[str, dict[str, Any]]:
    ensure_directories()
    configs = load_app_config()
    configure_logging(configs.get("settings", {}))
    db_path = configs["settings"].get("database", {}).get("path", "database/applications.db")
    database.init_db(db_path)
    return configs


def load_applications(configs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    db_path = configs["settings"].get("database", {}).get("path", "database/applications.db")
    return database.list_applications(db_path=db_path)


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
        notes = st.text_area("Notes", height=100, key=f"review_notes_{version}")

        status = st.selectbox(
            "Status",
            STATUS_VALUES,
            index=STATUS_VALUES.index("To Apply"),
            key=f"review_status_{version}",
        )

        create_col, retry_col, cancel_col = st.columns(3)
        create_clicked = create_col.form_submit_button("Create application")
        retry_clicked = retry_col.form_submit_button("Retry extraction")
        cancel_clicked = cancel_col.form_submit_button("Cancel")

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

    if not create_clicked:
        return

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
    applications = load_applications(configs)
    status_filter = st.selectbox("Status filter", ("All",) + STATUS_VALUES)
    if status_filter != "All":
        applications = [item for item in applications if item.get("status") == status_filter]

    if not applications:
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
            "Updated": item.get("date_updated", ""),
        }
        for item in applications
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def render_cv_matcher(configs: dict[str, dict[str, Any]]) -> None:
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
    return {
        f"{item.get('company_name') or 'Unknown company'} - {item.get('job_title') or 'Unknown role'}": item[
            "application_id"
        ]
        for item in applications
    }


def render_motivation_letter(configs: dict[str, dict[str, Any]]) -> None:
    applications = load_applications(configs)
    if not applications:
        st.info("No applications available.")
        return

    options = _application_options(applications)
    selected_label = st.selectbox("Application", list(options))
    selected = next(item for item in applications if item["application_id"] == options[selected_label])
    language = st.selectbox("Language", ("auto", "English", "French"))
    user_notes = st.text_area("Optional notes")

    if st.button("Generate draft"):
        letter = letter_generator.generate_letter(
            selected,
            selected.get("selected_cv") or selected.get("recommended_cv") or "ai",
            language=language,
            profile=configs["profile"],
            user_notes=user_notes,
        )
        st.text_area("Draft", value=letter, height=260)


def render_form_helper(configs: dict[str, dict[str, Any]]) -> None:
    applications = load_applications(configs)
    if not applications:
        st.info("No applications available.")
        return

    options = _application_options(applications)
    selected_label = st.selectbox("Application", list(options), key="form_application")
    selected = next(item for item in applications if item["application_id"] == options[selected_label])
    platforms = configs["settings"].get("form_helper", {}).get("supported_platforms", ["Other"])
    platform = st.selectbox("Platform", platforms)

    if st.button("Generate answers"):
        answers = form_helper.generate_common_answers(
            selected,
            configs["profile"],
            platform,
            configs["form_answers"],
        )
        st.json(answers)


def render_settings(configs: dict[str, dict[str, Any]]) -> None:
    settings = configs["settings"]
    db_path = resolve_path(settings.get("database", {}).get("path", "database/applications.db"))
    st.write(
        {
            "database": str(db_path),
            "llm_model": settings.get("llm", {}).get("model"),
            "google_sheets_enabled": settings.get("google_sheets", {}).get("enabled"),
            "automation": settings.get("automation", {}),
            "cv_keys": list(CV_KEYS),
        }
    )
    if st.button("Check Google Sheets scaffold"):
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
        render_settings(configs)


if __name__ == "__main__":
    main()
