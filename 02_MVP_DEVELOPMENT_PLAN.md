# 02_MVP_DEVELOPMENT_PLAN.md

# Job Search Automation Assistant - MVP Development Plan

## 1. Development Objective

The objective is to build a working local MVP as quickly as possible, then improve it based on real usage. The MVP must be practical, stable, and useful before adding advanced automation.

The tool must first solve the user's most painful workflows:

1. Tracking applications.
2. Extracting job post information.
3. Selecting the best fixed CV.
4. Generating motivation letters when needed.
5. Preparing answers for repetitive job application forms.
6. Exporting and syncing application data.

## 2. Development Principle

Build incrementally.

Do not start with a Chrome extension, scraping engine, or complex multi-user system. Start with a local app that works reliably and stores clean data.

The development order must be:

1. Local app skeleton.
2. SQLite database and manual tracker.
3. Excel export.
4. Local LLM job extraction.
5. CV recommendation.
6. Motivation letter generation.
7. Form helper.
8. Google Sheets sync.
9. Basic search support.
10. Later extension and advanced automation.

## 3. MVP Definition

The MVP is valid when the user can:

1. Launch the app locally.
2. Add an application manually.
3. Paste a job post.
4. Extract structured job data with a local model.
5. Review and edit extracted fields.
6. Save the application to SQLite.
7. Export applications to Excel.
8. Sync applications to Google Sheets.
9. Receive a CV recommendation among four fixed CV files.
10. Manually override the recommended CV.
11. Generate an editable motivation letter when needed.
12. Generate copy-ready answers for application forms.
13. Manage application statuses and notes.

## 4. Recommended Technology for MVP

```yaml
interface: Streamlit
language: Python
database: SQLite
early_export: Excel .xlsx
live_sync: Google Sheets
llm_provider: Ollama
llm_type: Local/free model
config: YAML
document_storage: Local folders
```

## 5. Phase 0 - Repository and Environment Setup

### 5.1 Tasks

- Create the repository.
- Create a Python virtual environment.
- Add `requirements.txt`.
- Add `.env.example`.
- Add `.gitignore`.
- Create the base folder structure.
- Add placeholder config files.
- Add placeholder README.
- Add sample job post data for testing.
- Add local folders for CVs, templates, exports, generated letters and logs.

### 5.2 Expected Folder Structure

```text
job_search_assistant/
│
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
│
├── config/
│   ├── profile.yaml
│   ├── documents.yaml
│   ├── settings.yaml
│   └── form_answers.yaml
│
├── database/
│   └── applications.db
│
├── documents/
│   ├── cvs/
│   └── templates/
│
├── generated/
│   ├── motivation_letters/
│   └── form_answers/
│
├── exports/
│   └── excel/
│
├── logs/
│   └── app.log
│
├── samples/
│   └── sample_job_posts/
│
└── src/
    ├── database.py
    ├── extractor.py
    ├── cv_matcher.py
    ├── letter_generator.py
    ├── form_helper.py
    ├── sheets_sync.py
    ├── excel_exporter.py
    ├── company_search.py
    └── utils.py
```

### 5.3 Acceptance Criteria

- The project installs locally.
- The app can be launched with one command.
- No credentials or secrets are committed.
- Folder structure is created.
- Config files can be loaded.

## 6. Phase 1 - Local App Skeleton

### 6.1 Goal

Create the basic Streamlit interface.

### 6.2 Required Tabs

The app must have these tabs or pages:

1. Dashboard.
2. Add Job.
3. Tracker.
4. CV Matcher.
5. Motivation Letter.
6. Form Helper.
7. Settings.

Optional late V1 tab:

8. Company Search.

### 6.3 Tab Responsibilities

#### Dashboard

Show quick metrics:

- Total applications.
- Applications by status.
- Applications by CV used.
- Applications by source platform.
- Upcoming follow-ups.
- Recent applications.

#### Add Job

Allow user to:

- Paste raw job post text.
- Enter job URL.
- Select source platform.
- Select application channel.
- Trigger job analysis.
- Review extracted information.
- Save application.

#### Tracker

Allow user to:

- View all applications.
- Filter by status, company, domain, source, CV, location.
- Update status.
- Edit application information.
- Archive or delete records.
- Export to Excel.
- Sync to Google Sheets.

#### CV Matcher

Allow user to:

- Select an application.
- View recommended CV.
- View confidence score.
- View explanation.
- Manually override selected CV.

#### Motivation Letter

Allow user to:

- Select an application.
- Choose language or auto-detect.
- Generate a motivation letter.
- Edit generated letter.
- Save letter locally.
- Copy text.

#### Form Helper

Allow user to:

