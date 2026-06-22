# Stage 6 Readiness

Date: 2026-06-19

## Stage 6 Target

Stage 6 is extraction evaluation and prompt/model improvement.

Stage 5 leaves the app with a stable synchronized tracker and a safer persistence layer, so Stage 6 can focus on measuring extraction quality.

## Ready Inputs

- Local database is schema version `2`.
- Sync outbox is healthy.
- Google Sheet reflects all 7 current local applications.
- Manual, startup, timer, and change-triggered sync paths exist.
- Recovery backups exist.
- Diagnostics report database, sync, Sheets, templates, CVs, and Ollama status.
- Prompt registry exists from Stage 3.

## Recommended Stage 6 Plan

1. Create labeled extraction evaluation dataset.
2. Include English and French job posts.
3. Include LinkedIn, company site, Workday/ATS-style posts.
4. Store expected extraction JSON.
5. Record actual extraction outputs.
6. Calculate field-level accuracy.
7. Add validators for hallucinated salary/company size and missing required fields.
8. Add user-correction capture from review edits.
9. Compare configured local models.
10. Version prompt/model configurations.
11. Add regression tests for known extraction failures.

## Guardrails

- Do not let automatic sync write evaluation sample data unless it is meant to become a tracked application.
- Keep real job-post samples in ignored local locations unless sanitized.
- Avoid changing prompt behavior without evaluation output.
- Preserve manual review before save.

