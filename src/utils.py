from __future__ import annotations

import json
import logging
import re
import uuid
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


def load_app_config() -> dict[str, dict[str, Any]]:
    return {name: load_yaml(path) for name, path in CONFIG_FILES.items()}


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

