from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.extraction_evaluation_service import DEFAULT_DATASET_PATH, run_evaluation  # noqa: E402
from src.utils import load_app_config, resolve_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage 6 extraction evaluation.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Dataset manifest path.")
    parser.add_argument("--runner", choices=("fixture", "live"), default="fixture", help="Evaluation runner.")
    parser.add_argument("--model", default="", help="Override Ollama model name for live runs.")
    parser.add_argument("--prompt-version", default="", help="Override extraction prompt version.")
    parser.add_argument("--output-dir", default=".tmp/extraction_evaluations", help="Directory for run artifacts.")
    parser.add_argument("--db-path", default="", help="Optional database path for recording run metadata.")
    parser.add_argument("--fail-under", type=float, default=0.8, help="Minimum aggregate field accuracy.")
    parser.add_argument("--no-db-record", action="store_true", help="Do not write run metadata to SQLite.")
    parser.add_argument("--json", action="store_true", help="Print full evaluation output as JSON.")
    args = parser.parse_args()

    configs = load_app_config()
    settings = configs["settings"]
    db_path = args.db_path or settings.get("database", {}).get("path", "database/applications.db")
    result = run_evaluation(
        settings,
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        runner=args.runner,
        model_name=args.model or None,
        prompt_version=args.prompt_version or None,
        db_path=resolve_path(db_path),
        record_to_db=not args.no_db_record,
        fail_under=args.fail_under,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True, default=str))
    else:
        metrics = result["aggregate_metrics"]
        print("Stage 6 extraction evaluation")
        print("-----------------------------")
        print(f"status: {result['status']}")
        print(f"dataset: {result['dataset_version']}")
        print(f"runner: {result['runner']}")
        print(f"prompt: {result['prompt_version']}")
        print(f"model: {result['model_name']}")
        print(f"field_accuracy: {metrics.get('field_accuracy')}")
        print(f"json_reliability: {metrics.get('json_reliability')}")
        print(f"total_validation_issues: {metrics.get('total_validation_issues')}")
        print(f"output: {result['output_path']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
