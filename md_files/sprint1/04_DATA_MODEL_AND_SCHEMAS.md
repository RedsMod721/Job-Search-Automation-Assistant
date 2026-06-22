# 04_DATA_MODEL_AND_SCHEMAS.md

# Job Search Automation Assistant - Data Model and Schemas

## 1. Data Model Principles

The database must be structured enough to support future automation, analytics, Google Sheets sync, and Chrome extension integration.

Rules:

1. SQLite is the source of truth in V1.
2. Google Sheets mirrors the application tracker.
3. Fields should be explicit rather than stored only in notes.
4. Raw job post text must always be preserved.
5. LLM list outputs should be stored as JSON strings in SQLite.
6. User must be able to edit extracted data.
7. Missing information should be stored as null or empty strings, not invented.
8. IDs should be stable UUID strings.

## 2. Main Entities

The core entities are:

- Applications.
- Companies.
- Contacts.
- Documents.
- Generated assets.

In V1, the application table is the most important. Companies and contacts can be minimal at first but should be designed early to avoid future migration problems.

## 3. Applications Table

### 3.1 SQL Schema

```sql
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,

    date_created TEXT NOT NULL,
    date_updated TEXT NOT NULL,

    company_name TEXT,
    company_size TEXT,
    company_industry TEXT,
    company_website TEXT,
    company_linkedin TEXT,
    career_page_url TEXT,

    job_title TEXT,
    job_domain TEXT,
    seniority_level TEXT,
    contract_type TEXT,
    job_length TEXT,
    salary TEXT,
    location TEXT,
    remote_policy TEXT,
    relocation_required TEXT,

    key_responsibilities TEXT,
    required_skills TEXT,
    preferred_qualifications TEXT,
    detected_language TEXT,
    raw_job_description TEXT,

    source_platform TEXT,
    application_channel TEXT,
    job_url TEXT,
    status TEXT,
    date_applied TEXT,
    follow_up_date TEXT,
    contact_person TEXT,
    contact_url TEXT,
    notes TEXT,

    recommended_cv TEXT,
    selected_cv TEXT,
    cv_confidence_score REAL,
    cv_recommendation_reason TEXT,
    cv_matched_keywords TEXT,

    motivation_letter_required INTEGER,
    motivation_letter_language TEXT,
    motivation_letter_file TEXT,

    form_answers_file TEXT,

    google_sheet_row_id TEXT,

    archived INTEGER DEFAULT 0
);
```

### 3.2 Field Notes

#### `application_id`

UUID string generated when record is created.

#### `date_created`

ISO datetime string.

#### `date_updated`

ISO datetime string, updated on every modification.

#### `key_responsibilities`

Stored as JSON string representing list of strings.

#### `required_skills`

Stored as JSON string representing list of strings.

#### `preferred_qualifications`

Stored as JSON string representing list of strings.

#### `cv_matched_keywords`

Stored as JSON string representing list of matched keywords.

#### `motivation_letter_required`

Use:

```text
1 = required
0 = not required
null = unknown
```

#### `archived`

Use:

```text
0 = active
1 = archived
```

## 4. Companies Table

### 4.1 SQL Schema

```sql
CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,

    date_created TEXT NOT NULL,
    date_updated TEXT NOT NULL,

    company_name TEXT NOT NULL,
    company_size TEXT,
    company_industry TEXT,
    company_website TEXT,
    company_linkedin TEXT,
    career_page_url TEXT,

    country TEXT,
    city TEXT,

    source TEXT,
    source_url TEXT,

    notes TEXT
);
```

### 4.2 Purpose

The companies table supports future search and sourcing workflows:

- Sector + location to companies.
- Company to career page.
- Company to job posts.
- Company to public contacts.

## 5. Contacts Table

### 5.1 SQL Schema

```sql
CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    company_id TEXT,

    date_created TEXT NOT NULL,
    date_updated TEXT NOT NULL,

    full_name TEXT,
    role_title TEXT,
    department TEXT,
    email TEXT,
    linkedin_url TEXT,

    source_type TEXT,
    source_url TEXT,
    manually_verified INTEGER DEFAULT 0,

    notes TEXT,

    FOREIGN KEY(company_id) REFERENCES companies(company_id)
);
```

### 5.2 Contact Source Rules

Allowed source types:

```text
Company Website
Public Career Page
Public Press Release
Public Email
Job Post
Manual LinkedIn Save
Other
```

Not allowed:

```text
Mass LinkedIn Scrape
Automated LinkedIn Profile Harvesting
Private or Hidden Data Extraction
```

## 6. Documents Table

### 6.1 SQL Schema

```sql
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,

    document_type TEXT,
    domain TEXT,
    label TEXT,
    file_path TEXT,
    language TEXT,
    active INTEGER DEFAULT 1,
    version TEXT,
    notes TEXT
);
```

### 6.2 Document Types

Allowed document types:

```text
cv
motivation_template
generated_motivation_letter
form_answers
other
```

## 7. Application Status Values

Use the following status values:

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

Do not create additional status values without updating all filters, exports and Google Sheets mappings.

## 8. Source Platform Values

Suggested values:

```text
LinkedIn
Company Website
Workday
Greenhouse
Lever
Welcome to the Jungle
Indeed
Email
Referral
Other
```

## 9. Application Channel Values

Suggested values:

```text
LinkedIn Easy Apply
LinkedIn External Link
Company Career Page
ATS Platform
Email
Referral
Manual
Other
```

## 10. Contract Type Values

Suggested values:

```text
Permanent
CDI
Temporary
CDD
Internship
Apprenticeship
Graduate Program
Freelance
Consulting
ESN
Unknown
```

