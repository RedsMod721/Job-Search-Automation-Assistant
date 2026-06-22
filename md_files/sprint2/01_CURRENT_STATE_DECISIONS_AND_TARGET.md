# Current State, Confirmed Decisions, and Target Product

## 1. Purpose

This document provides the development team with:

- A reliable summary of the Sprint 1 baseline.
- The confirmed Product Owner decisions.
- The known gaps between the existing MVP and the finished product.
- The target behavior of the final application.
- The constraints that apply to all later implementation work.

## 2. Sprint 1 Baseline

Sprint 1 delivered a substantial local MVP using Streamlit, Python, SQLite, YAML configuration, local file storage, Ollama integration, Excel export, optional Google Sheets synchronization, and a modular `src/` directory.

The current repository includes the following functional areas:

1. Dashboard.
2. Add Job.
3. Application Tracker.
4. CV Matcher.
5. Motivation Letter generator.
6. Form Helper.
7. Company Search.
8. Settings.

The database currently includes tables for:

- Applications.
- Companies.
- Contacts.
- Documents.

The source layer currently includes modules for:

- Constants and configuration.
- Database operations.
- Job extraction.
- CV matching.
- Motivation-letter generation.
- Form-answer generation.
- Excel export.
- Google Sheets synchronization.
- Company search.
- Shared utilities.

The current app has been used by the Product Owner with real job posts copied from LinkedIn.

Verified by user testing:

- The app launches.
- Job extraction returns results.
- Application storage works.
- CV recommendation returns an output.
- Motivation-letter generation returns an output.
- The UI is usable as a first draft.
- No visible blocking errors remained at the end of Sprint 1.

Not yet validated by the Product Owner:

- Real Google Sheets synchronization.
- Automatic bidirectional synchronization.
- Chrome extension.
- Scheduled search.
- End-to-end macOS packaging.
- Advanced company and job discovery.

## 3. Current Capabilities That Must Be Preserved

All future refactoring must preserve these existing capabilities unless a replacement is explicitly approved:

- Manual application creation.
- Raw job-post text entry.
- Editable extraction review before saving.
- SQLite persistence.
- Application filtering and status updates.
- Archive and confirmed deletion workflows.
- Deterministic CV matching.
- Manual CV override.
- English and French motivation-letter generation.
- Form-answer generation.
- Excel export.
- Configurable Ollama model.
- Optional Google Sheets connection.
- Basic public company lookup/enrichment.
- Existing unit tests.

## 4. Known Current Gaps

### 4.1 Job Extraction Quality

The extraction is acceptable for an initial version but sometimes misses information.

Required future work:

- Build a labeled evaluation dataset.
- Track prompt and model versions.
- Measure field-level accuracy.
- Run prompt A/B tests.
- Add validation and optional second-pass correction.
- Record user corrections to improve future versions.

### 4.2 URL-Based Job Capture

The current workflow is primarily text-based.

A stored URL is not equivalent to URL-based extraction.

Future work must distinguish:

1. Saving a URL.
2. Fetching a public page.
3. Extracting the visible job description.
4. Capturing authenticated pages through the browser extension.

LinkedIn must be handled through current-page browser-extension capture, not server-side mass scraping.

### 4.3 Google Sheets

The current implementation must be treated as an initial synchronization/export feature, not the final bidirectional sync engine.

The finished product requires:

- Automatic push after every local change.
- Automatic pull of changes made in Google Sheets.
- Field-level conflict detection.
- Offline retry.
- Sync queue.
- Conflict-resolution interface.
- No silent data loss.

### 4.4 Company Search

The current Company Search is a useful early feature, but it is not yet the complete discovery pipeline.

The finished system must separate:

- Company discovery.
- Company enrichment.
- Career-page discovery.
- Job collection.
- Job normalization.
- Job deduplication.
- Job fit scoring.
- Review queue.

### 4.5 CV Matching

The current keyword matcher must be retained as a deterministic baseline but improved.

Future behavior must:

- Distinguish CV recommendation from job-fit scoring.
- Support normalized synonyms.
- Avoid defaulting to a CV when evidence is insufficient.
- Explain matches.
- Allow manual override.
- Track outcomes for future analytics.

### 4.6 Application Structure

The current Streamlit application is a functional first draft but should be refactored before major new features.

Business logic must become independent of Streamlit so that:

- Unit tests can run without the UI.
- A local FastAPI service can reuse the same workflows.
- The Chrome extension can call the local service.
- Scheduled tasks can run while Streamlit is closed.

### 4.7 Database Evolution

The current database creation logic requires a migration system before schema growth.

The final application needs:

- Schema versioning.
- Reversible migrations where practical.
- Backup before migration.
- Data integrity checks.
- Duplicate detection.
- Recovery procedures.

### 4.8 Network Security

TLS verification must be enabled by default.

The app must support restricted corporate networks through:

