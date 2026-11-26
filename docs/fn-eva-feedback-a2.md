# FN feedback refinement — A2 validation status

## Provenance and isolation

The refinement worktree is on `exp/fn-eva-feedback-a2`, based on
`30687bccf0c4e762513dccc1b6e86f658d1ea832`, the source commit present in the
V100S checkout when its review launcher started. The serving launcher, API and
frontend processes were verified in `/home/elvouvali/IAM_CC/iam-sra-review-v100s`;
they remain untouched. The checkout later advanced to `4ba9dd81f0b766589b6f2350a54ce90e6688e19c`,
but that commit was not the revision loaded by Eva's running V100S processes.

Private registered references are read through a local symlink and are not
included in this branch. No private PDFs, model files, runtime transcripts,
tokens or review URLs are committed.

## Changes

- `ChatConversation.vue`: keeps the open-text composer beside all selectable
  answers, adds simple pause/skip/finish controls, retry wording, delayed
  processing feedback, and an optional post-review feedback field.
- `chat_session.py`: after a negative or uncertain citizen drone-recognition
  answer, requires the existing FN explanation branch before model-led routing
  can move on. Directly supplied explanations remain exposure records, not
  respondent knowledge. Pause/resume restores the actual last displayed
  question, and the substantive summary is withheld during pause and excludes
  administrative perspective/city selections. Optional UX feedback is stored
  separately and cannot alter evidence, scoring or the participant review.
- `schemas.py`, `adapter.py`, `service.py`: adds a bounded `chat_feedback` action
  that is privacy-screened, CSRF/session/version protected, allowed only after
  participant review, accepted once, and does not construct model clients or
  enter the readiness-interview action path.
- `eval/fn_generalisation_additional_personas_v1.json`: adds the fictional
  `eva_coimbra_extended_multiconcern` persona. It has no target level; the
  synthetic respondent receives participant facts and style, not the expected
  observations or prohibited-inference checks.
- `privacy.py`: after live reproduction, allows generated `m<N>` references
  only in exact server-owned routing/exposure and FN stage-ledger reference
  fields. It does not exempt participant text or arbitrary values.
- Regression tests cover negative recognition routing, pause/resume and summary
  visibility, feedback separation and one-time API handling, text entry
  alongside options, and the structural privacy-reference boundary.

The official FN materials and registered 15-indicator/readiness banks were not
modified. Indicator projection remains internal and conservative.

## Verification

- Selected Python/FN/controller/API regression group: **286 passed, 7
  deselected**. The deselected items require external live-browser or other
  excluded conditions; privacy-specific suites were run separately.
- Privacy and baseline privacy regressions, including the real local privacy
  resources check and the new evidence-reference regression: **103 passed**.
- The new registered persona was loaded through the existing live-harness
  loader and screened successfully; it contains no target score.
- Vue chat component tests: **19 passed**.
- Vue production build: **passed**.
- A local API/frontend pair started on isolated ports 8096/5096, but Firefox
  failed before the real-browser flow began (`Failed to launch the browser
  process`, exit code 11, during headless GPU/X initialization). The test-owned
  API and UI processes were then stopped. No model request was sent.

## A2 live-test results

Eva confirmed the A2 workload was project-owned. I used the already-running
A2 service on port `18023`; I did not stop/restart it or affect the separate A2
and V100S review launchers. At verification A2 used 12,383 MiB of 15,356 MiB.
The service reported `Qwen/Qwen3-8B-AWQ`, snapshot
`4da05a8edb55c6046cce958586c33b61da07bb79`, AWQ-Marlin 4-bit, reasoning enabled
with `deepseek_r1`, and 8,192-token context. The interviewer used thinking;
the Qwen-generated fictional respondent used soft no-think.

Three sequential attempts used the registered Coimbra extended-citizen
persona. Two privacy false positives were reproduced and narrowly fixed:

