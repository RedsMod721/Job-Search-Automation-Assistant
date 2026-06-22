# Stage 2 Environment and Tooling

Date: 2026-06-17

## Supported Python

Declared support:

```text
>=3.12,<3.15
```

CI matrix:

```text
Python 3.12, 3.13, 3.14
Windows latest
macOS latest
```

## Dependency Strategy

Canonical:

```powershell
uv sync --group dev
```

Lock file:

```text
uv.lock
```

Runtime fallback:

```powershell
pip install -r requirements.txt
```

Development fallback:

```powershell
pip install -r requirements-dev.txt
```

## Tooling

Configured in `pyproject.toml`:

- Ruff formatter.
- Ruff linter.
- mypy type checker.
- Bandit security scan.
- pip-audit dependency audit.

Optional pre-commit:

```powershell
uv run pre-commit install
uv run pre-commit run --all-files
```

## CI

Workflow:

```text
.github/workflows/ci.yml
```

CI runs:

- `uv sync --group dev`
- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run mypy app.py src tests`
- `uv run pytest`
- `uv run bandit -c pyproject.toml -r app.py src`
- `uv run pip-audit --cache-dir .tmp/pip-audit-cache`
- `uv run python scripts/diagnostics.py --json`

## Local Config Convention

Tracked base files:

```text
config/profile.yaml
config/documents.yaml
config/settings.yaml
config/form_answers.yaml
```

Tracked examples:

```text
config/profile.example.yaml
config/settings.example.yaml
```

Ignored local overrides:

```text
config/profile.local.yaml
config/documents.local.yaml
config/settings.local.yaml
config/form_answers.local.yaml
```

Precedence:

```text
base YAML
local YAML
environment variables
```

## Network Configuration

Tracked default:

```yaml
network:
  verify_tls: true
  custom_ca_bundle: ""
  http_proxy: ""
  https_proxy: ""
  no_proxy: ""
  request_timeout_seconds: 30
```

Environment overrides:

```text
JOB_SEARCH_VERIFY_TLS
JOB_SEARCH_CA_BUNDLE
REQUESTS_CA_BUNDLE
CURL_CA_BUNDLE
HTTP_PROXY
HTTPS_PROXY
NO_PROXY
JOB_SEARCH_REQUEST_TIMEOUT_SECONDS
```

