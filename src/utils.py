from __future__ import annotations

import json
import logging
import os
import re
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .constants import CONFIG_FILES, PROJECT_ROOT, REQUIRED_DIRECTORIES


def resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """Resolve a project-relative path unless it is already absolute."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (base_dir or PROJECT_ROOT) / candidate


def ensure_directories(paths: tuple[Path, ...] = REQUIRED_DIRECTORIES) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: str | Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Missing config file: {resolved}")
    with resolved.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {resolved}")
    return data


def local_config_path(path: str | Path) -> Path:
    resolved = resolve_path(path)
    return resolved.with_name(f"{resolved.stem}.local{resolved.suffix}")


def merge_dicts(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


def load_yaml_with_local(path: str | Path, include_local: bool = True) -> dict[str, Any]:
    base = load_yaml(path)
    if not include_local:
        return base

    local_path = local_config_path(path)
    if not local_path.exists():
        return base
    return merge_dicts(base, load_yaml(local_path))


def load_app_config(
    include_local: bool = True,
    include_env: bool = True,
) -> dict[str, dict[str, Any]]:
    configs = {name: load_yaml_with_local(path, include_local=include_local) for name, path in CONFIG_FILES.items()}
    if include_env:
        apply_runtime_config_overrides(configs)
    return configs


def apply_runtime_config_overrides(configs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    settings = configs.setdefault("settings", {})
    llm = settings.setdefault("llm", {})
    google_sheets = settings.setdefault("google_sheets", {})
    network = settings.setdefault("network", {})

    ollama_host = os.getenv("OLLAMA_HOST", "").strip()
    if ollama_host:
        llm["host"] = ollama_host

    spreadsheet_id = (
        os.getenv("STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID") or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or ""
    ).strip()
    if spreadsheet_id:
        google_sheets["spreadsheet_id"] = spreadsheet_id

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if credentials_path:
        google_sheets["credentials_path"] = credentials_path

    verify_tls = os.getenv("JOB_SEARCH_VERIFY_TLS", "").strip().lower()
    if verify_tls in {"0", "false", "no", "off"}:
        network["verify_tls"] = False
    elif verify_tls in {"1", "true", "yes", "on"}:
        network["verify_tls"] = True

    ca_bundle = (
        os.getenv("JOB_SEARCH_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("CURL_CA_BUNDLE") or ""
    ).strip()
    if ca_bundle:
        network["custom_ca_bundle"] = ca_bundle

    http_proxy = os.getenv("JOB_SEARCH_HTTP_PROXY", "").strip()
    if http_proxy:
        network["http_proxy"] = http_proxy
    https_proxy = os.getenv("JOB_SEARCH_HTTPS_PROXY", "").strip()
    if https_proxy:
        network["https_proxy"] = https_proxy
    no_proxy = os.getenv("JOB_SEARCH_NO_PROXY", "").strip()
    if no_proxy:
        network["no_proxy"] = no_proxy

    timeout = os.getenv("JOB_SEARCH_REQUEST_TIMEOUT_SECONDS", "").strip()
    if timeout:
        try:
            network["request_timeout_seconds"] = int(timeout)
        except ValueError:
            pass

    return configs


def write_yaml(path: str | Path, data: dict[str, Any]) -> None:
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def configure_logging(settings: dict[str, Any] | None = None) -> None:
    ensure_directories()
    logging_settings = (settings or {}).get("logging", {})
    if logging_settings.get("enabled", True) is False:
        logging.disable(logging.CRITICAL)
        return

    log_file = resolve_path(logging_settings.get("log_file", "logs/app.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    level_name = str(logging_settings.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        filename=log_file,
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def serialize_list(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "[]"
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return json.dumps([stripped], ensure_ascii=False)
        if isinstance(parsed, list):
            return json.dumps(parsed, ensure_ascii=False)
        return json.dumps([parsed], ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value), ensure_ascii=False)
    return json.dumps([value], ensure_ascii=False)


def deserialize_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return [value]
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return parsed if isinstance(parsed, list) else [parsed]


def list_to_readable_text(value: Any) -> str:
    items = deserialize_list(value)
    return "; ".join(str(item) for item in items if str(item).strip())


def normalize_boolish(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return 1 if value else 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "required", "1"}:
            return 1
        if lowered in {"false", "no", "not required", "0"}:
            return 0
    return None


def clean_string(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_filename(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_string(value))
    cleaned = cleaned.strip("._-")
    return cleaned or fallback
