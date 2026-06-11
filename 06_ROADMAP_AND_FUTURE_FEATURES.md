# 06_ROADMAP_AND_FUTURE_FEATURES.md

# Job Search Automation Assistant - Roadmap and Future Features

## 1. Roadmap Philosophy

The project should be built in layers. The first objective is not to build a complete job search robot. The first objective is to build a reliable local assistant that the user can use immediately.

The roadmap should avoid premature complexity. Each step must create usable value before moving to the next one.

## 2. Version Overview

```text
V1.0: Local MVP
V1.5: Browser extension proof of concept
V2.0: Advanced job and company search
V2.5: Public contact finder and outreach assistant
V3.0: Salary benchmark and application analytics
V4.0: Small closed multi-profile mode
```

## 3. V1.0 - Local MVP

### 3.1 Goal

Create a working local app that helps the user track applications, extract job post data, recommend CVs, generate motivation letters, prepare form answers, export Excel, and sync Google Sheets.

### 3.2 Features

- Streamlit local interface.
- SQLite tracker.
- Excel export.
- Google Sheets sync.
- Local LLM extraction through Ollama.
- CV recommendation among four fixed CVs.
- Motivation letter generator.
- Manual form helper.
- Config files.
- Basic settings page.

### 3.3 Excluded

- Chrome extension.
- Automated submissions.
- LinkedIn scraping.
- Full job crawler.
- Multi-user accounts.
- Public deployment.

### 3.4 Completion Criteria

V1 is complete when the user can use it for real job applications from start to finish while remaining in control of all final actions.

## 4. V1.5 - Chrome Extension Proof of Concept

### 4.1 Goal

Reduce form-filling pain directly in the browser, while keeping the user in control.

### 4.2 Features

- Chrome extension prototype.
- Detect visible fields on the current page.
- Suggest matching profile values.
- Suggest generated answers for text areas.
- Fill selected fields after user confirmation.
- Save job URL to local app.
- Send visible job text to local app for extraction if user triggers it.

### 4.3 Supported Sites Priority

1. LinkedIn.
2. Workday.
3. Greenhouse.
4. Lever.
5. Welcome to the Jungle.
6. Company websites.
7. Other ATS platforms.

### 4.4 Safety Rules

The extension must not:

- Click submit.
- Auto-apply.
- Auto-message.
- Auto-connect.
- Mass scrape LinkedIn.
- Bypass CAPTCHA.
- Work in background without user action.

## 5. V2.0 - Advanced Job and Company Search

### 5.1 Goal

Help the user find relevant companies and jobs beyond LinkedIn.

### 5.2 Search Workflow

The intended workflow:

```text
Sector + location + keywords
 ↓
List of companies
 ↓
Company websites and career pages
 ↓
Relevant job posts
 ↓
Save to tracker
```

### 5.3 Example Inputs

```text
Sector: AI consulting
Location: Geneva
Keywords: junior, analyst, AI product, business analyst
```

### 5.4 Desired Outputs

- Company name.
- Industry.
- Website.
- Career page URL.
- Relevant job URLs.
- Location.
- Source URL.
- Notes.
- Date found.

### 5.5 Search Source Priority

1. Company career pages.
2. Greenhouse boards.
3. Lever boards.
4. Workday pages where accessible.
5. Welcome to the Jungle.
6. Job boards.
7. LinkedIn manual helper only.

### 5.6 Not Allowed

- Mass LinkedIn scraping.
- Login bypass.
- CAPTCHA bypass.
- Scraping private data.
- Auto-applying.

## 6. V2.5 - Public Contact Finder and Outreach Assistant

### 6.1 Goal

Help identify relevant public contacts and prepare outreach messages.

### 6.2 Contact Sources

Allowed:

- Company website team pages.
- Recruitment pages.
- Public press releases.
- Public email addresses.
- Job post recruiter names.
- Manually saved LinkedIn profiles.

Not allowed:

- Automated LinkedIn profile harvesting.
- Private emails.
- Mass scraping.
- Automated messaging.

### 6.3 Contact Fields

- Full name.
- Role title.
- Department.
- Company.
- Email if public.
- LinkedIn URL if manually saved.
- Source type.
- Source URL.
- Verification status.
- Notes.

### 6.4 Outreach Assistant

The app may generate:

- Short LinkedIn message.
- Follow-up message.
- Email introduction.
- Referral request.
- Thank-you message after interview.

All outreach must be manually reviewed and sent by the user.

## 7. V3.0 - Salary Benchmark and Application Analytics

### 7.1 Salary Benchmark Helper

The user wants to later implement salary research through Glassdoor-like websites or other salary benchmark services.

V3 can add:

- Salary range lookup by role and location.
- Country-adjusted salary interpretation.
- Gross-to-net notes where possible.
- Source tracking.
- Comparison between job post salary and market data.

Important: V1 should not guess salary. V1 should only store salary if provided by the job post or user.

### 7.2 Application Analytics

Potential analytics:

- Applications by status.
- Applications by platform.
- Applications by country.
- Applications by CV used.
- Response rate by CV.
- Interview rate by platform.
- Response time.
- Follow-up reminders.
- Most successful job domains.

### 7.3 Useful Metrics

- Total applications.
- Applied this week.
- Interviews obtained.
- Rejections.
- Pending applications.
- Follow-ups due.
- Best-performing CV.
- Best-performing source platform.

## 8. V3.5 - Interview Preparation Module

Potential features:

- Generate interview questions from job post.
- Generate company research summary.
- Generate STAR examples from user profile.
- Prepare salary negotiation notes.
- Prepare questions to ask interviewer.
- Track interview outcomes.

## 9. V4.0 - Small Closed Multi-Profile Mode

### 9.1 Goal

Allow the tool to be reused by a few friends without turning it into a public SaaS.

### 9.2 Features

- Profile switching.
- Separate config folders.
- Separate CV folders.
- Separate Google Sheets settings.
- Separate application database per profile or profile_id column.
- No public registration system required.

### 9.3 Still Not Required

- Billing.
- Public accounts.
- Admin panel.
- Public cloud hosting.
- Complex permissions.

## 10. Possible Technical Migration

### V1

```text
Streamlit + SQLite + Ollama + Excel export + Google Sheets
```

### V1.5

```text
Streamlit + local API wrapper + Chrome extension proof of concept
```

### V2

```text
FastAPI backend + React frontend + Chrome extension
```

### V4

```text
Optional hosted version for small closed group
```

Only migrate when the current architecture becomes limiting.

## 11. Backlog Ideas

The following ideas should not block V1:

- Calendar follow-up reminders.
- Email draft generation.
- Gmail integration.
- Automatic duplicate detection across platforms.
- Resume keyword gap analysis.
- Cover letter version history.
- Company ranking by fit.
- Job rejection reason tracker.
- Recruiter relationship tracker.
- Interview question generator.
- Portfolio project recommendation.
- Skills gap learning plan.
- Optional paid LLM fallback.
- Browser extension field memory.
- One-click copy pack for full application.

## 12. Long-Term Product Vision

The long-term vision is a personal job search cockpit:

```text
Find opportunities
Track applications
Prepare documents
Assist form filling
Find contacts
Prepare outreach
Track follow-ups
Analyze results
Improve strategy
```

The tool should remain user-controlled, transparent, and configurable.
