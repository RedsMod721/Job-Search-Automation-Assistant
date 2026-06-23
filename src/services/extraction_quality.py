from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from src.constants import EXTRACTION_LIST_FIELDS, EXTRACTION_SCHEMA_KEYS
from src.utils import clean_string, deserialize_list

EMPTY_MARKERS = {
    "",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "not included",
    "not specified",
    "not provided",
    "non specifie",
}
FRENCH_MARKERS = (
    " cdi ",
    " cdd ",
    " poste ",
    " mission ",
    " missions ",
    " competences ",
    " compétences ",
    " lettre de motivation ",
    " teletravail ",
    " télétravail ",
    " candidature ",
    " francais ",
    " français ",
)
ENGLISH_MARKERS = (
    " role ",
    " responsibilities ",
    " required skills ",
    " qualifications ",
    " cover letter ",
    " hybrid ",
    " remote ",
    " apply ",
)
SALARY_PATTERN = re.compile(
    r"(\b\d{2,3}\s?k\b|\b\d{4,6}\b|€|\beur\b|\beuro\b|\beuros\b|\bsalary\b|\bcompensation\b|"
    r"\bpackage\b|\br[eé]mun[eé]ration\b|\bsalaire\b)",
    re.IGNORECASE,
)
COMPANY_SIZE_PATTERN = re.compile(
    r"(\b\d+[,+]?\s*(employees|people|consultants|collaborators|collaborateurs|salari[eé]s|employ[eé]s)\b|"
    r"\bstartup\b|\bscale[- ]?up\b|\benterprise\b|\bpme\b|\beti\b|\bgrand groupe\b)",
    re.IGNORECASE,
)
ATS_SOURCES = {"greenhouse", "lever", "workday", "ashby", "smartrecruiters"}


@dataclass(frozen=True)
class RuleValidationIssue:
    field_name: str
    severity: str
    issue_code: str
    message: str
    suggested_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalized_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = clean_string(value).lower()
    text = text.replace("é", "e").replace("è", "e").replace("ê", "e").replace("à", "a")
    text = text.replace("ç", "c").replace("ô", "o").replace("ù", "u")
    return text


def _emptyish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, list):
        return not [_normalized_text(item) for item in value if _normalized_text(item)]
    return _normalized_text(value) in EMPTY_MARKERS


def _blankish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return not value
    return _normalized_text(value) == ""


def _field_list(value: Any) -> list[str]:
    return sorted({_normalized_text(item) for item in deserialize_list(value) if not _emptyish(item)})


def infer_language(raw_text: str) -> str:
    padded = f" {_normalized_text(raw_text)} "
    french_score = sum(1 for marker in FRENCH_MARKERS if marker in padded)
    english_score = sum(1 for marker in ENGLISH_MARKERS if marker in padded)
    if french_score > english_score:
        return "French"
    if english_score > french_score:
        return "English"
    return "Unknown"


def infer_motivation_letter_required(raw_text: str) -> bool | None:
    text = _normalized_text(raw_text)
    negative_patterns = (
        "motivation letter is optional",
        "cover letter is optional",
        "motivation letter optional",
        "cover letter optional",
        "motivation letter not required",
        "cover letter not required",
        "no cover letter",
        "lettre de motivation facultative",
        "lettre de motivation optionnelle",
        "lettre de motivation non requise",
    )
    positive_patterns = (
        "motivation letter required",
        "cover letter required",
        "please include a cover letter",
        "include a motivation letter",
        "lettre de motivation requise",
        "lettre de motivation demandee",
        "merci de joindre une lettre de motivation",
    )
    if any(pattern in text for pattern in negative_patterns):
        return False
    if any(pattern in text for pattern in positive_patterns):
        return True
    return None


def infer_application_channel(raw_text: str, extraction: dict[str, Any]) -> str:
    source = _normalized_text(extraction.get("source_platform"))
    text = _normalized_text(raw_text)
    if source in ATS_SOURCES or any(source_name in text for source_name in ATS_SOURCES):
        return "ATS Platform"
    if "company career page" in text or "company career" in text or "site carriere" in text:
        return "Company Career Page"
    if source == "company website":
        return "Company Career Page"
    if source == "linkedin" and "company career page" in text:
        return "Company Career Page"
    return ""


