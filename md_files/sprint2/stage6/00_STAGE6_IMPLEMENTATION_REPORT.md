# Stage 6 Implementation Report

Date: 2026-06-22

## Objective

Stage 6 implements extraction evaluation and prompt/model improvement so extraction quality is measured before Stage 7 job-fit scoring work.

## Implemented

1. Added a versioned extraction evaluation dataset:
   - `samples/extraction_eval/v1/manifest.yaml`
   - Seven labeled sanitized fixtures covering AI Consultant, AI Product, Data Analyst, Business Analyst, Junior Consultant, Strategy Analyst, and Marketing Analyst.
   - English and French coverage.
   - LinkedIn copied text, Greenhouse, Lever, Workday, Ashby, and company career-page style sources.

2. Expanded prompt versioning:
   - `src/prompts/registry.py` now stores prompt task, version, language, template, schema version, creation date, status, owner, description, and notes.
   - `job_extraction` active prompt is now `stage6-v2`.
   - Prior `stage3-v1` extraction prompt is retained as `RETIRED` for comparison.
   - Prior `stage6-v1` extraction prompt is retained as `RETIRED` after the real corpus showed weak live performance.

3. Added extraction quality services:
   - `src/services/extraction_quality.py`
   - `src/services/extraction_evaluation_service.py`
   - `src/services/extraction_correction_service.py`
   - Rule validation and deterministic correction for unsourced salary/company size, language mismatch or missing language, and explicit motivation-letter signals.
   - Field-level scalar and list metrics.

4. Added evaluation command:
   - `uv run python scripts/evaluate_extraction.py`
   - `uv run python scripts/evaluate_extraction.py --json`
   - Supports `fixture` runner for CI and `live` runner for local Ollama benchmarking.

5. Added schema version 3:
   - `extraction_corrections`
   - `extraction_evaluation_runs`
   - `extraction_evaluation_results`
   - Current local database migrated to schema version `3`.
   - Pre-migration backup created: `database/backups/applications_pre_migration_2026-06-22T11-45-42.db`.

6. Added user correction logging:
   - The extraction review form now records changed fields after an application is created.
   - Logged data stores field deltas, raw text hash, prompt version, model name, and model parameters.
   - Full raw job post text is not stored in the correction table.

7. Added diagnostics and UI visibility:
   - Diagnostics now include `extraction_quality`.
   - Settings page shows latest extraction evaluation and correction summary.
   - Settings page can run the fixture extraction evaluation.

8. Added CI gate:
   - `.github/workflows/ci.yml` now runs:
     - `uv run python scripts/evaluate_extraction.py --runner fixture --no-db-record`

9. Resolved dependency audit issue:
   - `pip-audit` found vulnerable `msgpack 1.2.0`.
   - `uv.lock` was updated to `msgpack 1.2.1`.
   - Final `pip-audit` passed.

10. Imported user-supplied real extraction pairs locally:
   - Source supplied by user: `C:\Users\vazqse01\stage6_real_job_posts`.
   - Committed copy: `samples/extraction_eval/real_2026_06_23`.
   - Local ignored copy also exists at `.tmp/stage6_real_job_posts`.
   - Corpus contains 20 folders, each with `raw_post.txt`, `expected_extraction.json`, and `validation_audit.json`.
   - The evaluator now supports this JSON-manifest corpus format directly.

## Local Baseline Result

Latest sanitized fixture gate:

```text
status: PASS
dataset: stage6-v1
runner: fixture
prompt: stage6-v2
model: qwen3:4b
field_accuracy: 1.0
json_reliability: 1.0
total_validation_issues: 0
```

Latest real-corpus fixture gate:

```text
status: PASS
dataset: stage6-real-2026-06-23
runner: fixture
prompt: stage6-v2
model: qwen3:4b
field_accuracy: 1.0
json_reliability: 1.0
total_validation_issues: 7
dataset path: samples/extraction_eval/real_2026_06_23/MANIFEST.json
output: .tmp/extraction_evaluations/extraction_eval_stage6-real-2026-06-23_fixture_2026-06-23T15_51_18.json
```

Latest real-corpus Windows live Ollama run:

```text
status: FAIL
dataset: stage6-real-2026-06-23
runner: live
prompt: stage6-v2
model: qwen3:4b
field_accuracy: 0.5555
json_reliability: 1.0
total_validation_issues: 6
dataset path: samples/extraction_eval/real_2026_06_23/MANIFEST.json
output: .tmp/extraction_evaluations/extraction_eval_stage6-real-2026-06-23_live_2026-06-23T16_13_55.json
```

## Acceptance Gate

Stage 6 infrastructure is implemented, but the new real-corpus live benchmark shows extraction quality is not yet good enough to mark the quality-improvement gate complete.

Current interpretation:

- JSON reliability is good.
- The real expected-pair corpus is valid and usable.
- `stage6-v2` improved real-corpus live accuracy from `0.4003` to `0.5555`.
- The default `qwen3:4b` extraction pipeline still misses too many responsibilities, requirements, seniority, domain, and company metadata fields on real posts.

Remaining Stage 6 work:

- Improve extraction prompt/pipeline further or evaluate stronger local models.
- Run the same real corpus benchmark on the M3 Pro.
- Re-run the gate until the live real-corpus score reaches the configured threshold.
