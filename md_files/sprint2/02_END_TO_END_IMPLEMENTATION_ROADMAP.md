# End-to-End Implementation Roadmap

## 1. Purpose

This document defines the mandatory implementation order from the current Sprint 1 MVP to the finished product.

The roadmap uses ordered stages rather than dates. Each stage has:

- Objective.
- Required work.
- Deliverables.
- Dependencies.
- Acceptance gate.

A later stage must not be considered complete while its dependencies remain incomplete.

## 2. Roadmap Summary

```text
Stage 1  Baseline validation
Stage 2  Repository and environment stabilization
Stage 3  Core application refactor
Stage 4  Database migrations, backups, and deduplication
Stage 5  Automatic bidirectional Google Sheets synchronization
Stage 6  Extraction evaluation and prompt/model improvement
Stage 7  Job-fit scoring and improved CV selection
Stage 8  Verified profile knowledge base and content generation
Stage 9  UI refinement and local product packaging
Stage 10 Local API and background worker
Stage 11 Chrome extension job capture
Stage 12 Chrome extension form assistance
Stage 13 Real company and job discovery
Stage 14 Manual and scheduled search workflows
Stage 15 Public contact discovery and outreach assistance
Stage 16 Salary research using free/public sources
Stage 17 Analytics, follow-ups, and interview preparation
Stage 18 Final hardening and release
```

## 3. Stage 1 - Freeze and Validate the Sprint 1 Baseline

### Objective

Create a reproducible baseline before modifying architecture.

### Required Work

- Create a Git tag for the current working MVP.
- Record the current database schema.
- Run the complete test suite on macOS.
- Run the complete test suite on Windows where possible.
- Record pass/fail results.
- Add the four real CV files locally.
- Add English and French motivation-letter templates locally.
- Validate Ollama installation on the Mac.
- Test current extraction with real English and French job posts.
- Test current motivation-letter generation.
- Test current form-answer generation.
- Test Excel export.
- Configure and test current Google Sheets sync once.
- Record all setup problems and user-facing friction.
- Create a baseline backup of the SQLite database.
- Create a list of current UI workflows and expected behavior.

### Deliverables

- Baseline release tag.
- Baseline validation report.
- Test result report.
- Current schema snapshot.
- Known bug list.
- Real-world sample dataset.
- Verified local setup instructions.

### Acceptance Gate

- App starts reliably on the primary Mac.
- Current tests pass or failures are documented.
- Real CV and template paths work.
- At least one Google Sheets connection test succeeds or a specific blocking cause is documented.
- Database backup exists.
- Current behavior is reproducible.

## 4. Stage 2 - Repository and Environment Stabilization

### Objective

Make development, installation, and testing repeatable.

### Required Work

- Declare supported Python version or range.
- Add a dependency lock strategy.
- Separate runtime and development dependencies.
- Add formatter configuration.
- Add linter configuration.
- Add type-checking configuration.
- Add security scanning.
- Add GitHub Actions CI.
- Run tests on supported Python versions.
- Include macOS and Windows runners where practical.
- Add a diagnostic command or UI panel.
- Add a network diagnostics section.
- Add custom CA and proxy configuration.
- Remove global TLS verification disabling.
- Improve `.gitignore`.
- Add `profile.example.yaml`.
- Add local profile override support.
- Keep current personal profile behavior working during transition.
- Add pre-commit hooks if accepted by the team.

### Recommended Tooling

The team may use equivalent tools, but the implementation must cover these categories:

- Formatting: Ruff formatter or Black.
- Linting: Ruff.
- Type checks: mypy or Pyright.
- Tests: pytest.
- Security: Bandit and dependency audit.
- CI: GitHub Actions.
- Locking: `uv.lock`, Poetry lock, or a pinned requirements solution.

### Deliverables

- Reproducible environment.
- CI workflow.
- Network configuration.
- Health diagnostic.
- Example/local config convention.
- Updated installation documentation.

### Acceptance Gate

- Clean clone installs without undocumented steps.
- CI passes.
- TLS verification is enabled by default.
- App explains missing Ollama, model, credentials, or network access.
- Secrets and credentials are ignored.
- The repository can later be made private without configuration redesign.

## 5. Stage 3 - Refactor the Core Application

### Objective

Separate UI from domain logic before adding the extension and scheduler.

### Required Work

- Split Streamlit pages into separate modules.
- Create explicit domain models.
- Introduce service layer.
- Introduce repository layer.
- Move prompts into versioned prompt files or registry.
- Standardize exceptions.
- Standardize result objects.
- Standardize logging context.
- Remove duplicated serialization logic.
- Make workflows callable without Streamlit.
- Preserve current features and behavior.
- Expand tests around refactored services.

