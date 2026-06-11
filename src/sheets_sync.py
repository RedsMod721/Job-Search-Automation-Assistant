from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import GOOGLE_SHEETS_COLUMNS
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


def ensure_worksheet(spreadsheet_id: str, worksheet_name: str, client=None):
    if client is None:
        raise ValueError("A Google Sheets client is required.")
    spreadsheet = client.open_by_key(spreadsheet_id)
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
) -> dict[str, Any]:
    sheet_settings = settings.get("google_sheets", {})
    if not sheet_settings.get("enabled", False):
        return {
            "synced": 0,
            "updated": 0,
            "created": 0,
            "warnings": ["Google Sheets sync is disabled in config/settings.yaml."],
        }

    client = init_sheets_client(sheet_settings["credentials_path"])
    worksheet = ensure_worksheet(
        sheet_settings["spreadsheet_id"],
        sheet_settings.get("worksheet_name", "Applications"),
        client=client,
    )
    rows = [list(format_application_for_excel(application).values()) for application in applications]
    if rows:
        worksheet.update("A2", rows)
    return {"synced": len(rows), "updated": len(rows), "created": 0, "warnings": []}


def push_application(application: dict[str, Any]) -> str:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")


def update_application_row(application: dict[str, Any], row_id: str) -> None:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")