Note: the user is not looking for internships by default, but some job posts may still mention internships. The tool should not target internships unless the user explicitly asks.

## 11. LLM Job Extraction Schema

The LLM must return data in this shape.

```json
{
  "company_name": "",
  "company_size": "",
  "company_industry": "",
  "company_website": "",
  "company_linkedin": "",
  "career_page_url": "",
  "job_title": "",
  "job_domain": "",
  "seniority_level": "",
  "contract_type": "",
  "job_length": "",
  "salary": "",
  "location": "",
  "remote_policy": "",
  "relocation_required": "",
  "key_responsibilities": [],
  "required_skills": [],
  "preferred_qualifications": [],
  "detected_language": "",
  "source_platform": "",
  "application_channel": "",
  "job_url": "",
  "motivation_letter_required": null
}
```

## 12. LLM Extraction Validation Rules

The application should validate that:

- The output is valid JSON.
- List fields are arrays.
- Strings are strings or null.
- `motivation_letter_required` is true, false or null.
- Missing fields are added with default empty values.
- No save occurs until the user confirms.

## 13. CV Recommendation Schema

```json
{
  "recommended_cv": "ai",
  "secondary_cv": "consulting",
  "confidence_score": 0.82,
  "reason": "The job emphasizes AI strategy, automation, process improvement and client-facing transformation work.",
  "matched_keywords": [
    "AI strategy",
    "automation",
    "business transformation"
  ]
}
```

## 14. CV Keys

Use only these values:

```text
marketing
consulting
data_analysis
ai
```

## 15. Motivation Letter Output Schema

```json
{
  "application_id": "",
  "language": "English",
  "word_count": 0,
  "letter_text": "",
  "file_path": "",
  "warnings": []
}
```

## 16. Form Helper Output Schema

```json
{
  "application_id": "",
  "platform": "LinkedIn",
  "answers": {
    "personal_information": {
      "full_name": "",
      "email": "",
      "phone": "",
      "location": "",
      "linkedin_url": "",
      "github_url": ""
    },
    "common_questions": {
      "tell_us_about_yourself": "",
      "why_this_role": "",
      "why_this_company": "",
      "why_should_we_hire_you": "",
      "availability": "",
      "salary_expectations": "",
      "work_authorization": "",
      "relocation": ""
    }
  },
  "file_path": ""
}
```

## 17. Google Sheets Columns

The Google Sheet should use the following columns in this order:

```text
Application ID
Date Created
Date Updated
Company Name
Company Size
Company Industry
Company Website
Company LinkedIn
Career Page URL
Job Title
Job Domain
Seniority Level
Contract Type
Job Length
Salary
Location
Remote Policy
Relocation Required
Key Responsibilities
Required Skills
Preferred Qualifications
Detected Language
Source Platform
Application Channel
Job URL
Status
Date Applied
Follow-up Date
Contact Person
Contact URL
Notes
Recommended CV
Selected CV
CV Confidence Score
CV Recommendation Reason
CV Matched Keywords
Motivation Letter Required
Motivation Letter Language
Motivation Letter File
Form Answers File
Archived
```

## 18. Google Sheets Sync Rules

1. SQLite is source of truth.
2. If `google_sheet_row_id` is empty, create a new row.
3. If `google_sheet_row_id` exists, update that row.
4. Do not create duplicate rows for the same `application_id`.
5. If a row is missing in Google Sheets, recreate it and update `google_sheet_row_id`.
6. Sync errors must be shown to the user.
7. Do not delete rows from Google Sheets in V1. Mark archived instead.

## 19. Excel Export Column Rules

Excel export should use the same user-friendly column names as Google Sheets.

List fields should be formatted as bullet-like strings or semicolon-separated values.

Example:

```text
Python; SQL; Power BI; Machine Learning
```

## 20. Sample Application Record

```json
{
  "application_id": "1f3b9e3a-5c7a-4f2e-8db8-3f2b95190001",
  "date_created": "2026-06-10T14:30:00",
  "date_updated": "2026-06-10T14:30:00",
  "company_name": "Example AI Consulting Firm",
  "company_size": "",
  "company_industry": "Consulting",
  "company_website": "",
  "company_linkedin": "",
  "career_page_url": "",
  "job_title": "Junior AI Consultant",
  "job_domain": "AI Consulting",
  "seniority_level": "Junior",
  "contract_type": "Permanent",
  "job_length": "",
  "salary": "",
  "location": "Paris, France",
  "remote_policy": "Hybrid",
  "relocation_required": "",
  "key_responsibilities": ["Support AI transformation projects", "Analyze business processes", "Prepare client presentations"],
  "required_skills": ["Python", "AI", "Consulting", "Communication"],
  "preferred_qualifications": ["Azure AI", "LLM experience"],
  "detected_language": "English",
  "source_platform": "LinkedIn",
  "application_channel": "LinkedIn External Link",
  "job_url": "https://example.com/job",
  "status": "To Apply",
  "date_applied": "",
  "follow_up_date": "",
  "contact_person": "",
  "contact_url": "",
  "notes": "",
  "recommended_cv": "ai",
  "selected_cv": "ai",
  "cv_confidence_score": 0.86,
  "cv_recommendation_reason": "The role combines AI, consulting and business transformation.",
  "cv_matched_keywords": ["AI", "consulting", "business transformation"],
  "motivation_letter_required": null,
  "motivation_letter_language": "English",
  "motivation_letter_file": "",
  "form_answers_file": "",
  "google_sheet_row_id": "",
  "archived": 0
}
```
