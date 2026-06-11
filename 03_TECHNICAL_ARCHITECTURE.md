# 03_TECHNICAL_ARCHITECTURE.md

# Job Search Automation Assistant - Technical Architecture

## 1. Architecture Overview

The project is a local Python application with a Streamlit interface, SQLite database, local document storage, Excel export, Google Sheets sync, and local LLM capabilities through Ollama.

The architecture must be modular so that future features such as a Chrome extension, advanced company search, public contact finder, and salary benchmark module can be added without rewriting the core application.

## 2. Recommended Stack

```yaml
interface: Streamlit
language: Python
database: SQLite
export_format: Excel .xlsx
live_sync: Google Sheets
llm_runtime: Ollama
llm_models_to_test:
  - qwen2.5:7b
  - llama3.1:8b
  - mistral:7b
  - gemma2:9b
configuration: YAML
document_storage: Local filesystem
future_browser_extension: Chrome Extension
```

## 3. High-Level System Diagram

```text
User
 │
 │ interacts with
 ↓
Streamlit Local Web App
 │
 ├── Dashboard UI
 ├── Add Job UI
 ├── Tracker UI
 ├── CV Matcher UI
 ├── Motivation Letter UI
 ├── Form Helper UI
 └── Settings UI
 │
 │ calls
 ↓
Application Services
 │
 ├── Database Service
 ├── Job Extractor
 ├── CV Matcher
 ├── Letter Generator
 ├── Form Helper
 ├── Excel Exporter
 ├── Google Sheets Sync
 ├── Company Search Helper
 └── Utility Layer
 │
 │ stores and retrieves
 ↓
Local Storage
 │
 ├── SQLite database
 ├── CV files
 ├── Motivation letter templates
 ├── Generated letters
 ├── Generated form answers
 ├── Excel exports
 └── Logs
 │
 │ optionally syncs to
 ↓
Google Sheets
```

## 4. Core Design Rules

1. SQLite is the source of truth.
2. Google Sheets mirrors the tracker, but does not replace SQLite.
3. All LLM outputs must be reviewed or editable before use.
4. CV files are fixed and must not be modified automatically in V1.
5. The tool must never auto-submit job applications.
6. LinkedIn support must be manual and user-controlled in V1.
7. The architecture must keep business logic separate from the Streamlit UI.
8. Config values must not be hardcoded if they may change between users.

## 5. Module Responsibilities

## 5.1 `app.py`

### Purpose

Main Streamlit entry point.

### Responsibilities

- Render the app UI.
- Manage navigation/tabs.
- Load configuration.
- Initialize database.
- Call service modules.
- Display success and error messages.
- Handle user inputs.
- Display editable review screens.
- Trigger exports and sync.

### Must Not Do

- Contain complex business logic.
- Directly implement database SQL beyond initialization call.
- Contain LLM prompts inline if avoidable.
- Store secrets.

## 5.2 `src/database.py`

### Purpose

Manage SQLite database operations.

### Responsibilities

- Create database if missing.
- Create tables if missing.
- Insert application records.
- Update application records.
- Read application records.
- Archive records.
- Delete records only if explicitly confirmed.
- Manage companies table.
- Manage contacts table.
- Manage documents table.
- Store Google Sheets row mapping.
- Convert list fields to JSON strings when needed.
- Convert JSON strings back to Python objects.

### Key Functions

```python
init_db()
create_tables()
add_application(application: dict) -> str
update_application(application_id: str, updates: dict) -> None
get_application(application_id: str) -> dict
list_applications(filters: dict | None = None) -> list[dict]
archive_application(application_id: str) -> None
delete_application(application_id: str) -> None
upsert_company(company: dict) -> str
upsert_contact(contact: dict) -> str
```

## 5.3 `src/extractor.py`

### Purpose

Extract structured job data from raw job posts.

### Responsibilities

- Clean raw job post text.
- Detect basic source metadata.
- Build prompt for local LLM.
- Call Ollama.
- Request JSON output.
- Validate output against expected schema.
- Normalize field names.
- Handle missing fields.
- Return extraction with warnings if needed.

### Key Functions

```python
clean_job_text(raw_text: str) -> str
extract_job_post(raw_text: str, source_platform: str | None = None, job_url: str | None = None) -> dict
validate_extraction(extraction: dict) -> tuple[bool, list[str]]
normalize_extraction(extraction: dict) -> dict
```

