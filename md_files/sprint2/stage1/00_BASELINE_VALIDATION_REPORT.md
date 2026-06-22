# Stage 1 Baseline Validation Report

Date: 2026-06-17

## Overall Status

Stage 1 local Windows execution is complete.

Acceptance is conditionally blocked by items that require user-supplied local assets or Mac-side execution:

- Four real CV PDFs are not present in `documents/cvs/`.
- Google Sheets credentials and a dedicated test spreadsheet ID are not present.
- macOS validation must still be run on the MacBook Pro and recorded here.
- Real user-supplied English and French job posts are not present; controlled validation fixtures were used instead.

## Baseline Freeze

- Baseline tag: `sprint1-baseline-2026-06-17`
- Tag object: `0bf1684ceb42a1dbd4de3073974a9189c41ccb62`
- Tagged commit: `763f785b6a4533e60becd1766073cd39451ba92b`
- Commit subject: `Update project with latest changes and improvements`
- Tag message: `Sprint 1 baseline before Stage 2 architecture work`

The tag was created on the current committed MVP code only. It does not include the dirty documentation worktree.

Current worktree state at validation time:

```text
## main...origin/main
 D 01_PROJECT_CONTEXT.md
 D 02_MVP_DEVELOPMENT_PLAN.md
 D 03_TECHNICAL_ARCHITECTURE.md
 D 04_DATA_MODEL_AND_SCHEMAS.md
 D 05_LLM_AND_AUTOMATION_SPEC.md
 D 06_ROADMAP_AND_FUTURE_FEATURES.md
 D README_HANDOFF.md
?? md_files/
```

## Local Baseline Artifacts

- Database backup: `database/applications_stage1_baseline_2026-06-17.db`
- Backup SHA256: `FC4C86B7B41529CAE7C11EB99051E7EC7674C58C35DE476E3FB850E80A421F78`
- English validation fixture: `.tmp/stage1_samples/english_job_post.txt`
- English fixture SHA256: `F31047F6D5F1587F8239CF3110765E9359FBCBD147B4E07B457B1E4A57003931`
- French validation fixture: `.tmp/stage1_samples/french_job_post.txt`
- French fixture SHA256: `49E74C05D5E0F2D64FE42BF74A4D9D877D30DA8B4D2707280631E6CF11717B39`
- Excel validation export: `.tmp/stage1_exports/applications_export_2026-06-17T10-30-39.xlsx`

These artifacts are intentionally local or ignored. They should not be committed except for this report set.

## Database Baseline

Schema snapshot: `md_files/sprint2/stage1/02_CURRENT_SCHEMA_SNAPSHOT.sql`

Table counts:

| Table | Count |
|---|---:|
| applications | 7 |
| companies | 0 |
| contacts | 0 |
| documents | 0 |

## Validation Summary

| Area | Status | Evidence |
|---|---|---|
| Git baseline tag | Pass | Annotated tag exists and points to commit `763f785...` |
| Database backup | Pass | Backup file exists with matching size and recorded hash |
| SQLite schema snapshot | Pass | Schema dumped for 4 current tables |
| Windows tests | Pass | 50 tests passed |
| Streamlit launch | Pass | Headless launch returned HTTP 200 on local port 8502 |
| Ollama availability | Pass | `qwen3:4b` and `llama3.2:latest` installed |
| English extraction fixture | Pass with quality note | Structured JSON returned and validation warnings were empty |
| French extraction fixture | Pass | Structured JSON returned and validation warnings were empty |
| CV recommendation | Pass with asset blocker | Recommendation returned `data_analysis`, but all configured PDF files are missing |
| Motivation letter generation | Pass | English and French drafts generated under 250 words |
| Form-answer generation | Pass | Personal info and common question keys generated |
| Excel export | Pass | Export created for 7 applications |
| Google Sheets live sync | Blocked | Missing `config/google_service_account.json` and spreadsheet ID |
| macOS validation | Blocked | Must be run on MacBook Pro by user |

## Required Before Starting Stage 2

Stage 2 can begin after the Product Owner accepts these documented blockers, or after the following are completed:

1. Add the four real CV PDFs locally at the configured paths.
2. Add Google Sheets service-account credentials locally at `config/google_service_account.json`.
3. Provide a dedicated test spreadsheet ID through `STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID` or local settings.
4. Run the macOS validation checklist in `04_UI_WORKFLOWS_AND_SETUP.md`.
5. Replace or supplement the controlled validation fixtures with real English and French job posts if strict real-world extraction validation is required for Stage 1 acceptance.
