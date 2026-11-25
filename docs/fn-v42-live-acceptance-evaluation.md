# IAM-SRA2 v4.2 live acceptance evaluation

**Status: not cleared for participant-facing acceptance.** The saved citizen-short replay shows the end-to-end path can complete on Qwen, and offline/API/UI checks are strong. The current live endpoint is unavailable because Davinci reports no uniquely idle supported GPU. More importantly, the S7 live trace shows material concern-ledger and priority-tracking errors. Internal FN review can proceed as a **moderated prototype walkthrough only**, with the caveats below; do not rely on its concern projection or treat its numerical score as validated.

## Baseline and provenance

- Branch `feat/fn-v42-citizen-adaptive`, base commit `e34ed3b919f1697d525518fc9f52ed7cbbcd7d5e`. Changes in this checkout remain uncommitted.
- Saved live artifacts were produced with Qwen3-8B FP16, thinking enabled, 8,192-token context, A30 through the Liono endpoint `127.0.0.1:18007`. The recorded model revision is `b968826d9c46dd6066d109eabc6255188de91218`.
- On this acceptance continuation, `/health` at 18007 refused the connection. The repository's read-only Davinci A30 preflight reached the host but reported **“No unique idle supported GPU is available.”** No GPU process or tunnel was stopped or restarted. No Liono GPU or Davinci V100 was used.
- Official interview PDFs and the v4 bank were not edited. The bank is `fn-v4-1.0.0`, source SHA-256 `809ce70aec6444fd59358ac1d79806d7c47fcfce72460c8430cb1dad64882818`. No changes are staged under `references/`.
- Saved `.runtime` outputs are synthetic evaluation artifacts, not participant data or FN approval.

## Experiment matrix

| Run | Observed result | Acceptance interpretation |
|---|---|---|
| S2 saved-evidence score replay | Suggested CRL 2, adjacent CRL 1, four exact citations; 64.25 s | Validated output. Earlier abstentions were avoidable malformed scoring attempts, not a reason to force a score. |
| S6 saved-evidence score replay | Suggested CRL 2, adjacent CRL 1, four exact citations; 62.16 s | Validated output in the formatter-fix replay. A later stricter replay failed validation; it remains a historical failure, not the accepted result. |
| FN citizen-short live reference | Ended, non-partial; 39 respondent turns, 29 interviewer calls, zero reported failures/fallbacks; CRL 6; four citations and adjacent comparison; automated review choice A; JSON/JSONL/Markdown and trace saved | Full protocol/export path worked. Automated agreement is not participant validation. One optional `informing` question had no reference answer in the fixture; its synthetic “I do not know” was incorrectly expected to be explored. The harness now expects `unknown` when an optional question has no fixture answer. This correction is covered offline but the reference interview was not replayed. |
| S7 multi-concern extended | Ended, non-partial; 41 respondent turns, 39 interviewer calls, 3 adaptive questions, no reported fallback/interpretation/technical failures; CRL 6; review E (“not sure”), pending human review; 1,187 s total, median 20.632 s and p95 48.18 s | Technical completion passed. Concern and priority semantics did not: see the concern audit. The model's numerical result is only a provisional suggestion and needs expert boundary review. |
| FN citizen-extended reference | Not run in this continuation | Blocked: A30 unavailable. |
| FN organisation and technology references | Not run in this continuation | Blocked: A30 unavailable. |
| Unfamiliar organisation and technical personas | Not run | Blocked: A30 unavailable. |
| Fresh score repeatability on final code | Not run | Blocked: A30 unavailable. Historical repeated scores varied; see below. |
| Vue build and chat tests | Build passed; 18/18 chat component tests passed | Passed. |
| Browser layout | Firefox checked `/tools/sra-assessment`, its app alias, and `/chat` at 360, 768, 1200, and 1440 px; all passed. Firefox 136 lacks Puppeteer's orientation-override command; the harness now tolerates that unsupported command while keeping the viewport-size checks. | Responsive layout assertions passed; screen-orientation emulation was not tested. |
| Browser onboarding | Separate introduction screen and selectable three-profile cards passed in headless Firefox at 360 px | Passed through choice rendering. A model-backed profile-selection click-through could not complete with the endpoint unavailable; the safe UI error was displayed. |