### Target Layout

```text
app.py
pages/
src/
  domain/
  schemas/
  repositories/
  services/
  integrations/
  prompts/
  workers/
  api/
tests/
  unit/
  integration/
  contract/
```

### Deliverables

- Modular UI.
- Domain models.
- Service interfaces.
- Repository interfaces.
- Prompt registry.
- Updated tests.

### Acceptance Gate

- Core workflows run in tests without Streamlit.
- Existing UI behavior remains available.
- No business service imports Streamlit.
- All existing tests pass.
- New tests cover the service boundary.

## 6. Stage 4 - Database Migrations, Backups, and Deduplication

### Objective

Allow safe schema growth and prevent duplicate records.

### Required Work

- Add schema version table.
- Add migration runner.
- Add automatic backup before migration.
- Add manual backup and restore UI.
- Add integrity check.
- Add application duplicate detection.
- Add company duplicate detection.
- Add contact duplicate detection.
- Add canonical URL normalization.
- Add normalized company names.
- Add external job ID support.
- Add job-description content hash.
- Add soft-delete/tombstone rules.
- Add audit-event table.
- Add data export suitable for recovery.

### Deliverables

- Migration framework.
- Backup/restore.
- Deduplication service.
- Audit table.
- Recovery documentation.

### Acceptance Gate

- Existing user database upgrades without deletion.
- Duplicate test cases are detected.
- Backup restores successfully.
- Failed migration rolls back or restores safely.
- Audit records identify important changes.

## 7. Stage 5 - Automatic Google Sheets Push Synchronization

### Objective

Implement reliable local-to-Google-Sheets synchronization without depending on a paid Google Cloud workflow.

### Required Work

- Implement the architecture in `04_GOOGLE_SHEETS_TWO_WAY_SYNC_SPEC.md`.
- Keep the manual sync button.
- Add automatic sync on application startup.
- Add automatic sync after application create, update, and delete operations.
- Add a configurable timer-based sync, defaulting to every minute.
- Add row mapping.
- Add local change tracking.
- Add retry with backoff.
- Add offline queue.
- Add manual force sync.
- Add sync status indicators.
- Add live integration tests with a test spreadsheet.
- Add data type normalization.

### Deliverables

- Automatic local push.
- Manual sync button.
- Startup sync.
- Timer-based sync.
- Offline recovery.
- Sync audit log.

### Acceptance Gate

- Local edits appear in Sheets automatically.
- App startup triggers a sync pass.
- Timer-based sync keeps the sheet refreshed.
- Offline edits sync after reconnection.
- No duplicate Sheet rows are created.

## 8. Stage 6 - Extraction Evaluation and Prompt/Model Improvement

### Objective

Improve extraction quality using measurable evaluation.

### Required Work

- Build labeled job-post dataset.
- Include all target role families.
- Include English and French.
- Include multiple ATS sources.
- Store expected extraction JSON.
- Version prompts.
- Version model configuration.
- Record actual outputs.
- Calculate field-level metrics.
- Record user corrections.
- Add rule-based validators.
- Add optional second-pass correction.
- Benchmark local models on the M3 Pro.
- Compare quality, latency, memory, and JSON reliability.
- Add prompt A/B testing workflow.
- Add regression tests for known extraction failures.

### Deliverables

- Evaluation dataset.
- Prompt registry.
- Benchmark report.
- Improved extraction pipeline.
- Extraction quality dashboard or report.

### Acceptance Gate

- Extraction quality is measured, not estimated.
- Prompt/model changes cannot merge without regression evaluation.
- Hallucinated salary/company-size values are minimized.
- User correction rate decreases.
- A default model is chosen based on evidence.

## 9. Stage 7 - Job-Fit Scoring and Improved CV Selection

### Objective

Create explainable suitability evaluation while improving CV choice.

### Required Work

- Create job-fit rule model.
- Create search-profile rule model.
- Implement hard gates.
- Implement soft warnings.
- Implement score breakdown.
- Separate job fit from CV recommendation.
- Add normalized skill taxonomy.
- Add role-family taxonomy.
- Add language matching.
- Add location/relocation matching.
- Add work-authorization matching.
- Add contract matching.
- Add experience-gap warning.
- Add minimum-confidence behavior for CV selection.
- Add manual override.
- Store recommendation version and explanation.

### Deliverables

- Job-fit engine.
- CV recommendation engine v2.
- Explainable output.
- Configurable rules.

### Acceptance Gate

