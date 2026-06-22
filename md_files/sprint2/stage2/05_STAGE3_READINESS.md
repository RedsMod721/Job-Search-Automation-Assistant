# Stage 3 Readiness

Date: 2026-06-17

## Ready for Stage 3

Stage 2 makes the repository ready for the core application refactor because:

- Dependencies are locked.
- Runtime and development dependencies are separated.
- CI exists for Windows and macOS.
- Checks are repeatable.
- Config supports local overrides.
- Public defaults are safer.
- TLS behavior is explicit and tested.
- Diagnostics expose missing local dependencies before deeper refactors.
- The Google Sheets path stays manual-first and local-only until the sync triggers are refactored behind a service boundary.

## Stage 3 Starting Point

The main Stage 3 target remains unchanged:

```text
Separate Streamlit UI from domain logic before adding the extension and scheduler.
```

Current state:

- `app.py` still owns the Streamlit tabs and many workflow helpers.
- Core modules in `src/` are importable and covered by tests.
- No business service boundary exists yet.
- No repository-layer abstraction exists yet.
- Prompts are still embedded in Python modules.

## Recommended Stage 3 First Moves

1. Split Streamlit page rendering into page modules without changing behavior.
2. Extract application workflow functions into service modules callable without Streamlit.
3. Introduce typed service result objects only where they clarify existing behavior.
4. Move prompt templates into a prompt registry after workflow seams are stable.
5. Preserve the manual Google Sheets button, app-start sync hook, and periodic sync hook while the UI is being split from domain logic.

## Stage 3 Guardrails

- Do not introduce database migrations yet; that is Stage 4.
- Do not implement automatic Google Sheets push sync yet; that is Stage 5.
- Do not add FastAPI or background workers yet; that is Stage 10.
- Keep user-facing behavior stable while refactoring.
- Keep the Stage 2 checks passing after each meaningful refactor step.