The targeted Python group after the current scoring-schema and reference-harness edits passed **146 tests** (one spaCy/Click deprecation warning). The broader conversation/API regression run passed **370 tests** (one warning, 966.17 s) after the prior privacy-test fixture correction; it preceded the latest explanation-length schema constraint. The four-profile gate is being rerun separately against the current code. An earlier 145-test focused run failed because the test expected the wrong exception for an empty explanation; the assertion was corrected and the subsequent 146-test run passed.

## S7 concern-by-concern audit

The quoted phrases below are from the fictional S7 answers in the ignored local transcript. Status labels describe what is observed in that artifact; candidate mappings are not an assessment.

| Concern and evidence | Observed tracking / exploration | Official-bank candidate | Audit |
|---|---|---|---|
| Wildlife: m26, “repeated flights might disturb nesting birds by the wetland”; clarified at m30 as distinct from residential sound; selected at m34, explicitly less important than transparency at m36 | The opening multi-concern answer m26 produced no matching concern-ledger entries. A wildlife entry appeared only at m30, but its ledger evidence ID was the interviewer-prompted clarification and it was incorrectly marked spontaneous. It remained `selected_priority=true` after m36 said wildlife mattered less. | No direct wildlife/habitat indicator is established by this evidence. Indicator-07 is not a defensible wildlife mapping by itself. Indicator-03 covers energy/emissions life-cycle effects, not wildlife disturbance. | **Observed provenance error, omission, and stale priority.** Requires a dedicated environmental indicator decision from IAM experts if wildlife must map into the existing 15. Otherwise preserve as unmapped. |
| Residential sound/sleep: m26, “noise near homes could affect sleep”; m30 separately explains night noise and unknown measurements | No distinct residential-noise concern was retained in the ledger. The same m30 answer was represented as “Disturbance to nesting birds.” | Indicator-07 Noise is relevant to the separate acoustic/sleep clause under its official sound, operating-condition, context and human-response definition. | **Observed attribution error:** the projection attached a Noise candidate to the wildlife topic because the whole answer also contained the word “noise.” The quote contains acoustic evidence, but this is not evidence that wildlife disturbance is Noise. Projection needs claim-level separation before it can be relied on. |
| Possible observation/privacy: m26, a drone passing a bedroom window “might see inside,” with camera use explicitly unknown; selected at m34 and retained at m36 | Privacy was recorded and explored as an interviewer-suggested topic, although it was spontaneously raised at m26. It remained a priority at m36. | Indicator-09 Perceived Safety and Privacy is the best fit for possible observation and uncertainty. Indicator-10 Technical Safety, Security and Privacy is not established by a concern about being observed; no cyberattack, technical control, or system security evidence was given. The proposed camera/data rules at m52 are requests, not existing safeguards. | **Partial capture / provenance error.** The projection labels the evidence ambiguous between 09 and 10; the official definitions support 09 more directly. IAM review should decide whether m52's requested rules warrant a separate 10 candidate. |
| Distributional fairness: m26, “benefits and impacts may not be shared fairly”; fairness also discussed at m48 onward | No distinct fairness concern was retained from m26; no corresponding candidate appeared in the projection. | Indicator-13 Welfare and Equity is directly relevant to distribution of benefits and impacts. Indicator-05 would need evidence about access barriers or remote/vulnerable groups, which this respondent did not provide. | **Observed false negative in structured extraction/projection**, not absence of the original answer. |
| Transparency, consultation and influence: m26 says residents should know route decisions and be able to influence them; m36 explicitly makes this more important than wildlife | Not retained as a concern or current selected priority. The `priorities` record still contains wildlife and privacy from m34; the concern ledger does not reflect the m36 revision. Later m62 says the respondent has not personally influenced a route decision. | Indicator-14 Public Awareness and Trust is a plausible candidate for clear information, dialogue and accountability. Indicator-01 applies only if IAM is integrated into a Sustainable Urban Mobility Plan, which was not asserted. | **Observed missed priority change.** The respondent's willingness and proposed process are not evidence of actual participation or influence; m48 and m62 make that distinction explicit. |
| Perceived benefit: m26, faster urgent medical supplies | Retained in the transcript and explored later. | Indicator-05 requires access benefits for isolated/vulnerable populations and relevant barriers; none was established. Indicator-06 might be relevant to transport-chain comparison, but m54 describes a future comparison the respondent would make, not tested logistics evidence. | Do not force a mapping from “healthcare delivery” alone. |

