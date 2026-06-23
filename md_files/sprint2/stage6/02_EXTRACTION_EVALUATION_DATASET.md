# Extraction Evaluation Dataset

Date: 2026-06-22

## Location

```text
samples/extraction_eval/v1/
```

## Manifest

```text
samples/extraction_eval/v1/manifest.yaml
```

Dataset version: `stage6-v1`

## Fixture Coverage

| Fixture | Role Family | Language | Source Style |
| --- | --- | --- | --- |
| `ai_consultant_linkedin_en` | AI Consultant | English | LinkedIn copied text |
| `ai_product_greenhouse_en` | AI Product | English | Greenhouse |
| `data_analyst_workday_fr` | Data Analyst | French | Workday |
| `business_analyst_lever_fr` | Business Analyst | French | Lever |
| `junior_consultant_workday_en` | Junior Consultant | English | Workday |
| `strategy_analyst_ashby_en` | Strategy Analyst | English | Ashby |
| `marketing_analyst_company_fr` | Marketing Analyst | French | Company career page |

## Expected JSON

Each fixture has a matching expected extraction JSON under:

```text
samples/extraction_eval/v1/expected/
```

Expected JSON uses the current extraction schema:

- Company fields.
- Job title/domain/seniority/contract/location fields.
- Salary and remote policy.
- Responsibilities.
- Required skills.
- Preferred qualifications.
- Language, source, channel, URL, and motivation-letter requirement.

## Artifact Outputs

Evaluation outputs are local and ignored:

```text
.tmp/extraction_evaluations/
```

Latest Stage 6 run:

```text
extraction_eval_stage6-v1_fixture_2026-06-23T16_15_58.json
extraction_eval_stage6-v1_fixture_2026-06-22T12_02_16.json
extraction_eval_stage6-v1_live_2026-06-22T12_06_33.json
extraction_eval_stage6-real-2026-06-23_fixture_2026-06-23T15_51_18.json
extraction_eval_stage6-real-2026-06-23_live_2026-06-23T16_13_55.json
```

## Real Local Corpus

User-supplied extraction pairs were imported into the repository:

```text
samples/extraction_eval/real_2026_06_23/
```

An ignored working copy also exists at `.tmp/stage6_real_job_posts/`.

The committed corpus contains:

- `MANIFEST.json`
- `QA_SUMMARY.txt`
- 20 numbered job-post folders
- `raw_post.txt`
- `expected_extraction.json`
- `validation_audit.json`

The evaluator supports this JSON-manifest format directly:

```text
uv run python scripts/evaluate_extraction.py --dataset samples/extraction_eval/real_2026_06_23/MANIFEST.json --runner fixture --no-db-record
uv run python scripts/evaluate_extraction.py --dataset samples/extraction_eval/real_2026_06_23/MANIFEST.json --runner live --model qwen3:4b
```

Current real-corpus results:

| Runner | Prompt | Model | Status | Field Accuracy | JSON Reliability |
| --- | --- | --- | --- | --- | --- |
| fixture | `stage6-v2` | `qwen3:4b` | PASS | 1.0 | 1.0 |
| live | `stage6-v1` | `qwen3:4b` | FAIL | 0.4003 | 1.0 |
| live | `stage6-v2` | `qwen3:4b` | FAIL | 0.5555 | 1.0 |

## Privacy Note

The original Stage 6 `v1` fixtures are sanitized representative posts. The `real_2026_06_23` corpus contains the real examples supplied for cross-machine Stage 6 iteration and should be treated as project data.
