from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.database_backups import create_sqlite_backup, export_sql_dump, restore_sqlite_backup
from src.database_migrations import schema_status
from src.utils import resolve_path


def create_backup(db_path: str | Path, backup_dir: str | Path | None = None, label: str = "manual") -> Path:
    return create_sqlite_backup(db_path, backup_dir=backup_dir, label=label)


def restore_backup(
    backup_path: str | Path,
    db_path: str | Path,
    pre_restore_backup_dir: str | Path | None = None,
) -> Path | None:
    return restore_sqlite_backup(backup_path, db_path, pre_restore_backup_dir=pre_restore_backup_dir)


def create_recovery_export(
    db_path: str | Path,
    export_dir: str | Path | None = None,
    label: str = "recovery",
) -> Path:
    return export_sql_dump(db_path, export_dir=export_dir, label=label)


def run_integrity_check(db_path: str | Path) -> dict[str, Any]:
    path = resolve_path(db_path)
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "ok": False,
            "integrity_check": "missing",
            "foreign_key_issues": [],
            "schema": schema_status(path),
        }

    uri = f"file:{path.resolve().as_posix()}?mode=rw&nolock=1"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.execute("PRAGMA journal_mode=TRUNCATE")
        connection.execute("PRAGMA foreign_keys=ON")
        integrity_rows = [row[0] for row in connection.execute("PRAGMA integrity_check").fetchall()]
        foreign_key_rows = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]

    return {
        "path": str(path),
        "exists": True,
        "ok": integrity_rows == ["ok"] and not foreign_key_rows,
        "integrity_check": integrity_rows,
        "foreign_key_issues": foreign_key_rows,
        "schema": schema_status(path),
    }


def list_backups(backup_dir: str | Path | None = None) -> list[dict[str, Any]]:
    directory = resolve_path(backup_dir or "database/backups")
    if not directory.exists():
        return []
    backups = sorted(directory.glob("*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        {
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }
        for path in backups
    ]