The authenticated trace's projection is an internal rule-based candidate pass, not a 15-indicator assessment. It returned a Noise candidate for m30, ambiguous 09/10 for the m34/m36 privacy entries, and no results for the omitted fairness/transparency content in m26. Candidate rationales are not independent labels. The evidence indicates a model extraction/attribution limitation, not that the respondent failed to express these concerns.

## Correction, uncertainty, and readiness review

- In the completed S7 retry, m24 states a possible local test and explicit uncertainty. The controller retained `answer_kind=uncertain` / unknown coverage and did not assert that a flight occurred; its `local_basis` question was not asked because the branch is gated on a yes answer. The earlier incomplete S7 attempt did ask `local_basis`; its answer corrected “test” to “proposed route,” marked the earlier m24 inactive and linked it with `supersedes`. This verifies evidence-level supersession in that partial run, but the correction path has not been verified in a completed interview.
- m34 explicitly selects wildlife and privacy. m36 says privacy remains important and transparency/influence matters more than wildlife. The current priority state was not revised. The earlier record is preserved, but not marked superseded and the later preferred issue was not added as selected.
- m48 reports no invitation and conditional willingness; m62 explicitly denies personal influence. No experience or influence was invented in these answers. These distinctions must remain explicit in scoring and downstream use.
- The result was `validated_score`, CRL 6 / Informed evaluation, adjacent CRL 5 / Co-design. Citations are exact: m54 (a proposed future evidence comparison), m26 (concerns/benefit), m36 (priority statement), m52 (proposed safeguards). This is structurally cited but **semantic boundary is uncertain**: m54 says what the respondent *would* compare, not that they have used information, a demonstration, simulation or experience to compare options. m52 strongly supports proposing conditions (CRL 5). CRL 6 therefore requires FN adjudication and must not be treated as established by this test.
- The participant-facing result message m86 ended mid-sentence (“proposing and discus…”). The participant selected E, “I am not sure”; the review remains pending and does not independently validate the level. The current code now constrains explanation to 600 characters at schema-validation time and asks for complete sentences rather than silently cutting prose. Unit tests pass; this correction has not been live-tested because A30 is unavailable. The historical S7 export remains unchanged.

## Scoring stability and previous abstentions

The saved S2 replay accepted CRL 2 vs CRL 1 with four exact citations. The saved S6 formatter-fix replay accepted CRL 2 vs CRL 1 with four exact citations. These show the previous S2/S6 abstentions were avoidable scoring-output defects, not demonstrated evidence insufficiency. The stricter S6 validator replay that returned unavailable is preserved separately and is not counted as a valid score.

Existing A30 score-only artifacts using the same citizen-short evidence file hash `9d1b61d02f73…` selected CRL 5 or CRL 6 across repeated generations (with some retries/failures in the history). This is genuine observed variation. A new bounded repeatability set on the final code could not be run. Do not claim score stability from the latest citizen-short replay alone.

## Local artifact index

- S2 replay: `.runtime/fn-v42-live-acceptance-S2-score-final-20261125/S2_privacy_priority_shift_short-score-replay.json`
- S6 accepted formatter-fix replay: `.runtime/fn-v42-live-acceptance-S6-score-formatterfix-20261125/S6_challenging_correction_refusal_extended-score-replay.json`; stricter-validator failure preserved at `.runtime/fn-v42-live-acceptance-S6-score-validatorfix-20261125/`.
- Citizen-short interview and exports: `.runtime/fn-v42-live-acceptance-citizen-short-20261125/` (`citizen_short.json`, `.jsonl`, `.md`, `citizen_short-trace.json`, `citizen_short-reference-audit.json`, `metrics.json`, `summary.md`).
- First incomplete S7 attempt: `.runtime/fn-v42-live-acceptance-S7-multiconcern-20261125/`.
- Completed S7 interview and exports: `.runtime/fn-v42-live-acceptance-S7-multiconcern-retry-20261125/` (`S7_multi_concern_evolving_priorities_extended.json`, `.jsonl`, `.md`, `-trace.json`, `metrics.json`).
- Historical repeated citizen-short scoring attempts: `.runtime/fn-v42-a30-score-replays-final-20261125/`, `.runtime/fn-v42-a30-score-replays-validated-20261125/`, `.runtime/fn-v42-a30-score-replays-validated2-20261125/`, `.runtime/fn-v42-a30-score-replays-validated3-20261125/`.
- Firefox responsive layout and onboarding checks ran against isolated ports 15016/18016; no participant or model outputs were written by those checks. The temporary API/UI processes started for the checks were stopped afterward.

