# 05_LLM_AND_AUTOMATION_SPEC.md

# Job Search Automation Assistant - LLM and Automation Specification

## 1. Purpose

This file defines how LLM features and automation features must behave in the Job Search Automation Assistant.

The project should use a local/free model for V1, preferably through Ollama. Output quality can be lower than paid API models, but every generated output must be reviewable and editable.

The LLM is an assistant, not an authority. The user decides what to save, send, copy, or use.

## 2. LLM Provider Strategy

### 2.1 V1 Preference

Use a local LLM through Ollama.

Recommended starting model:

```text
qwen2.5:7b
```

Other models to test:

```text
llama3.1:8b
mistral:7b
gemma2:9b
```

### 2.2 Model Fallback

If the selected local model is not available, the app should show a clear message:

```text
The selected local model is not available. Please check that Ollama is running and that the model is installed.
```

The app should not crash.

## 3. LLM Tasks in V1

The LLM can be used for:

1. Job post extraction.
2. Job domain classification.
3. CV recommendation explanation.
4. Motivation letter generation.
5. Form answer generation.
6. Rewriting or shortening form answers.
7. Optional company summary from user-provided company text.

The LLM must not:

1. Invent missing facts.
2. Submit applications.
3. Send messages.
4. Scrape LinkedIn.
5. Make final decisions without user review.

## 4. Human Validation Rule

All LLM-generated outputs must be shown to the user before being saved or used.

This applies to:

- Job extraction.
- CV recommendation.
- Motivation letters.
- Form answers.
- Company summaries.
- Contact notes.

No LLM-generated output should be considered final by default.

## 5. Job Post Extraction Prompt Requirements

The extraction prompt must instruct the model to:

- Extract only information present in the job post.
- Use empty strings, null, or empty lists when information is missing.
- Do not invent salary.
- Do not invent company size.
- Do not invent job benefits.
- Do not invent company values if not provided.
- Keep key responsibilities concise.
- Keep required skills concise.
- Keep preferred qualifications concise.
- Detect language.
- Detect application channel if visible.
- Detect whether a motivation letter is required.
- Return valid JSON only.
- Follow the exact schema.

## 6. Job Post Extraction Prompt Template

Use a template similar to:

```text
You are an information extraction assistant for a job application tracking tool.

Your task is to extract structured information from the job post provided by the user.

Rules:
- Return JSON only.
- Follow the exact schema.
- Extract only facts present in the job post.
- Do not invent salary, company size, benefits, company website, or requirements.
- If a field is missing, use an empty string, null, or an empty list.
- Keep lists concise.
- Detect the language of the job post.
- Detect whether a motivation letter is explicitly requested.
- If unsure about a field, leave it empty.

Schema:
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

Job post:
{job_post_text}
```

## 7. Extraction Post-Processing

After the model returns JSON, the app must:

1. Validate JSON.
2. Add missing fields.
3. Normalize list fields.
4. Remove fields not in schema.
5. Display warnings.
6. Show editable review screen.
7. Save only after user confirmation.

## 8. CV Recommendation Logic

The CV recommendation should combine deterministic scoring and optional LLM explanation.

### 8.1 CV Categories

Use only these categories:

```text
marketing
consulting
data_analysis
ai
```

### 8.2 Deterministic Scoring

For each CV, calculate matches across:

- Job title.
- Job domain.
- Key responsibilities.
- Required skills.
- Preferred qualifications.
- Raw job description.

Apply stronger weight to:

1. Job title.
2. Required skills.
3. Responsibilities.
4. Preferred qualifications.
5. Raw description.

### 8.3 Example Weights

```yaml
weights:
  job_title: 3
  job_domain: 3
  required_skills: 3
  key_responsibilities: 2
  preferred_qualifications: 2
  raw_job_description: 1
```

### 8.4 Recommended Output

```json
{
  "recommended_cv": "ai",
  "secondary_cv": "consulting",
  "confidence_score": 0.82,
  "reason": "The job emphasizes AI strategy, automation, process improvement and client-facing transformation work.",
  "matched_keywords": ["AI strategy", "automation", "business transformation"]
}
```

### 8.5 Manual Override

The user must always be able to override the recommended CV.

## 9. Motivation Letter Generation

### 9.1 Rules

The letter generator must follow these rules:

- Generate only when user requests it or when the application process requires it.
- Default language: English.
- French supported when the job/company is French or the user selects French.
- Maximum default length: 250 words.
- Tone: professional, energetic, with a personal connection or short anecdote when relevant.
- Mention the company name.
- Mention the role title.
- Connect the role to the user's profile.
- Use the selected CV domain as guidance.
- Avoid generic phrases when possible.
- Do not overclaim.
- Do not invent experience.
- Do not mention salary.
- Do not mention visa unless relevant.
- Must be editable before saving.

### 9.2 Motivation Letter Prompt Template

