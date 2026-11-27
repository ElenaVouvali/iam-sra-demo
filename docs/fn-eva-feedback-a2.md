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

## A2 live follow-up — 26 November 2026

The isolated runner later obtained network access to the already-running A2
endpoint. Before inference, `/v1/models` reported
`Qwen/Qwen3-8B-AWQ`, snapshot
`4da05a8edb55c6046cce958586c33b61da07bb79`, and 8,192 context. The project
owner record identifies AWQ-Marlin, thinking enabled, the `deepseek_r1`
reasoning parser and `liono-a2`. No model process was started, stopped or
reassigned, and Eva's V100S deployment was not touched.

### S8 exact-answer regression

The unchanged scripted S8 persona completed against the refined interviewer,
interpreter and scorer. It reached participant review and exported JSON,
JSONL, Markdown and a developer trace. The provisional result was **CRL 5 —
Co-design**, citing the participant's conditions at `m44` and reason at `m46`.
The score is not accepted as semantically clean: its boundary names CRL 6 —
Informed evaluation, then describes “Influence,” which is CRL 7. An FN reviewer
must adjudicate the boundary; this output does not establish a validated score.

Compared with the previous S8 run: generation calls increased from 24 to 28,
respondent turns from 18 to 26, and elapsed time from 1,016.6 to 1,234.0 seconds.
Median measured generation latency decreased from 76.6 to 39.4 seconds and p95
from 88.4 to 85.5 seconds in these two runs. This is not evidence of an overall
speed improvement: the longer turn count increased total duration. The previous
11 controller fallbacks decreased to 2 by the harness metric, but the new
trace still contains 18 `question_fallback` events, 10 model question-wording
fallbacks, 10 next-goal fallbacks, and two privacy-classified interpretation
failures. `priority_understanding` was routed twice, including an unnecessary
request to explain what a drone is after the registered definition had already
been supplied. Noise and accountability were retained as selected concerns.

The numeric CRL is therefore a provisional model output with traceable
supporting evidence, but its adjacent-level explanation is inconsistent and
the conversation still repeats or falls back too often.

Artifacts (ignored runtime data):

- `.runtime/fn-eva-stabilisation-S8-A2-20261126/S8_uninformed_project_sceptic_short.md`
- `.runtime/fn-eva-stabilisation-S8-A2-20261126/S8_uninformed_project_sceptic_short.json`
- `.runtime/fn-eva-stabilisation-S8-A2-20261126/S8_uninformed_project_sceptic_short.jsonl`
- `.runtime/fn-eva-stabilisation-S8-A2-20261126/S8_uninformed_project_sceptic_short-trace.json`
- `.runtime/fn-eva-stabilisation-S8-A2-20261126/metrics.json`

### Coimbra extended multi-concern persona

The first Qwen-respondent run completed the conversation, automated review and
all three exports, but its scoring request was blocked before model generation.
The privacy diagnostic localized the detector false positive to the
server-generated `request_evidence_id` under `user.supplied_information`.
`privacy.py` now exempts only that exact structural field when its value matches
the generated `m<N>` reference form. A focused negative regression confirms
arbitrary values and participant text remain screened.

A scoring-only replay of the unchanged screened export then made one real Qwen
call and suggested **CRL 4 — Critical engagement**, adjacent to CRL 5 —
Co-design. It cited exact original answers `m26` and `m29` and explained that
they express concerns and request comparative evidence, without a concrete
service safeguard. The replay took 86.2 seconds including 84.3 seconds of model
generation. It did not modify the original export, score state or participant
review: that interview remains recorded as unavailable/pending, and the replay
is diagnostic evidence, not a retroactive participant result.

A fresh full interview after the metadata fix stopped at respondent turn 5.
The mandatory screen withheld a model-generated
`interpretation.information_request_quote` after a `PERSON` finding. The raw
rejected text was not retained. This is a fail-closed partial run, not a reason
to exempt quotation fields or weaken screening.

Across the completed Coimbra transcript, the synthetic Qwen respondent repeated
requests for the drone definition after receiving it, repeated broad requests
for explanation, and did not consistently honor the persona's intended
priority selection. The interviewer clarified several questions but also
repeated generic local-process explanations. Ten of ten interviewer turns
triggered question-wording fallback in that run; the open-priorities and
decision-process goals remained unresolved. No verified local facts were
invented. These results expose continuing adaptive-quality limitations rather
than validating multi-concern generalisation.

Artifacts (ignored runtime data):

- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126/citizen_extended.md`
- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126/citizen_extended.json`
- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126/citizen_extended.jsonl`
- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126/citizen_extended-trace.json`
- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126/metrics.json`
- `.runtime/fn-eva-stabilisation-Coimbra-score-replay2-A2-20261126/`
- `.runtime/fn-eva-stabilisation-Coimbra-A2-20261126-rerun/` (partial, privacy-screened)

### Follow-up validation and status

- Relevant Python/API/privacy suite after the structural privacy correction:
  **465 passed**, one upstream spaCy deprecation warning, 162.24 seconds.
- The earlier Vue component suite (19 passed) and production build passed;
  no frontend source changed in this follow-up.
- A headless browser startup probe passed, but no complete browser-backed
  application interview was run.
- The A2 evaluation is synthetic, uses Qwen for both parties in the Coimbra
  agent case, and is not human or independent FN validation. The S8 numeric
  output's adjacent-level mismatch, the Coimbra privacy-blocked full rerun,
  repeat behavior and lack of real-browser verification remain blockers to
  declaring this implementation ready without supervised FN scrutiny.
- Runtime transcripts and traces remain ignored local evidence, not GitHub
  artifacts. Do not treat the scoring replay as altering a participant review.

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

## Eva release-readiness checkpoint — 27 November 2026

The starting application commit for this checkpoint was `0bedf94485d18786471626b1fc7a438936037bea` on `exp/fn-eva-feedback-a2`. The registered FN sources and readiness scales were not changed. The existing V100S review deployment was not restarted or modified.

### Targeted fixes in this checkpoint

- Model-led question acceptance now restores a registered FN scenario preface and technical object scope when the generated question omits them. An out-of-context `What would you do?` fallback now uses the complete registered problem scenario.
- A drone-definition request is not followed by another request to define the drone after the FN explanation has been supplied; a covered explicit uncertainty does not trigger another clarification loop.
- Concern-topic menus and priority prompts are not reopened after the participant has closed topic discovery or already selected priorities. If a priority answer explicitly names existing ledger topics but Qwen omits some optional topic annotations, Python can recover only those exact already-grounded topics from that answer. It cannot create new issues or infer priorities absent explicit priority language.
- Optional `information_request_quote` is now a bounded source span resolved by Python against the screened original answer. Invalid spans drop only the optional request annotation; the answer itself remains available. Legacy copied quote metadata is excluded from the temporary output-screening copy; generated explanatory prose and other model fields remain screened.
- Scoring rejects explicit level/anchor references inconsistent with the selected adjacent direction, boundary prose describing a non-adjacent anchor, and an empty/heading-only boundary. For CRL 6 or above, the cited evidence must include a respondent-reported real demonstration or participation objective; a prospective information need or hypothetical proposal alone cannot support the Active Participation threshold.
- Frontend quick-answer choices are collapsed by default, leaving free text primary. Participant-facing recovery text no longer exposes GPU lifecycle details.

### New A2 S8 run and frozen-evidence score replays

The real A2 endpoint was `http://127.0.0.1:18023`, with pinned `Qwen/Qwen3-8B-AWQ`, AWQ 4-bit, thinking enabled and 8,192-token context. The respondent was the unchanged scripted fictional persona `S8_uninformed_project_sceptic_short` in Coimbra. The synthetic respondent was not given a target score; the interviewer/interpreter/scorer were live Qwen, not fixtures. The interview run used the implementation before the final priority-recovery and scoring-boundary changes and therefore is diagnostic evidence, not full validation of the final tree.

The interview completed and exported JSON, JSONL and a developer trace. It took 885.24 seconds, recorded 21 respondent messages (19 interview/profile questions plus two review answers), 19 interview generation calls and two scoring generations. The recorded interviewer median was 40.106 seconds and p95 133.804 seconds. Privacy/export passed. Participant review was provided as “I am not sure,” so review remains pending human review.

The transcript demonstrates that the registered drone definition and a bounded hypothetical sample-delivery explanation were supplied on request, and that the problem-action question now included the full scenario. It also shows two remaining defects: the interviewer asked the priority-selection question twice after the respondent named noise and accountability, and it used many FN wording/goal fallbacks. The first integrated score attempt returned unavailable after Qwen selected CRL 2 but described a non-adjacent anchor in its boundary; the validator correctly withheld the number.

Scoring-only replays of the frozen original answers are preserved separately:

- `.runtime/fn-eva-release-S8-score-replay-20261127/`: proposed CRL 5, but boundary incorrectly described level 7 as the next level after CRL 5. This demonstrated a validator gap.
- `.runtime/fn-eva-release-S8-score-replay-adjacent-fix-20261127/`: proposed CRL 5 with adjacent anchor 4, but prose still described higher-level trade-off evidence, an opposite-direction inconsistency.
- `.runtime/fn-eva-release-S8-score-replay-semantic-boundary-20261127/`: proposed CRL 6 with adjacent 7, but cited only the respondent's request for evidence to compare; the respondent had not actually evaluated evidence or participated in a demonstration. This was structurally valid but semantically unsupported.
- `.runtime/fn-eva-release-S8-score-replay-crl-active-participation-20261127/`: proposed CRL 5 with adjacent anchor 4, supported by the participant's concrete proposed conditions and evidence requirements. Its boundary was only the heading “Critical engagement”; this was too terse to explain the substantive distinction. It must not be treated as an accepted participant-facing score.