- Hard gates, warnings, and scores are visible.
- No job is silently rejected.
- CV recommendation can return insufficient confidence.
- Manual override is preserved.
- Test cases cover each rule category.

## 10. Stage 8 - Verified Profile Knowledge Base and Generation Quality

### Objective

Generate letters and answers only from verified facts.

### Required Work

- Create structured profile-fact store.
- Create experience records.
- Create project records.
- Create achievement records.
- Create skill evidence.
- Create STAR examples.
- Create personal anecdotes.
- Create English and French reusable answers.
- Add short, medium, and long variants.
- Add source and verification status.
- Add content approval.
- Add content versioning.
- Add deprecation.
- Improve motivation-letter prompts.
- Add form-answer quality checks.
- Prevent unsupported claims.

### Deliverables

- Verified knowledge base.
- Reusable answer library.
- Versioned generated content.
- Quality rules.

### Acceptance Gate

- Generated outputs use verified facts only.
- User can approve and edit reusable content.
- English and French generation work.
- Previous versions remain accessible.
- Unsupported claims trigger warnings.

## 11. Stage 9 - UI Refinement and Local Product Packaging

### Objective

Make the application efficient for daily use.

### Required Work

- Redesign navigation.
- Add application detail page.
- Add Kanban or pipeline view.
- Add saved filters.
- Add review queue page.
- Add extraction confidence display.
- Add job-fit warnings.
- Add sync status.
- Add duplicate warnings.
- Add loading and error states.
- Add quick-copy controls.
- Add keyboard-friendly actions.
- Add local health-check page.
- Add macOS launcher.
- Add optional start-on-login.
- Add clean shutdown.
- Add automatic local backup.
- Add Windows launch instructions.

### Deliverables

- Improved UI.
- macOS launcher.
- Health screen.
- Daily-use workflow.

### Acceptance Gate

- User does not need a terminal for normal use.
- Main workflows are clear and efficient.
- Sync and service health are visible.
- Errors provide recovery actions.
- Mac launch and shutdown are tested.

## 12. Stage 10 - Local API and Background Worker

### Objective

Provide a stable local integration layer for the extension, sync, and scheduler.

### Required Work

- Add FastAPI local service.
- Bind to localhost only.
- Add local API token.
- Add extension origin allowlist.
- Add health endpoint.
- Add application endpoints.
- Add extraction endpoint.
- Add form-answer endpoint.
- Add mark-applied endpoint.
- Add sync endpoint.
- Add scheduler worker.
- Add sync worker.
- Add event/outbox mechanism.
- Add macOS LaunchAgent.
- Add service status UI.
- Ensure Streamlit can be closed while workers continue.

### Deliverables

- Local API.
- Background worker.
- Service launcher.
- API documentation.

### Acceptance Gate

- API is not externally exposed.
- Extension can authenticate locally.
- Scheduled tasks run while Streamlit is closed.
- Health endpoint reports all dependencies.
- Service restarts safely.

## 13. Stage 11 - Chrome Extension Job Capture

### Objective

Capture visible job information without copy/paste.

### Required Work

- Build Manifest V3 extension.
- Add popup or side panel.
- Use minimal permissions.
- Capture active URL.
- Capture visible job title/company/description.
- Add site adapters.
- Add generic fallback.
- Show capture preview.
- Send to local API.
- Create application or review draft.
- Show CV recommendation.
- Open local application detail.
- Support LinkedIn current-page capture only.

### Deliverables

- Extension package.
- Job capture workflow.
- Site adapters.
- Permission documentation.

### Acceptance Gate

- LinkedIn current-page job capture works manually.
- At least two public ATS adapters work.
- User sees captured content before save.
- No background crawling exists.
- Extension permissions are minimal.

## 14. Stage 12 - Chrome Extension Form Assistance

### Objective

Assist form filling while preserving manual submission.

### Required Work

- Implement field detection.
- Implement field ontology.
- Implement matching confidence.
- Handle text fields.
- Handle text areas.
- Handle selects.
- Handle radio buttons.
- Handle checkboxes.
- Handle dates.
- Handle salary and authorization fields.
- Generate long-form answers through local API.
- Display suggested value and source.
- Allow Fill, Edit, or Skip.
- Detect CV upload field.
- Show recommended CV filename.
- Assist user-controlled file selection where supported.
- Detect probable success page.
- Ask for confirmation.
- Mark Applied after confirmation.
- Never click final submit.

### Deliverables

- Form assistant.
- Platform adapters.
- Generic fallback.
- Applied confirmation flow.

### Acceptance Gate

