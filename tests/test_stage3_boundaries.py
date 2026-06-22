from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.domain.application import ApplicationRecord
from src.prompts.registry import PROMPTS, get_prompt
from src.repositories.applications import ApplicationRepository
from src.services import sync_service


def _test_db_path() -> Path:
    return Path("database") / f"test_stage3_{uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    for candidate in (path, path.with_name(f"{path.name}-journal")):
        try:
            candidate.unlink(missing_ok=True)
        except PermissionError:
            pass


def test_business_services_do_not_import_streamlit() -> None:
    service_files = Path("src/services").glob("*.py")
    for path in service_files:
        assert "streamlit" not in path.read_text(encoding="utf-8").lower()


def test_application_repository_wraps_application_lifecycle() -> None:
    db_path = _test_db_path()
    repository = ApplicationRepository(db_path)
    try:
        repository.init()
        application_id = repository.add(
            {
                "company_name": "Stage 3 Co",
                "job_title": "Workflow Engineer",
                "status": "To Apply",
            }
        )

        saved = repository.get(application_id)
        assert saved is not None
        assert saved["company_name"] == "Stage 3 Co"

        repository.update(application_id, {"status": "Applied"})
        updated = repository.get(application_id)
        assert updated is not None
        assert updated["status"] == "Applied"

        repository.archive(application_id)
        archived = repository.get(application_id)
        assert archived is not None
        assert archived["archived"] == 1

        repository.delete(application_id)
        assert repository.get(application_id) is None
    finally:
        _cleanup_db(db_path)


def test_domain_application_model_preserves_legacy_extra_fields() -> None:
    record = ApplicationRecord.from_mapping(
        {
            "application_id": "app-123",
            "company_name": "Acme",
            "required_skills": ["Python"],
            "custom_stage3_field": "kept",
        }
    )

    payload = record.to_payload()
    assert payload["application_id"] == "app-123"
    assert payload["required_skills"] == ["Python"]
    assert payload["custom_stage3_field"] == "kept"


def test_sync_service_reports_stage5_automatic_modes() -> None:
    settings = {
        "google_sheets": {
            "enabled": True,
            "spreadsheet_id": "https://docs.google.com/spreadsheets/d/sheet-123/edit#gid=0",
            "credentials_path": "config/google_service_account.json",
        }
    }

    summary = sync_service.sync_mode_summary(settings)
    modes = sync_service.automatic_sync_modes(settings)

    assert summary.manual_sync_available is True
    assert summary.spreadsheet_configured is True
    assert summary.startup_sync_enabled is True
    assert summary.timer_sync_enabled is True
    assert summary.change_triggered_sync_enabled is True
    assert summary.stage5_required_for_automatic_sync is False
    assert modes == {
        "manual": True,
        "startup": True,
        "timer": True,
        "change_triggered": True,
    }


def test_manual_sync_service_returns_typed_result(monkeypatch) -> None:
    def fake_sync(applications, settings, db_path=None, sync_source="manual"):
        return {
            "synced": len(applications),
            "updated": 1,
            "created": 0,
            "skipped": 0,
            "warnings": [],
            "errors": [],
            "application_results": {},
        }

    monkeypatch.setattr(sync_service.sheets_sync, "sync_applications_to_sheet", fake_sync)

    result = sync_service.manual_sync_applications([{"application_id": "app-123"}], {"google_sheets": {}})

    assert result.ok
    assert result.synced == 1
    assert result.updated == 1


def test_prompt_registry_versions_core_llm_prompts() -> None:
    assert set(PROMPTS) == {"job_extraction", "motivation_letter", "form_answers"}
    assert get_prompt("job_extraction").version == "stage3-v1"
