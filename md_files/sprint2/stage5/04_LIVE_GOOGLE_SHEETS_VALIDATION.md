# Stage 5 Live Google Sheets Validation

Date: 2026-06-19

## Preconditions

- `config/google_service_account.json` exists locally.
- Google Sheets is enabled in merged local settings.
- Spreadsheet is configured.
- Worksheet: `Applications`.
- Credentials path redacted in diagnostics.

## Migration State

Local database:

```text
database/applications.db
```

Schema:

```text
current_version=2
target_version=2
pending_versions=[]
```

## Live Startup Sync

Command ran a startup-style sync through `sync_service.startup_sync`.

Result:

```json
{
  "synced": 7,
  "updated": 7,
  "created": 0,
  "skipped": 0,
  "warnings": [],
  "errors": []
}
```

Per-application row IDs were returned for all 7 local applications.

## Post-Sync State

```text
sync_outbox COMPLETED=14
applications SYNCED=7
sync_runs=1
last_run mode=startup
last_run status=OK
```

## Interpretation

The live Sheet already contained rows for the local application IDs, so the sync updated those rows rather than appending new rows. This validates row identity matching by `Application ID` and avoids duplicate row creation.