## Privacy, technical, and usability findings

- The first S7 attempt is preserved under `.runtime/fn-v42-live-acceptance-S7-multiconcern-20261125/`; the successful retry is under `.runtime/fn-v42-live-acceptance-S7-multiconcern-retry-20261125/`. The privacy false positive was reproduced offline: the synthetic sentence “Bird disturbance may matter near nesting habitat.” is rejected as a private detail, while “Birds could be affected even where residents hear little noise,” “I saw birds near the wetland,” “There are birds near the wetland,” and “Bird nesting areas may need monitoring” pass. This is a controlled-test nuisance and plausible user-facing friction. Privacy remains fail-closed; no broad PERSON relaxation or whitelist was added.
- S7's 41-turn extended conversation took about 19.8 minutes of model HTTP time/total run, before a real participant's reading, thinking and typing time. At p95 48.18 s per interviewer generation, it may feel slow and exceed the nominal 35-minute intention. Three adaptive wording events were recorded, but several later answers were “I do not know”; the count does not establish that adaptation improved relevance. Human usability remains unverified.
- No actual model reasoning was added to participant output. The raw/model evaluation artifacts remain ignored under `.runtime/`.

## Reproduction commands

Run offline tests and frontend checks from the repository root (Node 22.23.5 is available at the path below):

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python -m pytest -q \
  tests/test_chat_conversation.py tests/test_fn_reference_audit.py \
  tests/test_fn_citizen_stress.py \
  tests/test_fn_agent.py::test_exact_fn_review_prompts_do_not_allow_personal_data_or_changed_text
cd app
PATH=/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin:$PATH npm run build
PATH=/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin:$PATH npm run check:chat
```

To repeat the local browser checks, first confirm ports 18016 and 15016 are free, then start the API and UI in separate terminals. The model endpoint must be healthy to test a completed model-backed dialogue; this browser run only verified layout and onboarding choices.

```bash
# Terminal 1, repository root
IAM_BASE_URL=http://127.0.0.1:18007 IAM_MODEL_TIMEOUT_SECONDS=8 IAM_SRA_JOB_TIMEOUT=20 \
IAM_SRA_API_PORT=18016 \
IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:15016,http://localhost:15016 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract bash scripts/start-api.sh

# Terminal 2, app directory
HOST=127.0.0.1 IAM_SRA_UI_PORT=15016 IAM_SRA_API_TARGET=http://127.0.0.1:18016 \
../.venv-api/bin/python serve_app.py

# Terminal 3, app directory; layout plus intro/selectable options (no inference)
PATH=/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin:$PATH \
ONLY=sra-assessment FLOW='chat introduction and selectable' WIDTHS=360,768,1200,1440 \
BASE=http://127.0.0.1:15016 npm run check
```

When the approved A30 service is available again, verify `/health` and `/v1/models` first, then replay using the existing scripts, one at a time:

```bash
IAM_MODEL_VARIANT=fp16 IAM_MODEL_THINKING=1 IAM_SRA_ON_DEMAND_GPU=0 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python \
scripts/replay-chat-score.py --input .runtime/fn-v42-live-acceptance-citizen-short-20261125/citizen_short.json \
  --base-url http://127.0.0.1:18007 --output .runtime/fn-v42-replay-final-short