These results motivated the final tree's additional direction, non-adjacent-anchor, boundary-content and active-participation evidence checks. The final scoring changes have deterministic regressions, but the latest frozen-score replay and a complete live S8 interview using the final tree remain required before a release claim. No fictional numeric level is ground truth.

### Validation and readiness

Vue component checks passed 19/19 and the Vue production build passed. A Python suite before the last scoring checks had 355 passed and one known stale/deselected Golden fixture; after the priority recovery was added, the same suite passed 355 tests with that known obsolete extended-path fixture deselected. A final full suite after the latest scoring guard has not yet been rerun. Focused priority and score-boundary tests passed 4/4. The real Firefox browser walkthrough was not run, and no new review URL or QR code was generated. The live S8 run did not produce a numerical result; scoring-only replays exposed successive semantic boundary failures.

**Readiness verdict: NOT READY for Eva reevaluation on this checkpoint.** The specific scenario and priority fixes are narrow, but current A2 latency remains high, the latest implementation has not completed a full live S8 run, final semantic scoring needs live confirmation, browser acceptance is unverified, and no new deployment was safely validated. The older V100S worktree remains the untouched rollback; its actual served commit remains `4ba9dd81f0b766589b6f2350a54ce90e6688e19c` as last inspected. Do not share the older URL as though it serves this implementation.

Private live transcripts, exports and traces remain ignored under `.runtime/`; they are not included in this document or Git.

### Superseding final S8 validation — 27 November 2026

This addendum supersedes the earlier statement that a final-tree S8 run was
still pending. The unchanged scripted persona was run against the then-current
refinement tree and the live A2 service at `http://127.0.0.1:18023` (pinned
Qwen3-8B-AWQ, AWQ-Marlin 4-bit, thinking enabled, `deepseek_r1`, 8,192-token
context). The scripted respondent had no score target; the live Qwen service
handled interviewer interpretation, adaptive planning and scoring.

The completed interview reached the result/review flow and exported the
screened JSON, JSONL and trace. It took 944.85 seconds, with 24 respondent
messages/turn records, 20 interviewer generation calls and two scoring
generations. Warm interviewer latency was median 39.828 seconds and p95
141.721 seconds. The participant selected “I am not sure”; review therefore
remains pending human judgment. There were repeated/low-value routes and
registered-question fallbacks; completion does not imply good conversational
quality. In particular, the trace records a redundant conditions follow-up
and multiple fallback/rejection events.

