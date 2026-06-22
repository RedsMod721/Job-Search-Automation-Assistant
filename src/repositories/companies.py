from __future__ import annotations

from pathlib import Path
from typing import Any

from src import database


class CompanyRepository:
    """Repository wrapper for saved companies."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = db_path

    def upsert(self, company: dict[str, Any]) -> str:
        return database.upsert_company(company, db_path=self.db_path)
