from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from src import database, extractor
from src.constants import EXTRACTION_SCHEMA_KEYS, PROJECT_ROOT
from src.prompts.registry import get_prompt
from src.services.extraction_quality import evaluate_extraction_output
from src.utils import generate_uuid, now_iso, resolve_path, safe_filename

DEFAULT_DATASET_PATH = PROJECT_ROOT / "samples" / "extraction_eval" / "v1" / "manifest.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp" / "extraction_evaluations"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            payload = json.load(handle)
        else:
            payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Dataset manifest must contain a mapping: {path}")
    return payload


def _dataset_version_from_real_manifest(manifest: dict[str, Any]) -> str:
    generated_at = str(manifest.get("generated_at_utc", "")).split("T")[0]
    suffix = generated_at or now_iso().split("T")[0]
    return f"stage6-real-{suffix}"


def _expected_fields(expected: dict[str, Any], fixture: dict[str, Any]) -> list[str]:
    configured = fixture.get("expected_fields")
    if isinstance(configured, list):
        return [str(field) for field in configured if str(field) in EXTRACTION_SCHEMA_KEYS]
    return [field for field in EXTRACTION_SCHEMA_KEYS if field in expected]


def _source_to_ats_source(source_platform: str) -> str:
    if source_platform == "not included":
        return "Unknown"
    return source_platform


