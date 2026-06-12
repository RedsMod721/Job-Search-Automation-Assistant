from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests

from .utils import load_yaml, now_iso, resolve_path, safe_filename


def select_letter_language(
    application: dict[str, Any],
    user_preference: str = "auto",
) -> str:
    if user_preference.lower() != "auto":
        return user_preference
    detected = str(application.get("detected_language") or "").lower()
    return "French" if detected.startswith("fr") else "English"


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _profile_summary(profile: dict[str, Any] | None) -> str:
    profile = profile or {}
    user = profile.get("user", profile)
    education = profile.get("education", [])
    preferences = profile.get("work_preferences", {})
    parts = [
        f"{user.get('first_name', 'Sebastian')} {user.get('last_name', 'Vazquez')}",
        "business analytics, data, consulting, and practical AI profile",
        f"availability: {preferences.get('availability', 'Immediate')}",
    ]
    if education:
        first = education[0]
        parts.append(
            f"education: {first.get('degree_name') or first.get('degree', '')} "
            f"in {first.get('major', '')}".strip()
        )
    return "; ".join(part for part in parts if part)


def _application_summary(application: dict[str, Any]) -> str:
    keys = (
        "company_name",
        "job_title",
        "job_domain",
        "location",
        "required_skills",
        "key_responsibilities",
        "preferred_qualifications",
        "raw_job_description",
    )
    return "\n".join(f"{key}: {application.get(key, '')}" for key in keys)


def _call_ollama_text(prompt: str, llm_settings: dict[str, Any]) -> str:
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
                    "options": {"temperature": temperature},
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            text = str(response.json().get("response", "")).strip()
            if text:
                return text
            errors.append(f"{model} returned empty text")
        except Exception as exc:
            errors.append(f"{model}: {exc}")
    raise RuntimeError("; ".join(errors) or "No Ollama model response was available.")


def _load_template(
    language: str,
    documents_config: dict[str, Any] | None,
    warnings: list[str],
) -> str:
    template_key = "french" if language.lower().startswith("fr") else "english"
    templates = (documents_config or {}).get("documents", {}).get("motivation_letter_templates", {})
    template_path = templates.get(template_key, {}).get("file_path", "")
    if template_path:
        resolved = resolve_path(template_path)
        if resolved.exists():
            return resolved.read_text(encoding="utf-8")
        warnings.append(f"Template file missing: {resolved}")

    fallback = (
        "Madame, Monsieur,\n\n"
        "Je vous adresse ma candidature pour le poste de {job_title} chez {company_name}. "
        "Mon parcours combine analyse business, data et usages concrets de l'IA. "
        "Le profil {selected_cv_domain} semble pertinent pour cette opportunite.\n\n"
        "Je serais ravi d'echanger avec vous sur ma candidature.\n\n"
        "Cordialement,\nSebastian Vazquez"
        if template_key == "french"
        else "Dear Hiring Team,\n\n"
        "I am writing to express my interest in the {job_title} role at {company_name}. "
        "My background combines business analytics, structured problem solving, and hands-on "
        "work with data and AI tools. The {selected_cv_domain} profile appears to be the "
        "strongest fit for this opportunity.\n\n"
        "I would be glad to discuss how my profile could support your team.\n\n"
        "Kind regards,\nSebastian Vazquez"
    )
    return fallback


def _format_template_letter(
    application: dict[str, Any],
    selected_cv: str,
    language: str,
    documents_config: dict[str, Any] | None,
    warnings: list[str],
) -> str:
    template = _load_template(language, documents_config, warnings)
    return template.format(
        job_title=application.get("job_title") or "the role",
        company_name=application.get("company_name") or "the company",
        selected_cv_domain=selected_cv.replace("_", " "),
    )


def _build_letter_prompt(
    application: dict[str, Any],
    selected_cv: str,
    language: str,
    profile: dict[str, Any] | None,
    user_notes: str,
) -> str:
    return f"""You are helping Sebastian Vazquez draft a short motivation letter for a job application.

Rules:
- Maximum 250 words.
- Language: {language}.
- Tone: professional, energetic, and personally connected.
- Mention the company and job title.
- Connect the role to Sebastian's profile.
- Use the selected CV domain: {selected_cv}.
- Do not invent experience.
- Do not overclaim.
- Do not mention salary.
- Keep the letter ready to edit and send.

Sebastian profile summary:
{_profile_summary(profile)}

Job information:
{_application_summary(application)}

Optional user notes:
{user_notes}

Write the motivation letter only.
"""


def generate_letter(
    application: dict[str, Any],
    selected_cv: str,
    language: str = "auto",
    profile: dict[str, Any] | None = None,
    user_notes: str = "",
    documents_config: dict[str, Any] | None = None,
    llm_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_language = select_letter_language(application, language)
    warnings: list[str] = []
    letter_text = ""

    if llm_settings and str(llm_settings.get("provider", "ollama")).lower() == "ollama":
        prompt = _build_letter_prompt(application, selected_cv, selected_language, profile, user_notes)
        try:
            letter_text = _call_ollama_text(prompt, llm_settings)
        except RuntimeError as exc:
            warnings.append(
                "Ollama letter generation failed; used the configured template instead. "
                f"Details: {exc}"
            )

    if not letter_text:
        letter_text = _format_template_letter(
            application,
            selected_cv,
            selected_language,
            documents_config,
            warnings,
        )

    max_words = int((profile or {}).get("motivation_letters", {}).get("max_words", 250))
    word_count = _word_count(letter_text)
    if word_count > max_words:
        warnings.append(f"Draft is {word_count} words; target maximum is {max_words}.")

    return {
        "application_id": application.get("application_id", ""),
        "language": selected_language,
        "word_count": word_count,
        "letter_text": letter_text,
        "file_path": "",
        "warnings": warnings,
    }


def save_letter(application_id: str, letter_text: str, language: str) -> str:
    output_dir = resolve_path("generated/motivation_letters")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso().replace(":", "-")
    filename = safe_filename(f"{timestamp}_{application_id}_{language}.md")
    output_path = output_dir / filename
    output_path.write_text(letter_text, encoding="utf-8")
    return str(output_path)
