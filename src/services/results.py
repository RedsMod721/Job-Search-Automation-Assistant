from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ServiceResult(BaseModel):
    value: Any | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors
