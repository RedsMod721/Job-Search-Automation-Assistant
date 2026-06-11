from __future__ import annotations

from typing import Any


def search_companies(
    sector: str,
    location: str,
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    return []


def find_career_page(company_name: str, website: str | None = None) -> str | None:
    return None


def save_company_result(company: dict[str, Any]) -> str:
    from .database import upsert_company

    return upsert_company(company)

