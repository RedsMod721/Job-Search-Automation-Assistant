# Job Search Automation Assistant
# Post-Sprint 1 Developer Implementation Package

## Purpose

This documentation package defines the work required to transform the existing Sprint 1 MVP into the complete local Job Search Automation Assistant.

The documents are intentionally self-contained. The development team must not rely on undocumented assumptions, previous conversations, or verbal instructions. When a requirement is ambiguous, the rules and priorities in this package are the source of truth unless the Product Owner explicitly approves a change.

## Product Target

The final product is a local, single-user job-search application for Sebastian Vazquez.

It must:

- Run primarily on a personal MacBook Pro with an Apple M3 Pro processor, 36 GB RAM, and the latest macOS.
- Remain reasonably compatible with Windows for development and troubleshooting.
- Store authoritative data locally in SQLite.
- Synchronize application records automatically and bidirectionally with Google Sheets.
- Use local or free models and free/public data sources only.
- Provide a browser extension that captures visible job information and assists with form completion.
- Support manual and scheduled job discovery.
- Apply explainable hard gates, soft warnings, and fit scoring.
- Keep the final application submission click manual.
- Never mass scrape LinkedIn, bypass CAPTCHAs, or automate prohibited platform actions.

## Repository Visibility

The repository is public during active development for easier collaboration and will be changed to private later.

This decision does not remove the need for sound configuration and credential practices:

- Never commit Google credentials, API secrets, browser-extension tokens, or local database files.
- Prepare a future-safe separation between example configuration and local configuration.
- The current presence of personal profile information in the repository is accepted temporarily by the Product Owner.
- Moving the repository to private is a release-hardening task, not a blocker for immediate development.

## Document Reading Order

1. `01_CURRENT_STATE_DECISIONS_AND_TARGET.md`
2. `02_END_TO_END_IMPLEMENTATION_ROADMAP.md`
3. `03_TARGET_ARCHITECTURE_AND_DATA_EVOLUTION.md`
4. `04_GOOGLE_SHEETS_TWO_WAY_SYNC_SPEC.md`
5. `05_CHROME_EXTENSION_AND_LOCAL_API_SPEC.md`
6. `06_JOB_DISCOVERY_RANKING_AND_LLM_EVALUATION.md`
7. `07_QA_SECURITY_PACKAGING_AND_DEFINITION_OF_DONE.md`

## Priority Rule

The implementation order in `02_END_TO_END_IMPLEMENTATION_ROADMAP.md` is mandatory unless a dependency or verified technical constraint requires a change.

In particular:

- Do not build the full Chrome extension directly on top of the current monolithic Streamlit file.
- Do not expand scheduled searches before the local background service and data migrations exist.
- Do not implement automatic two-way Google Sheets synchronization without conflict handling.
- Do not treat the current Company Search feature as a complete company-discovery engine.
- Do not silently reject jobs or silently overwrite synchronization conflicts.
- Do not automate the final submission click.

## Product Owner Decisions Already Approved

The Product Owner has approved the following:

- Local-only, single-user final product.
- Automatic local-to-Google-Sheets push after local changes.
- Automatic Google-Sheets-to-local pull.
- Manual conflict resolution when both sides changed the same field.
- Manual and scheduled job searches.
- Scheduled search results enter a review queue instead of the main application tracker.
- Free/open/public data sources only.
- Browser extension may assist form filling and CV upload but must not submit the application.
- Mac-focused launcher and background service.
- Hard gates and soft warnings for job relevance.
- LinkedIn support through current-page/manual browser-extension capture, not mass scraping.
