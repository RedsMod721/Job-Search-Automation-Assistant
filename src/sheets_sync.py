from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .constants import GOOGLE_SHEETS_COLUMNS
from .database import update_application, update_application_sync_success
from .excel_exporter import format_application_for_excel
from .network import configure_session
from .utils import resolve_path

GOOGLE_SHEETS_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def init_sheets_client(credentials_path: str | Path, network_settings: dict[str, Any] | None = None):
    resolved = resolve_path(credentials_path)
    if not resolved.exists():
        raise FileNotFoundError(
            "Google Sheets credentials are missing. Add a service account JSON file and keep it out of Git."
        )

    import gspread
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_file(str(resolved), scopes=GOOGLE_SHEETS_SCOPES)
    session = AuthorizedSession(credentials)
    configure_session(session, network_settings)

    # AuthorizedSession uses a separate internal session for token-refresh requests
    # (_auth_request.session). Patch it too, otherwise it inherits system proxy settings.
    auth_request = getattr(session, "_auth_request", None)
    if auth_request is not None:
        inner_session = getattr(auth_request, "session", None)
        if inner_session is not None and inner_session is not session:
            configure_session(inner_session, network_settings)

    return gspread.Client(auth=credentials, session=session)


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


def normalize_sheet_value(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def calculate_application_sync_hash(application: dict[str, Any]) -> str:
    excluded_columns = {
        "Google Sheet Row ID",
        "Last Synced At",
        "Last Sync Source",
        "Sync Hash",
    }
    normalized = {
        column: normalize_sheet_value(value)
        for column, value in format_application_for_excel(application).items()
        if column not in excluded_columns
    }
    payload = json.dumps(normalized, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sync_applications_to_sheet(
    applications: list[dict[str, Any]],
    settings: dict[str, Any],
    db_path: str | Path | None = None,
    sync_source: str = "manual",
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
    application_results: dict[str, dict[str, Any]] = {}
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
        client = init_sheets_client(sheet_settings["credentials_path"], settings.get("network", {}))
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

            sync_hash = calculate_application_sync_hash(application)
            application["sync_hash"] = sync_hash
            row_values = [normalize_sheet_value(value) for value in format_application_for_excel(application).values()]
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
                    audit_action=None,
                    enqueue_sync=False,
                )
                application["google_sheet_row_id"] = str(target_row)
            if db_path is not None:
                update_application_sync_success(
                    application_id,
                    row_id=str(target_row),
                    sync_hash=sync_hash,
                    source=sync_source,
                    db_path=db_path,
                )
            application_results[application_id] = {
                "row_id": str(target_row),
                "sync_hash": sync_hash,
            }
    except Exception as exc:
        errors.append(str(exc))

    return {
        "synced": created + updated,
        "updated": updated,
        "created": created,
        "warnings": warnings,
        "errors": errors,
        "application_results": application_results,
    }


def push_application(application: dict[str, Any]) -> str:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")


def update_application_row(application: dict[str, Any], row_id: str) -> None:
    raise NotImplementedError("Use sync_applications_to_sheet for the V1 scaffold.")
