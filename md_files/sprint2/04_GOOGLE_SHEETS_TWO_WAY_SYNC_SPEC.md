# Google Sheets Automatic Push Synchronization Specification

## 1. Objective

Implement automatic synchronization from SQLite to Google Sheets without relying on a paid Google Cloud workflow.

Required behavior:

- Every committed local application change automatically queues a Google Sheets push.
- The app syncs on startup.
- The app syncs on a configurable timer, defaulting to every minute.
- The manual sync button remains available.
- SQLite remains the authoritative local operational database.
- Google Sheets remains a synchronized view.
- Offline changes queue safely.
- No silent overwrite or duplicate row creation.

## 2. Scope

Initial mandatory scope:

- Applications sheet.

Optional later scope:

- Companies.
- Contacts.
- Search profiles.

Do not delay application synchronization to implement optional sheets.

## 3. Synchronization Model

Use a local change queue and row identity mapping.

For each record, maintain:

1. Current local record.
2. Current remote Sheet row.
3. Last successfully synchronized timestamp or checksum.

This allows the engine to distinguish:

- Local-only changes.
- Pending local writes.
- Already-synced rows.

## 4. Technical Columns in Google Sheets

Add technical columns, preferably hidden:

```text
Application ID
Record Version
Last Synced At
Last Sync Source
Local Updated At
Sync Hash
Archived
```

`Application ID` is the immutable primary key.

Never use row number as the only identity because rows can move.

## 5. Local Sync Tables

### 5.1 `sync_outbox`

Suggested schema:

```sql
CREATE TABLE sync_outbox (
    outbox_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    next_attempt_at TEXT,
    last_error TEXT,
    status TEXT NOT NULL
);
```

Allowed status:

```text
PENDING
PROCESSING
RETRY
COMPLETED
DEAD_LETTER
```

### 5.2 `sync_state`

```sql
CREATE TABLE sync_state (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    remote_row_key TEXT,
    local_version INTEGER NOT NULL,
    remote_version INTEGER,
    last_synced_hash TEXT,
    last_synced_at TEXT,
    last_sync_source TEXT,
    sync_status TEXT,
    PRIMARY KEY(entity_type, entity_id)
);
```

### 5.3 `sync_conflicts`

```sql
CREATE TABLE sync_conflicts (
    conflict_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    base_value TEXT,
    local_value TEXT,
    remote_value TEXT,
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution TEXT,
    resolved_value TEXT,
    status TEXT NOT NULL
);
```

Allowed conflict status:

```text
OPEN
RESOLVED_LOCAL
RESOLVED_REMOTE
RESOLVED_MERGED
IGNORED
```

## 6. Local Write Flow

```text
User changes application
    ↓
Database transaction updates application
    ↓
Local version increments
    ↓
Audit event created
    ↓
Outbox event created in same transaction
    ↓
UI returns success
    ↓
Worker processes outbox
    ↓
Remote row created or updated
```

The application update and outbox creation must be atomic.

## 7. Remote Pull Flow

```text
Worker polls Google Sheets
    ↓
Read rows and technical metadata
    ↓
Map by Application ID
    ↓
Compare remote row with last synced snapshot
    ↓
No change: ignore
Remote-only change: update SQLite
Non-overlapping changes: merge
Same-field change: create conflict
```

## 8. Three-Way Merge Rules

For each synchronized field:

### Case A: Neither side changed

Keep value.

### Case B: Local changed, remote unchanged

Use local value and push remote.

### Case C: Remote changed, local unchanged

Use remote value and update SQLite.

### Case D: Both changed to same value

Use that value and mark synchronized.

### Case E: Both changed to different values

Create conflict.

Do not silently use timestamp-only last-write-wins for same-field conflicts.

## 9. Field Normalization

Before comparing values:

- Trim surrounding whitespace.
- Normalize line endings.
- Normalize boolean values.
- Normalize dates to ISO format.
- Normalize list fields.
- Normalize empty string and null consistently.
- Preserve intentional line breaks in notes and descriptions.
- Do not treat list order as a conflict when order has no meaning.