def infer_contract_type(raw_text: str) -> str:
    text = _normalized_text(raw_text)
    if " cdi " in f" {text} ":
        return "CDI"
    if "permanent" in text:
        return "Permanent"
    if " cdd " in f" {text} ":
        return "CDD"
    return ""


def infer_remote_policy(raw_text: str) -> str:
    text = _normalized_text(raw_text)
    if "remote within the eu" in text:
        return "Remote within EU"
    if "hybrid" in text or "hybride" in text or "teletravail" in text:
        return "Hybrid"
    if "remote" in text:
        return "Remote"
    return ""


def infer_seniority(raw_text: str, extraction: dict[str, Any]) -> str:
    text = _normalized_text(" ".join([str(extraction.get("job_title", "")), raw_text]))
    if "junior" in text:
        return "Junior"
    if "associate" in text:
        return "Associate"
    if "graduate" in text:
        return "Junior"
    if "strategy analyst" in text:
        return "Analyst"
    return ""


def infer_job_domain(raw_text: str, extraction: dict[str, Any]) -> str:
    text = _normalized_text(" ".join([str(extraction.get("job_title", "")), raw_text]))
    if "ai product" in text:
        return "AI Product"
    if "ai consultant" in text:
        return "AI Consulting"
    if "data analyst" in text:
        return "Data Analysis"
    if "business analyst" in text:
        return "Business Analysis"
    if "marketing analyst" in text or "crm" in text:
        return "Marketing Analytics"
    if "strategy analyst" in text:
        return "Strategy"
    if "junior consultant" in text:
        return "Consulting"
    return ""


def infer_company_industry(raw_text: str, extraction: dict[str, Any]) -> str:
    text = _normalized_text(" ".join([str(extraction.get("company_name", "")), raw_text]))
    if "b2b saas" in text or "workflow software" in text:
        return "B2B SaaS workflow software"
    if "retail" in text:
        return "Retail"
    if "mobility services" in text:
        return "Mobility services"
    if "beauty" in text:
        return "Beauty"
    if "strategy engagement" in text or "helio strategy" in text:
        return "Strategy consulting"
    if "kairo services" in text:
        return "Professional services"
    if "ai advisory" in text or "ai consultant" in text:
        return "AI consulting"
    return ""


def infer_job_length(raw_text: str) -> str:
    text = _normalized_text(raw_text)
    if "full-time" in text or "full time" in text:
        return "Full-time"
    if "graduate role" in text:
        return "Graduate role"
    return ""


def has_salary_signal(raw_text: str) -> bool:
    return SALARY_PATTERN.search(raw_text) is not None


def has_company_size_signal(raw_text: str) -> bool:
    return COMPANY_SIZE_PATTERN.search(raw_text) is not None


