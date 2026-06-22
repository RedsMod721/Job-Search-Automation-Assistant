from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any

from src import database


class ApplicationRepository:
    """Repository wrapper around the current SQLite application store."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = db_path

    def init(self) -> Path:
        return database.init_db(self.db_path)

    def add(self, application: dict[str, Any]) -> str:
        return database.add_application(application, db_path=self.db_path)

    def update(self, application_id: str, updates: dict[str, Any]) -> None:
        database.update_application(application_id, updates, db_path=self.db_path)

    def get(self, application_id: str, *, include_deleted: bool = False) -> dict[str, Any] | None:
        return database.get_application(application_id, db_path=self.db_path, include_deleted=include_deleted)

    def list(
        self,
        filters: dict[str, Any] | None = None,
        *,
        include_deleted: bool = False,
    ) -> builtins.list[dict[str, Any]]:
        return database.list_applications(filters=filters, db_path=self.db_path, include_deleted=include_deleted)

    def archive(self, application_id: str) -> None:
        database.archive_application(application_id, db_path=self.db_path)

    def delete(self, application_id: str) -> None:
        database.delete_application(application_id, db_path=self.db_path)

    def hard_delete(self, application_id: str) -> None:
        database.hard_delete_application(application_id, db_path=self.db_path)

    def audit_events(self, application_id: str | None = None, limit: int = 100) -> builtins.list[dict[str, Any]]:
        return database.list_audit_events(
            db_path=self.db_path,
            entity_type="application",
            entity_id=application_id,
            limit=limit,
        )


def application_repository_from_settings(settings: dict[str, Any]) -> ApplicationRepository:
    db_path = settings.get("database", {}).get("path", "database/applications.db")
    return ApplicationRepository(db_path)