- Select an application.
- Select platform.
- Generate copy-ready answers.
- Copy each answer.
- Save answers locally if desired.

#### Settings

Allow user to:

- View or update profile path.
- View or update document paths.
- Select local LLM model.
- Configure Google Sheets.
- Configure export folder.

### 6.4 Acceptance Criteria

- App launches locally.
- Navigation works.
- Basic page structure is implemented.
- Settings are loaded from YAML files.
- User can see clear placeholder states when no data exists.

## 7. Phase 2 - SQLite Tracker

### 7.1 Goal

Build reliable application storage before adding LLM automation.

### 7.2 Required Features

- Initialize SQLite database.
- Create application table.
- Add manual application record.
- List applications.
- Edit existing application.
- Update status.
- Archive application.
- Store raw job description.
- Store selected CV.
- Store motivation letter path.
- Store Google Sheets row ID for later sync.

### 7.3 Status Values

Use these status values:

```text
Saved
To Apply
Applied
Follow-up Needed
Interview
Rejected
Accepted
Archived
```

### 7.4 Manual Application Form Fields

The manual form must support at least:

- Company name.
- Job title.
- Location.
- Source platform.
- Job URL.
- Application channel.
- Contract type.
- Salary.
- Status.
- Selected CV.
- Notes.

### 7.5 Acceptance Criteria

- User can add an application manually.
- Data remains after closing and reopening the app.
- User can update an application.
- User can filter applications by status.
- User can archive records without deleting them permanently.

## 8. Phase 3 - Excel Export

### 8.1 Goal

Allow quick testing and external review of the tracker through Excel.

### 8.2 Required Features

- Export all applications to `.xlsx`.
- Export selected or filtered applications if practical.
- Save files in `exports/excel/`.
- Use timestamped filenames.
- Use readable column names.
- Convert JSON list fields into readable text.

### 8.3 Example Filename

```text
applications_export_2026-06-10_14-30.xlsx
```

### 8.4 Acceptance Criteria

- User can click export.
- Excel file is created successfully.
- File includes all relevant tracker columns.
- File can be opened without formatting problems.

## 9. Phase 4 - Local LLM Job Extraction

### 9.1 Goal

Use a local/free LLM to extract structured data from job posts.

### 9.2 Preferred Tool

Use Ollama as the local LLM runner.

Initial models to test:

```text
qwen2.5:7b
llama3.1:8b
mistral:7b
gemma2:9b
```

Default starting model:

```text
qwen2.5:7b
```

### 9.3 Required Features

- User pastes raw job post text.
- App cleans and normalizes text.
- App sends text to local model.
- Model returns JSON.
- App validates JSON.
- App shows editable review screen.
- App handles invalid JSON gracefully.
- App stores extraction confidence if available.

### 9.4 Extracted Fields

The extractor must attempt to identify:

- Company name.
- Company size.
- Company industry.
- Company website.
- Company LinkedIn.
- Career page URL.
- Job title.
- Job domain.
- Seniority level.
- Contract type.
- Job length.
- Salary.
- Location.
- Remote policy.
- Relocation required.
- Key responsibilities.
- Required skills.
- Preferred qualifications.
- Detected language.
- Source platform.
- Application channel.
- Job URL.
- Motivation letter required.

### 9.5 Extraction Rules

The LLM must be instructed to:

- Extract only information present in the job post.
- Use empty strings, null or empty arrays when information is missing.
- Never invent salary.
- Never invent company size.
- Never invent benefits.
- Keep bullet lists concise.
- Detect language.
- Detect whether a motivation letter is explicitly required.
- Preserve raw job post text in the database.

### 9.6 Acceptance Criteria

- Pasting a job post returns structured fields.
- Missing information is left blank rather than invented.
- User can edit all fields before saving.
- Bad model output does not crash the app.
- Raw job description is saved.

## 10. Phase 5 - CV Recommendation

### 10.1 Goal

Recommend the best CV among four fixed CV files.

### 10.2 Fixed CVs

- Marketing CV: `CV_Sebastian.Vazquez_Anglais-Marketing.pdf`
- Consulting CV: `CV_Sebastian.Vazquez_Anglais-Consulting.pdf`
- Data Analysis CV: `CV_Sebastian.Vazquez_Anglais-DataScience.pdf`
- AI CV: `CV_Sebastian.Vazquez_Anglais-AI.pdf`

### 10.3 Required Features

- Load CV categories from `documents.yaml`.
- Score job post against each CV domain.
- Use title, job domain, responsibilities, required skills and preferred qualifications.
- Return recommended CV.
- Return secondary CV.
- Return confidence score.
- Return explanation.
- Return matched keywords.
- Allow manual override.

### 10.4 Recommended Approach

Combine:

