# 01_PROJECT_CONTEXT.md

# Job Search Automation Assistant - Project Context

## 1. Project Summary

The project is a personal semi-automated job search assistant designed to help Sebastian Vazquez manage and accelerate his job search process. The tool must help track job applications, extract structured information from job posts, recommend the most relevant CV among four fixed CV files, generate customized motivation letters when needed, assist with repetitive application form fields, and gradually support job and company search.

The objective is not to build a fully automated application bot. The objective is to build a reliable personal productivity tool where the user remains in control. The user must always review extracted data, generated text, selected CVs, and form answers before using them.

The first version must be useful as soon as possible, then improved incrementally based on real usage.

## 2. Product Philosophy

The product must follow these principles:

1. Build a practical local MVP first.
2. Prioritize reliability and editable outputs over full automation.
3. Keep the user in control at every important decision point.
4. Avoid risky automation, especially on LinkedIn and final application submission.
5. Use local or free models first, even if output quality is lower.
6. Keep the tool configurable so the same app can later be used by a few trusted friends.
7. Store structured data cleanly so future modules can be built on top of it.

## 3. Main User Need

The user applies to jobs across LinkedIn, company websites, and potentially other job platforms. The process is repetitive and time-consuming because each job requires the user to:

- Read and understand the job post.
- Copy relevant information into a tracker.
- Identify the company, role, location, salary, contract type, and application channel.
- Understand the key responsibilities and required skills.
- Choose the best CV among several fixed versions.
- Generate or adapt a motivation letter when requested.
- Fill repeated form fields manually.
- Track whether the job was saved, applied to, followed up, rejected, or converted into an interview.
- Find more jobs from relevant companies or sectors.

The tool should reduce manual repetition and make the process more structured without removing user control.

## 4. Intended Users

### 4.1 V1 User

The first user is Sebastian Vazquez.

### 4.2 Future Small Closed Use

The tool may later be shared with a few friends also looking for jobs. However, V1 does not require user accounts, authentication, multi-user permissions, billing, or public deployment.

The app must still be configurable so another user can later change:

- Profile information.
- CV file paths.
- Motivation letter templates.
- Google Sheets account and spreadsheet.
- Preferred target roles and countries.

## 5. MVP Scope

The MVP is a local English interface with:

- SQLite as the source of truth.
- Excel export for early tests.
- Google Sheets live sync before final V1 validation.
- Local LLM extraction and generation through Ollama or equivalent.
- Fixed CV selection among four uploaded CV files.
- Motivation letter generation from templates.
- Manual form-filling assistant.
- Basic job and company search support if feasible after core features.
- No Chrome extension in the first MVP, but architecture should prepare for it later.

## 6. In-Scope Features for V1

The following features are required for V1:

### Application Tracking

The app must store job applications with detailed structured information:

- Company name.
- Company size.
- Company industry.
- Job domain.
- Salary if provided.
- Location.
- Job description key responsibilities.
- Job description required skills.
- Job description preferred qualifications.
- Application channel.
- Used CV.
- Motivation letter.
- Length of job or contract type.
- Source platform and job URL.
- Application status.
- Follow-up dates and notes.

### Job Post Extraction

The user must be able to paste a job post or job URL. In V1, URL extraction may be limited depending on technical difficulty. Pasting raw text must always work.

The app must use a local/free LLM to extract structured data into a predefined JSON schema.

### CV Recommendation

The app must recommend the most relevant CV among four fixed CV files:

- Marketing CV.
- Consulting CV.
- Data Analysis / Data Science CV.
- AI CV.

The tool must not edit CV content automatically in V1.

### Motivation Letter Generation

The app must generate a motivation letter only when needed or requested by the user. It must use editable templates and adapt the letter to:

- Company name.
- Job title.
- Job description.
- Relevant user experience.
- Language of the post or company.
- Preferred tone.

Default language is English. French must be supported when relevant.

Maximum default length: 250 words.

### Manual Form Helper

The app must help answer repeated application form fields. In V1 this is not a browser extension. It is a copy-ready assistant inside the local app.

It should produce answers for common fields such as:

- Tell us about yourself.
- Why are you interested in this role?
- Why this company?
- Why should we hire you?
- Availability.
- Salary expectations.
- Work authorization.
- Relocation.
- Languages.
- Technical skills.

### Excel Export

The app must export the tracker to an Excel file for early testing and offline review.

### Google Sheets Sync

Before final V1 validation, the app must sync the tracker to Google Sheets. SQLite remains the source of truth.

## 7. Explicitly Out of Scope for V1

The following must not be implemented in V1:

- Fully automated job application submission.
- Automatic click on final "Submit", "Send", "Apply", or equivalent buttons.
- Mass LinkedIn scraping.
- Automated LinkedIn connection requests.
- Automated LinkedIn messaging.
- Automated LinkedIn Easy Apply submissions.
- CAPTCHA bypassing.
- Circumventing platform restrictions or login protections.
- Public SaaS deployment.
- User account system.
- Payment system.
- Large-scale contact scraping.
- CV auto-editing.
- Full Chrome extension.

## 8. Automation Boundaries

Allowed in V1:

- Extract information from user-provided job posts.
- Generate editable motivation letters.
- Generate copy-ready form answers.
- Store applications in SQLite.
- Export Excel.
- Sync to Google Sheets.
- Save manually provided LinkedIn job or profile URLs.
- Use public company websites for basic company/career page discovery when technically and legally acceptable.

