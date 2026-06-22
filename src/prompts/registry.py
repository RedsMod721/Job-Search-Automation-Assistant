from __future__ import annotations

from pydantic import BaseModel


class PromptDefinition(BaseModel):
    prompt_id: str
    version: str
    owner: str
    description: str


PROMPTS: dict[str, PromptDefinition] = {
    "job_extraction": PromptDefinition(
        prompt_id="job_extraction",
        version="stage3-v1",
        owner="src.extractor",
        description="Extract structured job and company fields from pasted job posts.",
    ),
    "motivation_letter": PromptDefinition(
        prompt_id="motivation_letter",
        version="stage3-v1",
        owner="src.letter_generator",
        description="Draft a motivation letter for a selected application and CV profile.",
    ),
    "form_answers": PromptDefinition(
        prompt_id="form_answers",
        version="stage3-v1",
        owner="src.form_helper",
        description="Generate reusable form answers for application portals.",
    ),
}


def get_prompt(prompt_id: str) -> PromptDefinition:
    return PROMPTS[prompt_id]
