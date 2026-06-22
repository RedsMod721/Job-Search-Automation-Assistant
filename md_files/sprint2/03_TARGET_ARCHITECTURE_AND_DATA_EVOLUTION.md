# Target Architecture and Data Evolution

## 1. Purpose

This document defines the target technical architecture required to support:

- Streamlit user interface.
- Local FastAPI service.
- Background workers.
- Automatic bidirectional Google Sheets synchronization.
- Chrome extension.
- Manual and scheduled job search.
- Local Ollama models.
- Reliable SQLite persistence.
- Future analytics and interview workflows.

## 2. Architecture Principles

1. Local-first.
2. SQLite remains the authoritative operational database.
3. Google Sheets is a synchronized editable view.
4. Business logic is independent of Streamlit.
5. Chrome extension communicates only with a localhost API.
6. Scheduled tasks run through a local background service.
7. External data always keeps provenance.
8. Generated content always keeps version and source context.
9. No paid service is required.
10. Final application submission remains manual.

## 3. Target Component Diagram

```text
Chrome Extension
       │
       │ localhost authenticated API
       ▼
FastAPI Local Service
       │
       ├───────────────┐
       │               │
       ▼               ▼
Application Services   Background Workers
       │               ├── Google Sheets sync worker
       │               ├── Search scheduler
       │               ├── Search connectors
       │               └── Retry/outbox worker
       │
       ├── Extraction service ──► Ollama
       ├── Fit scoring service
       ├── CV recommendation service
       ├── Generation service
       ├── Company/job discovery service
       └── Contact/salary services
       │
       ▼
Repository Layer
       │
       ▼
SQLite Database
       │
       ├── Applications
       ├── Companies
       ├── Contacts
       ├── Jobs
       ├── Search profiles
       ├── Review queue
       ├── Sync metadata
       ├── Conflicts
       ├── Prompt evaluations
       ├── Generated content
       └── Audit events

Streamlit UI
       │
       └──────── uses the same service layer / local API

Google Sheets
       ▲
       └──────── automatic bidirectional sync
```

## 4. Target Repository Structure

```text
job-search-automation-assistant/
├── app.py
├── pyproject.toml
├── uv.lock or equivalent lock file
├── README.md
├── .env.example
├── .gitignore
│
├── pages/
│   ├── dashboard.py
│   ├── add_job.py
│   ├── tracker.py
│   ├── application_detail.py
│   ├── review_queue.py
│   ├── cv_matcher.py
│   ├── motivation_letter.py
│   ├── form_helper.py
│   ├── company_search.py
│   ├── sync_issues.py
│   └── settings.py
│
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── auth.py
│   │   └── routes/
│   ├── domain/
│   │   ├── application.py
│   │   ├── company.py
│   │   ├── contact.py
│   │   ├── job.py
│   │   ├── search_profile.py
│   │   ├── sync.py
│   │   └── generated_content.py
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── integrations/
│   │   ├── ollama/
│   │   ├── google_sheets/
│   │   ├── job_sources/
│   │   └── salary_sources/
│   ├── prompts/
│   ├── workers/
│   ├── migrations/
│   └── utils/
│
├── extension/
│   ├── manifest.json
│   ├── service_worker/
│   ├── content_scripts/
│   ├── adapters/
│   ├── ui/
│   └── tests/
│
├── config/
│   ├── profile.example.yaml
│   ├── profile.local.yaml
│   ├── documents.yaml
│   ├── settings.yaml
│   ├── form_answers.yaml
│   └── search_profiles/
│
├── documents/
├── generated/
├── exports/
├── database/
├── logs/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── fixtures/
└── scripts/
```

## 5. Runtime Processes

### 5.1 UI Process

Streamlit provides the interactive dashboard.

It must not own critical background work.

### 5.2 Local API Process

FastAPI must:

- Bind to `127.0.0.1`.
- Require a local token.
- Expose health.
- Serve the Chrome extension.
- Reuse the same services as Streamlit.
- Never bind publicly by default.

### 5.3 Worker Process

The worker must:

- Process sync queue.
- Poll Google Sheets.
- Run scheduled searches.
- Process retries.
- Record audit events.
- Continue running when Streamlit is closed.

### 5.4 Ollama Process

Ollama remains a separate local dependency.

The app must detect:

- Service unavailable.
- Model unavailable.
- Model loading.
- Timeout.
- Invalid structured output.

## 6. Domain Models

All domain models should use typed Pydantic models or equivalent.

### 6.1 Application

Must include:

- Identity.
- Company reference.
- Job reference.
- Source.
- Tracker status.
- Application timestamps.
- Selected CV.
- Generated asset references.
- Contact reference.
- Follow-up data.
- Sync metadata.
- Archive state.

### 6.2 Job

A dedicated normalized Job model is required before full discovery.

Suggested fields:

```text
job_id
external_job_id
source_name
source_url
canonical_url
company_id
title
normalized_title
role_family
description
responsibilities
required_skills
preferred_skills
required_languages
seniority
years_experience_min
years_experience_max
contract_type
employment_type
location_text
country
city
remote_policy
salary_min
salary_max
salary_currency
salary_period
salary_basis
published_at
expires_at
collected_at
content_hash
raw_payload
```