### Error Handling

The extractor must handle:

- Empty job post.
- Model unavailable.
- Invalid JSON.
- Missing required fields.
- Timeout.
- Overly long job post.
- Hallucinated fields, when detectable.

## 5.4 `src/cv_matcher.py`

### Purpose

Recommend the best fixed CV for a job post.

### Responsibilities

- Load CV domain keywords from `documents.yaml`.
- Score job post against each CV domain.
- Use job title, domain, responsibilities, required skills and preferred qualifications.
- Return recommended CV.
- Return secondary CV.
- Return confidence score.
- Return matched keywords.
- Return explanation.
- Allow manual override in UI.

### Key Functions

```python
score_cv_matches(application: dict, documents_config: dict) -> dict
recommend_cv(application: dict) -> dict
get_cv_file_path(cv_key: str) -> str
```

### Output Example

```json
{
  "recommended_cv": "ai",
  "secondary_cv": "consulting",
  "confidence_score": 0.82,
  "reason": "The job emphasizes AI strategy, automation, process improvement and client-facing transformation work.",
  "matched_keywords": ["AI strategy", "automation", "business transformation"]
}
```

## 5.5 `src/letter_generator.py`

### Purpose

Generate editable motivation letters from templates and application data.

### Responsibilities

- Load user profile.
- Load motivation letter template.
- Select language.
- Generate adapted letter with local model.
- Enforce max word count as much as possible.
- Save generated letter to local file.
- Link file path to application record.
- Return warnings when information is missing.

### Key Functions

```python
select_letter_language(application: dict, user_preference: str = "auto") -> str
generate_letter(application: dict, selected_cv: str, language: str = "auto") -> str
save_letter(application_id: str, letter_text: str, language: str) -> str
```

### Letter Constraints

- Default maximum: 250 words.
- Default language: English.
- French supported.
- Tone: professional, energetic, with personal connection when relevant.
- Must not overclaim experience.
- Must be editable before saving.

## 5.6 `src/form_helper.py`

### Purpose

Generate copy-ready answers for job application forms.

### Responsibilities

- Load profile data.
- Load reusable answer templates.
- Generate common application answers.
- Adapt answers to selected job and company.
- Handle platform-specific answer styles.
- Provide short, medium and long variants when possible.
- Respect salary, location, and authorization rules.

### Key Functions

```python
generate_personal_info_block(profile: dict) -> dict
generate_common_answers(application: dict, profile: dict, platform: str) -> dict
generate_answer_for_field(field_label: str, application: dict, profile: dict) -> str
save_form_answers(application_id: str, answers: dict) -> str
```

### Supported Platforms

- LinkedIn.
- Workday.
- Greenhouse.
- Lever.
- Welcome to the Jungle.
- Company website.
- Other.

## 5.7 `src/excel_exporter.py`

### Purpose

Export tracker data to Excel.

### Responsibilities

- Fetch applications from database.
- Convert fields to Excel-friendly format.
- Export `.xlsx`.
- Save timestamped files.
- Return export path.
- Handle empty tracker.

### Key Functions

```python
export_applications_to_excel(applications: list[dict], output_dir: str) -> str
format_application_for_excel(application: dict) -> dict
```

## 5.8 `src/sheets_sync.py`

### Purpose

Synchronize application tracker with Google Sheets.

### Responsibilities

- Authenticate with Google Sheets API.
- Read sheet headers.
- Create missing headers if needed.
- Push new rows.
- Update existing rows.
- Store sheet row ID in SQLite.
- Avoid duplicates.
- Handle credentials errors.
- Handle network errors.

### Key Functions

```python
init_sheets_client(credentials_path: str)
ensure_worksheet(spreadsheet_id: str, worksheet_name: str)
sync_applications_to_sheet(applications: list[dict]) -> dict
push_application(application: dict) -> str
update_application_row(application: dict, row_id: str) -> None
```

### Sync Rule

SQLite remains source of truth. If conflicts exist, SQLite overwrites Google Sheets in V1.

## 5.9 `src/company_search.py`

### Purpose

Support basic company and career page discovery.

### Responsibilities for V1 or Late V1

- Search companies by sector and location.
- Store company information.
- Store career page URLs.
- Store source/provenance.
- Avoid risky scraping.
- Avoid mass LinkedIn scraping.

