from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from src.constants import PROJECT_ROOT
from src.utils import now_iso, resolve_path

DEFAULT_BACKUP_DIR = PROJECT_ROOT / "database" / "backups"
DEFAULT_RECOVERY_EXPORT_DIR = PROJECT_ROOT / "database" / "recovery_exports"


def timestamp_for_filename() -> str:
    return now_iso().replace(":", "-").replace(".", "-")


def _connect_existing(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.resolve().as_posix()}?mode=rw&nolock=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA journal_mode=TRUNCATE")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def create_sqlite_backup(
    db_path: str | Path,
    backup_dir: str | Path | None = None,
    label: str = "manual",
) -> Path:
    source = resolve_path(db_path)
    if not source.exists():
        raise FileNotFoundError(f"Database does not exist: {source}")

    destination_dir = resolve_path(backup_dir or DEFAULT_BACKUP_DIR)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{source.stem}_{label}_{timestamp_for_filename()}.db"

    with _connect_existing(source) as source_connection:
        with sqlite3.connect(destination) as backup_connection:
            source_connection.backup(backup_connection)
    return destination


def restore_sqlite_backup(
    backup_path: str | Path,
    db_path: str | Path,
    pre_restore_backup_dir: str | Path | None = None,
) -> Path | None:
    backup = resolve_path(backup_path)
    destination = resolve_path(db_path)
    if not backup.exists():
        raise FileNotFoundError(f"Backup does not exist: {backup}")

    pre_restore_backup: Path | None = None
    if destination.exists():
        pre_restore_backup = create_sqlite_backup(
            destination,
            backup_dir=pre_restore_backup_dir or DEFAULT_BACKUP_DIR,
            label="pre_restore",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, destination)
    return pre_restore_backup


def export_sql_dump(
    db_path: str | Path,
    export_dir: str | Path | None = None,
    label: str = "recovery",
) -> Path:
    source = resolve_path(db_path)
    if not source.exists():
        raise FileNotFoundError(f"Database does not exist: {source}")

    destination_dir = resolve_path(export_dir or DEFAULT_RECOVERY_EXPORT_DIR)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{source.stem}_{label}_{timestamp_for_filename()}.sql"

    with _connect_existing(source) as connection:
        dump_lines = connection.iterdump()
        destination.write_text("\n".join(dump_lines) + "\n", encoding="utf-8")
    return destination