### 6.3 Search Profile

Suggested fields:

```text
search_profile_id
name
enabled
role_families
keywords
excluded_keywords
countries
cities
remote_preferences
contract_types
seniority_preferences
language_rules
authorization_rules
salary_rules
hard_gates
soft_warnings
sources
schedule
last_run_at
```

### 6.4 Review Queue Item

Suggested fields:

```text
queue_item_id
job_id
search_profile_id
fit_score
decision
hard_gate_failures
warnings
strengths
state
first_seen_at
last_seen_at
dismissal_reason
saved_application_id
```

## 7. Database Evolution

### 7.1 Migration System

Use a migration framework appropriate for SQLite.

Each migration must:

- Have a unique ordered identifier.
- Record applied state.
- Be idempotent where practical.
- Back up the database before execution.
- Fail safely.
- Be covered by migration tests.

### 7.2 New Tables

Recommended future tables:

```text
schema_migrations
audit_events
jobs
search_profiles
search_runs
review_queue
sync_outbox
sync_state
sync_conflicts
generated_content_versions
prompt_versions
extraction_evaluations
user_corrections
profile_facts
experience_evidence
scheduler_jobs
source_rate_limits
```

### 7.3 Audit Events

Record important actions:

- Application created.
- Application updated.
- Status changed.
- Record archived.
- CV recommendation generated.
- CV overridden.
- Letter generated.
- Form answers generated.
- Sync push.
- Sync pull.
- Conflict created.
- Conflict resolved.
- Search run completed.
- Review item dismissed.
- Application marked applied.

Audit records should include:

```text
event_id
entity_type
entity_id
event_type
source
timestamp
before_snapshot
after_snapshot
metadata
```

## 8. Deduplication

### 8.1 Job Deduplication

Priority keys:

1. Source + external job ID.
2. Canonical URL.
3. Company domain + normalized title + normalized location.
4. Description content hash.

A duplicate match should retain all source URLs where useful.

### 8.2 Company Deduplication

Priority keys:

1. Normalized website domain.
2. Verified external identifier.
3. Normalized legal/common name + country.

### 8.3 Contact Deduplication

Priority keys:

1. Normalized email.
2. Canonical LinkedIn URL.
3. Company + normalized full name + normalized role.

## 9. Configuration

### 9.1 Public Example Configuration

Committed:

```text
config/profile.example.yaml
config/settings.example.yaml
```

### 9.2 Local Configuration

Ignored:

```text
config/profile.local.yaml
config/settings.local.yaml
config/google_service_account.json
config/local_api_token
```

### 9.3 Configuration Precedence

Recommended order:

1. Environment variables.
2. Local YAML.
3. Base YAML.
4. Application defaults.

## 10. Network Configuration

Required settings:

```yaml
network:
  verify_tls: true
  custom_ca_bundle: ""
  http_proxy: ""
  https_proxy: ""
  request_timeout_seconds: 30
```

Rules:

- TLS verification enabled by default.
- Custom CA must be explicit.
- No global warning suppression.
- Network failures must state whether the likely cause is DNS, proxy, certificate, permission, or remote service.

## 11. Background Service on macOS

Use a macOS LaunchAgent or equivalent user-level service.

It should start:

- FastAPI local service.
- Worker process.

It should not require administrator privileges for normal installation.

Requirements:

- Start on login option.
- Restart on failure.
- Write logs to user application-data directory.
- Clean shutdown.
- Status command.
- Uninstall command.

## 12. Windows Compatibility

Windows remains secondary.

Provide:

- PowerShell startup script.
- Optional Task Scheduler instructions.
- Custom CA support.
- Proxy support.
- No assumption that work-network access will always succeed.

## 13. Local File Paths

Do not hardcode repository-relative paths as the only storage option.

Use a user data directory.

Recommended concept:

```text
macOS:
~/Library/Application Support/JobSearchAssistant/

Windows:
%APPDATA%\JobSearchAssistant\
```

Store:

- Database.
- Logs.
- Generated content.
- Backups.
- Local tokens.
- Scheduler state.

CV files may remain in a configured documents directory.

## 14. Data Backup

Required backup types:

- Automatic backup before migration.
- Scheduled local backup.
- Manual backup.
- Export backup.

Backups should include:

- SQLite database.
- Config.
- Generated content metadata.
- Search profiles.

Google Sheets is not a complete backup because it does not contain all local state.

## 15. API Versioning

Use versioned routes:

```text
/api/v1/...
```

Breaking changes require a new version or a migration strategy.

## 16. Observability

Required logs and metrics:

- Service startup.
- Worker startup.
- Ollama health.
- Sheets health.
- Search connector health.
- Queue size.
- Sync failures.
- Search failures.
- Extraction latency.
- Model name.
- Prompt version.
- Extension connection.
- API authentication failures.

Never log:

- Google credentials.
- API tokens.
- Full sensitive form values unless explicitly necessary.
