from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src import database
from src.constants import GOOGLE_SHEETS_COLUMNS, PROJECT_ROOT
from src.services import sync_service


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

    def open_by_key(self, spreadsheet_id: str) -> FakeSpreadsheet:
        return FakeSpreadsheet(self.worksheet)


def _test_db_path() -> Path:
    path = PROJECT_ROOT / ".tmp" / f"stage5-sync-{uuid4().hex}" / "applications.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _settings() -> dict[str, object]:
    return {
        "google_sheets": {
            "enabled": True,
            "spreadsheet_id": "sheet-123",
            "worksheet_name": "Applications",
            "credentials_path": "config/google_service_account.json",
            "startup_sync_enabled": True,
            "timer_sync_enabled": True,
            "change_triggered_sync_enabled": True,
            "timer_interval_seconds": 60,
            "max_retry_attempts": 3,
            "retry_backoff_seconds": 10,
        }
    }


def test_application_writes_queue_outbox_and_increment_version() -> None:
    db_path = _test_db_path()
    database.init_db(db_path)

    application_id = database.add_application(
        {
            "company_name": "Sync Co",
            "job_title": "Analyst",
            "status": "Saved",
        },
        db_path=db_path,
    )
    created = database.get_application(application_id, db_path=db_path)
    assert created is not None
    assert created["record_version"] == 1
    assert created["sync_status"] == "PENDING"
    assert created["sync_pending"] == 1

    database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
    updated = database.get_application(application_id, db_path=db_path)
    assert updated is not None
    assert updated["record_version"] == 2

    summary = database.sync_status_summary(db_path)
    assert summary["outbox"]["PENDING"] >= 2


def test_change_triggered_sync_creates_then_updates_without_duplicate_rows(monkeypatch) -> None:
    worksheet = FakeWorksheet()
    monkeypatch.setattr(
        sync_service.sheets_sync,
        "init_sheets_client",
        lambda credentials_path, network_settings=None: FakeClient(worksheet),
    )
    db_path = _test_db_path()
    database.init_db(db_path)
    application_id = database.add_application(
        {
            "company_name": "No Duplicate Co",
            "job_title": "AI Analyst",
            "status": "Saved",
        },
        db_path=db_path,
    )

    first = sync_service.change_triggered_sync(_settings(), db_path=db_path)

    assert first.ok
    assert first.created == 1
    assert len(worksheet.rows) == 2
    stored = database.get_application(application_id, db_path=db_path)
    assert stored is not None
    assert stored["google_sheet_row_id"] == "2"
    assert stored["sync_status"] == "SYNCED"

    database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
    second = sync_service.change_triggered_sync(_settings(), db_path=db_path)

    status_index = list(GOOGLE_SHEETS_COLUMNS).index("Status")
    assert second.ok
    assert second.updated == 1
    assert len(worksheet.rows) == 2
    assert worksheet.rows[1][status_index] == "Applied"
    assert database.sync_status_summary(db_path)["outbox"]["COMPLETED"] >= 2


def test_offline_failure_moves_outbox_to_retry(monkeypatch) -> None:
    def failing_client(credentials_path: str, network_settings=None):
        raise RuntimeError("network offline")

    monkeypatch.setattr(sync_service.sheets_sync, "init_sheets_client", failing_client)
    db_path = _test_db_path()
    database.init_db(db_path)
    application_id = database.add_application(
        {
            "company_name": "Offline Co",
            "job_title": "Analyst",
        },
        db_path=db_path,
    )

    result = sync_service.change_triggered_sync(_settings(), db_path=db_path)

    assert not result.ok
    assert "network offline" in result.errors[0]
    summary = database.sync_status_summary(db_path)
    assert summary["outbox"]["RETRY"] >= 1
    stored = database.get_application(application_id, db_path=db_path)
    assert stored is not None
    assert stored["sync_status"] == "ERROR"
    assert "network offline" in stored["sync_last_error"]


def test_manual_force_sync_processes_retry_before_due(monkeypatch) -> None:
    def failing_client(credentials_path: str, network_settings=None):
        raise RuntimeError("temporary outage")

    worksheet = FakeWorksheet()
    db_path = _test_db_path()
    database.init_db(db_path)
    application_id = database.add_application(
        {
            "company_name": "Force Co",
            "job_title": "Engineer",
        },
        db_path=db_path,
    )
    monkeypatch.setattr(sync_service.sheets_sync, "init_sheets_client", failing_client)
    failed = sync_service.change_triggered_sync(_settings(), db_path=db_path)
    assert failed.errors

    monkeypatch.setattr(
        sync_service.sheets_sync,
        "init_sheets_client",
        lambda credentials_path, network_settings=None: FakeClient(worksheet),
    )
    application = database.get_application(application_id, db_path=db_path)
    assert application is not None
    forced = sync_service.manual_sync_applications([application], _settings(), db_path=db_path)

    assert forced.ok
    assert forced.synced == 1
    assert database.get_application(application_id, db_path=db_path)["sync_status"] == "SYNCED"  # type: ignore[index]


def test_startup_sync_queues_existing_records(monkeypatch) -> None:
    worksheet = FakeWorksheet()
    monkeypatch.setattr(
        sync_service.sheets_sync,
        "init_sheets_client",
        lambda credentials_path, network_settings=None: FakeClient(worksheet),
    )
    db_path = _test_db_path()
    database.init_db(db_path)
    database.add_application(
        {
            "company_name": "Startup Co",
            "job_title": "Consultant",
        },
        db_path=db_path,
    )

    result = sync_service.startup_sync(_settings(), db_path=db_path)

    assert result.ok
    assert result.synced == 1
    assert len(worksheet.rows) == 2
