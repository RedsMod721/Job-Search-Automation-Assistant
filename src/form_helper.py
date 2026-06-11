from __future__ import annotations

import json
from typing import Any

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


def generate_common_answers(
    application: dict[str, Any],
    profile: dict[str, Any],
    platform: str,
    form_answers_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = (form_answers_config or {}).get("default_answers", {})
    company = application.get("company_name") or "this company"
    role = application.get("job_title") or "this role"
    selected_cv = application.get("selected_cv") or application.get("recommended_cv") or "selected"

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
            "platform": platform,
        },
    }


def generate_answer_for_field(
    field_label: str,
    application: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    field = field_label.lower()
    answers = generate_common_answers(application, profile, platform="Other")
    common = answers["common_questions"]
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

