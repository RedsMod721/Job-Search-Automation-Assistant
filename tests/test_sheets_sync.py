from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src import database, sheets_sync
from src.constants import GOOGLE_SHEETS_COLUMNS, PROJECT_ROOT


class FakeWorksheet:
    def __init__(self) -> None:
        self.rows: list[list[str]] = []

    def row_values(self, index: int) -> list[str]:
        if index - 1 < len(self.rows):
            return self.rows[index - 1]
        return []

    def update(self, cell: str, values: list[list[str]]) -> None:
        row_number = int(cell[1:])
        while len(self.rows) < row_number:
            self.rows.append([])
        self.rows[row_number - 1] = list(values[0])

    def get_all_values(self) -> list[list[str]]:
        return [list(row) for row in self.rows]

    def append_row(self, values: list[str], value_input_option: str | None = None) -> None:
        self.rows.append(list(values))


class FakeSpreadsheet:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self._worksheet = worksheet

    def worksheet(self, name: str) -> FakeWorksheet:
        return self._worksheet

    def add_worksheet(self, title: str, rows: int, cols: int) -> FakeWorksheet:
        return self._worksheet


class FakeClient:
    def __init__(self, worksheet: FakeWorksheet) -> None:
        self.worksheet = worksheet
        self.opened_key = ""

    def open_by_key(self, spreadsheet_id: str) -> FakeSpreadsheet:
        self.opened_key = spreadsheet_id
        return FakeSpreadsheet(self.worksheet)


def _test_db_path() -> Path:
    return PROJECT_ROOT / "database" / f"test_{uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    for candidate in (path, path.with_name(f"{path.name}-journal")):
        try:
            candidate.unlink(missing_ok=True)
        except PermissionError:
            pass


def test_sync_applications_to_sheet_creates_updates_and_stores_row_id(monkeypatch) -> None:
    worksheet = FakeWorksheet()
    client = FakeClient(worksheet)
    monkeypatch.setattr(sheets_sync, "init_sheets_client", lambda credentials_path: client)
    db_path = _test_db_path()

    try:
        database.init_db(db_path)
        application_id = database.add_application(
            {
                "company_name": "Acme AI",
                "job_title": "AI Analyst",
                "status": "To Apply",
            },
            db_path=db_path,
        )
        settings = {
            "google_sheets": {
                "enabled": True,
                "spreadsheet_id": "https://docs.google.com/spreadsheets/d/sheet-123/edit#gid=0",
                "worksheet_name": "Applications",
                "credentials_path": "config/google_service_account.json",
            }
        }

        first = sheets_sync.sync_applications_to_sheet(
            [database.get_application(application_id, db_path=db_path)],
            settings,
            db_path=db_path,
        )

        assert first == {"synced": 1, "updated": 0, "created": 1, "warnings": [], "errors": []}
        assert client.opened_key == "sheet-123"
        assert worksheet.rows[0] == list(GOOGLE_SHEETS_COLUMNS)
        assert database.get_application(application_id, db_path=db_path)["google_sheet_row_id"] == "2"

        database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
        second = sheets_sync.sync_applications_to_sheet(
            [database.get_application(application_id, db_path=db_path)],
            settings,
            db_path=db_path,
        )

        status_index = list(GOOGLE_SHEETS_COLUMNS).index("Status")
        assert second == {"synced": 1, "updated": 1, "created": 0, "warnings": [], "errors": []}
        assert worksheet.rows[1][status_index] == "Applied"
    finally:
        _cleanup_db(db_path)
