# Job Discovery, Fit Ranking, and LLM Evaluation Specification

## 1. Purpose

This document defines:

- Real company and job discovery.
- Source connector order.
- Normalized job records.
- Search profiles.
- Review queue.
- Hard gates.
- Soft warnings.
- Fit scoring.
- CV selection.
- LLM extraction evaluation.
- Prompt A/B testing.

## 2. Discovery Pipeline

```text
Search profile
    ↓
Company discovery
    ↓
Career-page discovery
    ↓
Job-source connectors
    ↓
Normalized job records
    ↓
Deduplication
    ↓
Extraction and enrichment
    ↓
Hard gates
    ↓
Soft warnings
    ↓
Fit score
    ↓
Review queue
```

## 3. Source Priority

Implement in this order:

1. Official company career pages.
2. Greenhouse public boards.
3. Lever public postings.
4. Ashby public boards.
5. SmartRecruiters public postings.
6. Workday public pages where accessible.
7. Welcome to the Jungle.
8. Indeed or Google Jobs through compliant methods only.
9. LinkedIn through manual browser-extension capture.

Only free/open/public sources may be assumed.

## 4. Connector Interface

Each connector should implement:

```text
source_name
supports_company_search
supports_job_search
search_companies(query)
search_jobs(search_profile)
list_company_jobs(company)
fetch_job(job_reference)
normalize(raw_record)
health_check()
rate_limit_policy()
```

Every returned record must include:

- Source name.
- Source URL.
- Retrieval time.
- External ID if available.
- Raw payload or raw text where permitted.
- Normalized data.

## 5. Company Discovery

Input:

- Sector.
- Location.
- Keywords.
- Role family.
- Optional company size.
- Optional industry.

Output:

- Company name.
- Website.
- Domain.
- Industry.
- Headquarters.
- Careers URL.
- Source.
- Confidence.
- Verification status.

A search must return multiple companies when available.

Treat current single-entity enrichment as a separate capability.

## 6. Career-Page Verification

A career page should be marked verified only when:

- URL resolves successfully.
- Page appears to be official.
- Domain is company-owned or known ATS.
- Page contains job/career indicators.

Store:

```text
career_page_url
verified_at
verification_method
ats_type
source_url
```

## 7. Normalized Job Model

Required fields:

```text
job_id
external_job_id
source_name
source_url
canonical_url
company_id
company_name
title
normalized_title
role_family
description
responsibilities
required_skills
preferred_skills
required_languages
seniority
years_experience_min
years_experience_max
contract_type
employment_type
location_text
country
city
remote_policy
salary_min
salary_max
salary_currency
salary_period
salary_basis
published_at
expires_at
collected_at
content_hash
raw_payload
```

## 8. Search Profiles

A search profile must include:

```yaml
name: ""
enabled: true

role_families: []
keywords: []
excluded_keywords: []

countries: []
cities: []
remote_preferences: []

contract_types: []
seniority_preferences: []

language_rules: {}
authorization_rules: {}
salary_rules: {}

hard_gates: []
soft_warnings: []

sources: []
schedule: {}
```

## 9. Review Queue

Scheduled and manual search results must first enter a review queue.

States:

```text
NEW
INTERESTING
DISMISSED
SAVED_TO_TRACKER
EXPIRED
DUPLICATE
```

The main tracker should contain jobs the user intends to manage or apply to.

Dismissed jobs should not reappear unless:

- Material job content changed.
- User resets dismissal.
- New source provides materially different information.

## 10. Hard Gates

Hard gates reject a job from recommended results but must show reasons.

Hard gates are configurable by search profile.

Potential rules:

- Internship excluded.
- Contract type explicitly excluded.
- Country outside selected scope.
- Mandatory language not spoken.
- Mandatory authorization impossible under configured rule.
- Role family outside selected target.
- Explicitly excluded keyword.
- Expired job.
- Invalid or inaccessible application URL.
- Duplicate of an existing application.

A hard-gated job may remain accessible in rejected/search history.

## 11. Soft Warnings

Soft warnings keep the job visible.

Potential warnings:

- Seniority above target.
- Required years of experience above profile.
- Remote policy mismatch.
- Onsite role.
- Relocation required.
- Salary absent.
- Salary below preference.
- Temporary role when permanent is preferred.
- Missing preferred skill.
- Missing required skill with uncertain interpretation.
- Company size mismatch.
- Role only partially matches.
- Job description quality is low.
- Post may be stale.
- Language may require improvement.

## 12. Fit Score

The score must be explainable.

Recommended default weighting:

```yaml
role_relevance: 30
skills_match: 25
experience_match: 15
location_and_work_mode: 10
contract_fit: 10
language_and_authorization: 10
```

