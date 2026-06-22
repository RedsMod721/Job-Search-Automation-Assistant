# Stage 4 Readiness

Date: 2026-06-17

## Stage 4 Target

Stage 4 is database migrations, backups, and deduplication.

The Stage 3 repository boundary was added so Stage 4 can evolve SQLite behavior without spreading database-specific logic deeper into Streamlit UI code.

## Ready Inputs

- `ApplicationRepository` centralizes application lifecycle operations.
- `CompanyRepository` centralizes company upsert.
- Current schema remains unchanged.
- Current test database lifecycle still passes.
- Diagnostics can already report table counts.
- Stage 3 tests confirm repository operations work against SQLite.
- 2026-06-18 readiness recheck passed Ruff, mypy, pytest, Bandit, diagnostics, and a zero-row manual Google Sheets setup check.

## Recommended Stage 4 Plan

1. Add schema version table.
2. Add a migration runner that executes ordered SQL/Python migrations.
3. Add automatic backup before every migration.
4. Add manual backup and restore UI in Settings.
5. Add SQLite integrity check command and Settings-page result.
6. Add duplicate detection for applications, companies, and contacts.
7. Add canonical URL normalization.
8. Add normalized company name fields.
9. Add external job ID and job-description hash.
10. Add soft-delete/tombstone rules.
11. Add audit-event table.
12. Add recovery export.

## Acceptance Checks For Stage 4

- Existing `database/applications.db` upgrades without deletion.
- Backup is created before migration.
- Backup restore succeeds against a copied database.
- Duplicate application cases are detected.
- Duplicate company cases are detected.
- Failed migration rolls back or clearly restores from backup.
- Audit records identify important create/update/archive/delete events.
- All Stage 3 tests remain green.

## Guardrails

- Do not commit local production databases.
- Test migrations on a copied database first.
- Do not add automatic Google Sheets sync in Stage 4 unless it is strictly needed for audit/outbox schema preparation.
- Keep the manual sync button working.
- Keep `config/google_service_account.json` ignored.
