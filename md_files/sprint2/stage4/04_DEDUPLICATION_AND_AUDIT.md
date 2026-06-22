# Stage 4 Deduplication and Audit

Date: 2026-06-19

## Normalization

`src/normalization.py` provides shared helpers:

- `normalize_company_name`
- `canonicalize_url`
- `content_hash`
- `normalize_email`

These are used by migrations, database writes, and duplicate detection.

## Duplicate Detection

`src/services/deduplication_service.py` checks:

Applications:

- same external job ID
- same canonical job URL
- same job-description hash
- same normalized company, role, and location

Companies:

- same normalized company name
- same canonical company website

Contacts:

- same company and normalized email
- same canonical LinkedIn URL

The current local database duplicate summary after migration:

```text
application_groups=1
company_groups=0
contact_groups=0
total_groups=1
```

## Audit Events

`audit_events` records:

- entity type
- entity ID
- action
- before JSON
- after JSON
- details JSON
- local actor
- created timestamp

Application actions covered:

- `create`
- `update`
- `archive`
- `delete`
- `hard_delete`

Company/contact upserts record:

- `create`
- `update`

## Tombstones

Application delete now writes:

- `deleted_at`
- `tombstone_reason`
- `status="Archived"`
- `archived=1`

Normal reads exclude tombstones. Recovery/admin reads can use `include_deleted=True`.

