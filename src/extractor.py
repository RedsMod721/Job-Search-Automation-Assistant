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
    payload = response.json()
    return str(payload.get("response", ""))


def extract_job_post(
    raw_text: str,
    source_platform: str | None = None,
    job_url: str | None = None,
    model: str = "qwen2.5:7b",
    timeout_seconds: int = 120,
    temperature: float = 0.2,
) -> dict[str, Any]:
    cleaned_text = clean_job_text(raw_text)
    if not cleaned_text:
        raise ValueError("Job post text is empty.")

    prompt = build_extraction_prompt(cleaned_text)
    try:
        response_text = _call_ollama(prompt, model, timeout_seconds, temperature)
        parsed = json.loads(response_text)
    except Exception:
        parsed = {}

    extraction = normalize_extraction(parsed)
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

