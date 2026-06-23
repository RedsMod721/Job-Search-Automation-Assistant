from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from src import database
from src.constants import PROJECT_ROOT
from src.services import extraction_correction_service, extraction_evaluation_service
from src.services.extraction_quality import apply_rule_based_corrections


def _test_dir() -> Path:
    path = PROJECT_ROOT / ".tmp" / f"stage6-tests-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_stage6_dataset_loads_required_coverage() -> None:
    dataset = extraction_evaluation_service.load_evaluation_dataset()
    fixtures = dataset["fixtures"]

    assert dataset["dataset_version"] == "stage6-v1"
    assert len(fixtures) == 7
    assert {fixture["role_family"] for fixture in fixtures} == {
        "AI Consultant",
        "AI Product",
        "Data Analyst",
        "Business Analyst",
        "Junior Consultant",
        "Strategy Analyst",
        "Marketing Analyst",
    }
    assert {fixture["language"] for fixture in fixtures} == {"English", "French"}
    assert {"Greenhouse", "Lever", "Workday", "Ashby"}.issubset({fixture["source_platform"] for fixture in fixtures})


def test_real_json_manifest_loads_posts_as_evaluation_fixtures() -> None:
    test_dir = _test_dir()
    post_dir = test_dir / "01_real_post"
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "raw_post.txt").write_text(
        "Example Co recrute un Business Analyst a Paris. Competences requises: SQL.",
        encoding="utf-8",
    )
    (post_dir / "expected_extraction.json").write_text(
        json.dumps(
            {
                "company_name": "Example Co",
                "job_title": "Business Analyst",
                "salary": "not included",
                "required_skills": ["SQL"],
                "detected_language": "French",
                "source_platform": "LinkedIn",
            }
        ),
        encoding="utf-8",
    )
    (test_dir / "MANIFEST.json").write_text(
        json.dumps(
            {
                "corpus_name": "Real test corpus",
                "generated_at_utc": "2026-06-23T13:22:39+00:00",
                "post_count": 1,
                "posts": [
                    {
                        "post_number": 1,
                        "folder": "01_real_post",
                        "company_name": "Example Co",
                        "job_title": "Business Analyst",
                        "source_platform": "LinkedIn",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    dataset = extraction_evaluation_service.load_evaluation_dataset(test_dir / "MANIFEST.json")

    assert dataset["dataset_version"] == "stage6-real-2026-06-23"
    assert dataset["fixtures"][0]["fixture_id"] == "01_real_post"
    assert dataset["fixtures"][0]["expected_fields"] == [
        "company_name",
        "job_title",
        "salary",
        "required_skills",
        "detected_language",
        "source_platform",
    ]


def test_committed_real_corpus_fixture_gate_passes() -> None:
    test_dir = _test_dir()
    dataset_path = PROJECT_ROOT / "samples" / "extraction_eval" / "real_2026_06_23" / "MANIFEST.json"

    dataset = extraction_evaluation_service.load_evaluation_dataset(dataset_path)
    result = extraction_evaluation_service.run_evaluation(
        {"llm": {"model": "fixture-static", "extraction_prompt_version": "stage6-v2"}},
        dataset_path=dataset_path,
        output_dir=test_dir / "evaluations",
        runner="fixture",
        record_to_db=False,
    )

    assert len(dataset["fixtures"]) == 20
    assert dataset["dataset_version"] == "stage6-real-2026-06-23"
    assert result["status"] == "PASS"
    assert result["aggregate_metrics"]["field_accuracy"] == 1.0


def test_rule_corrections_clear_unsourced_salary_and_company_size() -> None:
    raw_text = "Example Co is hiring an Analyst in Paris. Required skills: SQL and Excel. Cover letter not required."
    actual = {
        "company_name": "Example Co",
        "job_title": "Analyst",
        "salary": "EUR 65,000",
        "company_size": "500 employees",
        "detected_language": "",
        "required_skills": ["SQL", "Excel"],
        "motivation_letter_required": None,
    }

    corrected, issues = apply_rule_based_corrections(raw_text, actual)

    assert corrected["salary"] == ""
    assert corrected["company_size"] == ""
    assert corrected["detected_language"] == "English"
    assert corrected["motivation_letter_required"] is False
    assert {issue.issue_code for issue in issues}.issuperset(
        {
            "salary_without_source_signal",
            "company_size_without_source_signal",
            "language_missing",
            "motivation_letter_signal_missing",
        }
    )


def test_fixture_evaluation_passes_and_records_database_metadata() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "applications.db"
    output_dir = test_dir / "evaluations"
    database.init_db(db_path)

    result = extraction_evaluation_service.run_evaluation(
        {"llm": {"model": "fixture-static", "extraction_prompt_version": "stage6-v2"}},
        output_dir=output_dir,
        runner="fixture",
        db_path=db_path,
    )

    assert result["status"] == "PASS"
    assert result["aggregate_metrics"]["fixture_count"] == 7
    assert result["aggregate_metrics"]["field_accuracy"] >= 0.8
    assert Path(result["output_path"]).exists()

    summary = database.extraction_quality_summary(db_path)
    assert summary["latest_evaluation"]["evaluation_run_id"] == result["evaluation_run_id"]
    assert summary["latest_evaluation"]["aggregate_metrics"]["fixture_count"] == 7


def test_review_correction_logging_records_changed_fields() -> None:
    test_dir = _test_dir()
    db_path = test_dir / "applications.db"
    database.init_db(db_path)
    original = {
        "company_name": "Nexa AI Advisory",
        "job_title": "Junior AI Consultant",
        "salary": "EUR 70,000",
        "required_skills": ["Python"],
    }
    reviewed = {
        "company_name": "Nexa AI Advisory",
        "job_title": "Junior AI Consultant",
        "salary": "",
        "required_skills": "Python\nSQL",
    }

    count = extraction_correction_service.record_review_corrections(
        original,
        reviewed,
        raw_text="Nexa AI Advisory job post without salary. Required skills: Python and SQL.",
        application_id="app-stage6",
        settings={"llm": {"model": "fixture-static", "extraction_prompt_version": "stage6-v2"}},
        db_path=str(db_path),
    )

    corrections = database.list_extraction_corrections(db_path, application_id="app-stage6")
    assert count == 2
    assert {item["field_name"] for item in corrections} == {"salary", "required_skills"}
