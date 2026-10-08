# Stage-one calibration 7.6.0

The reported errors are mapping and facet-scoring errors, not failures of the mean or bottleneck arithmetic. This change does not alter manual targets, aggregation, bottleneck, follow-ups, model weights or model revision.

## Implementation

- Initial mapping now reads the complete testimony in five disjoint batches of three concerns. Every registered facet is considered once, with only that batch's facet keys allowed. Empty batches are valid. Python merges outputs without assigning positions or scores. This increases mapping inference calls to reduce competing topic distinctions within each request.
- Conditions from later sentences and independent positive judgments remain in scope in each batch. The existing focused route reread remains available when expressed facets accompany an unidentified or conflicting route stance.
- The numeric prompt is shorter and distinguishes evaluation of an effect from consideration of an alternative proposal. It recognizes ordinary-language participation, institutional trust, mechanical reliability, access, visual acceptance and airspace coordination.
- Removed the incorrect blanket veto of score 1 when conditional willingness is recorded. A citizen can categorically refuse an aspect while considering an alternative avoiding it. The LLM must still determine whether the testimony actually establishes categorical refusal.
- Guided numeric generation mirrors existing confirmed-position checks. Opposed facets allow 1–5, supported facets 6–9 and mixed facets 5, with null retained for unavailable evidence. Independent endorsement checks still govern 9. Python does not substitute a number for a model response.
- Evidence remains mandatory. No case IDs, target scores or answer-matching shortcuts are provided to the live model.

## Verification and limits

1,003 software tests passed, including disjoint batch coverage, complete testimony in every batch, scope isolation, preservation of evidence and categorical refusal despite consideration of alternatives. These are software-contract checks, not evidence of model accuracy.

Local pinned-tokenizer preflight checked five batches plus a worst-case full-registry position review for all 32 inputs (192 requests). The largest prompt plus 1,400 reserved output tokens was 3,494 of 4,096. No inputs were truncated.

The live nine-case run was attempted but blocked by local connection permissions (`Operation not permitted`). No live accuracy or demo-readiness claim is made. Results: `.runtime/calibration-v760-demo-cases.json`; context preflight: `.runtime/calibration-v760-context-check.json`.

## Live acceptance check

Start a new UI session after restarting the UI. Confirm prompt version 7.6.0. Run:

```bash
.venv/bin/python scripts/run-initial-manual-tests.py --ids T01,T02,T07,T08,T09,T10,T11,T23,T24 --output .runtime/demo-stage1-v760-results.json
```

Check `matches_expected`, not merely `success`. The latter only indicates that the pipeline completed. Inspect mapping, facet scores and arithmetic separately. A correct final integer can conceal incorrect concerns.

Authored expected initial totals: T01=4, T02=4, T07=3, T08=4, T09=5, T10=3, T11=3, T23=3, T24=6. T24 energy/emissions intentionally remains unassessed because lifecycle emissions are explicitly undecided; not every null is an error.
