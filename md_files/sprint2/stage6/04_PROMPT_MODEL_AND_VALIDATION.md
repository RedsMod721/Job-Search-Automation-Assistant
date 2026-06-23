# Prompt, Model, and Validation Workflow

Date: 2026-06-22

## Prompt Versions

Current active extraction prompt:

```text
prompt_id: job_extraction
version: stage6-v2
status: ACTIVE
schema_version: 1
owner: src.extractor
```

Previous extraction prompt:

```text
prompt_id: job_extraction
version: stage3-v1
status: RETIRED
```

Previous Stage 6 extraction prompt:

```text
prompt_id: job_extraction
version: stage6-v1
status: RETIRED
```

Configured setting:

```yaml
llm:
  extraction_prompt_version: "stage6-v2"
```

## Model Configuration

Current Windows baseline:

```text
provider: ollama
model: qwen3:4b
fallback_models:
  - llama3.2:latest
  - qwen2.5:7b
temperature: 0.2
timeout_seconds: 120
```

## Validators

Stage 6 added deterministic validators for:

- Salary extracted when no salary signal exists.
- Company size extracted when no size signal exists.
- Missing or mismatched detected language.
- Explicit motivation-letter requirement wording.
- Missing company name, job title, or required skills.

Correction behavior:

- Unsourced salary is cleared.
- Unsourced company size is cleared.
- Strong language signal can fill or correct `detected_language`.
- Explicit cover-letter or motivation-letter wording can fill `motivation_letter_required`.

## Evaluation Command

CI-safe fixture gate:

```text
uv run python scripts/evaluate_extraction.py --runner fixture --no-db-record
```

Local live Ollama benchmark:

```text
uv run python scripts/evaluate_extraction.py --runner live --model qwen3:4b
```

Prompt comparison example:

```text
uv run python scripts/evaluate_extraction.py --runner live --prompt-version stage3-v1 --model qwen3:4b
uv run python scripts/evaluate_extraction.py --runner live --prompt-version stage6-v1 --model qwen3:4b
uv run python scripts/evaluate_extraction.py --runner live --prompt-version stage6-v2 --model qwen3:4b
uv run python scripts/evaluate_extraction.py --dataset samples/extraction_eval/real_2026_06_23/MANIFEST.json --runner live --model qwen3:4b
```

## Benchmark Status

Windows fixture benchmark:

```text
status: PASS
field_accuracy: 1.0
json_reliability: 1.0
total_validation_issues: 0
```

Windows sanitized live Ollama benchmark:

```text
model: qwen3:4b
status: PASS
field_accuracy: 0.8932
json_reliability: 1.0
total_validation_issues: 0
```

Windows real-corpus live Ollama benchmark:

```text
model: qwen3:4b
prompt: stage6-v2
status: FAIL
field_accuracy: 0.5555
json_reliability: 1.0
total_validation_issues: 6
```

M3 Pro live benchmark:

```text
status: pending
```

Recommended Mac benchmark matrix:

- `qwen3:4b`
- `llama3.2:latest`
- Any additional local candidate model the user installs

Metrics to compare:

- Field accuracy.
- JSON reliability.
- Latency.
- Validation issue rate.
- Salary/company-size hallucination rate.
- English and French fixture performance.
