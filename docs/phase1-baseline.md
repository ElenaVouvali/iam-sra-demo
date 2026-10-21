# Current general interview: baseline-2.3.1

See [response recovery and effects prerequisites](baseline-recovery-2.3.1.md) for
the current UI controls, named-effect probes, privacy recovery and benchmark version.

New sessions now use the [role-aware adaptive interview](baseline-adaptive-interview.md),
with explicit evidence requirements and interleaved clarifications. See that document
for the current registry, routing rules, source mapping, tests and commands.
The 2.0 implementation notes below describe the preserved earlier instrument;
its core-first routing is **not** the policy for new 2.1 sessions.

# Previous instrument: baseline-2.0.0

This replaces the current 1.x instrument for **new sessions only**. Work started
from local commit `fa0262f`; the working tree was clean, and no AGENTS.md was found
in the workspace. Existing frozen instruments, stakeholder labels, confirmed
snapshots and the optional scenario assessment remain supported. The historical demo lives on the legacy branch. No scores,
acceptance classification or scenario facts enter this interview.

## What changed and why

| Files | Behaviour and reason |
|---|---|
| `configs/baseline.json` | Versioned eight-group GA taxonomy, separate interface responses/sector, seven possible core items, eight-item total/two-probe ceiling, optional draft definition. Avoids conflating familiarity, concept knowledge, delivery knowledge and impact reasoning. |
| `baseline.py` | Distinct `concept_explanation` and `use_knowledge` types; deterministic version-aware selection and coverage. Earlier confirmed evidence can omit later questions. Original 1.x selector retained for frozen sessions. |
| `baseline_session.py` | Frozen taxonomy metadata, omission reasons, total-budget stop, pending-answer screening/export, requested-definition exposure and pre-information snapshots. Corrections invalidate dependent conclusions without rewriting old evidence or undoing actual exposure. |
| `baseline_client.py`, both baseline prompts | Source-grounded extraction/review recognises everyday conceptual/use explanations without requiring causal reasoning. Explicit exposure context prevents presenting supplied definitions as prior knowledge. Existing bounded transport/retries remain. |
| `baseline_ui.py`, `ui_presentation.py` | Requested welcome title/subtitle, no redundant introduction, short privacy warning beside text fields, separate questions, optional definition display action, confirmed findings first and unanswered dimensions in an optional section. Existing style retained. |
| `privacy.py`, `privacy_ui.py` | Case-insensitive bounded local address supplements; preview bound to action/session/question/version/context/exposure and invalidated on new input/navigation. Mandatory screening and secret blocking unchanged. |
| `scripts/smoke-baseline.py` | Existing runner answers new question IDs; corrections, export and handoff still use the normal controller. Synthetic cases and automated confirmations remain explicitly labelled. |
| Baseline/privacy tests | Frozen 1.x compatibility plus new-flow, knowledge, participation, exposure, budget and masking/preview regressions. |
| `README.md`, `docs/privacy.md`, source register | Current flow, detector limits, source provenance, deployment obligations and pending approvals. |

## Source-to-question mapping

Originals were read locally, not replaced by repository summaries. Confidential
originals remain under ignored `references/private/`.

| Original reference | Implemented use |
|---|---|
| GA Part B §2.2.1 p.30 / PDF p.67 | Eight target groups, with **canonical source wording** and stable IDs. The GA distinguishes five key and three secondary groups; this interview does not rank respondents by that distinction. Display labels are simplified proposed wording. Other/withheld are interface responses, not ninth/tenth GA groups. |
| GA IAM-SRA2 description Part B p.16 / PDF p.53 | Separate individual/organisational reporting scope and stakeholder context; role is not evidence of capability. No inference of city SRL from an individual interview. |
| Workbook `Read me!J1:L13`, `D1:I13`, `N7:N11` | Understanding/agency distinguishable from technical and organisational capability; no new synthesis or evidence-to-level rule. |
| `SRA IAM indicators!D8/I8`, relevant comments | Awareness/experience before a specific noise diagnostic; no acceptance-as-readiness logic. |
| `D15/I15` | Separate recognition, information, trust, participation and influence; neutral needs questions without presuming a deficit or distrust. |
| `D16/I16` | Distinguish learning exposure, actual contribution, needs and hypothetical willingness. Attendance alone is not contribution or influence. |
| UI guide pp.11–12,14,17–18 | Clear labelled optional fields, one primary action, actionable errors, secondary controls and accessible downloads. Full guide text rechecked; p.12 form example visually inspected in this revision. Existing guide-derived style retained. |

All interview questions and the short neutral definition are **authored prototype
wording**, draft_pending_FN, approved_by=null. The definition records its authored
provenance and is not attributed as an FN quotation or a verified engineering
claim. At the original review date, no complete FN report/question bank/“135 × 3”
bank was supplied. The later v4 draft anchor bank is now available as
[private reference data](readiness-scale-reference-bank.md); questionnaire
approval and operational evidence-to-level policy remain separate.
Completed DMP D1.2/WP13 D13.1, approved branding/font kit and deployment/hub/privacy
ownership decisions remain unavailable/unresolved. GA lists planned obligations,
not completed privacy policies or approval of this instrument.

