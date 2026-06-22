# Chrome Extension and Local API Specification

## 1. Objective

Build a Chrome extension that:

- Captures the current visible job.
- Creates an application record.
- Assists job-application form filling.
- Recommends the correct CV.
- Assists CV upload where browser constraints allow.
- Detects likely submission success.
- Marks the application Applied after user confirmation.

The extension must never perform the final submission click.

## 2. Architecture

```text
Chrome Extension
    ↓ authenticated localhost request
FastAPI Local Service
    ↓
Application Services
    ↓
SQLite / Ollama / Workers
```

The extension must not access SQLite directly.

## 3. Local API Security

Requirements:

- Bind only to `127.0.0.1`.
- Use `/api/v1`.
- Require a random local token.
- Store token in OS-appropriate secure local storage where practical.
- Allow only configured extension origin.
- Reject unknown origins.
- Do not expose service on LAN.
- Add token rotation.
- Add connection health check.
- Never include Google credentials in extension.

## 4. Recommended API Endpoints

```text
GET  /api/v1/health

POST /api/v1/jobs/capture-preview
POST /api/v1/jobs/extract

POST /api/v1/applications
GET  /api/v1/applications/{application_id}
PATCH /api/v1/applications/{application_id}

POST /api/v1/applications/{application_id}/cv-recommendation
POST /api/v1/applications/{application_id}/form-answers
POST /api/v1/applications/{application_id}/mark-applied

GET  /api/v1/profile/form-values
GET  /api/v1/documents/cvs
POST /api/v1/extension/events
```

## 5. Extension Technology

Use Chrome Manifest V3.

Recommended components:

- Service worker.
- Content scripts.
- Popup or side panel.
- Site adapters.
- Generic field detector.
- Local API client.
- Local extension storage for preferences only.

## 6. Permissions

Use minimal permissions.

Recommended baseline:

```text
activeTab
scripting
storage
```

Use optional host permissions for supported sites.

Add localhost permission for the local API.

Avoid broad permanent access to all websites when optional permissions can be requested on demand.

## 7. Job Capture Workflow

```text
User opens a job page
    ↓
User opens extension
    ↓
Extension detects supported site
    ↓
Content script extracts visible fields
    ↓
Extension shows preview
    ↓
User edits/approves
    ↓
Extension sends to local API
    ↓
Local extraction and CV recommendation run
    ↓
Application draft created
```

## 8. Captured Job Data

Attempt to capture:

- Current URL.
- Page title.
- Job title.
- Company name.
- Location.
- Visible job description.
- Source platform.
- External job ID if visible.
- Employment type.
- Salary if visible.
- Recruiter name if visible.
- Application URL.
- Page language.

The preview must show what will be transmitted.

## 9. Site Adapter Strategy

Implement source-specific adapters in approved order:

1. LinkedIn current job page.
2. Greenhouse.
3. Lever.
4. Ashby.
5. SmartRecruiters.
6. Workday.
7. Welcome to the Jungle.
8. Generic page.

An adapter must expose a common interface:

```text
canHandle(url, document)
extractJob()
detectApplicationSuccess()
detectFormFields()
```

## 10. LinkedIn Rules

Allowed:

- User opens one job page.
- User explicitly activates extension.
- Extension reads visible current-page content.
- User previews and confirms.
- User manually saves a visible recruiter URL.

Not allowed:

- Background crawling.
- Pagination automation.
- Search-result harvesting.
- Profile harvesting.
- Automated connections.
- Automated messages.
- Automated Easy Apply submission.

## 11. Form Detection

Detect:

- Input type text.
- Email.
- Phone.
- Number.
- URL.
- Date.
- Textarea.
- Select.
- Radio.
- Checkbox.
- File.
- Custom combobox where accessible.
- ARIA-based widgets.

Use signals:

1. Associated label.
2. ARIA label.
3. Placeholder.
4. Name.
5. ID.
6. Nearby text.
7. Section heading.
8. Site adapter.
9. Generic ontology.
10. LLM fallback through local API.

## 12. Field Ontology

Normalize detected questions to keys such as:

```text
first_name
last_name
full_name
email
phone
current_city
current_country
relocation
linkedin_url
github_url
portfolio_url
work_authorization
visa_sponsorship
availability
salary_expectation
education
languages
years_experience
tell_us_about_yourself
why_this_role
why_this_company
why_should_we_hire_you
technical_skills
soft_skills
consent
source_referral
cv_upload
motivation_letter_upload
other_long_text
```

