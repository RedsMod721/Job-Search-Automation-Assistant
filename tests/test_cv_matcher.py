from __future__ import annotations

from src.cv_matcher import get_cv_file_path, recommend_cv, score_cv_matches
from src.utils import load_yaml


def test_cv_matcher_recommends_ai_for_ai_consulting_role() -> None:
    documents_config = load_yaml("config/documents.yaml")
    application = {
        "job_title": "Junior AI Consultant",
        "job_domain": "AI Consulting",
        "key_responsibilities": [
            "Support AI strategy workshops",
            "Identify process automation opportunities",
            "Prepare client presentations",
        ],
        "required_skills": ["Python", "LLM", "OpenAI API", "consulting"],
        "preferred_qualifications": ["Azure AI", "prompt engineering"],
        "raw_job_description": (
            "This role focuses on generative AI, LLM use cases, automation, "
            "business transformation, and client-facing AI product work."
        ),
    }

    recommendation = recommend_cv(application, documents_config)

    assert recommendation["recommended_cv"] == "ai"
    assert recommendation["secondary_cv"] in {"consulting", "data_analysis", "marketing"}
    assert recommendation["confidence_score"] > 0
    assert "LLM" in recommendation["matched_keywords"]


def test_score_cv_matches_uses_all_configured_cv_keys() -> None:
    documents_config = load_yaml("config/documents.yaml")
    scores = score_cv_matches(
        {"job_title": "Marketing Analyst", "required_skills": ["SEO", "CRM"]},
        documents_config,
    )

    assert set(scores) == {"marketing", "consulting", "data_analysis", "ai"}
    assert scores["marketing"]["score"] > 0


def test_get_cv_file_path_resolves_project_path() -> None:
    documents_config = load_yaml("config/documents.yaml")
    path = get_cv_file_path("ai", documents_config)

    assert path.endswith("documents\\cvs\\CV_Sebastian.Vazquez_Anglais-AI.pdf") or path.endswith(
        "documents/cvs/CV_Sebastian.Vazquez_Anglais-AI.pdf"
    )