def validate_extraction_rules(raw_text: str, extraction: dict[str, Any]) -> list[RuleValidationIssue]:
    issues: list[RuleValidationIssue] = []
    if not _emptyish(extraction.get("salary")) and not has_salary_signal(raw_text):
        issues.append(
            RuleValidationIssue(
                field_name="salary",
                severity="warning",
                issue_code="salary_without_source_signal",
                message="Salary is present in extraction, but no salary signal was found in the job post.",
                suggested_value="",
            )
        )
    if not _emptyish(extraction.get("company_size")) and not has_company_size_signal(raw_text):
        issues.append(
            RuleValidationIssue(
                field_name="company_size",
                severity="warning",
                issue_code="company_size_without_source_signal",
                message="Company size is present in extraction, but no company-size signal was found in the job post.",
                suggested_value="",
            )
        )

    inferred_language = infer_language(raw_text)
    detected_language = _normalized_text(extraction.get("detected_language"))
    if inferred_language != "Unknown" and detected_language and detected_language != inferred_language.lower():
        issues.append(
            RuleValidationIssue(
                field_name="detected_language",
                severity="warning",
                issue_code="language_mismatch",
                message=f"Detected language differs from rule-based language signal: {inferred_language}.",
                suggested_value=inferred_language,
            )
        )
    if inferred_language != "Unknown" and not detected_language:
        issues.append(
            RuleValidationIssue(
                field_name="detected_language",
                severity="info",
                issue_code="language_missing",
                message="Detected language is missing despite a strong language signal.",
                suggested_value=inferred_language,
            )
        )

    inferred_letter_required = infer_motivation_letter_required(raw_text)
    if inferred_letter_required is not None and extraction.get("motivation_letter_required") is None:
        issues.append(
            RuleValidationIssue(
                field_name="motivation_letter_required",
                severity="info",
                issue_code="motivation_letter_signal_missing",
                message="Motivation-letter requirement can be inferred from explicit wording.",
                suggested_value=inferred_letter_required,
            )
        )

    inferred_values = {
        "application_channel": infer_application_channel(raw_text, extraction),
        "contract_type": infer_contract_type(raw_text),
        "remote_policy": infer_remote_policy(raw_text),
        "seniority_level": infer_seniority(raw_text, extraction),
        "job_domain": infer_job_domain(raw_text, extraction),
        "company_industry": infer_company_industry(raw_text, extraction),
        "job_length": infer_job_length(raw_text),
    }
    for field_name, suggested_value in inferred_values.items():
        if suggested_value and _blankish(extraction.get(field_name)):
            issues.append(
                RuleValidationIssue(
                    field_name=field_name,
                    severity="info",
                    issue_code=f"{field_name}_rule_inference",
                    message=f"{field_name} can be inferred from explicit job-post wording.",
                    suggested_value=suggested_value,
                )
            )

    for field_name in ("company_name", "job_title"):
        if _emptyish(extraction.get(field_name)):
            issues.append(
                RuleValidationIssue(
                    field_name=field_name,
                    severity="warning",
                    issue_code="required_field_missing",
                    message=f"{field_name} is missing from the extraction.",
                )
            )
    if not _field_list(extraction.get("required_skills")):
        issues.append(
            RuleValidationIssue(
                field_name="required_skills",
                severity="warning",
                issue_code="required_skills_missing",
                message="No required skills were extracted.",
            )
        )
    return issues


def apply_rule_based_corrections(
    raw_text: str, extraction: dict[str, Any]
) -> tuple[dict[str, Any], list[RuleValidationIssue]]:
    corrected = dict(extraction)
    issues = validate_extraction_rules(raw_text, extraction)
    for issue in issues:
        if issue.issue_code in {
            "salary_without_source_signal",
            "company_size_without_source_signal",
            "language_missing",
            "motivation_letter_signal_missing",
        } or issue.issue_code.endswith("_rule_inference"):
            corrected[issue.field_name] = issue.suggested_value
    return corrected, issues


def _number_tokens(value: str) -> list[str]:
    return re.findall(r"\d+(?:[,.]\d+)?\s?k?", value.lower())


def _scalar_values_match(field_name: str, expected_norm: str, actual_norm: str) -> bool:
    if expected_norm == actual_norm:
        return True
    if not expected_norm or not actual_norm:
        return False
    if field_name in {"contract_type", "remote_policy", "job_length"}:
        return expected_norm in actual_norm or actual_norm in expected_norm
    if field_name in {"company_industry", "job_domain", "seniority_level", "application_channel"}:
        cleaned_expected = expected_norm.replace("from outside source:", "").strip()
        return cleaned_expected in actual_norm or actual_norm in cleaned_expected
    if field_name in {"salary", "company_size"}:
        expected_numbers = _number_tokens(expected_norm)
        actual_numbers = _number_tokens(actual_norm)
        return bool(expected_numbers) and expected_numbers == actual_numbers
    if field_name == "location":
        expected_parts = {part.strip() for part in re.split(r",|\bor\b", expected_norm) if part.strip()}
        return bool(expected_parts) and all(part in actual_norm for part in expected_parts)
    return False


def _scalar_result(field_name: str, expected: Any, actual: Any) -> dict[str, Any]:
    expected_norm = _normalized_text(expected)
    actual_norm = _normalized_text(actual)
    expected_missing = expected_norm in EMPTY_MARKERS
    actual_missing = actual_norm in EMPTY_MARKERS
    exact = (expected_missing and actual_missing) or _scalar_values_match(field_name, expected_norm, actual_norm)
    return {
        "field_name": field_name,
        "kind": "scalar",
        "expected": expected,
        "actual": actual,
        "exact": exact,
        "score": 1.0 if exact else 0.0,
        "expected_missing": expected_missing,
        "actual_missing": actual_missing,
        "missing_correct": expected_missing and actual_missing,
        "hallucinated": expected_missing and not actual_missing,
    }


