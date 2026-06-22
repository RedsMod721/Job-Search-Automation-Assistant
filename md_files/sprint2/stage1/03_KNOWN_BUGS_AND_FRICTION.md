# Stage 1 Known Bugs and Friction

Date: 2026-06-17

## Blockers

1. The four configured CV PDFs are missing locally:
   - `documents/cvs/CV_Sebastian.Vazquez_Anglais-Marketing.pdf`
   - `documents/cvs/CV_Sebastian.Vazquez_Anglais-Consulting.pdf`
   - `documents/cvs/CV_Sebastian.Vazquez_Anglais-DataScience.pdf`
   - `documents/cvs/CV_Sebastian.Vazquez_Anglais-AI.pdf`
2. Google Sheets live validation is blocked by missing local credentials and spreadsheet ID:
   - `config/google_service_account.json`
   - `STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID` or configured `google_sheets.spreadsheet_id`
3. macOS validation has not been run yet from the target MacBook Pro.
4. Stage 1 used controlled fixtures in `.tmp/stage1_samples/`, but the database already contains a few real copied job posts that should seed the versioned sample set for later extraction evaluation.

## Product Quality Notes

1. English extraction returned `motivation_letter_required: null` even though the validation fixture states that a motivation letter is requested.
2. The English extracted `job_title` included the fixture suffix `Stage 1 Validation Sample`, which shows extraction is sensitive to validation text in titles.
3. Current CV recommendation still defaults to a fixed available key even when the underlying PDF files are missing.
4. The current Google Sheets sync is a V1 push-style scaffold, not the final bidirectional conflict-safe engine required in Sprint 2.
5. Generated letters can contain model-dependent formatting. Later stages should make output style validation stricter.

## Repository and Environment Friction

1. The worktree has a documentation reorganization in progress: old top-level sprint docs are deleted and `md_files/` is untracked.
2. There are many ignored test and probe database files under `database/` from previous test runs.
3. Dependency versions are not locked. The current Windows virtualenv is using Python 3.14.3, while supported Python versions have not yet been declared.
4. `Get-CimInstance Win32_OperatingSystem` returned access denied on this Windows machine, so OS metadata was gathered through .NET runtime APIs.
5. Running Streamlit normally still requires a terminal in Sprint 1; launcher and packaging work belongs to later stages.

## Confirmed Non-Issues During Stage 1

1. The test suite passed on Windows.
2. The Streamlit app launched headlessly and returned HTTP 200.
3. Ollama is installed with the configured primary model `qwen3:4b`.
4. English and French motivation-letter templates exist at configured paths.
5. Excel export works for the current 7 application records.
