from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from .constants import EXTRACTION_LIST_FIELDS, EXTRACTION_SCHEMA_KEYS
from .utils import clean_string


def clean_job_text(raw_text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", clean_string(raw_text).replace("\\n", "\n"))


def default_extraction() -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key in EXTRACTION_SCHEMA_KEYS:
        data[key] = [] if key in EXTRACTION_LIST_FIELDS else ""
    data["motivation_letter_required"] = None
    return data


def build_extraction_prompt(job_post_text: str) -> str:
    schema = json.dumps(default_extraction(), indent=2)
    return f"""You are an information extraction assistant for a job application tracking tool.

Your task is to extract structured information from the job post provided by the user.

Rules:
- Return JSON only.
- Follow the exact schema.
- Extract only facts present in the job post.
- Do not invent salary, company size, benefits, company website, or requirements.
- If a field is missing, use an empty string, null, or an empty list.
- Keep lists concise.
- Detect the language of the job post.
- Detect whether a motivation letter is explicitly requested.
- If unsure about a field, leave it empty.

Schema:
{schema}

Job post:
{job_post_text}
"""


def _call_ollama(
    prompt: str,
    model: str,
    timeout_seconds: int,
    temperature: float,
    host: str | None = None,
) -> str:
    base_url = (host or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": temperature},
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Unable to reach Ollama at {base_url}. Please start Ollama and install the selected model."
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("Ollama returned a non-JSON response.") from exc

    response_text = str(payload.get("response", "")).strip()
    if not response_text:
        raise RuntimeError("Ollama returned an empty extraction response.")
    return response_text


def _has_meaningful_extraction(extraction: dict[str, Any]) -> bool:
    for key, value in extraction.items():
        if key == "motivation_letter_required":
            if value in (True, False):
                return True
            continue
        if isinstance(value, list):
            if value:
                return True
            continue
        if isinstance(value, str):
            if value.strip():
                return True
            continue
        if value not in (None, ""):
            return True
    return False


def _extract_with_model(
    prompt: str,
    model: str,
    timeout_seconds: int,
    temperature: float,
) -> dict[str, Any]:
    response_text = _call_ollama(prompt, model, timeout_seconds, temperature)
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("returned JSON, but not as an object")

    extraction = normalize_extraction(parsed)
    if not _has_meaningful_extraction(extraction):
        raise RuntimeError("returned an empty extraction")
    return extraction


def extract_job_post(
    raw_text: str,
    source_platform: str | None = None,
    job_url: str | None = None,
    model: str = "qwen2.5:7b",
    fallback_models: list[str] | None = None,
    timeout_seconds: int = 120,
    temperature: float = 0.2,
) -> dict[str, Any]:
    cleaned_text = clean_job_text(raw_text)
    if not cleaned_text:
        raise ValueError("Job post text is empty.")

    prompt = build_extraction_prompt(cleaned_text)
    candidate_models: list[str] = []
    for candidate in [model, *(fallback_models or [])]:
        if candidate and candidate not in candidate_models:
            candidate_models.append(candidate)

    last_error: str | None = None
    for candidate_model in candidate_models:
        try:
            extraction = _extract_with_model(prompt, candidate_model, timeout_seconds, temperature)
            break
        except RuntimeError as exc:
            last_error = f"{candidate_model} {exc}"
    else:
        raise RuntimeError(
            "All LLM extraction attempts failed: " + (last_error or "no model response was available.")
        )

    if source_platform:
        extraction["source_platform"] = source_platform
    if job_url:
        extraction["job_url"] = job_url
    return extraction


def validate_extraction(extraction: dict[str, Any]) -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if not isinstance(extraction, dict):
        return False, ["Extraction output is not a JSON object."]

    for key in EXTRACTION_LIST_FIELDS:
        if key in extraction and not isinstance(extraction[key], list):
            warnings.append(f"{key} must be a list.")

    motivation_value = extraction.get("motivation_letter_required")
    if motivation_value not in (True, False, None):
        warnings.append("motivation_letter_required must be true, false, or null.")

    return not warnings, warnings


def normalize_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    normalized = default_extraction()
    if not isinstance(extraction, dict):
        return normalized

    for key in EXTRACTION_SCHEMA_KEYS:
        value = extraction.get(key, normalized[key])
        if key in EXTRACTION_LIST_FIELDS:
            normalized[key] = value if isinstance(value, list) else []
        elif key == "motivation_letter_required":
            normalized[key] = value if value in (True, False, None) else None
        else:
            normalized[key] = "" if value is None else str(value).strip()
    return normalized