## Exact question sequence and routing

Onboarding (not counted): personal/organisation/withheld perspective; category;
city/region; optional broad other place, organisation function and optional sector.
Healthcare/pharmacy is sector detail, not a ninth category. None of these fields
establishes readiness. No LLM is used for structured context or familiarity.

Possible core questions, one per screen:

1. **Before today, how familiar were you with drones?** Never heard; heard the term
   but unsure what it meant; some familiarity; substantial familiarity; unsure;
   prefer not to say. Structured self-report only.
2. **In your own words, what is a drone?** Basic concept, not a technical exam.
3. **What have you heard about drones carrying goods, if anything?** Delivery-use
   knowledge, distinct from general drone familiarity.
4. **What difference, if any, could these deliveries make to people or local
   services?** Neutral impact question; helpful/difficult/no-change wording is
   configured as an optional clarification, not a supplied list of desired concerns.
5. **Before this session, have you had any direct experience, learning or involvement
   related to delivery drones? If yes, briefly describe what you did.** Organisation
   wording distinguishes the person's own action from organisational activity.
6. **What would you like to know more about?** Information needs only.
7. **What would help you take part in discussions or decisions about delivery drones?**
   Opportunity/support/barrier evidence only; organisational variant clarifies subject.

Earlier **confirmed** claims may address later dimensions and omit those core
items. Structured familiarity never covers knowledge dimensions. Known absence,
uncertainty or a clear refusal is retained as such, not repeatedly interrogated.
Reported exposure without contribution uses the narrower experience wording.
Omissions log rule/reason/version and supporting event IDs; unasked is missing,
not negative. Never route by support/opposition, stakeholder seniority or a score.

After remaining core items, eligible clarification priority is: ambiguous scope;
undetailed impact reasoning; contribution after actual exposure; unknown experience
domain; outcome after actual contribution. At most **two probes** and **eight
interview items total**. With all seven core items asked there is room for one
probe; covering earlier items may leave room for two. Onboarding, confirmations
and requested definition display do not consume interview items. Skip/unsure/
decline suppress repeat probes for that dimension. Influence never follows mere
attendance or intention. Stop reasons distinguish user_finish, question_budget and
completed (no further eligible questions), not personal improvement.

## Confirmation, information and export

Substantive answers require explicit interpretation confirmation before routing.
Confirmation means intended meaning, not external verification. Everyday definitions
and intended delivery purposes are preserved without asserting they are verified
facts. Detailed impact reasoning is a separate type; enthusiasm/opposition,
employment or unsupported claims of CRL9 do not create it.

A novice can continue without an explanation or explicitly request **Show definition**.
The definition text is not hidden in an expander that can reveal it without logging.
The action records exact text/ID/version, draft/source status, display time/sequence,
acknowledged=false and a pre-information profile. It is not a respondent answer.
Later questions/model requests/claims carry after_information; independent prior
knowledge is explicitly false for those claims. Repetition does not create learning
gains. No baseline FAQ/RAG or scoring rubric is silently supplied.

`iam-baseline-2.0.0` exports context, taxonomy version/canonical/display labels,
questions, original screened answers, pending/confirmed claims, corrections,
selection/omission reasons, initial/completed snapshots, pre-information profiles,
exposures, model/source/prompt/instrument provenance and stop reason. Numerical
CRL/ORL/TRL/SRL remain null. Old instruments still export their original schema and
IDs; ambiguous historical healthcare/operator categories are **not** mapped.
Edits deactivate the edited and later dependent answers, invalidating completed
profiles/handoffs. Historical snapshots and real exposure events remain intact.
Personal respondents may explicitly continue the existing illustrative corridor;
baseline evidence stays separate from scenario scoring and acceptance inputs.

## Three short manual demo scripts

1. **Novice:** personal → citizen → withheld city → never heard. Concept: “I do not
   know what a drone is.” Confirm; choose Show definition or continue without it.
   Delivery: “I have not heard of these uses.” Effects: Unsure. Experience: “I have
   no experience.” Needs: “I would like to know how they are controlled.” Opportunity:
   “I have not been invited, but I would be interested.” Confirm summary. Check
   unknown/absence/barrier distinctions and exposure provenance if requested.
2. **Familiar but not delivery-aware:** personal → citizen, optional healthcare
   sector → Madrid → substantial familiarity. “An aircraft without a pilot on
   board.” Delivery: “I have not heard of goods delivery.” Effects: Unsure. Experience:
   “I attended a seminar about camera drones and only listened.” Needs: “I want to
   know what goods they can carry.” Opportunity: “Evening meetings are difficult
   because of caring responsibilities.” Clarify domain if asked. No contribution,
   influence or numerical readiness should be inferred from familiarity/attendance.