IAM_MODEL_VARIANT=fp16 IAM_MODEL_THINKING=1 IAM_SRA_ON_DEMAND_GPU=0 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 IAM_CHAT_PROCESSING_SECONDS=3600 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python \
scripts/smoke-fn-interview.py --allow-live --case citizen_extended --respondent reference \
  --model-variant fp16 --thinking --base-url http://127.0.0.1:18007 --save-traces \
  --case-timeout-seconds 3600 --output .runtime/fn-v42-live-acceptance-citizen-extended
```

Use the same interview command sequentially with `--case organisational` and `--case technical`; do not run until the A30 service is confirmed healthy and idle ownership is clear. Reuse `scripts/smoke-fn-citizen-stress.py` for S7, not a new harness.

## Readiness decisions and required expert review

**A. Supervised internal FN review:** Suitable only as a moderated, non-data-collection prototype walkthrough, if FN is told that the A30-dependent cases and live UI completion are pending, concern/priority records can be wrong, and no score should be relied on. A supervised methodological review can help adjudicate the observed boundary and whether local-basis uncertainty should prompt clarification.

**B. Unmoderated/public participant testing:** Not ready. Blocking items: restore an approved inference backend; fix and live-verify multi-concern extraction and priority revision; complete citizen-extended, organisation and technical live interviews; complete model-backed browser review/export; obtain approval for public exposure and data handling.

**C. Scientifically validated CRL/ORL/TRL or indicator instrument:** Not validated. Requires independent IAM/FN review of anchor interpretation, repeatability, concern-to-indicator mapping and scoring boundaries. No synthetic run establishes instrument validity.

Priority next actions when the A30 is available: (1) reproduce S7 topic extraction and m36 priority revision without changing its answers; (2) validate that the explanation schema fix produces complete participant prose; (3) run citizen-extended, organisational and technical reference cases sequentially; (4) rerun the bounded score stability set on identical evidence; (5) complete a real model-backed Vue review/export journey. Seek IAM/FN adjudication for wildlife's taxonomy status and S7's CRL 5/6 boundary.

## Live generalisation continuation — 25 November 2026

This section records the later A30 work and supersedes the earlier statement that A30 live tests were blocked. It does not change the earlier S7 analysis. The source PDFs, source registry, official anchors and v4 indicator bank were unchanged.

**Configuration:** Davinci A30, Qwen3-8B FP16, thinking enabled, 8,192-token context, model revision `b968826d9c46dd6066d109eabc6255188de91218`, local Liono endpoint `http://127.0.0.1:18007`. All respondents below were synthetic Qwen-generated agents; the interviewer was live Qwen. Agent self-consistency is not independent validation. Tests ran sequentially. The consolidated ignored artifact directory is `.runtime/fn-v42-live-generalisation-a30-campaign-20261125/`.

| Persona | Profile/depth | Conversation/export | Model outcome | Observed failure or limitation |
|---|---|---|---|---|
| G1 unfamiliar citizen | CRL, short | Ended; 34 respondent turns, 29 interviewer calls; JSON/JSONL/Markdown/trace saved; 762.7 s generation HTTP time, 957.5 s elapsed | No accepted CRL | Exact citation validation rejected the score (`citations.quote`); zero accepted citations and no adjacent boundary. This is a scoring failure, not evidence insufficiency. |
| G3 multi-concern citizen, initial | CRL, extended | Partial/stopped at priorities; 15 turns; exports and trace retained | No score | Grounded priority-topic annotations were missing or rejected; controller displayed a technical-error recovery. |
| G3 multi-concern citizen, retry | CRL, extended | Ended; 39 turns, 34 interviewer calls; JSON/JSONL/Markdown saved; 784.3 s generation HTTP time, 1,087.7 s elapsed | No accepted CRL | Conversation completed with no interpretation/technical failures after the priority recovery. Scoring failed `alternative_anchor_id`; an earlier scoring attempt exceeded the explanation-length limit. The score remains unavailable. |
| G6 planning-unit organisation, initial | ORL | Partial/stopped at priorities; 14 turns; exports and trace retained | No score | Same priority-annotation failure as initial G3. |
| G6 planning-unit organisation, retry | ORL | Ended; 30 turns, 28 interviewer calls; JSON/JSONL/Markdown saved; 585.3 s generation HTTP time, 803.2 s elapsed | Provisional ORL 4; four evidence citations and adjacent boundary passed structural validation | Participant review was automated and selected uncertainty; it is not respondent agreement. The rationale says the unit had begun planning but had not formalised roles or tested plans; the adjacent-level explanation says partnerships/resources/procedures were not yet in place. Human review must verify that these claims match the transcript. |
| G8 routine-logistics organisation | ORL | Interview did not start; no transcript generated | Not assessed | Synthetic respondent output was blocked by the privacy screen (“Sensitive content was withheld”). Screening was not relaxed. The safe diagnostic is in `G8_routine_health_logistics/blocked-attempt.json`. The two-organisation live comparison remains incomplete. |
| G9 subsystem/lab technical | TRL | Ended; 29 turns, 27 interviewer calls; JSON/JSONL/Markdown/trace saved; 555.1 s generation HTTP time, 771.7 s elapsed | No accepted TRL | Boundary validation failed; no citations or boundary accepted. Conversation coverage alone does not establish that the subsystem was correctly kept separate from the complete system. |
| G11 representative-system technical | TRL | Ended; 35 turns, 33 interviewer calls; JSON/JSONL/Markdown/trace saved; 685.3 s generation HTTP time, 963.1 s elapsed | No accepted TRL | Boundary validation failed; explanation and boundary exceeded the configured length in one attempt. No numerical level was accepted. |

