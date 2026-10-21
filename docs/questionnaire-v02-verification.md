# Local verification: questionnaire v0.2 and scenario addendum

Date: 21 October 2026. Starting branch
`feature/indicator-assisted-self-assessment`, clean HEAD
`178d805152c5981d985f815bc24a34887ce97bac`. Changes remain local; no push,
merge or deployment replacement. Source packages, generated banks, synthetic
session exports and diagnostic output remain private/ignored.

## Scope and limitations addressed

| Reviewed limitation | Result |
| --- | --- |
| Interpretation labels/keywords pre-exclude statements and answer passages | Fixed: all nine statements remain eligible; full screened answers and correction history are authoritative; exact citations still mandatory |
| Inadequately justified model selections | Partly addressed: explicit alternative explanation, complete-statement/actor/temporal safeguards, strict rejection and unavailable reporting; observed semantic overinterpretation remains |
| Three generic citizen intents | Replaced by all 45 v0.2 modules, conditional shared probes and bounded optional case reflections; wording is draft |
| Citizen-only domain/UI | Shared citizen/CRL, organisational/ORL and technical/TRL scope, questions, review and report; automatic technical matching remains unreliable in live checks |
| Baseline-first, small-batch dead end and restarting results | Direct profile route, all fifteen across three sections, idempotent navigation, partial finish, explicit edits and linked-evidence invalidation |
| Fixed corridor preference and insufficient use-case context | Removed; primary local use case stays explicit; optional status-labelled cases use existing retrieval, source/version pinning and case-specific explanations |

All six additions are integrated. Two originals remain unavailable, as detailed
in [the scenario source table](scenario-expansion-v01.md). No approved instrument,
validated algorithm, real Living Lab baseline, overall citizen score or ecosystem
SRL is claimed. D3.1's proposed aggregation remains a separate project objective.

## Files by purpose

- Source configuration: `questionnaire.py`, `scenario_expansion.py`,
  `references/source-register.json`, and the existing corpus builder/loader,
  `conversation_sources.py` and retrieval ordering.
- Shared assessment: `indicator_assessment.py`, `indicator_client.py` and
  `conversation_session.py`. Policy is `indicator-matching-draft-2.0.1`;
  report schema is `indicator-self-assessment-2.0.0`.
- Interfaces/transport: API schemas/adapter/service, Vue indicator component and
  assessment page, Streamlit indicator/conversation renderers and keyword-safe
  privacy preview invocation. No new HTTP endpoint or application service.
- Evaluation: frozen authored cases, `evaluate-indicator-questionnaire.py`,
  `smoke-questionnaire.py`, removal of the old smoke's category gate, focused
  synthetic fixtures/domain/API/Streamlit/browser checks and these notes.

The exact selection policy, source versions, review ownership and commands are
in [the methodology/run note](questionnaire-v02-prototype.md). Dataset
expectations are authored provisional review references, never model targets.

## Deterministic, privacy and interface checks actually executed

Commands use `PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q` with the
listed selections. Counts overlap across incremental checks; do not add them
into an invented total.

| Selection / command | Observed result |
| --- | --- |
| `tests/test_privacy.py tests/test_baseline_privacy_v2.py tests/test_baseline_ui.py tests/test_conversation.py tests/test_conversation_updates.py` plus new nested-preview selection | 165 passed; 271.59 s; includes installed Presidio integration |
| `tests/test_questionnaire_v02.py tests/test_indicator_assessment.py`, after answer-basis field repair | 67 passed; 7.50 s |
| `tests/test_indicator_api.py tests/test_indicator_ui.py tests/test_questionnaire_v02.py`, intermediate integration | 47 passed; 45.31 s |
| `tests/test_indicator_api.py tests/test_questionnaire_v02.py`, including unavailable-suggestion/report recovery | 52 passed; 39.35 s |
| New keyword onboarding privacy preview | 1 passed; 1.20 s |
| Failed answer-addition rollback and normal addition/confirmation | 2 passed; 0.42 s |
| Comparison resume writes every reused record, including tail | 1 passed; 0.31 s |
| Invalid direct onboarding scope leaves onboarding intact | 3 passed; 0.47 s |
| Direct API journey/export recheck after onboarding guard | 3 passed; 9.02 s |
| Direct three-profile API and Streamlit paths after answer-basis repair | 4 passed; 19.72 s |
| Information exposure and Streamlit direct path after final presentation changes | 2 passed; 9.96 s |
| Scenario mapping/domain/staleness plus three API profile/export paths, excluding real-source test | 17 passed, 1 deselected; 8.90 s |
| Real old/new private corpus load, source identity/staleness and real privacy | 1 passed; 36.55 s; one existing spaCy/Click deprecation warning |
| Scenario outside-role/no-object guard plus other scenario domain checks | 16 passed, 1 deselected; 1.78 s |
| Conversation regressions after scenario integration, `-m 'not presidio_live'` | 58 passed, 4 deselected; 35.33 s |
| `node app/tests/transport_check.mjs`, isolated proxy | Passed cookies, CSRF, ownership, duplicate jobs, JSON/JSONL, DELETE, status forwarding and deep links |
| `npm --prefix app run build -- --outDir ../.runtime/questionnaire-v02/ui/dist --emptyOutDir` | Passed, 55 modules; final scenario build passed |
| Final preview guards across onboarding and previous privacy UI paths | 21 passed, 80 deselected; 2.98 s |
| Existing `tests/test_api_integration.py`, after shared adapter/signature changes | 23 passed; 56.06 s; two existing package deprecation warnings |
| Linked-source edit / change of a reusing indicator / case-dependent history | 3 passed; 0.64 s |
| Reconfirm unchanged ORL/TRL scope preserves completed result | 2 passed; 0.51 s |
| Resume policy consistency and complete JSONL tail | 1 passed |
| `git diff --check`, Python compilation | Passed |