Weights must be configurable.

## 13. Decision Output

```json
{
  "decision": "accepted_with_warnings",
  "fit_score": 74,
  "hard_gate_failures": [],
  "warnings": [
    "The role asks for four years of experience.",
    "The role is fully onsite."
  ],
  "strengths": [
    "Strong AI and automation match.",
    "Relevant Python and API experience."
  ],
  "missing_information": [
    "Salary not provided."
  ],
  "score_breakdown": {
    "role_relevance": 27,
    "skills_match": 20,
    "experience_match": 8,
    "location_and_work_mode": 5,
    "contract_fit": 8,
    "language_and_authorization": 6
  },
  "recommended_cv": "ai"
}
```

## 14. Job Fit and CV Selection Must Remain Separate

Job fit answers:

```text
Should the user consider applying?
```

CV recommendation answers:

```text
Which fixed CV is best for this job?
```

A job may have low fit but still map clearly to one CV.

## 15. Improved CV Recommendation

Use:

- Deterministic keyword baseline.
- Normalized role taxonomy.
- Normalized skill taxonomy.
- Semantic similarity when local resources permit.
- Minimum evidence threshold.
- Manual override.

Possible result:

```json
{
  "recommended_cv": null,
  "confidence": 0.22,
  "reason": "Insufficient evidence to choose reliably.",
  "manual_review_required": true
}
```

Do not default to AI when there is no evidence.

## 16. LLM Evaluation Dataset

Build a versioned dataset of real job posts.

Coverage:

- AI Consultant.
- AI Product.
- Data Analyst.
- Business Analyst.
- Junior Consultant.
- Strategy Analyst.
- Marketing Analyst.
- English.
- French.
- LinkedIn copied text.
- Greenhouse.
- Lever.
- Ashby.
- Workday.
- Short posts.
- Long posts.
- Missing salary.
- Multiple locations.
- Remote/hybrid.
- Mixed required and preferred skills.

Each fixture must include expected JSON.

## 17. Extraction Metrics

Measure:

- Company-name exact/normalized accuracy.
- Job-title accuracy.
- Location accuracy.
- Contract accuracy.
- Salary precision and recall.
- Language accuracy.
- Responsibility coverage.
- Required-skill coverage.
- Preferred-skill separation.
- Hallucination rate.
- Missing-field correctness.
- JSON validity.
- Latency.
- User correction count.
- User correction time.

## 18. Prompt Registry

Every prompt must have:

```text
prompt_id
task
version
language
template
schema_version
created_at
status
notes
```

Statuses:

```text
DRAFT
TESTING
ACTIVE
RETIRED
```

## 19. Evaluation Run Record

Store:

```text
evaluation_run_id
dataset_version
prompt_version
model_name
model_parameters
started_at
completed_at
aggregate_metrics
per_fixture_results
```

## 20. A/B Testing

A/B testing should compare:

- Prompt versions.
- Model versions.
- Temperature.
- One-pass vs two-pass.
- Schema detail.
- Validator behavior.

Do not compare only subjective quality.

## 21. Recommended Extraction Pipeline

```text
Raw text
    ↓
Cleaning
    ↓
Primary structured extraction
    ↓
Pydantic/schema validation
    ↓
Rule validation
    ↓
Optional correction pass
    ↓
Editable user review
    ↓
Correction logging
```

## 22. Model Benchmark on M3 Pro

Compare candidate local models for:

- Accuracy.
- JSON reliability.
- Speed.
- Memory.
- Long-context handling.
- English quality.
- French quality.
- Motivation-letter quality.
- Form-answer quality.

The chosen extraction model may differ from the chosen generation model.

## 23. User Corrections

When a user changes an extracted field, record:

- Original value.
- Corrected value.
- Field.
- Job fixture reference.
- Prompt version.
- Model.
- Timestamp.

Corrections must be usable for future evaluation, not automatically used as model training data without explicit design.

## 24. Search Scheduling

Support:

- Manual Run Now.
- Configurable recurring schedule.
- Enable/disable.
- Last run.
- Next run.
- Source-level failures.
- Result counts.
- New vs duplicate counts.

The local background service must be running for scheduled searches.

## 25. Connector Compliance

For every connector document:

- Public endpoint or page used.
- Robots/rate-limit behavior.
- Authentication requirement.
- Allowed use assumptions.
- Failure mode.
- Data retained.
- Removal process if source becomes non-compliant.

## 26. Acceptance Criteria

- Search returns normalized records.
- All records have provenance.
- Duplicates are managed.
- Review queue works.
- Hard gates and warnings are configurable.
- Scores are explainable.
- CV recommendation is separate.
- Extraction changes are benchmarked.
- Prompt/model regressions are detected.