| Attempt | Outcome |
|---|---|
| `.runtime/fn-eva-a2-coimbra-extended-20261126-live/` | Privacy screening failed during interpretation/export. The detector flagged a controller-owned `request_evidence_id` in routing metadata; no score was reached. |
| `.runtime/fn-eva-a2-coimbra-extended-20261126-live-retry1/` | Routing-metadata export passed, but prompt screening flagged an active evidence ID in `fn.stage_ledger[].goals[].evidence_ids[]`. Seven respondent turns; no score. |
| `.runtime/fn-eva-a2-coimbra-extended-20261126-live-retry2/` | Both privacy fixes held. JSON/JSONL/Markdown export and developer trace succeeded. The interview stopped after 9 respondent turns because Qwen repeatedly produced an invalid/redundant next question while the synthetic respondent repeated a request for a sample-delivery example. No score or participant review was reached. |

For retry2, the interviewer made 12 generation calls; the run records 524.061
seconds of generation HTTP time, 538.526 seconds generation wall time and
597.831 seconds total elapsed time. The Qwen respondent made 6 calls taking
32.324 seconds. There were 6 fallbacks, 3 question-wording fallbacks and one
terminal interpretation failure (`eligibility`, field `message`). The run
reported 17.37 generated tokens/second. This is a failed, interrupted run, not
a stable latency estimate.

The live evidence revealed two unresolved conversational issues: the Qwen
respondent repeated a drone-definition request after the approved definition
was supplied, and the interviewer did not recover after repeated requests for
a concrete sample-delivery example. It answered with general possible medical
payloads, then fell back to the same broad question before a later
question-generation failure. No numerical score, participant review, final
concern projection or completed-interview latency assessment is claimed. The
complete partial transcript and screened trace are retained in retry2's
ignored runtime directory.

The privacy correction exempts `m<N>` only at the exact server-owned routing
and information-exposure `request_evidence_id` fields and the exact
controller-built FN stage-ledger evidence-reference field. Tests confirm
participant prose, quoted IDs, malformed values and user-controlled fields
remain screened.

The A2 model process remains running. Firefox previously exited before opening
the application, so no genuine Vue-browser interview was performed.

## Final conversational-stabilisation pass — 26 November 2026

This pass continues from the saved S8 diagnosis above; it does not replace or
rewrite the earlier artifacts.

### Targeted implementation changes

- `chat_client.py` now treats a next-goal or question-wording defect as a
  planning rejection after validating the answer interpretation. Valid
  evidence, topics, uncertainty and information-request annotations therefore
  survive; the controller selects an eligible FN bridge or uses registered
  wording without repeating interpretation.
- `fn_interview.py` supplies the model with only applicable, uncovered,
  unasked next objectives, while retaining the current goal as a separately
  bounded clarification option. The model can still select across FN stages.
- `chat_session.py` records eligible choices and rejected proposals in
  developer traces, falls back to an eligible registered goal/question, and
  supplements omitted concern annotations only from exact participant spans.
  Grounded noise and accountability label variants are reconciled without
  adding internal mapping IDs to participant prose. Multiple evidence-backed
  concerns can trigger a natural priority invitation; only respondent choice
  changes selected priorities.
- `adaptive_interview.py` distinguishes direct questions from condition lists
  such as “publish evidence and explain accountability”; these conditions no
  longer cause unsolicited background. Explicit direct requests remain
  answerable, with question-specific clarifications recorded as separate
  information exposures.
- `chat_score.py` collapses identical normalized quotations across message IDs
  to one supporting observation. It does not remove the original transcript
  messages or count them as independent evidence.

The registered FN sources, official scales and 15-indicator bank were not
changed. Stage consideration remains distinct from demonstrated readiness.

### Verification

- Focused and relevant Python/API/privacy suite, with the isolated local
  `TLDEXTRACT_CACHE`: **465 passed**, one upstream spaCy deprecation warning
  (final run: 159.09 seconds).
- Vue chat component tests: **19 passed**.
- Vue production build: **passed**.
- The first broad privacy/API run omitted the required isolated cache and failed
  closed with `privacy_unavailable`; rerunning with the configured cache passed.
