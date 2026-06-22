from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.diagnostics import collect_diagnostics, diagnostics_summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Job Search Assistant diagnostics.")
    parser.add_argument("--json", action="store_true", help="Print full diagnostics as JSON.")
    args = parser.parse_args()

    diagnostics = collect_diagnostics()
    if args.json:
        print(json.dumps(diagnostics, indent=2, ensure_ascii=True))
        return 0

    summary = diagnostics_summary(diagnostics)
    print("Job Search Assistant diagnostics")
    print("--------------------------------")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
