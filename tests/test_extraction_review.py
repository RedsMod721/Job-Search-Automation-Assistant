from __future__ import annotations

from app import (
    _application_matches_filters,
    _build_company_search_request,
    _build_review_refresh_state,
    _merge_company_search_result,
    _review_refresh_defaults,
    build_application_from_company_search_result,
    build_application_from_reviewed_extraction,
)


def test_reviewed_extraction_builds_application_payload() -> None:
    application = build_application_from_reviewed_extraction(
        {
            "company_name": "Example AI Consulting Firm",
            "job_title": "Junior AI Consultant",
            "location": "Paris, France",
            "required_skills": "Python\nSQL\nLLM orchestration",
            "key_responsibilities": "Analyze business processes\nPrepare client presentations",
            "preferred_qualifications": "Azure AI\nConsulting experience",
            "source_platform": "LinkedIn",
            "job_url": "https://example.com/job",
            "motivation_letter_required": "No",
        },
        raw_job_description="Full pasted job post",
    )

    assert application["company_name"] == "Example AI Consulting Firm"
    assert application["job_title"] == "Junior AI Consultant"
    assert application["location"] == "Paris, France"
    assert application["raw_job_description"] == "Full pasted job post"
    assert application["status"] == "To Apply"
    assert application["required_skills"] == ["Python", "SQL", "LLM orchestration"]
    assert application["key_responsibilities"] == [
        "Analyze business processes",
        "Prepare client presentations",
    ]
    assert application["preferred_qualifications"] == ["Azure AI", "Consulting experience"]
    assert application["source_platform"] == "LinkedIn"
    assert application["job_url"] == "https://example.com/job"
    assert application["motivation_letter_required"] is False


def test_reviewed_extraction_accepts_existing_list_values_and_overrides_status() -> None:
    application = build_application_from_reviewed_extraction(
        {
            "required_skills": ["Python", "  Power BI  ", ""],
            "key_responsibilities": ["Build dashboards"],
            "preferred_qualifications": [],
            "motivation_letter_required": True,
        },
        raw_job_description="  Raw text with whitespace  ",
        status="Saved",
        notes="  Check salary before applying  ",
    )

    assert application["required_skills"] == ["Python", "Power BI"]
    assert application["key_responsibilities"] == ["Build dashboards"]
    assert application["preferred_qualifications"] == []
    assert application["motivation_letter_required"] is True
    assert application["raw_job_description"] == "Raw text with whitespace"
    assert application["status"] == "Saved"
    assert application["notes"] == "Check salary before applying"


def test_company_search_request_uses_reviewed_field_values() -> None:
    request = _build_company_search_request(
        {
            "company_name": "Manual Company",
            "company_industry": "Home automation",
            "job_domain": "Software",
            "job_title": "Python Developer",
            "location": "Paris, France",
            "company_website": "https://manual.example",
            "company_linkedin": "https://linkedin.example/manual",
            "career_page_url": "https://manual.example/careers",
            "job_url": "https://jobs.example/manual-python",
            "required_skills": "Python\nAPIs",
            "preferred_qualifications": ["Streamlit", "  Python  "],
        }
    )

    assert request["sector"] == "Home automation"
    assert request["location"] == "Paris, France"
    assert request["keywords"] == [
        "Manual Company",
        "https://manual.example",
        "https://linkedin.example/manual",
        "https://manual.example/careers",
        "Python Developer",
        "https://jobs.example/manual-python",
        "Python",
        "APIs",
        "Streamlit",
    ]


def test_company_search_merge_overwrites_found_company_fields_only() -> None:
    reviewed = {
        "company_name": "Old Company",
        "company_size": "Small",
        "company_industry": "Old Industry",
        "company_website": "https://old.example",
        "company_linkedin": "",
        "career_page_url": "https://old.example/jobs",
        "job_title": "Data Analyst",
        "required_skills": ["Python"],
    }

    merged = _merge_company_search_result(
        reviewed,
        {
            "company_name": "Found Company",
            "company_size": "1000-5000",
            "company_industry": "",
            "company_website": None,
            "company_linkedin": " https://linkedin.example/found ",
            "career_page_url": "https://found.example/careers",
        },
    )

    assert merged["company_name"] == "Found Company"
    assert merged["company_size"] == "1000-5000"
    assert merged["company_industry"] == "Old Industry"
    assert merged["company_website"] == "https://old.example"
    assert merged["company_linkedin"] == "https://linkedin.example/found"
    assert merged["career_page_url"] == "https://found.example/careers"
    assert merged["job_title"] == "Data Analyst"
    assert merged["required_skills"] == ["Python"]


def test_review_refresh_state_preserves_status_and_notes() -> None:
    state = _build_review_refresh_state("Applied", "Call recruiter after search")

    status, notes = _review_refresh_defaults(state)

    assert status == "Applied"
    assert notes == "Call recruiter after search"


def test_review_refresh_state_defaults_invalid_status() -> None:
    status, notes = _review_refresh_defaults({"status": "Unexpected", "notes": "Keep this"})

    assert status == "To Apply"
    assert notes == "Keep this"


def test_application_matches_tracker_filters() -> None:
    application = {
        "company_name": "Acme AI",
        "job_domain": "AI consulting",
        "location": "Geneva",
        "source_platform": "LinkedIn",
        "selected_cv": "ai",
        "status": "Applied",
        "archived": 0,
    }

    assert _application_matches_filters(
        application,
        status_filter="Applied",
        company_query="acme",
        domain_query="consult",
        source_filter="LinkedIn",
        cv_filter="ai",
        location_query="geneva",
    )
    assert not _application_matches_filters(application, status_filter="Rejected")
    assert not _application_matches_filters({**application, "archived": 1})


def test_company_search_result_builds_application_payload() -> None:
    application = build_application_from_company_search_result(
        {
            "company_name": "Acme AI",
            "company_website": "https://acme.example",
            "company_linkedin": "https://linkedin.example/acme",
            "career_page_url": "https://acme.example/careers",
            "company_industry": "AI",
            "source_url": "https://source.example",
        },
        job_title="AI Analyst",
        job_url="https://acme.example/jobs/ai-analyst",
        notes="Review fit",
    )

    assert application["company_name"] == "Acme AI"
    assert application["job_title"] == "AI Analyst"
    assert application["source_platform"] == "Company Website"
    assert application["application_channel"] == "Company Career Page"
    assert "https://source.example" in application["notes"]
