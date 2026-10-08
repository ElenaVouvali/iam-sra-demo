# Manual-case prompt calibration, 7.3.0

This is prompt calibration of the existing Qwen3-8B model, not weight training. T01–T24 and the privacy development pack informed the changes. T25–T32 were not used to select prompt changes; keep their live results separate. All numerical targets are authored experimental expectations, not established scientific ground truth.

The previous development report (`mapping-development-20261007-085814.json`, an older inactive pipeline) exposed conditional acceptance being treated as current support/mixed, lost uncertainty, conditions crossing facet boundaries and invented neighboring facets. These historical failures motivate checks; they do not measure the active prompt.

The active prompt now states distinctions for current versus future acceptance, prerequisites versus ongoing obligations, mixed versus uncertain positions, independent facets within one concern, generic route answers, and nearby constructs such as privacy/security, skills/training and medical support/awareness/equity. No example scores or automatic keyword overrides are added to interpretation. Existing ordinal scoring, aggregation and progression policy remain unchanged. No extra initial inference calls are added.

Run all live checks from the repository directory:

```bash
.venv/bin/python scripts/run-calibration.py
```

This runs development mapping with follow-up selection, the privacy mapping pack, development scoring with follow-up selection, and fresh-validation scoring with follow-up selection. It preserves four reports under `.runtime/calibration-*.json` and a summary. Successful transport is distinct from matching expectations. A blocked live preflight stops the run. Development mismatches do not suppress the separate validation report. The script never updates prompts or expected answers automatically. It tests selected follow-up IDs, not citizen answers or the entire stage-2 conversation.

Inspect missing/unexpected facets, positions, conditions, selected question IDs, numerical facet scores, aggregate discrepancies, execution failures and latency separately. A validation case used for subsequent tuning becomes development data; new independent validation is then required. A failed case must not be corrected before being counted as a model failure.

The agent's live preflight is blocked by `Operation not permitted`. Prompt changes therefore remain an unvalidated calibration candidate until these live reports are available. Engineering tests and offline context checks do not substitute for model runs.