Not allowed in V1:

- Auto-submit applications.
- Auto-fill hidden or protected fields without user visibility.
- Mass scrape LinkedIn.
- Auto-send messages or connection requests.
- Bypass CAPTCHA or anti-bot protections.
- Invent missing job data.

## 9. Stable User Profile

The following information can be used to configure the tool and generate application content.

### 9.1 Personal Information

```yaml
first_name: Sebastian
last_name: Vazquez
email: sebastian.vazquez.blue@gmail.com
phone: "+33 7 81 79 47 96"
current_location: Grenoble, France
location_usage_rule: "Use 'Open to relocation' when possible. Use 'Grenoble, France' only when a form requires a specific location."
linkedin_url: "https://www.linkedin.com/in/sebastian-vazquez-0999/"
github_url: "https://github.com/RedsMod721"
portfolio_url: null
personal_website: null
personal_website_note: "No public personal website, but user has worked on websites for clients."
```

### 9.2 Languages

```yaml
languages:
  french: Native
  spanish: Native
  english: C1
  open_to_learning:
    - Japanese
    - Chinese
```

### 9.3 Education

```yaml
education:
  - institution: KEDGE Business School Bordeaux
    degree: MSc Master of Science
    major: Data Analytics for Business
    dates: 2020-2026
    graduation: June 2026
    coursework:
      - Marketing
      - Negotiation
      - Accounting
      - Finance
      - Management
      - Law
      - Ethics
      - Agile management
      - Human resources
      - Excel
      - Machine learning
      - Data management and processing
      - SQL
      - Python
      - APIs
      - LLM manipulation
      - Stochastic programming
      - Statistics
      - Simulation development
      - Business development
      - AI

  - institution: University of Hull
    degree: Bachelor of Arts with Honours
    major: Business Management with Entrepreneurship
    dates: January 2022-June 2024
    coursework:
      - International business
      - Marketing
      - Entrepreneurship
      - Business development
      - Finance
      - Ethics

  - institution: Lycée Philippine Duchesne - ITEC Boisfleury
    degree: Baccalauréat
    major: Spanish European section
    graduation: July 2020
```

## 10. Work Preferences

```yaml
work_preferences:
  target_countries:
    - France
    - United Kingdom
    - Switzerland
    - Spain
    - Luxembourg
    - Belgium
    - Netherlands
    - Northern Europe
    - Italy
    - Latin America
    - Canada
    - Japan
    - China
    - Mexico
    - United States

  priority_cities:
    - Geneva

  preferred_work_mode: Hybrid

  contract_preferences:
    preferred:
      - Permanent contract
      - CDI
    open_to:
      - Temporary contract
      - CDD
      - ESN
      - Consulting company
    not_looking_for:
      - Internship

  availability: Immediate

  salary_strategy: "Flexible depending on the form, role, country, company and market. Avoid giving a fixed amount unless necessary."
  salary_private_reference: "Around 2000 EUR net/month would be a nice baseline, but should not be the default public answer."
  work_authorization: "European passport holder through Italian citizenship. Open to visa processes for strong international opportunities."
```

## 11. Job Target Preferences

The user should be able to select what to search for manually.

If a default order is needed, use:

1. AI Consultant / AI Product.
2. Data Analyst / Business Analyst.
3. Junior Consultant / Strategy Analyst.
4. Marketing Analyst.

## 12. CV Files

The project uses four fixed CV files:

```yaml
cv_files:
  marketing: CV_Sebastian.Vazquez_Anglais-Marketing.pdf
  consulting: CV_Sebastian.Vazquez_Anglais-Consulting.pdf
  data_analysis: CV_Sebastian.Vazquez_Anglais-DataScience.pdf
  ai: CV_Sebastian.Vazquez_Anglais-AI.pdf
```

### 12.1 CV Positioning

#### Marketing CV

Use for roles related to:

- Digital marketing.
- SEO.
- Google Ads.
- Campaigns.
- Customer engagement.
- Consumer behavior.
- CRM.
- Content automation.
- Marketing analytics.

#### Consulting CV

Use for roles related to:

- Consulting.
- Strategy.
- Business transformation.
- Process optimization.
- Stakeholder engagement.
- Client advisory.
- Business analysis.
- Project management.
- Operations improvement.

#### Data Analysis / Data Science CV

Use for roles related to:

- Data analyst.
- Business intelligence.
- SQL.
- Python.
- Power BI.
- Tableau.
- Dashboards.
- Reporting.
- Machine learning.
- Statistical analysis.
- Predictive analytics.
- Data visualization.

#### AI CV

Use for roles related to:

- AI.
- Generative AI.
- LLMs.
- OpenAI API.
- Azure AI.
- Automation.
- AI product.
- AI strategy.
- Process automation.
- Prompt engineering.

## 13. Motivation Letter Preferences

```yaml
motivation_letters:
  default_language: English
  allow_french: true
  language_selection_rule: "Match the job post and company language when useful."
  tone: "Professional, energetic, with a personal connection or short anecdote when relevant."
  max_words: 250
  generate_only_when_needed: true
```

## 14. Core Success Definition

The project is successful if the user can:

1. Track all applications in one reliable place.
2. Paste a job post and get structured data.
3. Quickly choose the right CV.
4. Generate an editable motivation letter when needed.
5. Generate copy-ready answers for application forms.
6. Export the tracker to Excel.
7. Sync the tracker to Google Sheets.
8. Reduce manual repetition without losing control.
