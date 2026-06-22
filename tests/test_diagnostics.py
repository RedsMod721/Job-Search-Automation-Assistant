from __future__ import annotations

from pathlib import Path

from src import diagnostics


def test_diagnostics_redacts_credentials_path(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics,
        "_ollama_status",
        lambda settings: {
            "host": "http://localhost:11434",
            "configured_model": "qwen3:4b",
            "available": False,
            "configured_model_installed": False,
            "installed_models": [],
            "error": "mocked",
        },
    )
    report = diagnostics.collect_diagnostics(
        {
            "settings": {
                "database": {"path": "database/applications.db"},
                "google_sheets": {
                    "enabled": False,
                    "spreadsheet_id": "sheet-123",
                    "worksheet_name": "Applications",
                    "credentials_path": "config/google_service_account.json",
                },
                "network": {"verify_tls": True, "request_timeout_seconds": 30},
                "llm": {"model": "qwen3:4b"},
            },
            "documents": {
                "documents": {
                    "cvs": {},
                    "motivation_letter_templates": {
                        "english": {"file_path": "documents/templates/motivation_letter_en.txt"}
                    },
                }
            },
        }
    )

    assert report["google_sheets"]["credentials_path"] == "<redacted>"
    assert report["google_sheets"]["manual_sync_only"] is False


def test_diagnostics_summary_reports_missing_assets() -> None:
    summary = diagnostics.diagnostics_summary(
        {
            "database": {"exists": True},
            "documents": {"missing_cvs": {"ai": str(Path("missing.pdf"))}},
            "ollama": {"available": False, "configured_model_installed": False},
            "google_sheets": {"credentials_exists": False, "spreadsheet_configured": False},
            "network": {"verify_tls": True},
        }
    )

    assert summary["database"] == "ok"
    assert summary["cv_files"] == "missing"
    assert summary["google_sheets"] == "manual setup needed"