1. Keyword scoring.
2. Optional LLM-based classification.
3. Simple deterministic rules for obvious cases.
4. Manual user override.

### 10.5 Acceptance Criteria

- The app recommends one CV.
- The app explains the recommendation.
- The user can override the recommendation.
- The selected CV is saved to the application record.

## 11. Phase 6 - Motivation Letter Generator

### 11.1 Goal

Generate short, editable motivation letters from templates.

### 11.2 Requirements

- Default language: English.
- French supported when useful.
- Maximum default length: 250 words.
- Tone: professional, energetic, with personal connection or short anecdote when relevant.
- Letter must mention the company and role.
- Letter must connect the role to Sebastian's profile.
- Letter must avoid overclaiming.
- Letter must be editable before saving.
- Letter must be saved locally if user chooses.

### 11.3 Inputs

- Application record.
- Job post information.
- Selected CV domain.
- User profile.
- Motivation letter template.
- Selected language.
- Optional user notes.

### 11.4 Outputs

- Editable letter text.
- Saved `.txt` or `.md` file.
- File path linked to application record.

### 11.5 Acceptance Criteria

- User can generate a letter for an application.
- Letter is under 250 words by default.
- Letter is not generic.
- User can edit before saving.
- Saved letter path is stored.

## 12. Phase 7 - Manual Form Helper

### 12.1 Goal

Reduce repetitive form filling without needing a Chrome extension yet.

### 12.2 Supported Platforms in V1

Priority order:

1. LinkedIn.
2. Workday.
3. Greenhouse.
4. Lever.
5. Welcome to the Jungle.
6. Company website.
7. Other.

### 12.3 Required Features

The user selects an application and platform. The app generates:

- Personal information block.
- Short answer block.
- Medium answer block.
- Salary expectations.
- Availability.
- Work authorization.
- Relocation answer.
- Why this role.
- Why this company.
- Tell us about yourself.
- Relevant technical skills.
- Relevant soft skills.

### 12.4 Form Answer Rules

- If location is requested, prefer "Open to relocation" when possible.
- If a mandatory city is needed, use "Grenoble, France".
- If salary is requested, default to a flexible market-based answer.
- If exact salary is required, allow user to manually enter a number.
- If work authorization is requested, mention European passport and Italian citizenship.
- If asked about internships, avoid presenting the user as looking for an internship.
- Keep answers concise unless the field clearly requests detail.

### 12.5 Acceptance Criteria

- User can generate answers for a selected application.
- Answers can be copied individually.
- Answers adapt to the selected job post.
- The tool never submits the application.

## 13. Phase 8 - Google Sheets Sync

### 13.1 Goal

Mirror SQLite tracker to Google Sheets before final V1 validation.

### 13.2 Requirements

- SQLite remains the source of truth.
- Google Sheets account and spreadsheet must be configurable.
- App must push new application rows.
- App must update existing rows when records change.
- App must avoid duplicate rows.
- App must store `google_sheet_row_id` or equivalent mapping.
- App must handle sync errors gracefully.

### 13.3 Configuration

Use `settings.yaml`:

```yaml
google_sheets:
  enabled: true
  spreadsheet_id: ""
  worksheet_name: "Applications"
  credentials_path: "config/google_service_account.json"
```

### 13.4 Acceptance Criteria

- User can configure Google Sheets.
- User can sync applications.
- Sheet contains all required columns.
- Updating a record in SQLite updates the corresponding row.
- Sync errors are shown clearly.

## 14. Phase 9 - Basic Company Search Support

### 14.1 Goal

Start helping the user find jobs beyond LinkedIn.

### 14.2 V1 or Late V1 Features

- Search input: sector, location, keywords.
- Return list of companies.
- Return company websites when found.
- Return career page URLs when found.
- Save company to database.
- Save job URL to tracker manually.
- Record source/provenance.

### 14.3 Not Required in V1

- Full crawler.
- Large scale scraping.
- Automated application to discovered jobs.
- Advanced ranking.
- Salary benchmark integration.

### 14.4 Acceptance Criteria

- User can store discovered companies.
- User can store career page URLs.
- User can convert a job link into an application record.

## 15. Final MVP Validation Checklist

The MVP is complete only when all of the following are true:

- App runs locally.
- Interface is in English.
- Config files are loaded.
- User can add applications manually.
- User can paste job posts.
- Local model extracts structured data.
- User can review and edit extracted data.
- SQLite stores all application records.
- User can export Excel.
- User can sync Google Sheets.
- CV recommendation works.
- User can override CV recommendation.
- Motivation letter generator works.
- Form helper works.
- Tool does not auto-submit applications.
- Tool does not mass scrape LinkedIn.
- Tool handles errors gracefully.
- Basic README explains installation and usage.