```text
You are helping Sebastian Vazquez draft a short motivation letter for a job application.

Rules:
- Maximum 250 words.
- Language: {language}.
- Tone: professional, energetic, and personally connected.
- Mention the company and job title.
- Connect the role to Sebastian's profile.
- Use the selected CV domain: {selected_cv}.
- Do not invent experience.
- Do not overclaim.
- Avoid generic corporate wording.
- Keep the letter ready to edit and send.

Sebastian profile summary:
{profile_summary}

Job information:
{application_data}

Optional user notes:
{user_notes}

Write the motivation letter only.
```

## 10. Form Helper Generation

### 10.1 Purpose

Generate copy-ready answers for application forms.

### 10.2 Common Questions

The form helper should support:

- Tell us about yourself.
- Why are you interested in this role?
- Why do you want to join this company?
- Why should we hire you?
- What are your strengths?
- What technical skills are relevant?
- What is your availability?
- What are your salary expectations?
- Are you open to relocation?
- Do you require sponsorship?
- What languages do you speak?
- Add any additional information.

### 10.3 Answer Lengths

When possible, generate:

```text
short: 1-2 sentences
medium: 3-5 sentences
long: 1 short paragraph or more if needed
```

### 10.4 Form Helper Rules

#### Location

Prefer:

```text
Open to relocation
```

Use:

```text
Grenoble, France
```

only when a specific current location is required.

#### Salary

Default:

```text
I am flexible and open to discussing compensation depending on the role, responsibilities, location and overall package.
```

If a number is mandatory, ask user to enter one manually.

#### Work Authorization

Default:

```text
I hold a European passport through Italian citizenship and am open to visa processes for strong international opportunities.
```

#### Availability

Default:

```text
I am available to start immediately.
```

#### Internship Questions

The user is not primarily looking for internships. If a form asks about internship duration, do not invent one. Use a cautious answer or ask for confirmation.

## 11. Form Helper Prompt Template

```text
You are generating copy-ready job application form answers for Sebastian Vazquez.

Rules:
- Keep answers clear and professional.
- Adapt the answer to the job and company.
- Do not invent experience.
- Do not overclaim.
- Prefer concise answers.
- If salary is asked, use a flexible market-based answer unless a number is required.
- If location is asked, prefer "open to relocation" unless a current city is mandatory.
- If work authorization is asked, mention European passport through Italian citizenship.
- Do not say Sebastian is looking for an internship unless the user explicitly asks.

Profile:
{profile}

Job:
{application_data}

Platform:
{platform}

Questions to answer:
{questions}
```

## 12. Automation Rules

### 12.1 Allowed Automation

The app may:

- Extract user-provided job post text.
- Generate editable text.
- Save tracker data.
- Export Excel.
- Sync Google Sheets.
- Save manually entered LinkedIn job or profile URLs.
- Search public company websites where allowed.
- Prepare answers for forms.
- Later fill selected visible fields only after user confirmation through a Chrome extension.

### 12.2 Forbidden Automation

The app must not:

- Automatically submit job applications.
- Automatically click final submit or send buttons.
- Mass scrape LinkedIn.
- Auto-connect on LinkedIn.
- Auto-message recruiters.
- Auto-apply to jobs.
- Bypass CAPTCHA.
- Circumvent anti-bot protections.
- Extract private or hidden data.
- Guess missing data and present it as fact.

## 13. Chrome Extension Future Rules

A Chrome extension is not part of V1. If developed later, it must follow these rules:

- Analyze only visible fields on the current page.
- Suggest values from the local app/profile.
- Let user choose which fields to fill.
- Fill selected fields only after confirmation.
- Never click final submit.
- Never run mass actions.
- Never scrape LinkedIn profiles at scale.
- Never bypass login or CAPTCHA.

## 14. LinkedIn Specific Rules

LinkedIn is a priority platform for the user, but the tool must be careful.

Allowed:

- User manually copies a LinkedIn job post into the app.
- User manually saves a LinkedIn job URL.
- User manually saves a recruiter profile URL.
- Future extension may read visible job information only with user action.

Not allowed:

- Mass job scraping.
- Mass profile scraping.
- Automated connection requests.
- Automated messaging.
- Automated Easy Apply submission.
- Background harvesting.

## 15. Hallucination Control

The app must reduce hallucination risk by:

- Using strict schemas.
- Asking for JSON only.
- Leaving missing fields blank.
- Showing editable review screens.
- Saving raw source text.
- Marking uncertain fields.
- Avoiding unsupported salary or company size estimates.

## 16. Quality Checks

Before saving LLM output, the app should check:

- Is company name missing?
- Is job title missing?
- Is detected language valid?
- Are salary and company size suspiciously specific despite not being in the post?
- Are list fields too long?
- Are required skills mixed with responsibilities?
- Is the generated letter above 250 words?
- Does the generated answer claim experience not present in the profile?

When possible, show warnings instead of blocking the user.