### Targeted priority-annotation correction

The initial G3 and G6 runs failed at the same controller boundary: a substantive answer to the priority question was marked covered, but Qwen did not provide acceptable entries in `interpretation.topics`. The validator turned an optional semantic annotation failure into a failed chat turn. The correction now reuses `priority_topics` only when their labels and exact quotations are grounded in the current answer; if no grounded topics remain, Python keeps the original answer, leaves the priority goal uncovered, and asks one bounded clarification. It does not infer or force a priority. Five focused tests passed, and the G3/G6 retries passed the priority stage and completed. A controller regression also caught and fixed loss of the internal recovery marker during the session's second contract validation. This does not repair the separate scorer failures.

G6's accepted participant-facing explanation was: “The organisation has initiated planning for drone services, focusing on logistics and staff readiness, as evidenced by discussions on secure handover and resource requirements. However, they have not yet formalized roles or tested plans, indicating they remain in the planning phase.” Its boundary was: “Level 5 requires putting in place partnerships, resources, and procedures, which this organisation has not yet done, as they await confirmed resources and a tested plan before proceeding.” The validator accepted four exact answer citations (`m44`, `m46`, `m32`, `m27`) and the adjacent ORL 5 comparison. These are the model's evidence-based result explanation, not hidden chain-of-thought. The automated participant selected “not sure”; the review remains pending.

### Participant-facing scoring rationale versus model reasoning

No raw chain-of-thought was retained or exported. The inspectable rationale is the validated participant-facing explanation and evidence/boundary fields. G6's ORL 4 rationale is reproduced above in summary. For G1, G3, G9 and G11, the invalid score outputs were replaced by the safe unavailable-result text; their candidate levels are not treated as assessments. The live metrics expose attempt counts and validation fields, not hidden reasoning tokens. Do not interpret `reasoning_characters` as a transcript of reasoning.

### Campaign conclusion and artifact handling

Five live synthetic interviews reached the terminal conversation stage: G1, G3 retry, G6 retry, G9 and G11. Only G6 yielded a structurally accepted numeric suggestion; its semantic validity and participant-facing review still need human assessment. The initial G3/G6 failures and blocked G8 attempt are retained. The original campaign files, including any developer traces and full transcripts, remain in ignored `.runtime/` paths and were not added to GitHub. This document contains only a sanitized evaluation summary. A full 6-case live set, a second completed organisation case, a live model-backed Vue session, and a valid numerical assessment for citizen/technical cases remain unverified.

Reproduce the A30 runs with `scripts/smoke-fn-interview.py --allow-live --respondent agent --persona-id <id> --case <profile-case> --thinking --respondent-no-think --base-url http://127.0.0.1:18007 --save-traces --output <unique-path>` after verifying the A30 endpoint. Use `scripts/replay-chat-score.py` for saved citizen evidence; do not rerun a full interview to debug a scoring-only failure. Never replace the synthetic summaries here with hidden reasoning or raw participant data.