3. **Reasoned participant:** personal → citizen → Milan → some familiarity. Concept:
   “An aircraft without a pilot on board; I have heard of carrying medicines.
   Repeated flights could disturb sleep because they happen while people rest.”
   Confirm; later covered knowledge/effects questions should be omitted. Experience:
   “Last year I attended a bus-route consultation and suggested a clinic stop.
   I do not know whether anything changed.” Needs: “I want measured sound data.”
   Opportunity: “I do not know where to submit comments.” Preserve transferable
   contribution and unknown influence. Edit an answer; check final/handoff invalidation.
   Supporting or opposing the deliveries with the same reasoning must not change
   evidence/scoring rules.

Use only synthetic personal context. Separate privacy check: submit a synthetic
lower-case address, review the cleaned preview, then navigate/skip and verify the
preview expires. A contextual synthetic PIN must block processing, consume no
question and never reach tokenisation/generation.

## Run and reproduce

```bash
cd ~/iam-sra-demo
# Restart only this project's UI if it was already running:
scripts/stop-ui.sh
IAM_ASSESSMENT_MODE=general_baseline scripts/start-ui.sh
# Open http://localhost:8501 and Start over for the new instrument.

.venv/bin/python -m pytest -q
.venv-privacy/bin/python -m pytest tests/test_baseline.py tests/test_baseline_v2.py tests/test_baseline_privacy_v2.py -m presidio_live -q
.venv-privacy/bin/python scripts/smoke-baseline.py --mock --output .runtime/baseline-v2-mock.json
.venv-privacy/bin/python scripts/smoke-baseline.py --output .runtime/baseline-v2-live.json
```

No services were restarted, pushed or deployed for this change. The existing
Streamlit/Qwen3-8B/vLLM stack is retained. Historical numerical policies live on the legacy branch.

## Remaining FN decisions and limits

Approve/revise wording, taxonomy application, evidence anchors, prerequisites,
verification and numerical/synthesis rules; decide how optional information and
chat participation count; supply reviewed local cases and specialised stakeholder
routes. Agree translations, content ownership, privacy/controller/lawful-basis/
retention/rights/access policy, assets and hub integration. This English prototype
is not an organisational audit, complete CRL instrument or calibrated adaptive test.

AppTest exercises Streamlit component/controller flow, not rendered browser
accessibility. No browser/Chromium tooling is available: desktop/mobile 390/360px,
200% zoom, keyboard/focus and screenshots remain manual/unverified. Model semantic
accuracy is separate from mock flow and real detector tests. See actual results
below; runtime traces remain ignored, and no private transcript is a fixture.

## Actual verification for 2.0.0

- Broad final regression run: **1,277 passed, 9 skipped** (205.91 s).
  Final UUID-separator handling and old-export compatibility refinements were
  subsequently checked by the focused/real-detector runs below; no mocked result
  is labelled semantic proof.
- Latest focused baseline, UI and privacy run: **130 passed, 9 skipped** (9.57 s).
  Includes frozen old sessions, new knowledge types, eight-question budget,
  participation/intention/outcome, pre/post information, edits/exports, address
  variants and stale previews. Synthetic detector doubles exercise flow.
- Actual installed Presidio/spaCy checks: **4 passed, 77 deselected** (14.64 s).
  Includes old/new controlled roles/cities, all eight canonical categories,
  definition/exposure/export, extraction/review request envelopes using a transport
  double, 13 synthetic address formats and benign controls. Initial real checks
  exposed a false address suffix match and intermittent PERSON spans on generated
  UUIDs including batch separator punctuation. Both have narrow regressions;
  contextual credentials remain blocked. This is bounded coverage, not a detection
  rate or anonymisation guarantee.
- Existing smoke runner: all three cases completed with the explicitly empty
  mock extractor, normal confirmations/correction/export/handoff and real privacy
  screening. Automation is not citizen confirmation or semantic validation.
- Live smoke: all three cases failed with transport errors (1.606/0.371/0.377 s);
  the configured service is unreachable from this execution environment. No model
  output or live semantic accuracy is claimed. Private results: `.runtime/baseline-v2-live.json`.
- `eval/baseline_v2_sample.json` is a new synthetic, real-detector-screened export
  with an unknown concept answer and requested definition. The old sample is
  intentionally retained as a frozen compatibility fixture, not rewritten.
- Python compilation, diff whitespace checks and original-source hashes pass.
  Private originals/runtime traces are ignored. No dependencies or shared-server
  services changed. Real browser/screenshots/mobile/keyboard checks remain unverified.

### Back navigation

A secondary **Back** button returns from interpretation review to the screened answer entry, from an interview question to the preceding answer, and from the completed summary to summary review. At the first question it returns to respondent details. Reopening an earlier confirmed answer uses the existing correction invalidation mechanism; initial and completed snapshot history is preserved, while dependent current results and handoffs are invalidated. Back does not invoke the model or retain unsent drafts. Privacy previews are cancelled through the shared action boundary. Returning from completion requires summary confirmation again before download or handoff.

Verification: Streamlit AppTest and baseline/privacy regression tests: 57 passed, 2 skipped. Real-browser layout and live-model checks were not repeated for this navigation change.
