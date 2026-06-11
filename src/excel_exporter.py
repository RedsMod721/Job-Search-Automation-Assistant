from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import GOOGLE_COLUMN_TO_FIELD, GOOGLE_SHEETS_COLUMNS
from .utils import list_to_readable_text, now_iso, resolve_path


def format_application_for_excel(application: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for column in GOOGLE_SHEETS_COLUMNS:
        field = GOOGLE_COLUMN_TO_FIELD[column]
        value = application.get(field, "")
        if field in {
            "key_responsibilities",
            "required_skills",
            "preferred_qualifications",
            "cv_matched_keywords",
        }:
            value = list_to_readable_text(value)
        row[column] = value
    return row


def export_applications_to_excel(
    applications: list[dict[str, Any]],
    output_dir: str | Path = "exports/excel",
) -> str:
    import pandas as pd

    resolved_output_dir = resolve_path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = now_iso().replace(":", "-")
    output_path = resolved_output_dir / f"applications_export_{timestamp}.xlsx"
    rows = [format_application_for_excel(application) for application in applications]
    dataframe = pd.DataFrame(rows, columns=GOOGLE_SHEETS_COLUMNS)
    dataframe.to_excel(output_path, index=False)
    return str(output_path)