def _load_yaml_fixture(dataset_dir: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    text_path = (dataset_dir / str(fixture["text_path"])).resolve()
    expected_path = (dataset_dir / str(fixture["expected_path"])).resolve()
    baseline_path = fixture.get("baseline_actual_path")
    loaded = dict(fixture)
    loaded["raw_text"] = _read_text(text_path)
    loaded["expected"] = _load_json(expected_path)
    loaded["expected_fields"] = _expected_fields(loaded["expected"], loaded)
    loaded["text_path"] = str(text_path)
    loaded["expected_path"] = str(expected_path)
    if baseline_path:
        resolved_baseline = (dataset_dir / str(baseline_path)).resolve()
        loaded["baseline_actual"] = _load_json(resolved_baseline)
        loaded["baseline_actual_path"] = str(resolved_baseline)
    return loaded


def _load_real_manifest_fixture(dataset_dir: Path, post: dict[str, Any]) -> dict[str, Any]:
    folder = str(post["folder"])
    post_dir = (dataset_dir / folder).resolve()
    text_path = post_dir / "raw_post.txt"
    expected_path = post_dir / "expected_extraction.json"
    audit_path = post_dir / "validation_audit.json"
    expected = _load_json(expected_path)
    source_platform = str(post.get("source_platform") or expected.get("source_platform") or "")
    loaded = {
        "fixture_id": folder,
        "post_number": post.get("post_number"),
        "role_family": str(expected.get("job_domain") or ""),
        "language": str(expected.get("detected_language") or ""),
        "source_platform": source_platform,
        "ats_source": _source_to_ats_source(source_platform),
        "company_name": post.get("company_name", expected.get("company_name", "")),
        "job_title": post.get("job_title", expected.get("job_title", "")),
        "raw_text": _read_text(text_path),
        "expected": expected,
        "expected_fields": _expected_fields(expected, {}),
        "text_path": str(text_path),
        "expected_path": str(expected_path),
        "validation_audit_path": str(audit_path) if audit_path.exists() else "",
        "sha256": post.get("sha256", {}),
    }
    return loaded


def load_evaluation_dataset(dataset_path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    manifest_path = resolve_path(dataset_path)
    manifest = _load_manifest(manifest_path)

    dataset_dir = manifest_path.parent
    fixtures = []
    if "posts" in manifest:
        for post in manifest.get("posts", []):
            if isinstance(post, dict):
                fixtures.append(_load_real_manifest_fixture(dataset_dir, post))
        manifest["dataset_id"] = manifest.get("dataset_id") or "stage6-real-job-posts"
        manifest["dataset_version"] = manifest.get("dataset_version") or _dataset_version_from_real_manifest(manifest)
        manifest["description"] = manifest.get("corpus_name", "Stage 6 real job posts")
    else:
        for fixture in manifest.get("fixtures", []):
            if isinstance(fixture, dict):
                fixtures.append(_load_yaml_fixture(dataset_dir, fixture))
    manifest["fixtures"] = fixtures
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def _model_parameters(settings: dict[str, Any], model_name: str, prompt_version: str) -> dict[str, Any]:
    llm = settings.get("llm", {})
    return {
        "provider": llm.get("provider", "ollama"),
        "model": model_name,
        "fallback_models": list(llm.get("fallback_models", [])),
        "timeout_seconds": int(llm.get("timeout_seconds", 120)),
        "temperature": float(llm.get("temperature", 0.2)),
        "prompt_version": prompt_version,
        "rule_correction": True,
    }


def _aggregate_fixture_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    aggregates = [result.get("aggregate", {}) for result in results]
    numeric_keys = sorted(
        {
            key
            for aggregate in aggregates
            for key, value in aggregate.items()
            if isinstance(value, int | float) and not isinstance(value, bool)
        }
    )
    summary = {
        key: round(mean(float(aggregate.get(key, 0.0) or 0.0) for aggregate in aggregates), 4) for key in numeric_keys
    }
    summary["fixture_count"] = len(results)
    summary["json_reliability"] = (
        round(
            mean(1.0 if aggregate.get("json_valid") else 0.0 for aggregate in aggregates),
            4,
        )
        if aggregates
        else 0.0
    )
    summary["total_validation_issues"] = sum(
        int(aggregate.get("validation_issue_count", 0) or 0) for aggregate in aggregates
    )
    summary["total_hallucinated_fields"] = sum(
        int(aggregate.get("hallucinated_field_count", 0) or 0) for aggregate in aggregates
    )
    return summary


def _fixture_actual(fixture: dict[str, Any]) -> dict[str, Any]:
    return dict(fixture.get("baseline_actual") or fixture["expected"])


def _live_actual(
    fixture: dict[str, Any],
    settings: dict[str, Any],
    *,
    model_name: str,
    prompt_version: str,
) -> dict[str, Any]:
    llm = settings.get("llm", {})
    return extractor.extract_job_post(
        fixture["raw_text"],
        source_platform=fixture.get("source_platform", ""),
        model=model_name,
        fallback_models=list(llm.get("fallback_models", [])),
        timeout_seconds=int(llm.get("timeout_seconds", 120)),
        temperature=float(llm.get("temperature", 0.2)),
        prompt_version=prompt_version,
        enable_rule_correction=True,
    )


def run_evaluation(
    settings: dict[str, Any] | None = None,
    *,
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    runner: str = "fixture",
    model_name: str | None = None,
    prompt_version: str | None = None,
    db_path: str | Path | None = None,
    record_to_db: bool = True,
    fail_under: float = 0.8,
) -> dict[str, Any]:
    settings = settings or {}
    llm = settings.get("llm", {})
    configured_prompt_version = prompt_version or str(llm.get("extraction_prompt_version") or "") or None
    prompt = get_prompt("job_extraction", configured_prompt_version)
    selected_model = model_name or str(llm.get("model") or "fixture-static")
    dataset = load_evaluation_dataset(dataset_path)
    started_at = now_iso()
    evaluation_run_id = generate_uuid()
    fixture_results: list[dict[str, Any]] = []

    for fixture in dataset["fixtures"]:
        start = time.perf_counter()
        errors: list[str] = []
        json_valid = True
        if runner == "fixture":
            actual = _fixture_actual(fixture)
        elif runner == "live":
            try:
                actual = _live_actual(fixture, settings, model_name=selected_model, prompt_version=prompt.version)
            except Exception as exc:
                actual = extractor.default_extraction()
                errors.append(str(exc))
                json_valid = False
        else:
            raise ValueError(f"Unsupported extraction evaluation runner: {runner}")

        latency_seconds = time.perf_counter() - start
        evaluated = evaluate_extraction_output(
            fixture["raw_text"],
            fixture["expected"],
            actual,
            latency_seconds=latency_seconds,
            json_valid=json_valid,
            field_names=fixture.get("expected_fields"),
        )
        fixture_results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "role_family": fixture.get("role_family", ""),
                "language": fixture.get("language", ""),
                "source_platform": fixture.get("source_platform", ""),
                "ats_source": fixture.get("ats_source", ""),
                "errors": errors,
                **evaluated,
            }
        )

    aggregate_metrics = _aggregate_fixture_metrics(fixture_results)
    status = (
        "PASS"
        if aggregate_metrics.get("field_accuracy", 0.0) >= fail_under
        and not any(result.get("errors") for result in fixture_results)
        else "FAIL"
    )
    completed_at = now_iso()
    output_path = resolve_path(output_dir) / (
        safe_filename(f"extraction_eval_{dataset.get('dataset_version', 'dataset')}_{runner}_{completed_at}") + ".json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run_record = {
        "evaluation_run_id": evaluation_run_id,
        "dataset_id": dataset.get("dataset_id", ""),
        "dataset_version": dataset.get("dataset_version", ""),
        "prompt_id": prompt.prompt_id,
        "prompt_version": prompt.version,
        "model_name": selected_model,
        "model_parameters": _model_parameters(settings, selected_model, prompt.version),
        "runner": runner,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "aggregate_metrics": aggregate_metrics,
        "fail_under": fail_under,
        "manifest_path": dataset.get("manifest_path", ""),
        "output_path": str(output_path),
        "results": fixture_results,
    }
    output_path.write_text(json.dumps(run_record, indent=2, ensure_ascii=True, default=str), encoding="utf-8")

    if record_to_db and db_path is not None:
        database.init_db(db_path)
        database.record_extraction_evaluation_run(run_record, fixture_results, db_path=db_path)
    return run_record


def latest_evaluation_summary(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    path = resolve_path(output_dir)
    if not path.exists():
        return {"exists": False, "latest_output": "", "aggregate_metrics": {}}
    candidates = sorted(path.glob("extraction_eval_*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        return {"exists": False, "latest_output": "", "aggregate_metrics": {}}
    latest = candidates[0]
    try:
        payload = _load_json(latest)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"exists": True, "latest_output": str(latest), "aggregate_metrics": {}, "read_error": True}
    return {
        "exists": True,
        "latest_output": str(latest),
        "dataset_version": payload.get("dataset_version", ""),
        "prompt_version": payload.get("prompt_version", ""),
        "model_name": payload.get("model_name", ""),
        "runner": payload.get("runner", ""),
        "status": payload.get("status", ""),
        "aggregate_metrics": payload.get("aggregate_metrics", {}),
    }
