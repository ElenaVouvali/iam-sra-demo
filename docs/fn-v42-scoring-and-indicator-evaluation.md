# IAM-SRA v4.2 scoring and indicator evaluation

Checkpoint: 25 November 2026. The registered FN PDFs and v4 readiness bank are unchanged; their registered hashes still validate. Results below are prototype experiments, not FN approval or independent validation.

## Scoring corrections

The repeated CRL failures had several distinct causes. `ProfileMatch` made rationale fields nullable but did not require a boundary; the generic retry instruction also suggested empty optional fields. After those fields became required, the validator still accepted an alternative anchor that was not adjacent, or a boundary that discussed a different level from `alternative_anchor_id`. The scorer now requires the fields, Python checks adjacency and that the first boundary sentence names the same adjacent label/level, and the retry instruction is scorer-specific. Short internal message and exposure IDs were also falsely classified as person names by privacy screening. The scorer request uses neutral evidence/exposure aliases and maps citations back to original IDs before exact-quote validation. Original exports are unchanged.

CRL Awareness has a separate explicit instruction: one respondent-identified possible benefit, risk or concern can support that anchor, including a concern first articulated after an explanation or suggested topic. Such evidence is not described as prior knowledge. Exact quotations remain required for numeric suggestions; insufficient or contradictory evidence may still produce a model abstention. A privacy/schema/adjacency rejection is recorded as an unavailable result, not an abstention.

## Live scoring replays

The current scoring-only artifacts are under `.runtime/fn-v42-a30-score-replays-validated3-20261125/`. They use the A30 endpoint, Qwen3-8B FP16, thinking enabled, an 8,192-token context and the existing bounded scorer. Evidence came from already-saved FN citizen-short, FN citizen-extended and S1 interviews; no full interview was replayed for scorer debugging.

| Evidence | Accepted provisional suggestion | Adjacent comparison | Evidence / status |
| --- | --- | --- | --- |
| FN citizen short | CRL 5, Co-design | CRL 4, Critical engagement | Exact citations from the saved respondent record; structurally and adjacency validated. FN's worked example says CRL 6, so this is a substantive discrepancy. A separate accepted A30 replay selected CRL 6, showing score instability on identical evidence. |
| FN citizen extended | CRL 5, Co-design | CRL 6, Informed evaluation | Exact citations; valid adjacent comparison. This differs from FN's illustrative CRL 6. |
| S1 unfamiliar / nesting birds | CRL 2, Awareness | CRL 1, Recognition | Exact citations include m21, m23, m25 and m28. The evidence is respondent-expressed during the interview, after information exposure; it is not prior knowledge. |

These are provisional model suggestions, not verified readiness findings. On identical short-reference evidence, two accepted A30 runs selected levels 5 and 6. Thus the structural failure is corrected, but scoring consistency and agreement with FN's worked interpretation remain open methodological/model-quality issues. Model abstention, invalid output, and insufficient evidence are kept distinct in the replay JSON.

## Indicator projection benchmark

`eval/iam_indicator_concern_cases_v1.json` contains 17 fictional answers spanning all 15 registered IAM indicators, multi-indicator and deliberately unmapped cases, including wildlife. The offline evaluator uses only official indicator names and definitions from the registered bank (`scripts/evaluate-indicator-projection.py`); it makes no model call. Results are in `.runtime/fn-v42-indicator-projection-benchmark4-20261125/indicator-projection-evaluation.json`.

The top-three lexical baseline produced TP=13, FP=31, FN=5: precision 0.295, recall 0.722, F1 0.419. It correctly left 1 of 2 deliberately unmapped cases without a candidate and incorrectly proposed the Noise indicator for the wildlife case. All candidates are labelled unreviewed and tied to exact fictional evidence. This baseline is too imprecise for application behavior. The saved live S1/S2 annotations preserve concerns but currently return zero Qwen indicator IDs; that is under-mapping, not evidence of validated alignment. No 15-assessment-per-turn feature was added.

## Adaptive evidence and artifacts

- S1 adaptive-off: `.runtime/fn-v42-a2-stress-S1-short-adaptive0-full/`.
- S1 adaptive-on: `.runtime/fn-v42-a2-stress-S1-short-adaptive3/`.
- S2 privacy-priority change: `.runtime/fn-v42-a2-stress-S2-short-adaptive3/`.
- The controlled S1 comparison on A2 recorded 0 versus 3 adaptive-question events; adaptive wording specifically named bird disturbance near wetlands. The participant's newer privacy/noise priorities remained respondent-selected, and earlier topics were retained as history.
- An S1 annotation once added “residential areas” to a wildlife answer. Topic evidence now accepts only issue-label terms grounded in the exact quote, allowing simple inflections such as “land”/“landing” while rejecting extra affected groups/impacts. Unit regression tests cover both cases.

The six fictional personas live in `eval/fn_citizen_stress_v1.json`; `scripts/smoke-fn-citizen-stress.py` writes screened JSON/JSONL, Markdown, metrics and authenticated developer traces. Long live cases emit per-question progress on stderr.

