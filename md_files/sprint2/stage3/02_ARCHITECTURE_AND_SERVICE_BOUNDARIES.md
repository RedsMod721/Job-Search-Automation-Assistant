# Stage 3 Architecture and Service Boundaries

Date: 2026-06-17

## New Structure

```text
src/
  domain/
    application.py
    sync.py
  prompts/
    registry.py
  repositories/
    applications.py
    companies.py
  services/
    application_service.py
    extraction_service.py
    sync_service.py
    exceptions.py
    results.py
  ui/
    page_runner.py
pages/
  01_dashboard.py
  02_add_job.py
  03_tracker.py
  04_cv_matcher.py
  05_motivation_letter.py
  06_form_helper.py
  07_company_search.py
  08_settings.py
```

## Domain Layer

`src/domain/application.py` provides typed views for application and company payloads while preserving legacy extra fields.

`src/domain/sync.py` provides typed Google Sheets sync results and sync-mode summaries.

## Repository Layer

`ApplicationRepository` wraps current SQLite application operations:

- initialize database
- add application
- update application
- get application
- list applications
- archive application
- delete application

`CompanyRepository` wraps company upsert.

The repositories currently delegate to `src.database`, which is intentional. Stage 4 can add migrations, backups, deduplication, and audit events behind these adapters without forcing the UI to know those details.

## Service Layer

`application_service` contains business logic formerly embedded in `app.py`:

- extraction review list parsing
- motivation-letter-required coercion
- reviewed extraction to application payload
- company search request construction
- company search result merge
- tracker filtering
- display label construction
- company-search result to application payload
- review refresh state helpers

`extraction_service` owns extraction orchestration from settings to extractor call.

`sync_service` owns manual sync orchestration and explicit Stage 3 sync-mode status.

## UI Boundary

The main tabbed Streamlit app remains in `app.py`.

Separate page entrypoints exist under `pages/` and call the same renderers. This avoids duplicate UI implementations while enabling page-level Streamlit entrypoints for future decomposition.

## Streamlit Import Rule

Business services do not import Streamlit. This is covered by `test_business_services_do_not_import_streamlit`.

Streamlit imports remain in:

- `app.py`
- `src/ui/page_runner.py`
- top-level `pages/` entrypoints through the renderer imports

## Prompt Registry

`src/prompts/registry.py` records prompt IDs and versions for:

- `job_extraction`
- `motivation_letter`
- `form_answers`

The prompt body text still lives in the current generator modules. The registry is now the canonical place to track prompt identity and version before deeper prompt extraction.