- Fields can be reviewed before filling.
- Multiple ATS forms are supported.
- CV recommendation is shown.
- Final submission remains manual.
- Applied status changes only after confirmation.

## 15. Stage 13 - Real Company and Job Discovery

### Objective

Replace the basic search with a structured discovery pipeline.

### Required Work

- Implement connector interface.
- Implement company discovery.
- Implement company enrichment.
- Implement career-page discovery.
- Implement public job collection.
- Implement normalized job schema.
- Implement source provenance.
- Implement canonical URLs.
- Implement deduplication.
- Implement connector rate limits.
- Implement source-specific failure handling.
- Implement first connectors in approved order.

### Deliverables

- Discovery engine.
- Source connectors.
- Normalized job records.
- Provenance and deduplication.

### Acceptance Gate

- Sector/location search returns multiple real companies.
- Official career pages are verified.
- Jobs from different sources normalize consistently.
- Duplicate jobs merge.
- Source URLs are stored.

## 16. Stage 14 - Manual and Scheduled Search Workflows

### Objective

Support user-triggered and automatic searches.

### Required Work

- Add saved search profiles.
- Add hard-gate configuration.
- Add warning configuration.
- Add source selection.
- Add manual Run Now.
- Add scheduler.
- Add review queue.
- Add New, Interesting, Dismissed, Saved states.
- Remember dismissed jobs.
- Prevent repeated display of unchanged dismissed jobs.
- Add search-run history.
- Add notifications inside app.
- Add optional OS notification.

### Deliverables

- Search profiles.
- Scheduler.
- Review queue.
- Search history.

### Acceptance Gate

- Manual search works.
- Scheduled search works while background service runs.
- Results enter review queue.
- Dismissed jobs are remembered.
- Accepted jobs can move to tracker.

## 17. Stage 15 - Public Contact Discovery and Outreach Assistance

### Objective

Support responsible public contact research.

### Required Work

- Implement public contact source connectors.
- Store source provenance.
- Link contacts to companies.
- Deduplicate contacts.
- Add manual LinkedIn profile save.
- Add verification status.
- Add notes.
- Add interaction history.
- Generate outreach drafts.
- Keep sending manual.

### Deliverables

- Contact finder.
- Contact tracker.
- Outreach draft assistant.

### Acceptance Gate

- Every contact has a source.
- Private/hidden data is not collected.
- LinkedIn profiles are manually captured.
- No outreach is sent automatically.

## 18. Stage 16 - Salary Research Using Free/Public Sources

### Objective

Provide sourced salary context.

### Required Work

- Research compliant public salary sources.
- Implement source adapters only when permitted.
- Store source URL and retrieval time.
- Normalize currencies.
- Normalize annual/monthly.
- Separate gross/net.
- Normalize location and seniority.
- Display ranges.
- Compare job offer with benchmark.
- Generate flexible salary-answer suggestions.
- Never invent missing salary.

### Deliverables

- Salary benchmark records.
- Salary comparison view.
- Sourced answer assistant.

### Acceptance Gate

- Every benchmark has provenance.
- Basis is explicit.
- No restricted source is scraped improperly.
- Salary suggestions are editable.

## 19. Stage 17 - Analytics, Follow-Ups, and Interview Preparation

### Objective

Support the full application lifecycle.

### Required Work

- Funnel analytics.
- CV performance.
- Source performance.
- Role/country performance.
- Response time.
- Follow-up reminders.
- Follow-up drafts.
- Interview question generation.
- Company briefing.
- STAR story suggestions.
- Interview notes.
- Outcome tracking.
- Offer comparison.

### Deliverables

- Analytics dashboard.
- Follow-up workflow.
- Interview workspace.
- Offer comparison.

### Acceptance Gate

- Metrics are based on real data.
- Follow-ups are traceable.
- Interview content distinguishes sourced facts from generated suggestions.
- Full application lifecycle is supported.

## 20. Stage 18 - Final Hardening and Release

### Objective

Produce a reliable finished personal product.

### Required Work

- Full regression testing.
- macOS installation test.
- Windows compatibility test.
- Migration test.
- Backup/restore test.
- Sync conflict test.
- Offline recovery test.
- Extension permission review.
- Security review.
- Search-source compliance review.
- Performance test.
- Ollama failure recovery.
- Network failure recovery.
- Documentation update.
- User guide.
- Troubleshooting guide.
- Release packaging.
- Changelog.
- Repository changed to private.
- Final release tag.

### Acceptance Gate

All conditions in `07_QA_SECURITY_PACKAGING_AND_DEFINITION_OF_DONE.md` are met.
