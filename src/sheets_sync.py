from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import GOOGLE_SHEETS_COLUMNS
from .database import update_application
from .excel_exporter import format_application_for_excel
from .utils import resolve_path


def init_sheets_client(credentials_path: str | Path):
    resolved = resolve_path(credentials_path)
    if not resolved.exists():
        raise FileNotFoundError(
            "Google Sheets credentials are missing. Add a service account JSON file "
            "and keep it out of Git."
        )

    import gspread

    return gspread.service_account(filename=str(resolved))


def normalize_spreadsheet_id(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    match = re.search(r"/spreadsheets/d/([^/?#]+)", raw_value)
    if match:
        return match.group(1)
    return re.split(r"[/#?]", raw_value, maxsplit=1)[0]


def ensure_worksheet(spreadsheet_id: str, worksheet_name: str, client=None):
    if client is None:
        raise ValueError("A Google Sheets client is required.")
    spreadsheet = client.open_by_key(normalize_spreadsheet_id(spreadsheet_id))
    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=50)
    existing_headers = worksheet.row_values(1)
    if existing_headers != list(GOOGLE_SHEETS_COLUMNS):
        worksheet.update("A1", [list(GOOGLE_SHEETS_COLUMNS)])
    return worksheet


def sync_applications_to_sheet(
    applications: list[dict[str, Any]],
    settings: dict[str, Any],
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    sheet_settings = settings.get("google_sheets", {})
    if not sheet_settings.get("enabled", False):
        return {
            "synced": 0,
            "updated": 0,
            "created": 0,
            "warnings": ["Google Sheets sync is disabled in config/settings.yaml."],
            "errors": [],
        }

    warnings: list[str] = []
    errors: list[str] = []
    created = 0
    updated = 0

    spreadsheet_id = normalize_spreadsheet_id(sheet_settings.get("spreadsheet_id", ""))
    if not spreadsheet_id:
        return {
            "synced": 0,
            "updated": 0,
            "created": 0,
            "warnings": warnings,
            "errors": ["Google Sheets spreadsheet_id is missing."],
        }

    try:
        client = init_sheets_client(sheet_settings["credentials_path"])
        worksheet = ensure_worksheet(
            spreadsheet_id,
            sheet_settings.get("worksheet_name", "Applications"),
            client=client,
        )
        values = worksheet.get_all_values()
        if not values:
            worksheet.update("A1", [list(GOOGLE_SHEETS_COLUMNS)])
            values = [list(GOOGLE_SHEETS_COLUMNS)]

        existing_by_application_id: dict[str, int] = {}
        for index, row in enumerate(values[1:], start=2):
            if row and str(row[0]).strip():
                existing_by_application_id[str(row[0]).strip()] = index

        next_row_number = len(values) + 1
        for application in applications:
            application_id = str(application.get("application_id", "")).strip()
            if not application_id:
                warnings.append("Skipped an application without application_id.")
                continue

            row_values = list(format_application_for_excel(application).values())
            stored_row_id = str(application.get("google_sheet_row_id", "") or "").strip()
            target_row: int | None = None
            if stored_row_id.isdigit():
                candidate_row = int(stored_row_id)
                if 2 <= candidate_row <= len(values):
                    row = values[candidate_row - 1]
                    if row and str(row[0]).strip() == application_id:
                        target_row = candidate_row

            if target_row is None:
                target_row = existing_by_application_id.get(application_id)

            if target_row is None:
                worksheet.append_row(row_values, value_input_option="USER_ENTERED")
                target_row = next_row_number
                next_row_number += 1
                values.append(row_values)
                existing_by_application_id[application_id] = target_row
                created += 1
            else:
                worksheet.update(f"A{target_row}", [row_values])
                if target_row <= len(values):
                    values[target_row - 1] = row_values
                updated += 1

            if db_path is not None and stored_row_id != str(target_row):
                update_application(
                    application_id,
                    {"google_sheet_row_id": str(target_row)},
                    db_path=db_path,
                )
                application["google_sheet_row_id"] = str(target_row)
    except Exception as exc:
        errors.append(str(exc))

    return {
        "synced": created + updated,
        "updated": updated,
        "created": created,
        "warnings": warnings,
        "errors": errors,
    }


def push_application(application: dict[str, Any]) -> str:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")


def update_application_row(application: dict[str, Any], row_id: str) -> None:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")