- A headless Firefox startup probe against `about:blank` passed after the
  earlier browser-process startup issue. A real-browser application interview
  was not completed: no app/API interview flow was exercised, so this is not
  browser acceptance.

### Requested live A2 evaluations

The A2 model ownership record inspected in
`/home/elvouvali/IAM_CC/iam-sra-model-led-v100/.runtime/vllm.pid.json` identifies
the project-owned `liono-a2` service at port 18023: Qwen3-8B-AWQ snapshot
`4da05a8edb55c6046cce958586c33b61da07bb79`, AWQ-Marlin, `--enable-reasoning`,
`deepseek_r1`, `--max-model-len 8192`, and `IAM_MODEL_THINKING=1`. The service
was not restarted. `model-host.py check` refused a second start because the A2
is occupied, as intended.

The S8 and Coimbra live commands were attempted from this isolated execution
environment. The Python harness could not connect to `127.0.0.1:18023`
(`Operation not permitted` in the restricted run and `Connection refused` in
the escalated run). No new transcript, score or live inference is claimed from
these attempts. The existing S8 and Coimbra results above remain diagnostic
baseline evidence, not validation of this refinement.

New bounded offline regressions cover the S8 `evaluation_evidence` failure,
eligible-goal exclusion, multi-concern retention, priority invitation,
condition-vs-request classification and duplicate score citations. The current
code has therefore passed deterministic tests but still requires the two live
A2 runs and a real-browser flow from an execution environment that can reach
the owning A2 service. Do not treat this pass as completed live generalisation
or as independent FN validation.

## Reproduce the offline checks

```bash
cd /home/elvouvali/IAM_CC/iam-sra-eva-feedback-a2
TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
PYTHONPATH="$PWD/src" \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python -m pytest -q \
  tests/test_fn_model_led.py tests/test_fn_interview.py \
  tests/test_chat_conversation.py tests/test_chat_choices.py \
  tests/test_api_integration.py -m 'not presidio_live' \
  --deselect=tests/test_api_integration.py::test_api_real_privacy_resources_context_preview

TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
PYTHONPATH="$PWD/src" \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python -m pytest -q \
  tests/test_privacy.py tests/test_baseline_privacy_v2.py \
  tests/test_api_integration.py::test_api_real_privacy_resources_context_preview

cd app
/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin/node \
  --experimental-vm-modules tests/chat_conversation.test.mjs
/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin/node node_modules/vite/bin/vite.js build
```

## Reproduce a later A2 interview

The captured interview failed before scoring. After reviewing the semantic
failure and ensuring no active reviewer is using the service, use a fresh
ignored runtime directory. Verify the endpoint at `/health` and `/v1/models`
first; the prior run used port `18023` because that was the verified live A2
service. Keep the model configuration and worktree consistent:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-eva-feedback-a2
TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
IAM_MODEL_VARIANT=awq IAM_MODEL_THINKING=1 \
IAM_CHAT_INTERVIEW_STRATEGY=model_led_fn IAM_SRA_ON_DEMAND_GPU=0 \
IAM_BASE_URL=http://127.0.0.1:18023 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python \
  scripts/smoke-fn-interview.py --allow-live --respondent agent \
  --respondent-no-think --case citizen_extended \
  --persona-id eva_coimbra_extended_multiconcern \
  --model-variant awq --thinking --base-url http://127.0.0.1:18023 \
  --save-traces --max-agent-calls 60 --max-turns 100 \
  --case-timeout-seconds 3600 \
  --output .runtime/fn-eva-a2-coimbra-extended-20261126-next
