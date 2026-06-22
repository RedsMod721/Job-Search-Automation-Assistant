# QA, Security, Packaging, and Definition of Done

## 1. Purpose

This document defines the quality gates required before the project can be considered complete.

## 2. Test Strategy

Required layers:

1. Unit tests.
2. Integration tests.
3. Contract tests.
4. Browser-extension tests.
5. End-to-end tests.
6. Manual acceptance tests.
7. Migration tests.
8. Recovery tests.
9. Security checks.
10. Source-compliance checks.

## 3. Unit Tests

Cover:

- Domain models.
- Validation.
- Database repositories.
- Deduplication.
- Job-fit rules.
- CV recommendation.
- Sync merge.
- Conflict creation.
- Prompt registry.
- Field ontology.
- Search normalization.
- Salary normalization.
- Retry policies.

## 4. Integration Tests

Cover:

- SQLite repository.
- Ollama client with mocked and local modes.
- Google Sheets fake client.
- Google Sheets live test environment.
- Search connector fixtures.
- Local FastAPI endpoints.
- Worker queues.
- File generation.
- Backup/restore.

## 5. Contract Tests

Every connector and local API must have contract tests.

Examples:

- Greenhouse normalized result.
- Lever normalized result.
- Extension capture payload.
- Application API response.
- Sheets row serialization.
- Ollama structured extraction schema.

## 6. Browser Extension Tests

Use fixture pages for:

- LinkedIn job page.
- Greenhouse form.
- Lever form.
- Ashby form.
- SmartRecruiters form.
- Workday form.
- Generic form.

Test:

- Field detection.
- Filling.
- Skip/edit.
- Sensitive fields.
- CV input.
- Submission protection.
- Success confirmation.

## 7. End-to-End Scenarios

### Scenario A: Manual Job

- Paste job.
- Extract.
- Correct fields.
- Save.
- CV recommend.
- Generate letter.
- Generate form answers.
- Mark applied.
- Sync to Sheet.

### Scenario B: Extension Capture

- Open job page.
- Capture.
- Preview.
- Save application.
- Fill form.
- Manual submit.
- Confirm success.
- Sync.

### Scenario C: Scheduled Search

- Saved search runs.
- Results normalized.
- Duplicates removed.
- Fit scored.
- Review queue updated.
- User saves one to tracker.

### Scenario D: Sync Conflict

- Edit same field locally and remotely.
- Conflict appears.
- User resolves.
- Both sides update.

### Scenario E: Offline

- Network unavailable.
- Local edits continue.
- Outbox queues.
- Network returns.
- Sync recovers.

## 8. CI Requirements

CI should include:

- Formatting check.
- Lint.
- Type check.
- Unit tests.
- Integration tests not requiring secrets.
- Coverage report.
- Dependency audit.
- Security scan.
- Build/package smoke test.

Use macOS and Windows runners where practical.

## 9. Coverage

Do not use coverage percentage as the only quality metric.

Minimum expectations:

- High coverage for core domain logic.
- Explicit tests for all hard gates.
- Explicit tests for all sync merge cases.
- Explicit tests for migration paths.
- Explicit tests preventing auto-submit behavior.

## 10. Security Requirements

### Local API

- Localhost only.
- Token required.
- Origin allowlist.
- No public bind.
- Rate limit extension calls if needed.
- Validate all payloads.

### Secrets

Never commit:

- Google service account JSON.
- Local API token.
- OAuth tokens.
- Private database.
- Extension production secrets.

### Browser Extension

- Minimal permissions.
- Optional host permissions.
- No hidden background scraping.
- No final submission.
- No sensitive-field auto-selection.
- No credential capture.

### Network

- TLS verification enabled.
- Custom CA explicit.
- Proxy explicit.
- Timeouts.
- No blanket warning suppression.

### Data

- Local backup.
- Safe migrations.
- Audit log.
- Archive over delete.
- Configurable log redaction.

## 11. Privacy

The repository is public during development and will later become private.

Before final release:

- Change repository to private.
- Review Git history for committed secrets.
- Rotate any accidentally committed secret.
- Decide whether personal profile should remain in history.
- Remove unnecessary sensitive data.
- Confirm local data paths are ignored.