## 10. List Fields

Examples:

- Required skills.
- Preferred qualifications.
- Responsibilities.
- Matched keywords.

Recommended Sheet representation:

- Newline-separated values.

Recommended comparison:

- Parse to normalized lists.
- Compare case-insensitively where appropriate.
- Preserve original display casing from selected source.

## 11. Automatic Push

Trigger after:

- Application create.
- Application edit.
- Status change.
- CV selection.
- Letter link update.
- Form-answer link update.
- Archive.

The UI should not block until Google responds.

Show:

```text
Saved locally
Sync pending
```

Then update to:

```text
Synchronized
```

## 12. Automatic Pull

Use configurable polling while the background service is running.

Suggested initial default:

```yaml
google_sheets:
  auto_push: true
  auto_pull: true
  polling_interval_seconds: 30
```

The polling interval must be configurable.

Avoid unnecessary full-sheet writes.

## 13. Conflict Resolution UI

Add `Sync Issues` page.

For each conflict show:

| Field | Last synced | Local | Google Sheets | Resolution |
|---|---|---|---|---|

Resolution options:

- Keep local.
- Keep Google Sheets.
- Enter merged value.

After resolution:

- Update SQLite.
- Push resolved value to Sheets.
- Update last-synced snapshot.
- Close conflict.
- Create audit event.

## 14. Offline Behavior

When Google is unavailable:

- Local save succeeds.
- Outbox remains pending.
- Retry with exponential backoff.
- UI shows offline/pending state.
- No data is discarded.
- User can force retry.

Suggested retry pattern:

```text
Immediate
Short delay
Longer delay
Capped periodic retry
```

Exact values may be configurable.

## 15. Google Sheets Manual Edits

Users may edit business columns directly.

Technical columns should be protected or hidden where possible.

Invalid remote values must not corrupt SQLite.

Examples:

- Unknown status value.
- Invalid date.
- Invalid boolean.
- Duplicate Application ID.
- Deleted technical ID.

Invalid rows should create a sync issue with a clear error.

## 16. Row Creation and Matching

Use `Application ID`.

On push:

- If Application ID exists remotely, update that row.
- If not, create new row.
- If duplicate remote IDs exist, create a sync error requiring repair.

Do not rely solely on stored row number.

## 17. Archive and Delete

V1/V2 rule:

- Archive, do not physically delete through synchronization.
- Set `Archived = true`.
- Keep history.

Physical deletion should require a separate explicit maintenance workflow.

## 18. Initial Sync

When connecting an existing Sheet:

1. Validate headers.
2. Back up local database.
3. Read all remote rows.
4. Identify matching IDs.
5. Identify rows without IDs.
6. Show import preview.
7. Require confirmation before bulk import.
8. Create initial snapshots.
9. Do not silently overwrite.

## 19. Sync Status in UI

Application-level indicators:

```text
Synced
Pending
Offline
Conflict
Error
```

Global status:

- Last successful sync.
- Pending queue count.
- Conflict count.
- Last error.
- Google account/spreadsheet.
- Worker health.

## 20. Tests

### Unit Tests

- Three-way merge cases.
- Normalization.
- List comparison.
- Conflict creation.
- Retry calculation.
- Row serialization.

### Integration Tests

- Fake Google client.
- Create row.
- Update row.
- Pull remote edit.
- Non-overlapping merge.
- Same-field conflict.
- Offline retry.
- Duplicate ID.

### Live Manual Tests

Use a dedicated test spreadsheet.

Test:

- Local create.
- Local edit.
- Remote edit.
- Simultaneous different-field edit.
- Simultaneous same-field edit.
- Network interruption.
- Sheet permission removal.
- Row reordering.
- Column reordering.
- Invalid remote status.

## 21. Acceptance Criteria

- Automatic push works.
- Automatic pull works.
- Local changes never depend on immediate network availability.
- Non-overlapping changes merge automatically.
- Same-field conflicts appear in UI.
- Conflict resolution updates both systems.
- Duplicate rows are prevented.
- Technical metadata remains consistent.
- All sync actions are audited.