```

The synthetic respondent is Qwen-generated and is not independent human
validation. Inspect the complete transcript, question repeats, information
exposures, concern evidence, projection, score/abstention, adjacent boundary,
participant review and export before making any review-readiness claim.

## A2 sceptical-citizen live run and corrective refinements

The new fictional persona `S8_uninformed_project_sceptic_short` is registered
in `eval/fn_citizen_stress_v1.json`. It is a Coimbra resident with no prior
drone knowledge, no participation experience and a consistently sceptical
view. It has no target readiness score. Its answers are scripted; the
interviewer, interpretation, routing, scorer and participant-review flow use
the live A2 Qwen endpoint.

The initial run completed through review and exported a provisional CRL 5. The
saved retest, after the first source-bound privacy change, also completed with
CRL 5, JSON/JSONL export and a participant response of `E` (uncertain), leaving
the result pending human review. The two exact citations were valid and the
adjacent distinction was CRL 6 Informed evaluation. The rationale is plausible:
the respondent proposed conditions and evidence comparisons, but had not
demonstrated using evidence to evaluate options and provide feedback. This
boundary still needs FN adjudication; no ground-truth score exists for the
fictional persona.

The live retest established the following failure chain and changes:

| Observation | Change | Evidence and remaining limitation |
|---|---|---|
| A model-generated request quote exactly echoed screened respondent text and was falsely flagged as PERSON. | Screen a temporary copy of the model response with only an exact quote substring removed from its metadata location, after the original answer has passed request screening. Preserve the untouched model response for exact-source validation. | Retest had no privacy failures; deterministic tests verify non-matching quotes and all other generated prose remain screened. |
| Two model question outputs failed the bounded `eligibility/message` check. Previously, such an error appeared to the participant. | Save the original answer, record its goal as unresolved, answer only a detectable explicit information request, and continue using a different registered FN objective. | Retest completed without a participant-facing technical-error message; trace records two recovered interpretation failures. |
| A request for accountability was accompanied by unrelated medical-need and road-comparison statements; the model annotation led to extra background being supplied. | Restrict request detection to the clause containing the request cue, validate model labels against their exact quoted request, and cap responses to the requested categories. | Deterministic regressions pass. The full A2 retest preceded this last clause-scoping change, so its live effect remains unverified. |
| The same conditions answer was elicited again after the first copy was left unresolved, producing duplicate score citations. | Treat a documented unresolved goal as considered for stage completion, retain it in `unresolved_gaps`, and exclude it from automatic repeated routing. It is not positive readiness evidence. | Deterministic routing/export regressions pass. The live retest preceded this final unresolved-goal change; no live confirmation is claimed. |

The retest took 1,016.59 seconds (16m 57s), with 18 respondent turns, 24
generation calls including retries, one scoring call, 13 timed generation HTTP
requests, median 76.591 seconds and p95 88.356 seconds. There were 11
controller question fallbacks and two recovered interpretation failures; no
timeouts, token-budget failures or privacy failures. These timings show that
the app is still slow on this A2 setup. The implementation keeps thinking,
AWQ, 8,192 context and the existing model capacity. It does not claim a measured
latency reduction; explanations are deterministic and use the existing turn
generation, with no separate explanatory inference call.

Retest artifacts are preserved in the ignored local runtime directory and a synthetic-only GitHub bundle at `eval/fn-eva-a2-s8-live-retest-20261126/`. The bundle contains the transcript, export, JSONL, structured developer trace and metrics; it contains no private FN PDFs or model weights. Original runtime artifacts remain untouched.

Original local runtime paths:

- `.runtime/fn-eva-a2-s8-live-retest-20261126/S8_uninformed_project_sceptic_short.md`
- `.runtime/fn-eva-a2-s8-live-retest-20261126/S8_uninformed_project_sceptic_short.json`
- `.runtime/fn-eva-a2-s8-live-retest-20261126/S8_uninformed_project_sceptic_short.jsonl`
- `.runtime/fn-eva-a2-s8-live-retest-20261126/S8_uninformed_project_sceptic_short-trace.json`
- `.runtime/fn-eva-a2-s8-live-retest-20261126/metrics.json`

Final focused local validation after the request-scoping and unresolved-routing
changes: 285 passed across model-led, adaptive helper, thinking/privacy,
persona, interpretation and conversation tests. A separate selected API/privacy
run had 168 passes and one environment failure because the private corpus was
unavailable in this isolated worktree; that test is not a live-app pass. The
last request-scoping and unresolved-routing changes have only deterministic
verification, not a subsequent full live interview.
