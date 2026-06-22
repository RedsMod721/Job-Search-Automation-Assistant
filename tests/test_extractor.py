from __future__ import annotations

import json

import pytest

from src import extractor


def test_extract_job_post_uses_fallback_model_when_primary_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_call_ollama(
        prompt: str,
        model: str,
        timeout_seconds: int,
        temperature: float,
        host: str | None = None,
    ) -> str:
        calls.append(model)
        if model == "primary-model":
            return json.dumps(
                {
                    "company_name": "",
                    "job_title": "",
                    "required_skills": [],
                    "preferred_qualifications": [],
                    "key_responsibilities": [],
                    "detected_language": "",
                    "source_platform": "",
                    "application_channel": "",
                    "job_url": "",
                    "motivation_letter_required": None,
                }
            )
        return json.dumps(
            {
                "company_name": "Example AI Consulting Firm",
                "job_title": "Junior AI Consultant",
                "required_skills": ["Python", "SQL"],
                "preferred_qualifications": ["Azure AI"],
                "key_responsibilities": ["Analyze business processes"],
                "detected_language": "English",
                "source_platform": "LinkedIn",
                "application_channel": "Company Career Page",
                "job_url": "https://example.com/job",
                "motivation_letter_required": False,
            }
        )

    monkeypatch.setattr(extractor, "_call_ollama", fake_call_ollama)

    result = extractor.extract_job_post(
        "Example job post text",
        model="primary-model",
        fallback_models=["fallback-model"],
    )

    assert calls == ["primary-model", "fallback-model"]
    assert result["company_name"] == "Example AI Consulting Firm"
    assert result["job_title"] == "Junior AI Consultant"
    assert result["required_skills"] == ["Python", "SQL"]
    assert result["motivation_letter_required"] is False


def test_extract_job_post_raises_after_all_models_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_ollama(*args: object, **kwargs: object) -> str:
        return ""

    monkeypatch.setattr(extractor, "_call_ollama", fake_call_ollama)

    with pytest.raises(RuntimeError, match="All LLM extraction attempts failed"):
        extractor.extract_job_post(
            "Example job post text",
            model="primary-model",
            fallback_models=["fallback-model"],
        )