## 13. Suggestion Model

Each detected field should show:

```json
{
  "field_key": "salary_expectation",
  "detected_label": "What are your salary expectations?",
  "suggested_value": "I am flexible...",
  "source": "profile.default_answers",
  "confidence": 0.94,
  "action": "review_required"
}
```

Actions:

- Fill.
- Edit.
- Skip.
- Fill all high-confidence.
- Review low-confidence.

## 14. Personal Information Filling

Use verified profile values.

Location rule:

- Prefer Open to relocation where free text allows.
- Use Grenoble, France when a specific current city is mandatory.

Salary rule:

- Prefer flexible answer.
- If number input is mandatory, request user input.
- Do not insert private salary baseline automatically.

Work authorization rule:

- Use European passport/Italian citizenship language.
- Do not claim automatic work authorization outside applicable regions.
- Distinguish eligibility from willingness to obtain a visa.

## 15. Long-Form Answers

For text areas:

1. Detect normalized question.
2. Check approved reusable answer.
3. Adapt to job context.
4. Show generated answer.
5. Require review.
6. Fill only after user action.

Generated answers must include:

- Prompt version.
- Model version.
- Application ID.
- Generation timestamp.

## 16. Select, Radio, and Checkbox Handling

The extension may suggest an option, but must avoid unsafe assumptions.

Examples requiring explicit review:

- Disability.
- Gender.
- Ethnicity.
- Veteran status.
- Legal declarations.
- Consent.
- Background checks.
- Criminal history.
- Sponsorship.

Sensitive voluntary demographic fields should default to no automatic selection.

## 17. CV Recommendation and Upload Assistance

### Recommendation

The extension requests the current application CV recommendation from local API.

Display:

- Recommended CV.
- Secondary CV.
- Confidence.
- Reason.
- Exact filename.
- File exists status.

### Upload

Browser constraints may prevent silent file selection.

Allowed assistance:

- Detect file input.
- Highlight input.
- Display correct filename.
- Open user-controlled picker when supported.
- Confirm selected filename.
- Warn if wrong CV appears selected.

Do not bypass browser file protections.

## 18. Motivation Letter Upload

If a file input requests a motivation letter:

- Detect requirement.
- Check generated letter exists.
- Offer to open application in local app.
- Allow user to generate/save.
- Assist user-controlled file selection.
- Never invent that a letter was uploaded.

## 19. Submission Protection

The extension must never:

- Click Submit.
- Trigger form submission through JavaScript.
- Simulate Enter on final submit.
- Trigger hidden submission.
- Automatically accept legal declarations.

## 20. Applied Status Workflow

After user manually submits:

1. Adapter detects success message/page where possible.
2. Extension shows confirmation:
   `Was this application submitted successfully?`
3. User confirms.
4. Extension calls `mark-applied`.
5. Local application status changes to Applied.
6. Date applied is stored.
7. Sync event is queued.
8. Optional follow-up date is suggested.

Automatic success detection alone must not change status without user confirmation.

## 21. Extension UI States

Required states:

```text
Local app disconnected
Connected
Unsupported page
Job detected
Capture preview
Application created
Form detected
Suggestions ready
Review required
Submission likely successful
Error
```

## 22. Offline/Disconnected Behavior

If local API is unavailable:

- Show clear connection error.
- Do not lose captured text.
- Allow copy to clipboard.
- Optionally store a temporary local draft with explicit user approval.
- Retry connection.
- Do not store sensitive long-form answers unnecessarily in extension storage.

## 23. Tests

### Unit

- Field ontology.
- Label extraction.
- Adapter parsing.
- Suggestion mapping.
- Submission protection.

### Browser Integration

- Fixture pages for each ATS.
- Text inputs.
- Custom selects.
- Radio and checkbox.
- File input.
- Success page.

### Manual Site Tests

- LinkedIn.
- Greenhouse.
- Lever.
- Ashby.
- SmartRecruiters.
- Workday.
- Welcome to the Jungle.
- Generic company form.

## 24. Acceptance Criteria

- Current-page LinkedIn job capture works.
- Application record is created locally.
- Visible fields are detected.
- Suggested values show source and confidence.
- User controls every fill action.
- Long-form answers are reviewable.
- Recommended CV is displayed.
- CV upload is assisted where possible.
- Final submit is never automated.
- Applied status requires user confirmation.
