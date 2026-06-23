from __future__ import annotations

from typing import Any

from src import extractor


def run_extraction(raw_text: str, settings: dict[str, Any]) -> dict[str, Any]:
    llm_settings = settings.get("llm", {})
    return extractor.extract_job_post(
        raw_text,
        model=llm_settings.get("model", "qwen2.5:7b"),
        fallback_models=list(llm_settings.get("fallback_models", [])),
        timeout_seconds=int(llm_settings.get("timeout_seconds", 120)),
        temperature=float(llm_settings.get("temperature", 0.2)),
        prompt_version=str(llm_settings.get("extraction_prompt_version") or "") or None,
        enable_rule_correction=True,
    )
