# Stage 5 Known Bugs and Friction

Date: 2026-06-19

## Current Friction

1. Timer sync depends on the Streamlit app being open.
   - The implementation uses browser refresh with the configured interval.
   - There is no separate background worker or OS scheduler.

2. Stage 5 is push-only.
   - Remote edits in Google Sheets are not pulled back into SQLite.
   - `sync_conflicts` exists for future bidirectional work but is not active.

3. Tombstones are pushed as row updates, not remote row deletes.
   - This preserves history and avoids accidental remote deletion.
   - A future UX can decide whether hidden/deleted Sheet rows are desirable.

4. Live sync updated existing rows instead of creating rows.
   - Result: `updated=7`, `created=0`.
   - This is expected because the configured Sheet already had rows for the local application IDs.

5. Existing Stage 4 duplicate application group still exists.
   - It did not block sync.
   - It should be reviewed before relying on the Sheet as a clean operational view.

## Validation Friction

1. Mac validation was not run during Stage 5.
   - Windows validation passed.

2. `pip-audit` requires network access.
   - The sandboxed run failed through a refused local proxy.
   - The approved normal-network run passed.

## Operational Notes

1. Change-triggered sync is opportunistic and synchronous inside the Streamlit request.
   - If Google is unavailable, local saves still succeed and outbox retries later.

2. Startup sync queues all applications.
   - This ensures the Sheet catches up after offline work.
   - Row identity by `Application ID` prevents duplicate row creation.

3. `config/google_service_account.json` remains ignored.
   - Do not commit credentials.

