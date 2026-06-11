# README_HANDOFF.md

# Job Search Automation Assistant - Developer Handoff Package

This package contains the documentation needed to build the Job Search Automation Assistant.

## Files

1. `01_PROJECT_CONTEXT.md`
   - Product context, user need, stable user information, constraints and MVP scope.

2. `02_MVP_DEVELOPMENT_PLAN.md`
   - Step-by-step MVP development plan with phases and acceptance criteria.

3. `03_TECHNICAL_ARCHITECTURE.md`
   - Technical architecture, modules, folder structure, data flows and security rules.

4. `04_DATA_MODEL_AND_SCHEMAS.md`
   - SQLite schemas, JSON schemas, Google Sheets columns and data rules.

5. `05_LLM_AND_AUTOMATION_SPEC.md`
   - Local LLM behavior, prompts, automation limits, motivation letter and form helper rules.

6. `06_ROADMAP_AND_FUTURE_FEATURES.md`
   - Future versions after MVP, including Chrome extension, search, contact finder and analytics.

7. `config_examples/`
   - Example YAML config files for the app.

## Important Development Rule

The project is a semi-automated assistant, not an auto-apply bot.

The tool must never automatically click final application submission buttons, mass scrape LinkedIn, auto-send messages, bypass CAPTCHA, or run hidden background application actions.

The user must remain in control.