### Key Functions

```python
search_companies(sector: str, location: str, keywords: list[str]) -> list[dict]
find_career_page(company_name: str, website: str | None = None) -> str | None
save_company_result(company: dict) -> str
```

## 5.10 `src/utils.py`

### Purpose

Common utilities.

### Responsibilities

- Load YAML config.
- Validate paths.
- Generate UUIDs.
- Format dates.
- Clean strings.
- Convert lists to JSON.
- Convert JSON to lists.
- Logging setup.
- Error message formatting.

## 6. Configuration Files

### 6.1 `config/profile.yaml`

Stores stable user information.

### 6.2 `config/documents.yaml`

Stores CV file paths, document labels, domain keywords and motivation templates.

### 6.3 `config/settings.yaml`

Stores app behavior, model selection, database paths, export settings and Google Sheets settings.

### 6.4 `config/form_answers.yaml`

Stores reusable answers and default phrasing for common form fields.

## 7. Data Flow - Add Job

```text
1. User opens Add Job tab.
2. User pastes job post text and optionally job URL.
3. User selects source platform.
4. User clicks Analyze.
5. Extractor cleans text.
6. Extractor calls local LLM.
7. LLM returns structured JSON.
8. App validates and normalizes JSON.
9. App shows editable review screen.
10. CV matcher recommends CV.
11. User confirms or overrides selected CV.
12. User saves application.
13. Application is stored in SQLite.
14. User may export to Excel or sync to Google Sheets.
```

## 8. Data Flow - Motivation Letter

```text
1. User selects an application.
2. User selects language or auto.
3. Letter generator loads profile and template.
4. Generator creates letter using local LLM.
5. App displays editable letter.
6. User edits if needed.
7. User saves letter.
8. Letter file is stored locally.
9. Application record is updated with letter path.
```

## 9. Data Flow - Form Helper

```text
1. User selects an application.
2. User selects platform.
3. Form helper loads profile and application data.
4. App generates personal info blocks and job-specific answers.
5. User copies answers manually.
6. Optional: answers saved locally.
```

## 10. File Storage Rules

### CVs

Store in:

```text
documents/cvs/
```

CVs are fixed and must not be modified automatically.

### Templates

Store in:

```text
documents/templates/
```

### Generated Motivation Letters

Store in:

```text
generated/motivation_letters/
```

Recommended filename:

```text
{date}_{company_name}_{job_title}_{language}.md
```

### Generated Form Answers

Store in:

```text
generated/form_answers/
```

### Excel Exports

Store in:

```text
exports/excel/
```

### Logs

Store in:

```text
logs/app.log
```

## 11. Logging

The app should log:

- App startup.
- Database initialization.
- Extraction attempts.
- Extraction failures.
- CV recommendations.
- Letter generation attempts.
- Export attempts.
- Google Sheets sync attempts.
- Errors.

Logs must not contain sensitive credentials.

## 12. Error Handling Requirements

The app must show clear user-facing errors for:

- Missing config file.
- Missing CV file.
- Missing template file.
- Database connection error.
- Ollama not running.
- Local model unavailable.
- Invalid LLM JSON.
- Google Sheets credentials missing.
- Google Sheets sync failure.
- Empty job post.
- Export failure.

## 13. Security and Privacy Requirements

- Store data locally by default.
- Do not commit credentials.
- Use `.env` for secrets.
- Keep Google service account file out of Git.
- Keep personal data configurable.
- Do not auto-submit applications.
- Do not mass scrape LinkedIn.
- Do not bypass anti-bot systems.
- User must review generated content.

## 14. Future Extension Readiness

The architecture should prepare for a later Chrome extension by keeping the following logic in services, not in Streamlit:

- Profile field retrieval.
- Application field retrieval.
- Form answer generation.
- CV selection.
- Job post extraction.

A future Chrome extension should call these services through a local API or exported local endpoint if the architecture is later migrated to FastAPI.

## 15. Recommended Future Migration Path

V1:

```text
Streamlit + SQLite + Ollama + Excel + Google Sheets
```

V1.5:

```text
Streamlit + optional local FastAPI service + Chrome extension proof of concept
```

V2:

```text
FastAPI backend + React frontend + Chrome extension
```

Only migrate when the MVP is validated.