The integrated numerical result was **unavailable**. Two scoring generations
did not produce a mutually consistent adjacent-level selection and boundary
explanation. Frozen-evidence replays also showed score instability and
unsupported or contradictory boundary claims (including a CRL 6+ proposal
supported only by prospective evidence requests, and a lower-level proposal
that omitted the respondent's stated co-design conditions). The implementation
now rejects these cases rather than presenting a misleading score. The
synthetic persona has no independent numerical ground truth; no score is
claimed validated. A provisional numeric result remains a release blocker.

The final focused Python regressions were rerun after the null-safe optional
priority-annotation correction and scoring-boundary changes: **357 passed, 1
deselected, 1 upstream spaCy deprecation warning** in 85.73 seconds. The
deselected test requires a larger scoring budget and is outside this bounded
regression run. Vue chat component tests pass 19/19 and the production build
passes. A real browser application interview was not completed. No
replacement V100S deployment or URL was created: the current refinement is not
yet a better review candidate because its integrated score is unavailable,
the live interview remains slow and repetitive, and browser acceptance is
unverified. Eva's existing V100S deployment remains untouched as rollback.

Exact final-r2 artifacts remain private and ignored:

- `.runtime/fn-eva-release-S8-A2-20261127-final-r2/S8_uninformed_project_sceptic_short.md`
- `.runtime/fn-eva-release-S8-A2-20261127-final-r2/S8_uninformed_project_sceptic_short.json`
- `.runtime/fn-eva-release-S8-A2-20261127-final-r2/S8_uninformed_project_sceptic_short.jsonl`
- `.runtime/fn-eva-release-S8-A2-20261127-final-r2/S8_uninformed_project_sceptic_short-trace.json`
- `.runtime/fn-eva-release-S8-A2-20261127-final-r2/metrics.json`

**Updated verdict: NOT READY for replacing Eva's V100S review build.** A valid
score, lower repetition/call count, and browser-backed acceptance must be
demonstrated before publishing a new review link.

### Scoring replay and V100S manual preview — 27 November 2026

The user requested a score-oriented recheck and then redirected the preview
from A2 to V100S. No full interview was repeated for the scoring check. A
scoring-only Qwen replay of the unchanged, screened S8 evidence succeeded after
one bounded correction: **provisional CRL 5 — Co-design**, with adjacent **CRL
6 — Informed evaluation**. It cited the respondent's actual proposal to show
medical need, compare road options, publish impact evidence and explain
responsibility (`m38`); conditional non-support without that evidence (`m40`);
the original noise/accountability concerns (`m18`); and the respondent's
explicitly selected priorities (`m30`). The boundary states that the
respondent requested comparisons but did not report using evidence/experience
to evaluate options or provide informed feedback. The first generated boundary
failed validation; the second passed. The replay took 131.824 seconds and used
two scoring generations. This is a successful validated score for a frozen
evidence replay, not a retroactive modification of the completed session and
not independent ground truth. The original integrated interview's score
remains unavailable.

When a citizen has raised no concern after open discussion, the registered FN
`suggested_topics` prompt presents the PDF-derived additional concerns; tests
cover that conditional route. A respondent who already raised concerns (as S8
did) does not receive an unnecessary list. In the interrupted A2 publication
attempt, the user asked to switch immediately to V100S; only the A2 citizen
short partial artifact was retained, the launcher was interrupted cleanly,
and its owned A2 process was released.

The V100S manual preview is served from the application code at commit
`d69388333d91d4a759485ceb99ae150eda8e1669`. It uses pinned Qwen3-8B FP16
revision `b968826d9c46dd6066d109eabc6255188de91218`, thinking enabled, the
validated reasoning parser and 8,192-token context on Liono V100S. The real
V100S generation probe passed; the Vue/API route, session ownership cookie,
CSRF checks and public HTTPS page check also passed. The full three-profile
synthetic interview/scoring publication gate was skipped at the user's request
for an immediate manual link. Therefore V100S full interview/scoring is not
claimed validated; the separate A2 frozen-evidence replay above is the only
successful score recheck. The current V100S model is on-demand and releases
after 300 idle seconds while the review services remain running.

The temporary public URL is intentionally not recorded in Git; it is saved in
the ignored `.runtime/fn-review/chat-url.txt`. Traffic passes through Cloudflare
and anyone who receives the URL can open it. Use fictional/general answers.
The running launcher must remain open to keep the temporary link alive. The
prior V100S instance was idle when checked and was not terminated; this review
uses its own application/API/model ownership state and port 18022.

This is suitable for **supervised exploratory FN review**, with the explicit
limitations above: the full V100S score path has not been exercised, A2's
integrated S8 score was unavailable despite the successful frozen replay, and
the existing latency/redundancy issues remain. It is not a release or
independent validation claim.

### A2 score-display fallback and V100S handoff — 27 November 2026

At the user's request, our temporary V100S review launcher was stopped and
subsequent scoring work moved to Liono A2. Eva's own V100S deployment was not
targeted by the stop action. The A2 host ran pinned Qwen3-8B AWQ with thinking
enabled. After the scoring-only replay, both GPUs reported 1 MiB used and 0%
utilisation; the old temporary V100S URL was no longer available.

The frozen S8 evidence was replayed against A2 once more, without repeating
the interview. The model returned a validated **CRL 5 — Co-design**, adjacent
**CRL 6 — Informed evaluation**, citing active answer `m38`; the replay took
64.25 seconds and used one scoring generation. This is a model-generated,
structurally validated provisional result for fictional evidence, not an
independent ground-truth score or a change to the original completed session.
The exact replay output is in the ignored artifact directory
`.runtime/fn-eva-release-S8-score-fallback-check-A2-20261127/`.

The implementation also adds a clearly labelled unvalidated-model-estimate
path for structured scoring failures: it may display the model's registered
1–9 anchor only when the failed response named that anchor and cited active
respondent evidence. Python resolves the quote from the screened original
answer; it does not create a level or accept model-written quotation text.
The validated result remains unavailable in that branch, and the UI labels
the candidate **unvalidated** with a warning and exact cited answers. If the
model abstains, proposes no registered anchor, cites no active answer, or
inference/schema processing fails before a usable proposal exists, there is no
honest numeric candidate to show. The application therefore cannot guarantee
a number on every failure without inventing a score; no such invention or
forced fallback was added. Offline regressions cover both the safe candidate
display and rejection of invented anchors/evidence. The successful A2 replay
did not exercise the unvalidated UI branch.

Code changes described in this addendum were local at the time of writing and
were not yet reflected in the pushed branch. Runtime transcripts and exports
remain ignored and are not published.
