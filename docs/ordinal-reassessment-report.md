# Consistent ordinal reassessment — offline verification

Reviewed baseline: ffa601f on local main, clean at task start. No unrelated work, dependencies, GPU allocation or deployment configuration changed. Local FN PDF physical pp.5–9 was reread. The source supplies illustrative scores/outcomes, not a universal update equation.

## Implemented behaviour

- One ordinal3.0 descriptive decision policy replaces model-generated integers in the guided scorer. Python applies predicates after confirmation, then the unchanged aggregate policy.
- Clear acceptance8 is distinct from explicit authored unqualified endorsement9. Yes/choices/applicability agreement alone cannot satisfy9. Highest candidates receive a bounded independent semantic check.
- Confirmed equivalent unchanged facet meanings can retain their source decision, with exact original/applicability links. Mitigated or changed meanings are reviewed; decreases are allowed. Unknowns/contradictions stay unavailable.
- Independent attribution, decisiveness, confirmations, immutable initial snapshots, original/modified isolation, all15 concerns and answer-revision invalidation remain covered by regressions.
- Session-local bounded exact-request caching, edit invalidation, stage call/retry/latency records and plain-language UI progress reduce repeated work without new unconditional model reviews.
- Export5.3 adds rule/policy/origin/source records for every domain and profile. Existing field/legacy adapter compatibility and historical files are preserved.
- FN replay now fails when mandatory evidence, rule, context, arithmetic or revision checks fail. Separate statuses distinguish completion, correctness and model use. Additional bounded ordinal contrast runner covers15 synthetic cases, including sparse/mixed answers and valid/invalid capacity/facility attributions.

## FN before/after evidence

| Status and proposal | Medical benefit | Noise | Viewing privacy | Mean inputs / mean | Cap / result |
|---|---:|---:|---:|---|---|
| Previously recorded live FN, original |8|3|2|3 /13÷3=4.3333|4 /4|
| Previously recorded live FN, modified |9|8|9|3 /26÷3=8.6667|none /9|
| New controlled descriptive fixture, original |8|3|2|3 /13÷3=4.3333|4 /4|
| New controlled descriptive fixture, accepted modifications + unchanged medical support |8|8|8|3 /24÷3=8|none /8|

The last two rows are deterministic controlled-meaning tests, **not new Qwen results**. Original→modified changes compare proposals. The unchanged medical8 is reused only after explicit equivalent applicability. Modified privacy/noise8 follow clear acceptance descriptors; cautious/qualified acceptance would use6/7, and remaining objections can stay low. The table does not force a live FN outcome.

The exact source fixture with visual4 still verifies8/3/4/2→mean4.25→cap4→result4. The stricter three-dimension mapping excludes unsupported visual/infrastructure/airspace evidence; denominator differences are visible. The new illustrative modified8 differs from FN's suggested6–7 because FN provides no complete anchor/update formula. No single-example tuning or fixed bonuses were introduced.

## Verification and live status

Complete offline suite: **415 passed** (13.11 seconds on the recorded full run). Compile checks and git diff --check passed. There are35 new parametrized regression checks beyond the baseline380. Regression coverage includes all nine predicates; highest eligibility; unchanged reuse and policy/construct invalidation; changed support/decreases; Skip/Unsure; contextual evidence; cache invalidation/isolation/failures; complete exports; broken arithmetic/attribution checks; UI session-client persistence and hidden scores; transport failures and nonzero disabled-replay exits. Existing scope, blocker, contradictory clarification, joint acceptance and editing regressions are retained.

**Live attempts in this task:0.** The user explicitly said not to use GPU. No live inference, GPU execution, model service start/stop or restart was attempted. Disabled FN and ordinal runs record not_attempted/live_model_used=false and intentionally exit1; mock/double results are never labelled live passes. New live stage latency, retry rates and memory use are therefore unavailable, not0. Offline request metrics are transport-double assertions, not V100 performance measurements.

Before that restriction, bounded read-only health/log inspection found both project endpoints unavailable; historical logs contained HTTP500 and shutdown messages. The shutdown cause is unknown. No recovery was attempted, and no conclusion about the server's current health is inferred from those old logs. The deployment/model/environment are unchanged.

## Limits and commands

Semantic descriptors and independent reviewers can still misattribute meaning or intensity. Full correctness of final attribution guards plus the new policy requires an authorized live replay. Minimum3 can still prevent an aggregate; no coverage rule was relaxed. Ordinal averaging, anchors, shared construct, facet minimum, endorsement criterion and bottleneck generalization are experimental application extensions requiring FN calibration, not psychometric or population validity.

Offline tests:

    cd /home/elvouvali/IAM_CC/iam-sra-demo
    PYTHONPATH=src .venv/bin/python -m pytest -q
    PYTHONPATH=src .venv/bin/python -m compileall -q src app.py scripts
    git diff --check

GPU-free labelled UI demonstration:

    IAM_MOCK=1 PYTHONPATH=src .venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502

Real demo, only after GPU use is permitted and the existing endpoint is healthy:

    scripts/health-check.sh
    scripts/start-ui.sh

Project-only UI restart if needed (not executed):

    scripts/stop-ui.sh
    scripts/start-ui.sh

Existing vLLM launch remains scripts/start-vllm.sh; no launch/runtime argument changed. This report does not recommend starting it during the no-GPU restriction. From the laptop use ssh -N -L8502:127.0.0.1:8501 elvouvali@liono.microlab.ntua.gr and open http://localhost:8502 for the real server UI.

Later authorized serial live checks:

    PYTHONPATH=src .venv/bin/python scripts/replay-fn-evidence.py
    PYTHONPATH=src .venv/bin/python scripts/replay-ordinal.py --cases medical_short qualified_noise medical_privacy_mixed
    PYTHONPATH=src .venv/bin/python scripts/replay-attribution.py --cases altitude_only traffic_separation landing_pad

Each command writes a Git-ignored report and exits nonzero for mandatory failure/unexecuted cases. No pushing or service restart is part of this delivery.
