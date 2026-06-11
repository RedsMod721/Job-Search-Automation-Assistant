from __future__ import annotations

from typing import Any

import streamlit as st

from src import cv_matcher, database, extractor, form_helper, letter_generator, sheets_sync
from src.constants import (
    APPLICATION_CHANNEL_VALUES,
    CONTRACT_TYPE_VALUES,
    CV_KEYS,
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
    st.dataframe(recent_rows, use_container_width=True, hide_index=True)


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
    raw_text = st.text_area("Paste a job post for local extraction", height=180)
    if st.button("Analyze with local model"):
        llm_settings = settings.get("llm", {})
        try:
            extraction = extractor.extract_job_post(
                raw_text,
                model=llm_settings.get("model", "qwen2.5:7b"),
                timeout_seconds=int(llm_settings.get("timeout_seconds", 120)),
                temperature=float(llm_settings.get("temperature", 0.2)),
            )
            st.json(extraction)
        except ValueError as exc:
            st.warning(str(exc))


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
    st.dataframe(rows, use_container_width=True, hide_index=True)


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