- Custom CA bundle.
- Explicit proxy configuration.
- Clear diagnostics.

Global TLS verification disabling is not acceptable as a production default.

## 5. Confirmed Final Product Decisions

### 5.1 Product Type

The final product is:

- Local.
- Single-user.
- Personal.
- Not a public SaaS.
- Not a hosted multi-user app.
- Not an auto-apply bot.

### 5.2 Main Runtime Environment

Primary environment:

```text
MacBook Pro
Apple M3 Pro
36 GB RAM
Latest macOS
```

Secondary development environment:

```text
Windows work computer
Possible corporate TLS interception and network restrictions
```

### 5.3 Repository Visibility

- Public during current development.
- Changed to private later.
- Credentials must never be committed.
- Personal profile data may remain temporarily by Product Owner choice.
- Example/local config separation should still be implemented before final release.

### 5.4 Google Sheets

Required final behavior:

- Automatic push after local changes.
- Automatic pull of Google Sheets changes.
- SQLite remains the authoritative local database.
- Google Sheets remains an editable synchronized view.
- Non-overlapping field edits may merge automatically.
- Conflicting edits to the same field require manual resolution.
- Sync failures must queue and retry.

### 5.5 Browser Extension

Required capabilities:

- Capture current job URL.
- Capture visible job description.
- Create an application record.
- Detect text inputs and text areas.
- Fill personal information.
- Generate and fill long-form answers.
- Detect select menus, radio buttons, and checkboxes.
- Choose the recommended CV.
- Assist with CV upload when technically possible.
- Detect likely successful submission.
- Ask the user to confirm success.
- Mark the application as Applied after confirmation.

Prohibited:

- Final submission click.
- Background mass collection.
- Mass LinkedIn scraping.
- Automated recruiter messaging.
- CAPTCHA bypass.
- Hidden application actions.

### 5.6 Job Discovery

Required modes:

- Manual/on-demand search.
- Scheduled search.

Scheduled results must enter a review queue.

They must not automatically become main tracker applications.

Confirmed source priority:

1. Official company career pages.
2. Greenhouse public job boards.
3. Lever public postings.
4. Ashby public job boards.
5. SmartRecruiters public postings.
6. Workday public pages where accessible.
7. Welcome to the Jungle.
8. Indeed or Google Jobs only through compliant methods.
9. LinkedIn through manual current-page extension capture.

### 5.7 Data Source Cost

Use only:

- Free sources.
- Open sources.
- Publicly accessible sources.
- Public APIs where permitted.

Do not assume paid APIs.

### 5.8 Job Filtering

The system must support:

- Hard gates.
- Soft warnings.
- Explainable fit score.
- Human-readable strengths and gaps.
- Manual override.

The system must never silently reject a job without exposing the reason.

## 6. User Profile Rules Relevant to Product Behavior

### Location

Preferred answer:

```text
Open to relocation
```

Use current location only when required:

```text
Grenoble, France
```

### Availability

```text
Available immediately
```

### Work Authorization

```text
European passport holder through Italian citizenship.
Open to visa processes for strong international opportunities.
```

### Salary

Default behavior:

- Remain flexible.
- Do not automatically expose the private baseline.
- Use market-based phrasing unless an exact number is mandatory.
- Future salary research must use cited free/public sources.

### Contract Type

Preferred:

- Permanent.
- CDI.

Open to:

- Temporary.
- CDD.
- ESN.
- Consulting company.

Not targeted by default:

- Internship.

### Role Order When a Default Is Needed

1. AI Consultant / AI Product.
2. Data Analyst / Business Analyst.
3. Junior Consultant / Strategy Analyst.
4. Marketing Analyst.

The user must still be able to select any search target manually.

## 7. Final Product User Journey

The finished product should support this complete sequence:

```text
Create or select a search profile
    ↓
Run manual or scheduled searches
    ↓
Review discovered jobs
    ↓
Apply hard gates, warnings, and fit score
    ↓
Save selected job to tracker
    ↓
Capture additional job data through browser extension if needed
    ↓
Review extraction
    ↓
Select recommended CV
    ↓
Generate letter or form answers
    ↓
Assist application form completion
    ↓
User performs final submit click
    ↓
Confirm successful submission
    ↓
Mark application Applied
    ↓
Synchronize automatically with Google Sheets
    ↓
Track follow-up, interview, rejection, or offer
    ↓
Analyze outcomes
```

## 8. Non-Negotiable Product Constraints

- Final submission remains manual.
- Local data must not be lost when offline.
- Sync conflicts must not be silently overwritten.
- Missing job facts must not be invented.
- Every search result must keep provenance.
- Every salary benchmark must keep provenance.
- Every public contact must keep provenance.
- Generated content must remain editable.
- Personal credentials must remain outside Git.
- Browser permissions must be minimized.
- The app must remain usable without paid services.