Private-source checks rebuilt the FN bank to an alternate private filename and
compared it to the existing bank: identical. Actual counts are 15 indicators,
45 criteria, 405 statements and 36 generic descriptions. All 45 modules resolve
nine distinct exact source statements. Noise/citizen matches G56:G64. JSONL
matches the JSON's 45 modules; all 20 verbatim-tagged Topic-cell selections match.
All three profile exports passed the installed privacy detector. The expanded
corpus built successfully with 15 unique cards, 65 questions and 24 passages;
old nine-card JSONs remained identical and the deployed corpus was not rewritten.

Browser verification used the existing Node 22.23.3, Puppeteer 25.13.0 and isolated
Firefox 157.0.1. It ran through test-only inference/privacy fixtures against local
review ports 18005/5005; it is **not live-model semantic evidence**. Eleven distinct
flows passed across incremental targeted runs: catalogue; complete legacy
interview/correction/information/exports; mobile privacy/failure recovery; reset
and ownership-related processing; direct assessment for each profile; unavailable
suggestion with explicit participant selection; optional case for each profile.
Reload, navigation across sections, alternative selection, stale review rejection,
partial finish, exports and case decline/invalidation were exercised. Static
pages passed the four documented widths, and the new citizen case passed at
360 px with a sideways-scroll assertion. Initial browser creation failed because
the isolated API allowed the wrong origin; configuring only the test proxy's
origin fixed that environmental setup without relaxing CSRF.

## Exploratory before/after matching

The frozen 13 citizen cases used the same v4 bank, model endpoint/configuration,
answers, annotations and scope for old/revised matching. The old client was
preserved from the starting Git commit before editing. This isolates matching;
it is not an old-versus-new full-interview accuracy study. No desired level was
sent to the model. Live trajectories are stochastic and the expectations await
FN/ISCTE review.

Old ledger: 13 structurally valid results, including 6 abstentions, 13 generation
calls, 165.432 recorded seconds. Revised 2.0.0 ledger for those same citizen cases:
11 valid results, 2 rejected results, 19 calls, 259.429 seconds. Including one new
ORL and one TRL case gives 15 cases, 13 valid results, 23 calls and 321.547 seconds.
This ledger reuses completed records and includes bounded retries of failures;
it is not a fresh single-pass run, nor the total number of development calls.
Earlier failures remain in separate private reports.

| Case | Original client | Revised 2.0.0 observation |
| --- | --- | --- |
| Equivalent safeguards: “I propose” / “should” / “would propose” | CRL1 / CRL1 / abstention | Noise CRL5 for all three; exact passages remain citable despite imperfect annotations |
| Willingness without action | Abstention | Abstention |
| Bare understanding claim vs explanation | Abstention / Technical Safety CRL3 | Abstention / Technical Safety CRL3 |
| Attendance without influence | Public Awareness CRL1 | CRL1; no participation/influence elevation |
| Contribution linked to a change | Competence CRL5 | CRL8, above the authored CRL7 expectation: possible unsupported inference of broader agency/support to others |
| Unavailable opportunities | Competence CRL1 | Abstention; no inability inference or opportunity bonus |
| Contradictory evidence | Abstention | Abstention |
| Critical information / correction case | CRL1 / abstention | Both rejected for missing alternative distinction; unavailable, never converted into low scores |

