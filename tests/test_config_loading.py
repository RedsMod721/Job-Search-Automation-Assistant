from __future__ import annotations

import importlib
from uuid import uuid4

from src.constants import CONFIG_FILES, PROJECT_ROOT
from src.utils import (
    apply_runtime_config_overrides,
    load_app_config,
    load_yaml,
    load_yaml_with_local,
    local_config_path,
    write_yaml,
)


def test_active_config_files_exist_and_load() -> None:
    for path in CONFIG_FILES.values():
        assert path.exists()
        assert load_yaml(path)

    configs = load_app_config(include_local=False, include_env=False)
    assert configs["profile"]["user"]["first_name"] == "Sebastian"
    assert configs["settings"]["google_sheets"]["enabled"] is False
    assert configs["settings"]["automation"]["auto_submit_applications"] is False


def test_tracked_settings_defaults_are_public_safe() -> None:
    settings = load_yaml(CONFIG_FILES["settings"])

    assert settings["google_sheets"]["enabled"] is False
    assert settings["google_sheets"]["spreadsheet_id"] == ""
    assert settings["network"]["verify_tls"] is True


def test_local_yaml_override_merges_with_base() -> None:
    test_dir = PROJECT_ROOT / ".tmp" / f"config-loading-{uuid4().hex}"
    test_dir.mkdir(parents=True, exist_ok=True)
    base_path = test_dir / "settings.yaml"
    local_path = local_config_path(base_path)
    write_yaml(
        base_path,
        {
            "google_sheets": {"enabled": False, "spreadsheet_id": ""},
            "network": {"verify_tls": True, "request_timeout_seconds": 30},
        },
    )
    write_yaml(
        local_path,
        {
            "google_sheets": {"spreadsheet_id": "local-sheet"},
            "network": {"request_timeout_seconds": 45},
        },
    )

    merged = load_yaml_with_local(base_path)

    assert merged["google_sheets"] == {"enabled": False, "spreadsheet_id": "local-sheet"}
    assert merged["network"] == {"verify_tls": True, "request_timeout_seconds": 45}


def test_google_sheets_spreadsheet_id_can_be_overridden_from_env(monkeypatch) -> None:
    monkeypatch.setenv("STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID", "sheet-override-123")

    configs = apply_runtime_config_overrides(load_app_config())

    assert configs["settings"]["google_sheets"]["spreadsheet_id"] == "sheet-override-123"


def test_network_runtime_overrides_from_env(monkeypatch) -> None:
    monkeypatch.setenv("JOB_SEARCH_VERIFY_TLS", "false")
    monkeypatch.setenv("JOB_SEARCH_REQUEST_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("JOB_SEARCH_CA_BUNDLE", "config/corporate-ca.pem")
    monkeypatch.setenv("JOB_SEARCH_HTTPS_PROXY", "https://proxy.local:8443")
    monkeypatch.setenv("JOB_SEARCH_NO_PROXY", "localhost,127.0.0.1")

    configs = apply_runtime_config_overrides(load_app_config(include_env=False))

    assert configs["settings"]["network"]["verify_tls"] is False
    assert configs["settings"]["network"]["request_timeout_seconds"] == 17
    assert configs["settings"]["network"]["custom_ca_bundle"] == "config/corporate-ca.pem"
    assert configs["settings"]["network"]["https_proxy"] == "https://proxy.local:8443"
    assert configs["settings"]["network"]["no_proxy"] == "localhost,127.0.0.1"


def test_generic_proxy_env_vars_are_not_runtime_overrides(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")

    configs = apply_runtime_config_overrides(load_app_config(include_local=False, include_env=False))

    assert configs["settings"]["network"]["http_proxy"] == ""
    assert configs["settings"]["network"]["https_proxy"] == ""
    assert configs["settings"]["network"]["no_proxy"] == ""


def test_service_modules_are_importable() -> None:
    modules = [
        "src.constants",
        "src.utils",
        "src.network",
        "src.normalization",
        "src.database_backups",
        "src.database_migrations",
        "src.diagnostics",
        "src.domain.application",
        "src.domain.sync",
        "src.database",
        "src.repositories.applications",
        "src.repositories.companies",
        "src.services.application_service",
        "src.services.deduplication_service",
        "src.services.extraction_correction_service",
        "src.services.extraction_evaluation_service",
        "src.services.extraction_quality",
        "src.services.extraction_service",
        "src.services.recovery_service",
        "src.services.sync_service",
        "src.extractor",
        "src.cv_matcher",
        "src.letter_generator",
        "src.form_helper",
        "src.excel_exporter",
        "src.sheets_sync",
        "src.company_search",
        "src.prompts.registry",
        "src.ui.page_runner",
    ]
    for module_name in modules:
        assert importlib.import_module(module_name)
