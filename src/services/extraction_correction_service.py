from __future__ import annotations

from typing import Any

from src import database, extractor
from src.constants import EXTRACTION_LIST_FIELDS, EXTRACTION_SCHEMA_KEYS
from src.normalization import content_hash
from src.prompts.registry import get_prompt
from src.services.application_service import coerce_motivation_letter_required, parse_review_list


def _coerce_review_value(field_name: str, value: Any) -> Any:
    if field_name in EXTRACTION_LIST_FIELDS:
        return parse_review_list(value)
    if field_name == "motivation_letter_required":
        return coerce_motivation_letter_required(value)
    return "" if value is None else str(value).strip()


def _normalized_comparison_value(field_name: str, value: Any) -> Any:
    if field_name in EXTRACTION_LIST_FIELDS:
        return [str(item).strip() for item in parse_review_list(value) if str(item).strip()]
    if field_name == "motivation_letter_required":
        return coerce_motivation_letter_required(value)
    return "" if value is None else str(value).strip()


def build_correction_records(
    original_extraction: dict[str, Any],
    reviewed_extraction: dict[str, Any],
    *,
    raw_text: str,
    application_id: str = "",
    settings: dict[str, Any] | None = None,
    fixture_id: str = "",
    source: str = "review_form",
) -> list[dict[str, Any]]:
    settings = settings or {}
    llm_settings = settings.get("llm", {})
    prompt_version = str(llm_settings.get("extraction_prompt_version") or get_prompt("job_extraction").version)
    model_name = str(llm_settings.get("model") or "")
    model_parameters = {
        "provider": llm_settings.get("provider", "ollama"),
        "temperature": llm_settings.get("temperature"),
        "timeout_seconds": llm_settings.get("timeout_seconds"),
        "fallback_models": list(llm_settings.get("fallback_models", [])),
    }
    normalized_original = extractor.normalize_extraction(original_extraction)
    records: list[dict[str, Any]] = []
    for field_name in EXTRACTION_SCHEMA_KEYS:
        original_value = _normalized_comparison_value(field_name, normalized_original.get(field_name))
        corrected_value = _normalized_comparison_value(
            field_name, _coerce_review_value(field_name, reviewed_extraction.get(field_name))
        )
        if original_value == corrected_value:
            continue
        records.append(
            {
                "application_id": application_id,
                "fixture_id": fixture_id,
                "raw_text_hash": content_hash(raw_text),
                "field_name": field_name,
                "original_value": original_value,
                "corrected_value": corrected_value,
                "prompt_version": prompt_version,
                "model_name": model_name,
                "model_parameters": model_parameters,
                "source": source,
            }
        )
    return records


def record_review_corrections(
    original_extraction: dict[str, Any],
    reviewed_extraction: dict[str, Any],
    *,
    raw_text: str,
    application_id: str,
    settings: dict[str, Any],
    db_path: str,
) -> int:
    records = build_correction_records(
        original_extraction,
        reviewed_extraction,
        raw_text=raw_text,
        application_id=application_id,
        settings=settings,
    )
    return database.record_extraction_corrections(records, db_path=db_path)
