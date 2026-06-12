from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from src.constants import PROJECT_ROOT
from src import form_helper, letter_generator


def test_generate_letter_returns_schema_and_saves_file(
    monkeypatch,
) -> None:
    output_root = PROJECT_ROOT / f"pytest-cache-files-generated-{uuid4().hex}"
    monkeypatch.setattr(letter_generator, "resolve_path", lambda path: output_root / path)
    try:
        result = letter_generator.generate_letter(
            {
                "application_id": "app-1",
                "company_name": "Acme AI",
                "job_title": "AI Analyst",
                "detected_language": "English",
            },
            selected_cv="ai",
            profile={"motivation_letters": {"max_words": 250}},
            documents_config={},
        )

        assert result["application_id"] == "app-1"
        assert result["language"] == "English"
        assert "Acme AI" in result["letter_text"]
        assert result["word_count"] > 0
        assert result["file_path"] == ""

        file_path = Path(letter_generator.save_letter("app-1", result["letter_text"], result["language"]))
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == result["letter_text"]
    finally:
        shutil.rmtree(output_root, ignore_errors=True)


def test_generate_form_answers_returns_schema_and_saves_file(
    monkeypatch,
) -> None:
    output_root = PROJECT_ROOT / f"pytest-cache-files-generated-{uuid4().hex}"
    monkeypatch.setattr(form_helper, "resolve_path", lambda path: output_root / path)
    profile = {
        "user": {
            "first_name": "Sebastian",
            "last_name": "Vazquez",
            "email": "sebastian@example.com",
            "phone": "+33",
            "linkedin_url": "https://linkedin.example/sebastian",
            "github_url": "https://github.example/sebastian",
        }
    }

    try:
        result = form_helper.generate_common_answers(
            {"application_id": "app-2", "company_name": "Acme AI", "job_title": "AI Analyst"},
            profile,
            "LinkedIn",
            {"default_answers": {"availability": "Immediate"}},
        )

        assert result["application_id"] == "app-2"
        assert result["platform"] == "LinkedIn"
        assert result["answers"]["personal_information"]["full_name"] == "Sebastian Vazquez"
        assert result["answers"]["common_questions"]["availability"] == "Immediate"
        assert result["file_path"] == ""

        file_path = Path(form_helper.save_form_answers("app-2", result))
        assert file_path.exists()
        saved = json.loads(file_path.read_text(encoding="utf-8"))
        assert saved["application_id"] == "app-2"
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
