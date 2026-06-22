# Stage 1 Sample Dataset Manifest

Date: 2026-06-17

## Dataset Status

Stage 1 required English and French extraction validation. No real user-supplied job posts were present in the workspace, so controlled local fixtures were created under `.tmp/stage1_samples/`.

These fixture files are ignored and should not be committed. This manifest records their purpose, hashes, and extraction results without storing the full fixture text in committed documentation.

## Local Fixtures

| File | Language | Type | SHA256 |
|---|---|---|---|
| `.tmp/stage1_samples/english_job_post.txt` | English | Controlled validation fixture | `F31047F6D5F1587F8239CF3110765E9359FBCBD147B4E07B457B1E4A57003931` |
| `.tmp/stage1_samples/french_job_post.txt` | French | Controlled validation fixture | `49E74C05D5E0F2D64FE42BF74A4D9D877D30DA8B4D2707280631E6CF11717B39` |

Existing repository sample:

```text
samples/sample_job_posts/example_ai_consultant.txt
```

Additional real samples already stored in the database:

| Application ID | Company | Job Title | Language | Notes |
|---|---|---|---|---|
| `9657d318-fd7f-4075-820f-653fd0c0491c` | Alibaba Cloud | GenAI Business Development - Paris | English | AI and cloud transformation role with hybrid work |
| `326ca5cf-6b2e-4abe-abb5-e82724e7f0f5` | Deloitte | Stage de fin d'études en Conseil en Transformation F/H Lyon | Français | Consulting / transformation internship example |
| `3c8fec37-ee1a-489c-bc3a-081d38d50272` | Smile | Business Analyst E-Commerce | French | E-commerce business-analysis example copied from a real posting |

These database rows are better seed examples than the temporary validation fixtures because they already represent real copied job descriptions. They can be promoted into the future versioned extraction dataset once the Stage 6 sample set is built.

## Extraction Results

English fixture:

```text
status: PASS
company_name: Northstar Analytics
job_title: AI Product Analyst - Stage 1 Validation Sample
detected_language: English
motivation_letter_required: null
validation_warnings: none
```

French fixture:

```text
status: PASS
company_name: Atelier Conseil Digital
job_title: Consultant Junior Data et IA
detected_language: Francais
motivation_letter_required: null
validation_warnings: none
```

## Follow-Up for Stage 6

The Stage 6 extraction evaluation dataset should replace these temporary fixtures with versioned real job posts covering:

- English and French.
- LinkedIn copied text.
- Greenhouse.
- Lever.
- Ashby.
- Workday.
- AI Consultant and AI Product roles.
- Data Analyst and Business Analyst roles.
- Junior Consultant and Strategy Analyst roles.
- Marketing Analyst roles.
- Short and long descriptions.
- Missing salary cases.
- Remote, hybrid, onsite, and multi-location cases.

Each future fixture should include expected JSON, prompt version, model version, output JSON, field-level metrics, and user-correction records.
