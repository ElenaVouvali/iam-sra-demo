# Current verification status

This file describes the current guided application. Historical live-calibration and implementation reports are preserved in the [external cleanup archive](repository-cleanup.md); their test counts and model results are not current performance claims.

## Offline checks

The final cleanup check completed the full offline suite: **912 tests passed**. This includes an assertion that evaluation uses the confirmed application scoring path. Code compilation passed and all 42 internal documentation link targets resolved.

The checks cover session transitions, confirmed evidence, immutable initial snapshots, original versus hypothetical contexts, scoring validation, request budgets/retries, current UI controls, optional combined assessment, aggregation and exports. The 32-case manual pack's 155 scripted baseline branches are exercised with authored mappings and substituted baseline numbers. Those checks validate progression/state/arithmetic contracts, not live LLM accuracy.

The GPU-free synthetic evaluator completed 35 attempts using `MockConversationClient` through the current initial assessment flow. These are plumbing checks: fixed mock uncertainty cannot establish semantic agreement or scientific validity. Code compilation and internal documentation links are also checked during cleanup.

Reproduce:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python eval/run.py --mock --repeats 1 --output .runtime/evaluation-mock.json
```

## Live and manual evaluation

No live inference, service restart, model download or GPU/deployment change was performed for repository cleanup. Live interpretation and scoring still require testing against the pinned model. Earlier live reports exposed semantic attribution and intensity errors; removing them from the active tree does not establish that those errors are fixed.

Use [the end-to-end walkthrough](../manual-tests/end-to-end-manual-tests.md), [case scripts](../manual-tests/followup-assessment-manual-tests.md) and [blank results sheet](../manual-tests/end-to-end-results-template.csv). Keep T01–T24 development results separate from T25–T32 fresh-validation results. Record stage-1 mismatches separately from follow-up calculations based on the actual baseline. Do not tune authored targets simply to match outputs.

## Scientific interpretation

The +2 progression policy is an explicit pilot design, not a numerical requirement established by FN or GA. Consistent tests demonstrate implementation fidelity, not psychometric validity or accurate ecosystem SRL. FN/ISCTE review, sensitivity analysis and Living Lab calibration remain necessary. See [methodology](methodology.md) and [update-policy rationale](fn-followup-update-policy.md).
