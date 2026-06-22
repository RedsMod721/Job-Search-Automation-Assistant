# Stage 3 Google Sheets Sync Boundary

Date: 2026-06-17

## Current Decision

Stage 3 keeps Google Sheets sync manual only.

This is deliberate. The Sprint 2 roadmap assigns automatic startup sync, timer sync, create/update/delete-triggered sync, retry/backoff, offline queue, and sync audit logging to Stage 5.

## Implemented In Stage 3

- `src/services/sync_service.py`
  - `manual_sync_applications(applications, settings, db_path=None)`
  - `sync_mode_summary(settings)`
  - `automatic_sync_modes(settings)`
- `src/domain/sync.py`
  - `SyncResult`
  - `SyncModeSummary`
- Tracker button now calls `manual_sync_applications`.
- Settings diagnostics show the sync-mode summary inside detailed diagnostics.
- Tests verify automatic sync modes are disabled.

## Active Behavior

| Mode | Stage 3 Status |
| --- | --- |
| Manual button sync | Available |
| Startup sync | Disabled |
| Timer sync | Disabled |
| Change-triggered sync | Disabled |
| Offline queue | Not implemented |
| Retry/backoff | Not implemented |
| Sync audit log | Not implemented |

## Credential State

Diagnostics on 2026-06-18 show:

- Spreadsheet configured locally: yes.
- Google Sheets enabled: true.
- Credentials exist: true.
- Credentials path: redacted in diagnostics.

A zero-row manual setup check passed with:

```json
{"synced":0,"updated":0,"created":0,"warnings":[],"errors":[]}
```

Manual sync with real application rows still depends on the same current configuration and should use the Tracker button.

## Stage 5 Handoff

Stage 5 should build on `sync_service` rather than call `src.sheets_sync` directly from UI pages.

Recommended additions for Stage 5:

- sync state/outbox table through Stage 4 migrations
- last local update timestamp per application
- dirty flag or pending operation queue
- startup sync hook after `bootstrap`
- timer worker with configurable interval
- post-write sync trigger after repository add/update/archive/delete
- retry/backoff state
- visible sync status
- live integration test using a dedicated spreadsheet