def _list_result(field_name: str, expected: Any, actual: Any) -> dict[str, Any]:
    expected_items = set(_field_list(expected))
    actual_items = set(_field_list(actual))
    matched: set[str] = set()
    unmatched_actual = set(actual_items)
    for expected_item in expected_items:
        exact_match = expected_item if expected_item in unmatched_actual else ""
        if exact_match:
            matched.add(expected_item)
            unmatched_actual.remove(exact_match)
            continue
        for actual_item in list(unmatched_actual):
            expected_tokens = set(expected_item.split())
            actual_tokens = set(actual_item.split())
            overlap = len(expected_tokens & actual_tokens)
            denominator = max(len(expected_tokens | actual_tokens), 1)
            if expected_item in actual_item or actual_item in expected_item or overlap / denominator >= 0.6:
                matched.add(expected_item)
                unmatched_actual.remove(actual_item)
                break
    precision = (
        1.0 if not actual_items and not expected_items else len(matched) / len(actual_items) if actual_items else 0.0
    )
    recall = (
        1.0
        if not expected_items and not actual_items
        else len(matched) / len(expected_items)
        if expected_items
        else 0.0
    )
    f1 = 0.0 if precision + recall == 0 else (2 * precision * recall) / (precision + recall)
    return {
        "field_name": field_name,
        "kind": "list",
        "expected": sorted(expected_items),
        "actual": sorted(actual_items),
        "matched": sorted(matched),
        "missing_items": sorted(expected_items - matched),
        "extra_items": sorted(unmatched_actual),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "score": round(f1, 4),
        "exact": expected_items == actual_items,
        "hallucinated": not expected_items and bool(actual_items),
    }


def calculate_field_metrics(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    field_names: list[str] | None = None,
) -> dict[str, Any]:
    field_results: dict[str, dict[str, Any]] = {}
    scores: list[float] = []
    scalar_scores: list[float] = []
    list_scores: list[float] = []
    missing_results: list[bool] = []
    hallucinations = 0

    evaluated_fields = field_names or list(EXTRACTION_SCHEMA_KEYS)
    for field_name in evaluated_fields:
        if field_name not in EXTRACTION_SCHEMA_KEYS:
            continue
        if field_name in EXTRACTION_LIST_FIELDS:
            result = _list_result(field_name, expected.get(field_name, []), actual.get(field_name, []))
            list_scores.append(float(result["score"]))
        else:
            result = _scalar_result(field_name, expected.get(field_name, ""), actual.get(field_name, ""))
            scalar_scores.append(float(result["score"]))
            if result["expected_missing"]:
                missing_results.append(bool(result["actual_missing"]))
        hallucinations += 1 if result.get("hallucinated") else 0
        scores.append(float(result["score"]))
        field_results[field_name] = result

    aggregate = {
        "field_accuracy": round(mean(scores), 4) if scores else 0.0,
        "scalar_exact_accuracy": round(mean(scalar_scores), 4) if scalar_scores else 0.0,
        "list_f1": round(mean(list_scores), 4) if list_scores else 0.0,
        "missing_field_correctness": round(mean([1.0 if item else 0.0 for item in missing_results]), 4)
        if missing_results
        else 1.0,
        "hallucinated_field_count": hallucinations,
        "evaluated_field_count": len(field_results),
    }
    return {"fields": field_results, "aggregate": aggregate}


def evaluate_extraction_output(
    raw_text: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    latency_seconds: float = 0.0,
    json_valid: bool = True,
    field_names: list[str] | None = None,
) -> dict[str, Any]:
    corrected_actual, validation_issues = apply_rule_based_corrections(raw_text, actual)
    metrics = calculate_field_metrics(expected, corrected_actual, field_names=field_names)
    aggregate = dict(metrics["aggregate"])
    aggregate.update(
        {
            "json_valid": json_valid,
            "latency_seconds": round(latency_seconds, 4),
            "validation_issue_count": len(validation_issues),
            "blocking_issue_count": sum(1 for issue in validation_issues if issue.severity == "error"),
        }
    )
    return {
        "actual": actual,
        "corrected_actual": corrected_actual,
        "validation_issues": [issue.to_dict() for issue in validation_issues],
        "field_results": metrics["fields"],
        "aggregate": aggregate,
    }
