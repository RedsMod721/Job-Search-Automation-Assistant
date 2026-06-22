from __future__ import annotations

import json
from typing import Any

import requests

from .utils import now_iso, resolve_path, safe_filename


def _profile_user(profile: dict[str, Any]) -> dict[str, Any]:
    return profile.get("user", profile)


def generate_personal_info_block(profile: dict[str, Any]) -> dict[str, str]:
    user = _profile_user(profile)
    return {
        "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "location": "Open to relocation",
        "linkedin_url": user.get("linkedin_url", ""),
        "github_url": user.get("github_url", ""),
    }


def _deterministic_answers(
    application: dict[str, Any],
    profile: dict[str, Any],
    platform: str,
    form_answers_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = (form_answers_config or {}).get("default_answers", {})
    company = application.get("company_name") or "this company"
    role = application.get("job_title") or "this role"
    selected_cv = application.get("selected_cv") or application.get("recommended_cv") or "selected"

    languages = defaults.get(
        "languages",
        "French and Spanish are my native languages, and I have a C1 level in English.",
    )
    return {
        "personal_information": generate_personal_info_block(profile),
        "common_questions": {
            "tell_us_about_yourself": (
                "I am Sebastian Vazquez, a business and data analytics profile with "
                "experience connecting business needs, data tools, and practical AI use cases."
            ),
            "why_this_role": (
                f"I am interested in {role} because it connects closely with my {selected_cv} "
                "profile and gives me the opportunity to contribute to concrete business outcomes."
            ),
            "why_this_company": (
                f"I am interested in {company} because the role description suggests work where "
                "analytical thinking, communication, and practical execution matter."
            ),
            "why_should_we_hire_you": (
                "I bring a mix of business understanding, data skills, adaptability, and strong "
                "motivation to learn quickly in demanding environments."
            ),
            "availability": defaults.get("availability", "I am available to start immediately."),
            "salary_expectations": defaults.get(
                "salary_expectations",
                "I am flexible and open to discussing compensation depending on the role.",
            ),
            "work_authorization": defaults.get("work_authorization", ""),
            "relocation": defaults.get("relocation", "I am open to relocation for the right opportunity."),
            "languages": languages,
            "relevant_technical_skills": (
                "Relevant skills include business analytics, Python, SQL, data analysis, "
                "dashboarding, automation, and practical AI tooling."
            ),
            "relevant_soft_skills": (
                "I bring structured problem solving, communication, adaptability, curiosity, "
                "and a strong learning mindset."
            ),
            "platform": platform,
        },
    }


def _build_form_prompt(
    application: dict[str, Any],
    profile: dict[str, Any],
    platform: str,
) -> str:
    return f"""You are generating copy-ready job application form answers for Sebastian Vazquez.

Rules:
- Return valid JSON only.
- Keep answers clear and professional.
- Adapt the answer to the job and company.
- Do not invent experience.
- Do not overclaim.
- Prefer concise answers.
- If salary is asked, use a flexible market-based answer unless a number is required.
- If location is asked, prefer "open to relocation" unless a current city is mandatory.
- If work authorization is asked, mention European passport through Italian citizenship.
- Do not say Sebastian is looking for an internship unless explicitly asked.

Schema:
{{
  "personal_information": {{
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin_url": "",
    "github_url": ""
  }},
  "common_questions": {{
    "tell_us_about_yourself": "",
    "why_this_role": "",
    "why_this_company": "",
    "why_should_we_hire_you": "",
    "availability": "",
    "salary_expectations": "",
    "work_authorization": "",
    "relocation": "",
    "languages": "",
    "relevant_technical_skills": "",
    "relevant_soft_skills": ""
  }}
}}

Profile:
{profile}

Job:
{application}

Platform:
{platform}
"""


def _call_ollama_json(prompt: str, llm_settings: dict[str, Any]) -> dict[str, Any]:
    host = str(llm_settings.get("host") or "http://localhost:11434").rstrip("/")
    timeout_seconds = int(llm_settings.get("timeout_seconds", 120))
    temperature = float(llm_settings.get("temperature", 0.2))
    models = [
        llm_settings.get("model", "qwen2.5:7b"),
        *list(llm_settings.get("fallback_models", [])),
    ]
    errors: list[str] = []
    for model in [model for index, model in enumerate(models) if model and model not in models[:index]]:
        try:
            response = requests.post(
                f"{host}/api/generate",
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
            text = str(response.json().get("response", "")).strip()
            if text:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            errors.append(f"{model} returned invalid JSON")
        except Exception as exc:
            errors.append(f"{model}: {exc}")
    raise RuntimeError("; ".join(errors) or "No Ollama model response was available.")


def _normalize_answers(value: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "personal_information": dict(fallback.get("personal_information", {})),
        "common_questions": dict(fallback.get("common_questions", {})),
    }
    if isinstance(value.get("personal_information"), dict):
        for key, item in value["personal_information"].items():
            normalized["personal_information"][key] = "" if item is None else str(item)
    if isinstance(value.get("common_questions"), dict):
        for key, item in value["common_questions"].items():
            normalized["common_questions"][key] = "" if item is None else str(item)
    return normalized


def generate_common_answers(
    application: dict[str, Any],
    profile: dict[str, Any],
    platform: str,
    form_answers_config: dict[str, Any] | None = None,
    llm_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    fallback = _deterministic_answers(application, profile, platform, form_answers_config)
    answers = fallback

    if llm_settings and str(llm_settings.get("provider", "ollama")).lower() == "ollama":
        try:
            llm_answers = _call_ollama_json(_build_form_prompt(application, profile, platform), llm_settings)
            answers = _normalize_answers(llm_answers, fallback)
        except RuntimeError as exc:
            warnings.append(f"Ollama form answer generation failed; used deterministic answers instead. Details: {exc}")

    return {
        "application_id": application.get("application_id", ""),
        "platform": platform,
        "answers": answers,
        "file_path": "",
        "warnings": warnings,
    }


def generate_answer_for_field(
    field_label: str,
    application: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    field = field_label.lower()
    answers = generate_common_answers(application, profile, platform="Other")
    common = answers["answers"]["common_questions"]
    if "salary" in field:
        return common["salary_expectations"]
    if "authorization" in field or "sponsor" in field:
        return common["work_authorization"]
    if "relocation" in field:
        return common["relocation"]
    if "availability" in field or "start" in field:
        return common["availability"]
    if "company" in field:
        return common["why_this_company"]
    if "role" in field or "position" in field:
        return common["why_this_role"]
    return common["tell_us_about_yourself"]


def save_form_answers(application_id: str, answers: dict[str, Any]) -> str:
    output_dir = resolve_path("generated/form_answers")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso().replace(":", "-")
    filename = safe_filename(f"{timestamp}_{application_id}_form_answers.json")
    output_path = output_dir / filename
    output_path.write_text(json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)
