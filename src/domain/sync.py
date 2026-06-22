from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SyncMode = Literal["manual", "startup", "timer", "change_triggered"]


class SyncResult(BaseModel):
    synced: int = 0
    updated: int = 0
    created: int = 0
    skipped: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    application_results: dict[str, dict[str, str]] = Field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> SyncResult:
        return cls.model_validate(value)

    @property
    def ok(self) -> bool:
        return not self.errors


class SyncModeSummary(BaseModel):
    manual_sync_available: bool = True
    startup_sync_enabled: bool = True
    timer_sync_enabled: bool = True
    change_triggered_sync_enabled: bool = True
    stage5_required_for_automatic_sync: bool = False
    configured: bool = False
    credentials_path: str = ""
    spreadsheet_configured: bool = False
    timer_interval_seconds: int = 60
    max_retry_attempts: int = 5
    retry_backoff_seconds: int = 60