A general full-clause support clarification did **not** resolve the Competence
CRL8 result on its targeted recheck (2 calls, 34.29 s). This remains a semantic
limitation, not a reason to change the source anchor or benchmark expectation.
The range labels are provisional author judgments, not approved gold labels or
an accuracy percentage.

## Live controller checks and observed waiting/calls

Current policy 2.0.1 renamed the misleading `follow_up_quote` field to
`answer_basis_quote`: diagnosis showed the model copying a question into that
field. Exact-answer validation was retained. A conditional-schema experiment
produced missing-field objects with the pinned guided-output path; it was
reverted, not bypassed. Fields now have explicit answer/alternative semantics.

| Real Qwen/controller run | Outcome | Generation calls | Recorded controller elapsed |
| --- | --- | --- | --- |
| No-information citizen | Completed; tool abstained; participant unsure | 2 | 33.072 s |
| Citizen disagreement without added case | Rejected quotation | 4 | 53.179 s |
| Organisational without added case | Rejected missing alternative distinction | 3 | 49.338 s |
| Technical without added case | Rejected missing alternative distinction | 3 | 44.695 s |
| Citizen Noise + expansion-04 | Completed; tool CRL5; explicit different participant statement and correction retained | 4 | 64.293 s |
| Organisational Noise + expansion-04 | Completed; tool abstained; explicit participant selection after abstention | 3 | 49.807 s |
| Technical Safety + expansion-03 | Rejected missing alternative distinction; failed/incomplete export retained | 3 | 53.210 s |

The three expanded-case requests were serialized; no extra GPU service was
started. Their 10 generation calls took 167.310 recorded controller seconds;
client model/transport latency totals 122.397 s. Recorded per-case time includes
assessment/privacy work but excludes cold controller/source construction. The
CLI now records whole-run wall time for future invocations; that newer timing
field is not retroactively claimed for these runs.

Both completed expanded-case sessions and the failed technical session have
screened SYNTHETIC JSON/JSONL exports under `.runtime/questionnaire-v02/scenario-live-*`.
The corrected uncertainty session is under `basis-repair-smoke/`. Controlled
participant alternatives test review mechanics, not scientific ground-truth
levels. Do not pool these contexts into an accuracy estimate or attribute
successes causally to the added scenarios. The same Qwen service serves all
components, so agreement is not independent validation.

## Remaining failures and readiness

- **Model-output / semantic problems:** occasional incorrect quotations, omitted
  alternative distinctions and the possible Competence overestimate. Rejections
  remain failures; no fabricated fallback level. API/Streamlit preserve an
  unavailable marker and allow explicit participant assessment or uncertainty.
- **Application defects found and fixed:** Streamlit keyword privacy preview;
  initial scope-form display; stale onboarding profile previews; dependent linked-answer invalidation; atomic
  answer-addition failure recovery; incomplete resumed JSONL reports; invalid
  onboarding leaving its route; case changes erasing outside-role/no-object
  status. Focused regression checks cover these boundaries.
- **Environment/source limitations:** origin configuration for isolated browser
  tests and a sandbox-blocked local transport connection were corrected without
  changing deployed security. The guided-schema experiment was reverted. Two
  scenario originals and several questionnaire supplementary originals remain
  missing; differing source binaries remain disclosed. Source identity does not
  verify current operations or model revision.

Internal demonstration: **yes, supervised**, showing participant-owned levels,
source status, partial coverage and unavailable-suggestion recovery. A fully
automatic, reliably scored three-profile demonstration is **not established**.
Partner methodology review: usable now; a partner pilot presented as a validated
instrument is **not ready**. Unattended scoring: **not ready**.

FN/ISCTE agreement and empirical evaluation are still needed for evidence
sufficiency, material alternatives, questionnaire routing/burden, ORL/TRL scope,
case/local validation, externally verified versus reported facts, and future
aggregation input. See the two linked operator notes for exact review build/run
commands and the three-profile demonstration sequence. No passing fixture,
source mapping or JSON schema check is treated as methodological validation.

Final read-only probes returned HTTP 200 for the existing model (Qwen/Qwen3-8B alias), API on port 8001 and deployed UI on port 5001. Only temporary test API/UI processes were stopped; the GPU/model service and deployed corpus stayed in place.