## Reproduction

Run these from the repository on Liono with the A30 model tunnel active at `127.0.0.1:18006`:

```bash
IAM_MODEL_VARIANT=fp16 IAM_MODEL_THINKING=1 IAM_SRA_ON_DEMAND_GPU=0 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
.venv-api/bin/python scripts/replay-chat-score.py \
  --input .runtime/fn-v42-a2-reference-short-verified-20261125/citizen_short.json \
  --input .runtime/fn-v42-a2-reference-extended-20261125/citizen_extended.json \
  --input .runtime/fn-v42-a2-stress-S1-short-adaptive0-full/S1_unfamiliar_birds_short.json \
  --base-url http://127.0.0.1:18006 \
  --output .runtime/choose-a-new-ignored-output-directory
```

The indicator baseline can be reproduced without the GPU:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
.venv-api/bin/python scripts/evaluate-indicator-projection.py \
  --transcript .runtime/fn-v42-a2-stress-S1-short-adaptive0-full/S1_unfamiliar_birds_short.json \
  --transcript .runtime/fn-v42-a2-stress-S2-short-adaptive3/S2_privacy_priority_shift_short.json \
  --output .runtime/choose-a-new-ignored-output-directory
```

For future interviews the currently validated model-host command is `python3 scripts/model-host.py start davinci-a30 --variant fp16 --thinking --port 18006`. AWQ is only supported by this repository's launch policy on Liono A2; switching to Davinci therefore preserves Qwen3-8B, thinking and context/timeout policy, but changes quantization to FP16. The SSH tunnel terminal must remain open.

## Remaining review items

- FN review is needed for the repeated CRL 5 versus illustrative CRL 6 discrepancy and score variance on identical evidence.
- The lexical 15-indicator baseline must not be used as an automatic mapping; expected mappings themselves need methodological review.
- The wildlife concern has no explicit matching v4 indicator and should remain visible without forced mapping.
- A30 FP16 and Liono A2 AWQ are different inference variants; cross-hardware scores are not a controlled same-precision comparison.

## A30 migration and later runs

The A2 vLLM process was stopped and its process record removed after the A30 endpoint was healthy; Liono showed only 1 MiB allocated immediately after shutdown. Later GPU utilization changed, consistent with other users taking the freed device. Do not stop those unrelated processes. Live Davinci experiments used the repository's `davinci-a30` launcher, Qwen3-8B FP16, thinking enabled, 8,192-token context, at `127.0.0.1:18006` through the SSH tunnel. FP16 replaces AWQ because this launcher does not support AWQ on Davinci. At the end of this work, `127.0.0.1:18006` was no longer accepting connections; the completed runs remain preserved, but further live tests require the existing service/tunnel to be restored by its owner.

S2 was completed earlier on A2 and its files remain intact at `.runtime/fn-v42-a2-stress-S2-short-adaptive3/`. The subsequent S6 correction/refusal challenge ran on A30 and completed in 1,234.7 seconds (46 interviewer generation calls; median 18.99 s, p95 36.21 s). It ended non-partially and executed one scoring call; the scorer abstained. The run had one interpretation failure (`interpretation.topics`), one adaptive fallback, two adaptive question events, and no technical or timeout failures. It preserved the participant's one-time correction, refusal, simplification request, and priority change without a repeated intervention. Its unresolved evidence list remained extensive, so completion did not establish methodological completeness or a numeric readiness result.

Artifacts: `.runtime/fn-v42-a30-stress-S6-extended-adaptive3-corrected2-20261125/S6_challenging_correction_refusal_extended.{json,jsonl,md}`, `...-trace.json`, and the same directory's `metrics.json`.

The participant transcript exposed a further scorer defect: the model marked its result abstained, but its explanation asserted an Awareness anchor, contained empty quotation slots, and leaked message/indicator references. The run is preserved as observed; it is not a valid participant explanation. A validator correction now rejects abstention prose containing any FN anchor label or internal message/evidence/indicator/anchor identifiers, routing it to the distinct `unavailable` result and safe participant-facing explanation. A focused regression covers this. The S6 run itself was not rewritten or rerun after the correction.

The controlled four-profile API regression was rerun after correcting repeated-question fixture matching, but still failed: all four journeys ended in `job_failed` on the final submitted answer (before scoring/review). Pytest's temporary directory was later cleaned, so those four-case artifacts are no longer available. A separate citizen-short reference run is preserved at `.runtime/fn-v42-controlled-reference-test-preaccepted-reading-20261125/`; it records a pre-fix evaluator mismatch on the qualified uncertain decision answer. The evaluator now accepts its actual `partial` reading only when the original answer contains explicit uncertainty and the controller preserved that marker; the targeted reference CLI test passes. The four-profile API failure remains unresolved; its export did not preserve the service's safe public job error, so the exact underlying failure was not established. Do not treat canonical dialogue coverage as an end-to-end API pass.
