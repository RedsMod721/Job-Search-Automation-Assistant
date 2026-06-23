# Stage 6 Known Bugs and Friction

Date: 2026-06-22

## Known Friction

1. The committed Stage 6 dataset is sanitized and representative.
   - It is suitable for regression testing.
   - It is no longer the only evidence source; a committed real corpus now exists under `samples/extraction_eval/real_2026_06_23`.

2. The fixture evaluation runner uses golden expected outputs.
   - This is intentional for CI stability.
   - Real model quality still requires `--runner live`.

3. The real local corpus live benchmark currently fails the quality gate.
   - `stage6-v1` with `qwen3:4b`: `field_accuracy 0.4003`.
   - `stage6-v2` with `qwen3:4b`: `field_accuracy 0.5555`.
   - JSON reliability stayed at `1.0`, so the main issue is field quality, not JSON validity.

4. M3 Pro live model benchmarking has not been run yet.
   - The command exists.
   - The benchmark needs to be repeated on the Mac with Ollama models installed.

5. The default extraction model is still `qwen3:4b`, but the real corpus shows it is not yet a proven default for extraction quality.
   - The sanitized dataset passed.
   - The real dataset failed.
   - A final cross-device default should be chosen after stronger prompt/model benchmarks.

6. Rule validators are conservative regex and heuristic checks.
   - They reduce obvious hallucinated salary/company-size values.
   - They are not a full semantic verifier.

7. User correction-rate trend is not available yet.
   - Stage 6 now records corrections.
   - A trend needs real review usage over time.

8. Motivation-letter and form-answer prompt bodies still live in their generator modules.
   - The prompt registry tracks metadata for all three prompt families.
   - Full prompt-file extraction can be done later if needed.

9. Existing tracker duplicate data from earlier stages is not solved by Stage 6.
   - This remains a database/data hygiene issue, not an extraction evaluation blocker.

## Non-Blockers

- Google Sheets sync remains healthy after schema version 3.
- Diagnostics report extraction evaluation status, and the latest real live benchmark should be read as a quality blocker.
- The local database integrity check passes.
- CI now has an extraction regression gate.
