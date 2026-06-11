from __future__ import annotations

import importlib

from src.constants import CONFIG_FILES
from src.utils import load_app_config, load_yaml


def test_active_config_files_exist_and_load() -> None:
    for path in CONFIG_FILES.values():
        assert path.exists()
        assert load_yaml(path)

    configs = load_app_config()
    assert configs["profile"]["user"]["first_name"] == "Sebastian"
    assert configs["settings"]["google_sheets"]["enabled"] is False
    assert configs["settings"]["automation"]["auto_submit_applications"] is False


def test_service_modules_are_importable() -> None:
    modules = [
        "src.constants",
        "src.utils",
        "src.database",
        "src.extractor",
        "src.cv_matcher",
        "src.letter_generator",
        "src.form_helper",
        "src.excel_exporter",
        "src.sheets_sync",
        "src.company_search",
    ]
    for module_name in modules:
        assert importlib.import_module(module_name)

