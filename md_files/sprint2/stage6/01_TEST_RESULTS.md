# Stage 6 Test Results

Date: 2026-06-22

## Commands Run

```text
uv run ruff format --check .
```

Result: pass, 63 files already formatted.

```text
uv run ruff check .
```

Result: pass, all checks passed.

```text
uv run mypy app.py src tests
```

Result: pass, no issues found in 47 source files.

```text
uv run pytest
```

Result: pass, 88 tests passed.

```text
uv run python scripts/evaluate_extraction.py --runner fixture --no-db-record
```

Result: pass.

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

```text
uv run python scripts/evaluate_extraction.py --dataset samples/extraction_eval/real_2026_06_23/MANIFEST.json --runner fixture --no-db-record
```

Result: pass.

```text
status: PASS
dataset: stage6-real-2026-06-23
runner: fixture
prompt: stage6-v2
model: qwen3:4b
field_accuracy: 1.0
json_reliability: 1.0
total_validation_issues: 7
```

```text
uv run python scripts/evaluate_extraction.py --dataset samples/extraction_eval/real_2026_06_23/MANIFEST.json --runner live --model qwen3:4b
```

Result: fail, but useful benchmark.

```text
status: FAIL
dataset: stage6-real-2026-06-23
runner: live
prompt: stage6-v2
model: qwen3:4b
field_accuracy: 0.5555
json_reliability: 1.0
total_validation_issues: 6
```

```text
uv run bandit -c pyproject.toml -r app.py src
```

Result: pass, no issues identified.

```text
uv run python scripts/diagnostics.py
```

Result: pass.

```text
database: ok
cv_files: ok
ollama: ok
ollama_model: ok
google_sheets: ready
extraction_eval: attention
network_tls: enabled
```

```text
uv run python -m compileall -q app.py src pages scripts tests
```

Result: pass.

```text
uv run pip-audit --cache-dir .tmp/pip-audit-cache-stage6
```

Initial result: fail, `msgpack 1.2.0` had `GHSA-6v7p-g79w-8964`.

Fix:

```text
uv lock --upgrade-package msgpack
uv sync --group dev
```

Final result: pass, no known vulnerabilities found.

## New Tests

Added `tests/test_stage6_extraction_evaluation.py` covering:

- Dataset coverage.
- JSON-manifest real-corpus loading.
- Committed real-corpus fixture gate.
- Rule-based correction of unsourced salary and company size.
- Fixture evaluation pass and database recording.
- Review correction logging.

Updated existing tests for:

- Active extraction prompt version.
- Import smoke coverage for new Stage 6 services.
- JSON-manifest real-corpus loading.

## Notes

Network escalation was required for `uv lock`, `uv sync`, and `pip-audit` because the sandbox proxy blocked PyPI access.
