# IAM-SRA2 v4.2 correctness checkpoint

This checkpoint preserves `6bf43209bb2ffd7fa4916954f761d4bad16934c1` and adds targeted corrections on `feat/fn-v42-citizen-adaptive`.

## Four-profile API reliability

The reproduced failure occurred while the controller rendered the final respondent review question. The phrase `Level 4` was flagged by Presidio as a person name (`PERSON`) and the queued job failed before committing the answer. The failure was not a model timeout, respondent inconsistency, queue-loss, or scoring failure. Review templates now name the profile scale (CRL/ORL/TRL) and the provisional result, avoiding the detector collision. Failed jobs also retain a bounded, process-local diagnostic containing the stage/category/code and, for privacy failures, detector labels and schema paths; it is excluded from the participant `JobView` and contains no matched text or traceback. In this restricted execution environment, the real-detector test also requires `TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract`; without it, tldextract attempted to create a lock under the read-only home cache and privacy screening correctly failed closed.

The four-profile controlled API journey reached the expected review/export path for citizen-short, citizen-extended, organisation and technology. Each journey ended non-partially, executed the scorer, recorded respondent validation and produced JSON, JSONL and Markdown exports. The gate passed again after the scoring-outcome metadata change: 1 test passed in 773 seconds. Reproducible protected artifacts are in `.runtime/fn-v42-controlled-four-profile-api-fixed-20261125/`; the pre-fix diagnosis is in `.runtime/fn-v42-agent-citizen-short-api-diagnostic2-20261125/`.

## Scoring and result review

An abstention containing an anchor claim or internal reference is rejected as invalid scoring output. The conversation reports a safe unavailable result, leaves the initial proposal unset, and permits uncertainty/comments with review pending. Exported `scoring_outcome` metadata distinguishes validated score, model abstention (including insufficient evidence or conflict), invalid model output, model errors, and scoring not run for missing scope/evidence or operational limits. Valid numeric scoring remains evidence-cited and must name an adjacent anchor with a participant-readable boundary. A genuine abstention remains allowed when the scorer gives a concrete missing/contradictory-evidence reason.

The historical S6 transcript and S2 transcript have not been rewritten. The S6 contradictory abstention is preserved at `.runtime/fn-v42-a30-stress-S6-extended-adaptive3-corrected2-20261125/`. A deterministic test exercises the correction. Archived S2 included an invalid abstention whose prose named an anchor and embedded its internal anchor ID; the archived scan identifies assistant message index 42. The current validator rejects that shape, but the historical participant artifact remains evidence of the earlier leak and is not represented as fixed retroactively.

## Concern projection to the 15 indicators

The projector runs once on conclusion against active, respondent-provided evidence and the registered v4 bank. It emits exact-quote-linked candidate mappings, or `ambiguous`/`unmapped`; it does not score readiness, alter routing, or expose indicator IDs in chat or participant downloads. Results remain on the in-memory session and are available only through the existing authenticated developer trace. It is a small phrase/concept rule set, not an LLM semantic classifier. The bank loader validates registered identity and source hash. The method has no model calls and cannot claim comprehensive indicator assessment.

The fictional challenge benchmark compares the lexical top-three baseline with this conservative rule projection. Baseline P/R/F1 was 0.299/0.743/0.426 (TP 26, FP 61, FN 9); revision was 0.912/0.886/0.899 (TP 31, FP 3, FN 4). Wildlife-only disturbance is unmapped rather than mapped to Noise; the benchmark also covers negation, ambiguous privacy/safety, cyber controls, multi-indicator answers and unsupported concepts. The rule method correctly left all four reference-unmapped cases unmapped and both ambiguous cases ambiguous. These are exploratory synthetic labels and need IAM/FN expert adjudication; they are not independent ground truth or validated real-world accuracy. The projector remains phrase-dependent and has remaining false positives/negatives.

The evaluation artifact is `.runtime/indicator-projection-v2-final2-20261125/indicator-projection-evaluation-v2.json`. Archived respondent evidence re-evaluated with the current projector is in the same artifact; its original JSON was left untouched. The seven residual binary errors are localized in the per-case table: three false positives involving siting/landscape or broad noise wording, and four missed labels involving access, personal privacy, or training. This highlights the phrase rules' remaining limits.

## Live model and cross-profile limits

Existing S1, S2 and S6 A2/A30 synthetic sessions were used as archived evidence; no additional live inference ran in this checkpoint. The A30 host preflight reported no unique idle supported GPU and retained existing workloads. Liono A2 remains released. Therefore this checkpoint does not establish live Qwen quality for the projection or new rich citizen/organisation/technology personas. Existing ORL/TRL deterministic FN golden-path and four-profile API journeys are local controlled tests, not new live model interviews.

To reproduce the offline indicator comparison:

```bash
cd ~/IAM_CC/iam-sra-demo
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src .venv-api/bin/python scripts/evaluate-indicator-projection-v2.py \
  --transcript .runtime/fn-v42-a2-stress-S1-short-adaptive0-full/S1_unfamiliar_birds_short.json \
  --transcript .runtime/fn-v42-a2-stress-S2-short-adaptive3/S2_privacy_priority_shift_short.json \
  --transcript .runtime/fn-v42-a30-stress-S6-extended-adaptive3-corrected2-20261125/S6_challenging_correction_refusal_extended.json \
  --output .runtime/indicator-projection-replay-$(date +%Y%m%d-%H%M%S)
```

The focused deterministic/API regression group used for this checkpoint:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q \
  tests/test_indicator_projection_v2.py tests/test_indicator_projection_eval.py \
  tests/test_fn_interview.py tests/test_fn_reference_audit.py \
  tests/test_fn_v4_reliability.py tests/test_fn_v4_uncertain_recognition.py \
  tests/test_fn_interpretation.py tests/test_chat_conversation.py \
  tests/test_api_integration.py
```

The recorded result was `312 passed, 1 warning` before the final additive
`scoring_outcome` field. After that field and the authenticated-trace-only
projection routing were added, the affected chat, interpretation and full
four-profile API gate passed again: `196 passed, 1 warning`. The full focused
group can be rerun with the command above.

## Remaining review items

- Have IAM/FN experts validate the synthetic concern-to-indicator reference mappings and candidate rationales before using this projection analytically.
- Expand language coverage and evaluate with independently authored, expert-labelled examples before claiming general indicator alignment.
- Retest abstention rejection against a live A30 scoring response once an idle approved A30 is available.
- Run new richer citizen and unfamiliar ORL/TRL live scenarios sequentially; do not use the occupied A30 or released A2 without availability confirmation.
- The nine-level CRL/ORL/TRL scales remain unchanged. FN example numeric levels are illustrative; current FN citizen reference outputs vary from CRL 5 to 6 according to the evidence and boundary returned by the scorer.
