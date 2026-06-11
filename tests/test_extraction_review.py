from __future__ import annotations

from app import build_application_from_reviewed_extraction


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