## 12. Source Compliance

For each search/contact/salary source:

- Record usage method.
- Respect public access limitations.
- Respect rate limits.
- Avoid CAPTCHA bypass.
- Avoid authenticated scraping.
- Store provenance.
- Disable connector if compliance becomes uncertain.

## 13. Packaging

### macOS Target

Required final user experience:

```text
Double-click launcher
    ↓
Local API and worker start
    ↓
Streamlit opens in browser
    ↓
Health status displayed
```

Package or launcher must:

- Avoid requiring normal terminal use.
- Use user-level paths.
- Start background service.
- Detect Ollama.
- Detect required model.
- Detect credentials.
- Support clean shutdown.
- Support uninstall.

### Windows Secondary Support

Provide:

- PowerShell launcher.
- Setup instructions.
- Proxy/CA instructions.
- Known limitations.

## 14. Health Check

Health screen must show:

- App version.
- Database status.
- Migration status.
- Backup status.
- Ollama status.
- Selected model status.
- Google Sheets status.
- Sync worker status.
- Search scheduler status.
- Extension connection status.
- Pending sync count.
- Conflict count.
- Last successful search.
- Network/proxy status.

## 15. Logging

Required:

- Rotating logs.
- Structured context where possible.
- Separate user-readable errors and technical details.
- Redact tokens and credentials.
- Record correlation IDs for background jobs.
- Include source connector name.

## 16. Performance Expectations

The app must remain responsive with:

- Thousands of application records.
- Thousands of discovered jobs.
- Large descriptions.
- Pending sync queue.
- Multiple saved searches.

Long operations must not freeze the UI.

Use background processing for:

- LLM calls.
- Search runs.
- Bulk sync.
- Large exports.

## 17. Backup and Recovery

Test:

- Database backup.
- Restore.
- Failed migration recovery.
- Corrupted database handling.
- Rebuilding Sheet mapping.
- Reconnecting extension.
- Reinstalling app without data loss.

## 18. Release Checklist

Before final release:

- All required stages complete.
- CI green.
- Migration tested.
- Live Sheets test passed.
- Extension permissions reviewed.
- Auto-submit protection tested.
- Search connectors reviewed.
- Mac launcher tested.
- Backup/restore tested.
- User guide complete.
- Troubleshooting complete.
- Repository private.
- Release tag created.
- Changelog written.

## 19. Definition of Done for Individual Features

A feature is done only when:

- Requirement implemented.
- Error handling implemented.
- Unit tests added.
- Integration tests added where applicable.
- UI state included.
- Logging included.
- Documentation updated.
- Migration included if needed.
- Product Owner acceptance criteria met.
- No prohibited automation introduced.

## 20. Final Product Definition of Done

The project is complete when all of the following are true.

### Core Application

- Launches easily on macOS.
- Works without normal terminal use.
- SQLite data persists.
- Migrations and backups are reliable.
- UI supports daily workflow.

### Google Sheets

- Automatic push works.
- Automatic pull works.
- Conflicts are field-level and manually resolvable.
- Offline retry works.
- No duplicate rows.

### Extraction and Generation

- Extraction has measurable evaluation.
- Prompt/model versions are tracked.
- English and French supported.
- Generated content uses verified facts.
- User can edit all outputs.

### Job Intelligence

- Hard gates work.
- Soft warnings work.
- Fit score is explainable.
- CV recommendation is separate.
- Manual override works.

### Browser Extension

- Captures visible jobs.
- Creates records.
- Detects fields.
- Fills reviewed values.
- Assists CV upload.
- Never submits.
- Marks Applied only after confirmation.

### Search

- Manual searches work.
- Scheduled searches work.
- Results enter review queue.
- Approved sources are supported.
- Provenance and deduplication work.

### Lifecycle

- Applications can be tracked through offer/rejection.
- Follow-ups work.
- Analytics work.
- Interview preparation is available.

### Security and Reliability

- Local API is protected.
- Credentials are not committed.
- TLS verification is enabled.
- Repository is private.
- Backup and restore work.
- Failures do not cause data loss.
