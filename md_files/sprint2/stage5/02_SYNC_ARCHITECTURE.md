# Stage 5 Sync Architecture

Date: 2026-06-19

## Scope

Stage 5 syncs applications from SQLite to Google Sheets.

SQLite remains the authoritative database. Google Sheets is a synchronized view.

## Local Tables

`sync_outbox`

- queue of local changes to push
- statuses: `PENDING`, `PROCESSING`, `RETRY`, `COMPLETED`, `DEAD_LETTER`
- records attempt count, next retry time, and last error

`sync_state`

- row identity and last successful sync metadata per entity
- stores local version, remote row key, sync hash, sync timestamp, and status

`sync_runs`

- records each sync pass
- stores mode, status, created/updated/synced/skipped counts, warnings, and errors

`sync_conflicts`

- reserved for future bidirectional sync
- not populated in Stage 5 push-only mode

## Write Flow

```text
Local application write
  -> update application row
  -> increment record_version
  -> write audit event
  -> write sync_outbox item
  -> mark sync_state/application as PENDING
  -> optionally process change-triggered sync
```

## Push Flow

```text
Sync worker reads due outbox items
  -> loads unique application records
  -> opens configured worksheet
  -> maps existing rows by Application ID
  -> updates existing row or appends new row
  -> writes row ID and sync hash locally
  -> marks outbox COMPLETED
  -> records sync run
```

## Retry Flow

On Google/network failure:

- outbox item moves to `RETRY`
- attempt count increments
- `next_attempt_at` is set using backoff
- application sync status becomes `ERROR`
- manual force sync can process retry rows before the delay

## Timer Behavior

Timer sync is enabled through Streamlit/browser refresh while the app is open.

Default interval:

```text
60 seconds
```

The interval is configurable in Settings.

## Row Identity

Rows are matched by `Application ID`, not by row number alone.

`google_sheet_row_id` is retained as a performance hint, but the sync engine verifies the row still contains the expected `Application ID`. If the row moved, it falls back to the full Application ID lookup.

