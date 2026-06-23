from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import requests

from . import cv_matcher
from .database import extraction_quality_summary
from .database_migrations import schema_status
from .network import describe_network_settings
from .services.extraction_evaluation_service import latest_evaluation_summary
from .services.recovery_service import run_integrity_check
from .services.sync_service import sync_status_summary
from .sheets_sync import normalize_spreadsheet_id
from .utils import load_app_config, local_config_path, resolve_path

SECRET_MARKERS = ("token", "secret", "password", "credential", "api_key", "service_account")


def redact_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if lowered.endswith("_exists") or isinstance(value, bool):
        return value
    if any(marker in lowered for marker in SECRET_MARKERS):
        return "<redacted>" if value else ""
    return value


def redact_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_value(str(key), redact_mapping(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_mapping(item) for item in value]
    return value


def _table_counts(db_path: Path) -> dict[str, int]:
    if not db_path.exists():
        return {}
    with sqlite3.connect(db_path) as connection:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        ]
        return {
            name: int(connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])  # nosec B608
            for name in names
        }


def _ollama_status(settings: dict[str, Any]) -> dict[str, Any]:
    llm = settings.get("llm", {})
    host = str(llm.get("host") or "http://localhost:11434").rstrip("/")
    model = str(llm.get("model") or "")
    timeout = min(int(settings.get("network", {}).get("request_timeout_seconds", 30)), 5)
    status: dict[str, Any] = {
        "host": host,
        "configured_model": model,
        "available": False,
        "configured_model_installed": False,
        "installed_models": [],
        "error": "",
    }
    try:
        response = requests.get(f"{host}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        installed = sorted(str(item.get("name", "")) for item in payload.get("models", []) if item.get("name"))
        status.update(
            {
                "available": True,
                "configured_model_installed": model in installed,
                "installed_models": installed,
            }
        )
    except Exception as exc:
        status["error"] = str(exc)
    return status


def collect_diagnostics(configs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    configs = configs or load_app_config()
    settings = configs.get("settings", {})
    documents = configs.get("documents", {})

    db_path = resolve_path(settings.get("database", {}).get("path", "database/applications.db"))
    sheets = settings.get("google_sheets", {})
    credentials_path = resolve_path(sheets.get("credentials_path", "config/google_service_account.json"))

    template_status: dict[str, dict[str, Any]] = {}
    for language, meta in documents.get("documents", {}).get("motivation_letter_templates", {}).items():
        path = resolve_path(meta.get("file_path", ""))
        template_status[language] = {"path": str(path), "exists": path.exists()}

    local_config = {
        name: {
            "path": str(local_config_path(path)),
            "exists": local_config_path(path).exists(),
        }
        for name, path in {
            "profile": "config/profile.yaml",
            "documents": "config/documents.yaml",
            "settings": "config/settings.yaml",
            "form_answers": "config/form_answers.yaml",
        }.items()
    }

    diagnostics = {
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "table_counts": _table_counts(db_path),
            "schema": schema_status(db_path),
            "integrity": run_integrity_check(db_path),
        },
        "config": {
            "local_overrides": local_config,
            "settings_public_safe": not bool(
                str(settings.get("google_sheets", {}).get("spreadsheet_id", "")).strip()
                and not local_config["settings"]["exists"]
            ),
        },
        "documents": {
            "missing_cvs": cv_matcher.validate_cv_files(documents),
            "templates": template_status,
        },
        "ollama": _ollama_status(settings),
        "google_sheets": {
            "manual_sync_only": False,
            "enabled": bool(sheets.get("enabled", False)),
            "spreadsheet_configured": bool(normalize_spreadsheet_id(sheets.get("spreadsheet_id", ""))),
            "worksheet_name": sheets.get("worksheet_name", "Applications"),
            "credentials_path": str(credentials_path),
            "credentials_exists": credentials_path.exists(),
            "automatic_push": {
                "startup_sync_enabled": bool(sheets.get("startup_sync_enabled", True)),
                "timer_sync_enabled": bool(sheets.get("timer_sync_enabled", True)),
                "change_triggered_sync_enabled": bool(sheets.get("change_triggered_sync_enabled", True)),
                "timer_interval_seconds": int(sheets.get("timer_interval_seconds", 60)),
            },
            "sync_status": sync_status_summary(db_path) if db_path.exists() else {},
        },
        "extraction_quality": {
            "database_summary": extraction_quality_summary(db_path) if db_path.exists() else {},
            "latest_artifact": latest_evaluation_summary(
                settings.get("extraction_evaluation", {}).get("output_dir", "")
            ),
        },
        "network": describe_network_settings(settings.get("network", {})),
    }
    return redact_mapping(diagnostics)


def diagnostics_summary(diagnostics: dict[str, Any]) -> dict[str, str]:
    missing_cvs = diagnostics.get("documents", {}).get("missing_cvs", {})
    ollama = diagnostics.get("ollama", {})
    sheets = diagnostics.get("google_sheets", {})
    extraction_quality = diagnostics.get("extraction_quality", {})
    database_evaluation_status = (
        extraction_quality.get("database_summary", {}).get("latest_evaluation", {}).get("status")
    )
    artifact_evaluation_status = extraction_quality.get("latest_artifact", {}).get("status")
    if database_evaluation_status == "FAIL" or artifact_evaluation_status == "FAIL":
        extraction_eval_status = "attention"
    elif database_evaluation_status == "PASS" or artifact_evaluation_status == "PASS":
        extraction_eval_status = "ok"
    else:
        extraction_eval_status = "pending"
    return {
        "database": "ok" if diagnostics.get("database", {}).get("exists") else "missing",
        "cv_files": "ok" if not missing_cvs else "missing",
        "ollama": "ok" if ollama.get("available") else "unavailable",
        "ollama_model": "ok" if ollama.get("configured_model_installed") else "missing",
        "google_sheets": "ready"
        if sheets.get("credentials_exists") and sheets.get("spreadsheet_configured")
        else "manual setup needed",
        "extraction_eval": extraction_eval_status,
        "network_tls": "enabled" if diagnostics.get("network", {}).get("verify_tls") else "disabled",
    }
