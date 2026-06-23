from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

PromptStatus = Literal["DRAFT", "TESTING", "ACTIVE", "RETIRED"]


class PromptDefinition(BaseModel):
    prompt_id: str
    task: str
    version: str
    language: str = "multilingual"
    template: str = ""
    schema_version: str = "1"
    created_at: str = ""
    status: PromptStatus = "ACTIVE"
    owner: str
    description: str
    notes: str = ""

    def render(self, **values: str) -> str:
        return self.template.format(**values)


JOB_EXTRACTION_STAGE6_V1_TEMPLATE = """You are an information extraction assistant for a job application tracking tool.

Extract structured information from the job post provided by the user.

Rules:
- Return JSON only.
- Follow the exact schema.
- Extract only facts present in the job post.
- Do not infer or invent salary, company size, benefits, company website, LinkedIn URL, or requirements.
- If salary is absent, use an empty string.
- If company size is absent, use an empty string.
- Separate required skills from preferred qualifications.
- Keep lists concise and factual.
- Detect the language of the job post as English, French, or Unknown.
- Detect whether a motivation letter or cover letter is explicitly required.
- If a field is missing or uncertain, leave it empty, null, or an empty list.

Schema:
{schema}

Job post:
{job_post_text}
"""


JOB_EXTRACTION_STAGE6_V2_TEMPLATE = """You are an information extraction assistant for a job application tracking tool.

Extract structured information from the pasted job page text.

Rules:
- Return JSON only.
- Follow the exact schema.
- Extract only facts present in the pasted text.
- Treat pasted company panels, source headers, and application widgets as available evidence
  when they are included in the text.
- Do not invent salary, company size, benefits, company website, LinkedIn URL, application channel, or requirements.
- If salary is absent, use an empty string.
- If company size is absent, use an empty string.
- If application route is not explicitly stated, leave application_channel empty.
- Fill job_domain when the title or body clearly identifies the function, such as business
  analysis, strategy, AI engineering, data engineering, marketing analytics, product,
  consulting, or business development.
- Fill seniority_level only when the title or requirements state it, such as internship,
  junior, confirmed, senior, graduate, entry level, 2+ years, or 5+ years.
- Preserve explicit profile requirements as required_skills, including education,
  experience, languages, tools, methods, and soft skills.
- Separate optional, bonus, nice-to-have, or plus items into preferred_qualifications.
- Capture the main explicit responsibilities and requirements; do not collapse them to only keywords.
- Detect the substantive job-post language as English, French, or Unknown; ignore source
  UI labels when the body language is clear.
- Detect whether a motivation letter or cover letter is explicitly required.
- If a field is missing or uncertain, leave it empty, null, or an empty list.

Schema:
{schema}

Job post:
{job_post_text}
"""


JOB_EXTRACTION_STAGE3_TEMPLATE = """You are an information extraction assistant for a job application tracking tool.

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


PROMPT_HISTORY: dict[str, tuple[PromptDefinition, ...]] = {
    "job_extraction": (
        PromptDefinition(
            prompt_id="job_extraction",
            task="structured_job_post_extraction",
            version="stage3-v1",
            language="multilingual",
            template=JOB_EXTRACTION_STAGE3_TEMPLATE,
            schema_version="1",
            created_at="2026-06-17",
            status="RETIRED",
            owner="src.extractor",
            description="Original Stage 3 structured job extraction prompt.",
            notes="Kept for regression comparison.",
        ),
        PromptDefinition(
            prompt_id="job_extraction",
            task="structured_job_post_extraction",
            version="stage6-v1",
            language="multilingual",
            template=JOB_EXTRACTION_STAGE6_V1_TEMPLATE,
            schema_version="1",
            created_at="2026-06-22",
            status="RETIRED",
            owner="src.extractor",
            description="Extract structured job and company fields from pasted job posts.",
            notes="Adds stricter missing-field and no-hallucination instructions for salary and company size.",
        ),
        PromptDefinition(
            prompt_id="job_extraction",
            task="structured_job_post_extraction",
            version="stage6-v2",
            language="multilingual",
            template=JOB_EXTRACTION_STAGE6_V2_TEMPLATE,
            schema_version="1",
            created_at="2026-06-23",
            status="ACTIVE",
            owner="src.extractor",
            description="Extract structured job and company fields from real pasted job pages.",
            notes=(
                "Uses Stage 6 real corpus evidence to improve company-panel handling, role/domain fields, "
                "profile requirements, and application-channel abstention."
            ),
        ),
    ),
    "motivation_letter": (
        PromptDefinition(
            prompt_id="motivation_letter",
            task="motivation_letter_generation",
            version="stage3-v1",
            language="multilingual",
            template="See src.letter_generator for the current rendered template.",
            schema_version="1",
            created_at="2026-06-17",
            status="ACTIVE",
            owner="src.letter_generator",
            description="Draft a motivation letter for a selected application and CV profile.",
        ),
    ),
    "form_answers": (
        PromptDefinition(
            prompt_id="form_answers",
            task="application_form_answer_generation",
            version="stage3-v1",
            language="multilingual",
            template="See src.form_helper for the current rendered template.",
            schema_version="1",
            created_at="2026-06-17",
            status="ACTIVE",
            owner="src.form_helper",
            description="Generate reusable form answers for application portals.",
        ),
    ),
}


PROMPTS: dict[str, PromptDefinition] = {
    prompt_id: next(item for item in reversed(history) if item.status == "ACTIVE")
    for prompt_id, history in PROMPT_HISTORY.items()
}


def get_prompt(prompt_id: str, version: str | None = None) -> PromptDefinition:
    if version is None:
        return PROMPTS[prompt_id]
    for prompt in PROMPT_HISTORY[prompt_id]:
        if prompt.version == version:
            return prompt
    raise KeyError(f"Unknown prompt version for {prompt_id}: {version}")


def list_prompt_versions(prompt_id: str) -> tuple[PromptDefinition, ...]:
    return PROMPT_HISTORY[prompt_id]
