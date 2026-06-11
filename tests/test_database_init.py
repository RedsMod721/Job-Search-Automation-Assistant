from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from src import database
from src.constants import PROJECT_ROOT


def _test_db_path() -> Path:
    return PROJECT_ROOT / "database" / f"test_{uuid4().hex}.db"


def _cleanup_db(path: Path) -> None:
    for candidate in (path, path.with_name(f"{path.name}-journal")):
        try:
            candidate.unlink(missing_ok=True)
        except PermissionError:
            pass


def test_database_init_creates_core_tables() -> None:
    db_path = _test_db_path()
    try:
        database.init_db(db_path)

        with sqlite3.connect(db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }

        assert {"applications", "companies", "contacts", "documents"}.issubset(tables)
    finally:
        _cleanup_db(db_path)


def test_application_crud_round_trip() -> None:
    db_path = _test_db_path()
    try:
        database.init_db(db_path)

        application_id = database.add_application(
            {
                "company_name": "Example AI Consulting Firm",
                "job_title": "Junior AI Consultant",
                "status": "To Apply",
                "required_skills": ["Python", "LLM", "consulting"],
            },
            db_path=db_path,
        )

        saved = database.get_application(application_id, db_path=db_path)
        assert saved is not None
        assert saved["company_name"] == "Example AI Consulting Firm"
        assert saved["required_skills"] == ["Python", "LLM", "consulting"]

        database.update_application(application_id, {"status": "Applied"}, db_path=db_path)
        updated = database.get_application(application_id, db_path=db_path)
        assert updated is not None
        assert updated["status"] == "Applied"

        database.archive_application(application_id, db_path=db_path)
        archived = database.get_application(application_id, db_path=db_path)
        assert archived is not None
        assert archived["status"] == "Archived"
        assert archived["archived"] == 1
    finally:
        _cleanup_db(db_path)
