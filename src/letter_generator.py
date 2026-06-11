from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import now_iso, resolve_path, safe_filename


def select_letter_language(
    application: dict[str, Any],
    user_preference: str = "auto",
) -> str:
    if user_preference.lower() != "auto":
        return user_preference
    detected = str(application.get("detected_language") or "").lower()
    return "French" if detected.startswith("fr") else "English"


def generate_letter(
    application: dict[str, Any],
    selected_cv: str,
    language: str = "auto",
    profile: dict[str, Any] | None = None,
    user_notes: str = "",
) -> str:
    selected_language = select_letter_language(application, language)
    company = application.get("company_name") or "the company"
    role = application.get("job_title") or "the role"
    cv_label = selected_cv.replace("_", " ")

    if selected_language.lower().startswith("fr"):
        return (
            f"Madame, Monsieur,\n\n"
            f"Je vous adresse ma candidature pour le poste de {role} chez {company}. "
            f"Mon parcours combine analyse business, data et une forte curiosite pour "
            f"les usages concrets de l'IA. Le profil {cv_label} semble le plus pertinent "
            f"pour cette opportunite.\n\n"
            f"Je serais ravi d'echanger avec vous sur ma candidature.\n\n"
            f"Cordialement,\nSebastian Vazquez"
        )

    return (
        f"Dear Hiring Team,\n\n"
        f"I am writing to express my interest in the {role} role at {company}. "
        f"My background combines business analytics, structured problem solving, and "
        f"hands-on work with data and AI tools. The {cv_label} profile appears to be "
        f"the strongest fit for this opportunity.\n\n"
        f"I would be glad to discuss how my profile could support your team.\n\n"
        f"Kind regards,\nSebastian Vazquez"
    )


def save_letter(application_id: str, letter_text: str, language: str) -> str:
    output_dir = resolve_path("generated/motivation_letters")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso().replace(":", "-")
    filename = safe_filename(f"{timestamp}_{application_id}_{language}.md")
    output_path = output_dir / filename
    output_path.write_text(letter_text, encoding="utf-8")
    return str(output_path)

