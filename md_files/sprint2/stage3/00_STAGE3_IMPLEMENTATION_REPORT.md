# Stage 3 Implementation Report

Date: 2026-06-17

## Objective

Stage 3 refactored the MVP into clearer boundaries before database migration work begins in Stage 4. The goal was to keep current user behavior available while making core workflows callable and testable outside Streamlit.

## Implementation Plan

1. Re-read Sprint 2 documentation, with special focus on Google Sheets manual sync, timed sync, and startup sync.
2. Keep timed/startup/change-triggered Google Sheets sync out of Stage 3 because the roadmap assigns it to Stage 5.
3. Add domain models, repositories, services, and a prompt registry.
4. Route the existing Streamlit app through those boundaries without changing database schema or public config defaults.
5. Add Stage 3 tests for service boundaries, repositories, prompt registry, manual sync, and automatic sync mode guardrails.
6. Run the full local validation suite and document remaining frictions.

## Implemented Changes

- Added domain models:
  - `src/domain/application.py`
  - `src/domain/sync.py`
- Added repository adapters:
  - `src/repositories/applications.py`
  - `src/repositories/companies.py`
- Added service modules:
  - `src/services/application_service.py`
  - `src/services/extraction_service.py`
  - `src/services/sync_service.py`
  - `src/services/exceptions.py`
  - `src/services/results.py`
- Added prompt registry:
  - `src/prompts/registry.py`
- Added Streamlit page entrypoints:
  - `pages/01_dashboard.py`
  - `pages/02_add_job.py`
  - `pages/03_tracker.py`
  - `pages/04_cv_matcher.py`
  - `pages/05_motivation_letter.py`
  - `pages/06_form_helper.py`
  - `pages/07_company_search.py`
  - `pages/08_settings.py`
- Updated `app.py` to use repository and service boundaries for application writes, extraction orchestration, manual Google Sheets sync, and settings diagnostics.
- Added tests in `tests/test_stage3_boundaries.py`.
- Expanded import coverage in `tests/test_config_loading.py`.

## Google Sheets Decision

Manual sync remains the only active sync path in Stage 3.

The docs mention timed sync and startup sync as future work, but the Sprint 2 roadmap places those items in Stage 5. Stage 3 therefore adds the `sync_service` boundary and explicit sync-mode reporting while keeping automatic modes disabled:

- Manual sync: available.
- Startup sync: disabled.
- Timer sync: disabled.
- Change-triggered sync: disabled.
- Stage 5 required for automatic sync: true.

## Acceptance Status

- Core application payload builders and filters are in `src/services/application_service.py` and tested without Streamlit.
- Manual Google Sheets sync now goes through `src/services/sync_service.py`.
- Business services do not import Streamlit.
- Application persistence is available behind `ApplicationRepository`.
- Existing UI behavior remains available through the tabbed app.
- Separate Streamlit page entrypoints exist and reuse the existing renderers.
- All local Windows validation gates passed.

## Not Changed

- No database schema change.
- No automatic Google Sheets startup sync.
- No timed Google Sheets sync.
- No change-triggered Google Sheets sync after create/update/delete.
- No Google credentials committed.
- No product behavior intentionally removed.

