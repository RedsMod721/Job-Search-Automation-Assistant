# Stage 1 Test Results

Date: 2026-06-17

## Environment

Workspace:

```text
C:\Users\vazqse01\Job Search Automation Assistant
```

Runtime:

```text
OS: Microsoft Windows 10.0.26200, X64
Python: 3.14.3
Streamlit: 1.58.0
pytest: 8.4.2
```

Ollama:

```text
NAME               ID              SIZE      MODIFIED
llama3.2:latest    a80c4f17acd5    2.0 GB    3 months ago
qwen3:4b           359d7dd4bcda    2.5 GB    3 months ago
```

Note: `Get-CimInstance Win32_OperatingSystem` returned access denied in this Windows environment. OS metadata above was recorded through .NET runtime APIs.

## Dependency Snapshot

```text
altair==6.2.1
annotated-types==0.7.0
anyio==4.13.0
attrs==26.1.0
blinker==1.9.0
cachetools==7.1.4
certifi==2026.5.20
cffi==2.0.0
charset-normalizer==3.4.7
click==8.4.1
colorama==0.4.6
cryptography==48.0.1
et_xmlfile==2.0.0
gitdb==4.0.12
GitPython==3.1.50
google-auth==2.53.0
google-auth-oauthlib==1.4.0
gspread==6.2.1
h11==0.16.0
httptools==0.8.0
idna==3.18
iniconfig==2.3.0
itsdangerous==2.2.0
Jinja2==3.1.6
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
MarkupSafe==3.0.3
narwhals==2.22.1
numpy==2.4.6
oauthlib==3.3.1
openpyxl==3.1.5
packaging==26.2
pandas==2.3.3
pillow==12.2.0
pluggy==1.6.0
protobuf==7.35.1
pyarrow==24.0.0
pyasn1==0.6.3
pyasn1_modules==0.4.2
pycparser==3.0
pydantic==2.13.4
pydantic_core==2.46.4
pydeck==0.9.2
Pygments==2.20.0
pytest==8.4.2
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
python-multipart==0.0.32
pytz==2026.2
PyYAML==6.0.3
referencing==0.37.0
requests==2.34.2
requests-oauthlib==2.0.0
rpds-py==2026.5.1
six==1.17.0
smmap==5.0.3
starlette==1.3.1
streamlit==1.58.0
tenacity==9.1.4
toml==0.10.2
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2026.2
urllib3==2.7.0
uvicorn==0.49.0
watchdog==6.0.0
websockets==16.0
```

## Automated Tests

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Result:

```text
platform win32 -- Python 3.14.3, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\vazqse01\Job Search Automation Assistant
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0
collected 50 items

tests\test_company_search.py ............................
tests\test_config_loading.py ..
tests\test_cv_matcher.py ....
tests\test_database_init.py ..
tests\test_excel_exporter.py .
tests\test_extraction_review.py ........
tests\test_extractor.py ..
tests\test_generated_assets.py ..
tests\test_sheets_sync.py .

50 passed in 3.71s
```

## Streamlit Launch

Command shape:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.port 8502 --browser.gatherUsageStats false
```

Result:

```text
STREAMLIT_STATUS=200
STREAMLIT_EXITED=True
```

## Workflow Probe Results

Extraction:

| Fixture | Status | Company | Job title | Detected language | Notes |
|---|---|---|---|---|---|
| English | Pass | Northstar Analytics | AI Product Analyst - Stage 1 Validation Sample | English | `motivation_letter_required` returned `null` despite the fixture saying a letter is requested |
| French | Pass | Atelier Conseil Digital | Consultant Junior Data et IA | Francais | No validation warnings |

CV recommendation:

```text
recommended_cv: data_analysis
secondary_cv: consulting
confidence_score: 0.52
matched_keywords: SQL, Python, Power BI, Tableau, dashboard
```

Asset status:

```text
Missing CV PDFs:
- documents/cvs/CV_Sebastian.Vazquez_Anglais-Marketing.pdf
- documents/cvs/CV_Sebastian.Vazquez_Anglais-Consulting.pdf
- documents/cvs/CV_Sebastian.Vazquez_Anglais-DataScience.pdf
- documents/cvs/CV_Sebastian.Vazquez_Anglais-AI.pdf

Templates present:
- documents/templates/motivation_letter_en.txt
- documents/templates/motivation_letter_fr.txt
```

Generation:

```text
English letter: generated, 228 words, no warnings
French letter: generated, 235 words, no warnings
Form answers: generated for Company Website, no warnings
Excel export: .tmp/stage1_exports/applications_export_2026-06-17T10-30-39.xlsx
Exported application count: 7
```

Google Sheets:

```text
Status: BLOCKED
Missing:
- config/google_service_account.json
- STAGE1_GOOGLE_SHEETS_SPREADSHEET_ID or config google_sheets.spreadsheet_id
```

## macOS Validation

Not run from this Windows workspace.

Required command on Mac after cloning and installing dependencies:

```bash
python -m pytest
```

Record the full output here before treating Stage 1 as fully accepted on the primary Mac.
