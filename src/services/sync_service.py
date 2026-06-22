from __future__ import annotations

from pathlib import Path
from typing import Any

from src import database, sheets_sync
from src.domain.sync import SyncModeSummary, SyncResult


def _sheet_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return settings.get("google_sheets", {})


def _sync_enabled(settings: dict[str, Any]) -> bool:
    return bool(_sheet_settings(settings).get("enabled", False))


def _bool_setting(sheet_settings: dict[str, Any], key: str, default: bool = True) -> bool:
    return bool(sheet_settings.get(key, default))


def _int_setting(sheet_settings: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(sheet_settings.get(key, default))
    except (TypeError, ValueError):
        return default


def sync_mode_summary(settings: dict[str, Any]) -> SyncModeSummary:
    sheet_settings = _sheet_settings(settings)
    spreadsheet_id = sheets_sync.normalize_spreadsheet_id(sheet_settings.get("spreadsheet_id", ""))
    return SyncModeSummary(
        configured=_sync_enabled(settings),
        credentials_path=str(sheet_settings.get("credentials_path", "config/google_service_account.json")),
        spreadsheet_configured=bool(spreadsheet_id),
        startup_sync_enabled=_bool_setting(sheet_settings, "startup_sync_enabled", True),
        timer_sync_enabled=_bool_setting(sheet_settings, "timer_sync_enabled", True),
        change_triggered_sync_enabled=_bool_setting(sheet_settings, "change_triggered_sync_enabled", True),
        timer_interval_seconds=_int_setting(sheet_settings, "timer_interval_seconds", 60),
        max_retry_attempts=_int_setting(sheet_settings, "max_retry_attempts", 5),
        retry_backoff_seconds=_int_setting(sheet_settings, "retry_backoff_seconds", 60),
    )


def _disabled_result(message: str) -> SyncResult:
    return SyncResult(warnings=[message])


def process_sync_outbox(
    settings: dict[str, Any],
    *,
    db_path: str | Path,
    mode: str,
    force: bool = False,
    limit: int = 50,
) -> SyncResult:
    if not _sync_enabled(settings):
        result = _disabled_result("Google Sheets sync is disabled.")
        database.record_sync_run(
            mode=mode,
            status="SKIPPED",
            warnings=result.warnings,
            db_path=db_path,
        )
        return result

    sheet_settings = _sheet_settings(settings)
    due_items = database.list_due_sync_outbox(db_path=db_path, limit=limit, force=force)
    if not due_items:
        database.record_sync_run(mode=mode, status="NOOP", skipped=0, db_path=db_path)
        return SyncResult(skipped=0)

    outbox_ids = [str(item["outbox_id"]) for item in due_items]
    database.mark_sync_outbox_processing(outbox_ids, db_path=db_path)

    application_ids = sorted(
        {
            str(item["entity_id"])
            for item in due_items
            if str(item.get("entity_type", "")) == "application" and str(item.get("entity_id", "")).strip()
        }
    )
    applications = [
        application
        for application_id in application_ids
        if (application := database.get_application(application_id, db_path=db_path, include_deleted=True)) is not None
    ]
    skipped = len(application_ids) - len(applications)

    if not applications:
        database.mark_sync_outbox_completed(outbox_ids, db_path=db_path)
        result = SyncResult(skipped=skipped)
        database.record_sync_run(mode=mode, status="NOOP", skipped=skipped, db_path=db_path)
        return result

    result = SyncResult.from_mapping(
        sheets_sync.sync_applications_to_sheet(applications, settings, db_path=db_path, sync_source=mode)
    )
    result.skipped = skipped

    if result.errors:
        error_message = "; ".join(result.errors)
        database.mark_sync_outbox_retry(
            outbox_ids,
            error_message,
            db_path=db_path,
            max_attempts=_int_setting(sheet_settings, "max_retry_attempts", 5),
            backoff_seconds=_int_setting(sheet_settings, "retry_backoff_seconds", 60),
        )
        for application in applications:
            database.update_application_sync_failure(str(application["application_id"]), error_message, db_path=db_path)
        database.record_sync_run(
            mode=mode,
            status="ERROR",
            synced=result.synced,
            created=result.created,
            updated=result.updated,
            skipped=skipped,
            warnings=result.warnings,
            errors=result.errors,
            db_path=db_path,
        )
        return result

    database.mark_sync_outbox_completed(outbox_ids, db_path=db_path)
    database.record_sync_run(
        mode=mode,
        status="OK",
        synced=result.synced,
        created=result.created,
        updated=result.updated,
        skipped=skipped,
        warnings=result.warnings,
        errors=result.errors,
        db_path=db_path,
    )
    return result


def manual_sync_applications(
    applications: list[dict[str, Any]],
    settings: dict[str, Any],
    db_path: str | Path | None = None,
) -> SyncResult:
    if db_path is None:
        return SyncResult.from_mapping(
            sheets_sync.sync_applications_to_sheet(applications, settings, db_path=None, sync_source="manual")
        )

    for application in applications:
        application_id = str(application.get("application_id", "")).strip()
        if application_id:
            database.enqueue_application_sync(application_id, operation="manual", db_path=db_path)
    return process_sync_outbox(settings, db_path=db_path, mode="manual", force=True)


def startup_sync(settings: dict[str, Any], *, db_path: str | Path) -> SyncResult:
    if not _bool_setting(_sheet_settings(settings), "startup_sync_enabled", True):
        return _disabled_result("Startup sync is disabled.")
    database.enqueue_all_applications_sync(operation="startup", db_path=db_path, include_deleted=True)
    return process_sync_outbox(settings, db_path=db_path, mode="startup", force=True)


def timer_sync(settings: dict[str, Any], *, db_path: str | Path) -> SyncResult:
    if not _bool_setting(_sheet_settings(settings), "timer_sync_enabled", True):
        return _disabled_result("Timer sync is disabled.")
    return process_sync_outbox(settings, db_path=db_path, mode="timer")


def change_triggered_sync(settings: dict[str, Any], *, db_path: str | Path) -> SyncResult:
    if not _bool_setting(_sheet_settings(settings), "change_triggered_sync_enabled", True):
        return _disabled_result("Change-triggered sync is disabled.")
    return process_sync_outbox(settings, db_path=db_path, mode="change_triggered", limit=20)


def automatic_sync_modes(settings: dict[str, Any]) -> dict[str, bool]:
    summary = sync_mode_summary(settings)
    return {
        "manual": summary.manual_sync_available,
        "startup": summary.startup_sync_enabled,
        "timer": summary.timer_sync_enabled,
        "change_triggered": summary.change_triggered_sync_enabled,
    }


def sync_status_summary(db_path: str | Path) -> dict[str, Any]:
    return database.sync_status_summary(db_path)
