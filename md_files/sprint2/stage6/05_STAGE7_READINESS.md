# Stage 7 Readiness

Date: 2026-06-22

## Stage 7 Target

Stage 7 is job-fit scoring and improved CV selection.

Stage 6 leaves the application with measured extraction output, correction telemetry, and a role-family fixture set that can seed the Stage 7 fit rules.

The newly imported real corpus shows that extraction quality still needs more work before the extraction gate should be considered fully closed.

## Ready Inputs

- Schema version `3` is active.
- Extraction correction table exists.
- Evaluation run tables exist.
- Prompt registry supports active and retired extraction prompt versions.
- Extraction evaluation command exists.
- CI runs the fixture extraction gate.
- Dataset includes the target Stage 7 role families.
- Diagnostics expose extraction evaluation status.
- Real extraction-pair corpus exists under `samples/extraction_eval/real_2026_06_23`.

## Recommended Stage 7 Plan

1. Add role-family taxonomy.
2. Add skill taxonomy.
3. Add deterministic job-fit rule model.
4. Keep job-fit scoring separate from CV recommendation.
5. Add hard gates.
6. Add soft warnings.
7. Add explainable score breakdown.
8. Use Stage 6 extracted fields as inputs.
9. Add minimum-confidence behavior for CV selection.
10. Add tests for each rule category.

## Carry-Forward Notes

- Use correction telemetry to identify fields that should be treated as low-confidence.
- Use Stage 6 dataset fixtures as the first job-fit test fixtures.
- Treat current real-corpus extraction output as low-confidence until the live benchmark reaches the configured gate.
- Do not block jobs silently; show hard-gate reasons and soft warnings.
- CV recommendation should return insufficient confidence when evidence is weak.
