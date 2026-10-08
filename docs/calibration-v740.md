# Initial interpretation calibration 7.4.0

The reported FN response supports medical benefit and opposes noise and private viewing. Its requested industrial-area flight path is a remedy for those effects, not evidence of a ground facility or land allocation position. The expected initial concern scores remain privacy 2, noise 3 and medical benefit 8; the capped initial aggregate is 4/9. No expected score was rewritten to match model output.

The active production path is the single-request `direct_interpretation` mapper. Its prompt and facility/land facet definitions now distinguish the evaluated experience from a proposed remedy, require a separate evaluation before adding another facet, and explicitly allow an empty facet array for bare route positions or irrelevant text. Independently expressed uncertainty, support and genuine ground-facility objections remain eligible. Numerical scoring uses the existing anchors; unsupported facility objects cannot acquire scores just from a routing condition. This is prompt calibration, not model-weight training or a deterministic keyword correction.

`manual-tests/routing-facility-mapping-cases.json` adds four development contrasts: flight rerouting for noise; actual landing-pad relocation; actual protection of garden land; and flight avoidance for injury risk. It is a mapping-only pack. Existing fresh-validation responses and score targets remain unchanged.

The final UI shows one updated SRL. Historical concern scores, arithmetic and policy adjustments remain available in exports rather than occupying the final slide.

Validation: the local pinned tokenizer checks all 48 initial/privacy/routing cases without a network request; see `.runtime/calibration-v740-context-check.json`. This checks context fit, not semantics. The attempted live development run is recorded in `.runtime/calibration-v740-development.json`; it was blocked by `Operation not permitted` contacting the model. No improved live accuracy is established.

When the live endpoint is reachable, run development comparisons first:

```bash
.venv/bin/python scripts/run-initial-manual-tests.py --mapping-only --check-followups --output .runtime/mapping-v740-development.json
.venv/bin/python scripts/run-initial-manual-tests.py --mapping-only --case-file manual-tests/routing-facility-mapping-cases.json --output .runtime/routing-v740-development.json
.venv/bin/python scripts/run-initial-manual-tests.py --check-followups --output .runtime/scoring-v740-development.json
```

Only then evaluate the existing fresh-validation split separately. Neither unit tests with scripted model responses nor context-fit checks establish generalization to every possible citizen answer.
