from __future__ import annotations

import re
from typing import Any

from .constants import CONFIG_FILES, CV_KEYS
from .utils import deserialize_list, load_yaml, resolve_path


FIELD_WEIGHTS = {
    "job_title": 3,
    "job_domain": 3,
    "required_skills": 3,
    "key_responsibilities": 2,
    "preferred_qualifications": 2,
    "raw_job_description": 1,
}


def _normalize_text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        value = " ".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value or "").lower())


def _field_text(application: dict[str, Any], field: str) -> str:
    value = application.get(field, "")
    if field in {"required_skills", "key_responsibilities", "preferred_qualifications"}:
        value = deserialize_list(value)
    return _normalize_text(value)


def _load_documents_config(documents_config: dict[str, Any] | None) -> dict[str, Any]:
    if documents_config is not None:
        return documents_config
    return load_yaml(CONFIG_FILES["documents"])


def score_cv_matches(
    application: dict[str, Any],
    documents_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = _load_documents_config(documents_config)
    cv_config = config.get("documents", {}).get("cvs", {})
    scores: dict[str, dict[str, Any]] = {}

    for cv_key in CV_KEYS:
        cv_data = cv_config.get(cv_key, {})
        keywords = cv_data.get("domain_keywords", [])
        score = 0
        matched_keywords: list[str] = []

        for keyword in keywords:
            keyword_text = _normalize_text(keyword)
            if not keyword_text:
                continue
            for field, weight in FIELD_WEIGHTS.items():
                if keyword_text in _field_text(application, field):
                    score += weight
                    if keyword not in matched_keywords:
                        matched_keywords.append(str(keyword))

        scores[cv_key] = {
            "score": score,
            "matched_keywords": matched_keywords,
            "label": cv_data.get("label", cv_key),
        }

    return scores


def recommend_cv(
    application: dict[str, Any],
    documents_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scores = score_cv_matches(application, documents_config)
    ranked = sorted(
        scores.items(),
        key=lambda item: (item[1]["score"], item[0] == "ai"),
        reverse=True,
    )
    recommended_cv = ranked[0][0] if ranked else "ai"
    secondary_cv = ranked[1][0] if len(ranked) > 1 else ""
    top_score = scores.get(recommended_cv, {}).get("score", 0)
    total_score = sum(score_data["score"] for score_data in scores.values())
    confidence = round(top_score / total_score, 2) if total_score else 0.0
    matched_keywords = scores.get(recommended_cv, {}).get("matched_keywords", [])

    if top_score:
        reason = (
            f"The role matches the {scores[recommended_cv]['label']} profile through "
            f"{', '.join(matched_keywords[:5])}."
        )
    else:
        reason = (
            "No strong keyword match was found. AI CV is used as the default starting "
            "point and should be reviewed manually."
        )
        recommended_cv = "ai"
        secondary_cv = "data_analysis"

    return {
        "recommended_cv": recommended_cv,
        "secondary_cv": secondary_cv,
        "confidence_score": confidence,
        "reason": reason,
        "matched_keywords": matched_keywords,
        "scores": scores,
    }


def get_cv_file_path(
    cv_key: str,
    documents_config: dict[str, Any] | None = None,
) -> str:
    if cv_key not in CV_KEYS:
        raise ValueError(f"Unknown CV key: {cv_key}")
    config = _load_documents_config(documents_config)
    file_path = config.get("documents", {}).get("cvs", {}).get(cv_key, {}).get("file_path")
    if not file_path:
        raise KeyError(f"Missing file path for CV key: {cv_key}")
    return str(resolve_path(file_path))

