# Conversational IAM-SRA2 meeting demonstration

This document describes the earlier 1.1 implementation and its verification.
New sessions on `main` use the versioned objective
planner described in [adaptive conversation v1.2](adaptive-conversation-v1.2.md).

This is a working internal prototype, not a scientifically validated instrument,
approved FN questionnaire or production service. It implements citizen evidence
and an illustrative discussion for organisational respondents; it does not audit
an organisation. Overall SRL requires ecosystem evidence and agreed synthesis.

## Launch on the model host

Keep the existing Qwen3-8B/vLLM service and environments. From this checkout:

```bash
cd ~/iam-sra-demo
.venv-privacy/bin/python scripts/check-privacy.py
.venv-privacy/bin/python scripts/build-conversation-corpus.py
scripts/health-check.sh
scripts/stop-ui.sh
IAM_MOCK=0 IAM_BASE_URL=http://127.0.0.1:8000 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation scripts/start-ui.sh
```

Open **http://localhost:8501** through the existing host/SSH forwarding setup.
The model must serve `Qwen/Qwen3-8B`, configured revision
`b968826d9c46dd6066d109eabc6255188de91218`, on port 8000 with the existing
4096-token context and structured decoding. Start it with `scripts/start-vllm.sh`
only if absent; model loading takes time. Do not launch a second GPU process just
because its health endpoint is not ready yet. No model/runtime upgrade is needed.

The model address is supplied through `IAM_BASE_URL`. The current davinci setup
uses port 18000; use that address consistently for health checks and UI launch:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 scripts/health-check.sh
IAM_MOCK=0 IAM_BASE_URL=http://127.0.0.1:18000 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation scripts/start-ui.sh
```

The earlier command uses port 8000 for a directly hosted service. Use the address
of your existing service. The diagnostic script can inspect GPU inventory and
reachable model aliases; alias/health checks do not verify loaded revision,
tokenization or guided-decoding compatibility. Model recovery is a separate
host operation and is unnecessary when only reloading the interview UI.

The existing default remains `general_baseline`. The new mode is also available
under **Choose interview mode**; switching requires confirmation and starts a
fresh session. Existing scenario mode is retained. Historical executable scoring
is on the existing `legacy` branch/check-out, as before this change. This checkout
provides the separate historical FN reference with `IAM_DEVELOPER=1`.

**Restart the UI after code changes.** File watching is disabled in this checkout.
A browser refresh alone does not reload changed Python modules. Use Start over
and confirm before each independent case; download any session you want to keep.

The 1.1 update is described in [conversation-update-1.1.md](conversation-update-1.1.md).
The historical copy-paste scenarios below refer to the FN corridor: explicitly
choose that example when using their operating details. The successor automated
bank `eval/conversation_meeting_cases_v2.json` supplies route-neutral responses
and explicit answers for the new branches; the original bank is preserved.

## Journey and controls

1. Choose personal/organisational perspective, a GA-mapped role and broad city.
   No identifying organisation name is requested. These selections require no LLM.
2. Answer the general interview, up to eight items, including at most two probes.
   Confirm each substantive interpretation or use correction/re-read/Back.
3. Confirm the editable general summary. It contains no scenario acceptance.
4. Accept or decline the suggested medical-corridor example. The same illustrative
   card applies to every city; it is not a local plan. Organisational respondents
   can discuss it without receiving an ORL/TRL assessment.
5. Share an initial view, followed by zero to four relevant follow-ups. Existing
   evidence can make questions unnecessary. Skip and Finish are valid options.
6. Optionally request a sourced explanation after confirmation. Opening its
   expander does not expose explanatory content. **Show sourced explanation**
   records the exact displayed excerpts and sources. Acknowledging reading is
   separate. Optional reflection occupies one of the four follow-up slots.
7. Check and confirm the final summary. Download screened JSON/JSONL. The evidence
   details link exact supporting words, interpretation, criterion, context and
   confirmation. Edits invalidate downstream results while retaining history.

The export's approved numerical CRL, ORL, TRL and SRL fields remain null. After a
personal interview, an explicitly optional **draft citizen estimate** reuses the
existing workbook model-judgement module with this versioned scope. It cites
supporting answers and the workbook anchor, may abstain, and is separate from
approved numerical fields. Its input excludes third-party/organisation evidence
and proposal stances, retains every relevant own claim and exact supporting
quotations, and keeps information context. It has not been live-validated here. It is unavailable
for an organisational perspective. Never call a personal estimate societal SRL.

## Retrieval and planning policy

The builder verifies source hashes and current configuration, then prepares three
private collections: 65 general/scenario question variants, nine scenario cards and
18 explanatory/reference passages. Eight cards come from GA routes; FN-specific
passages stay restricted to the original corridor. Workbook explanations can
apply across cases.
`references/private/conversation-coverage.json` reports objective/role coverage and
gaps. `conversation-source-notes.json` retains original D/H/I cells and relevant
comments for private review; those raw drafts are not planner instructions or
citizen explanation passages. The corpus itself is inspectable JSON and available
for developer-only internal download. All these files remain Git-ignored.

Deterministic rules exclude inapplicable, completed, covered and suppressed items,
enforce activity/contribution prerequisites and budgets, and construct eligible
candidates. Local lexical retrieval ranks eligible records. Qwen selects from
at most five records and may paraphrase or ask a neutral answer-specific
clarification within the selected objective. A separate model check reviews new
wording for meaning, neutrality, source grounding, actor and uncertainty. Failed
planning/review uses an authored eligible fallback. Both calls share the existing
deadline and bounded per-call repair policy; this adds latency. Source and
trigger identifiers, stage, topic suppression and budgets remain mandatory.
Model review is not independent semantic proof. Extraction failure never becomes
negative evidence.

The model cannot change the registry or route through a readiness estimate.
Confirmed evidence controls future eligibility. Attendance, contribution and
outcome are different; a team activity and a personal contribution keep separate
subjects. Activity matching requires explicit compatible scope. The same activity
link can prevent a duplicate question without converting individual action into
organisational capability. Unknown influence is retained as unknown.

Scenario information needs/barriers already supplied need not be repeated.
Contextual understanding applies to the new card; baseline knowledge is not
relabelled as a scenario response. Scenario display and explanations are exposure
events, and later evidence is marked after information. No new readiness gain is
inferred from reading, repetition or additional elicitation.

## Source-to-implementation traceability

| Actual source / locator | Basis used | Status and implementation choice |
|---|---|---|
| GA T3.2–T3.4, PDF p.9; Part B p.5/PDF p.42, p.16/PDF p.53 | Empowerment, agency, distinct stakeholder inputs, individual/organisational/citizen scope; SRL synthesis | Contract governs scope; no executable CRL formula inferred |
| GA Part B §2.2.1, p.30/PDF p.67 | Eight canonical stakeholder groups | Existing versioned taxonomy retained; profession never establishes readiness |
| Workbook Read me!J1:L13 | Citizen readiness anchors; distinguish CRL from TRL/ORL/SRL | Draft partner descriptions, not approved evidence-to-level prerequisites |
| SRA IAM indicators!D/H/I8; C8/D8/H8/J8 comments | Separate noise acceptance/trust from readiness; reasoning and evidence needs | Neutral understanding/reasoning questions and scenario effects; wording is proposed |
| SRA IAM indicators!D/H/I15 | Information, trust and empowerment are distinct | Recognition/use knowledge and information needs, not trust-based scoring |
| SRA IAM indicators!D/H/I16 | Existing knowledge, actual learning/activity, needs and application | Experience/contribution/domain/scope probes; willingness is not actual activity |
| Use case(s) per LL!A2, B2:D2 | Template with unpopulated city columns | No completed local case or operational facts fabricated |
| SRA_LLM_FN_concept.pdf p.5, pp.8–9 | Fixed medical-corridor narrative; hypothetical changes | Illustrative facts and unknowns stored separately; no engineering guarantees |
| Same FN PDF pp.6–7 | Historical example 8,3,4,2; mean 4.25; cap 4 | Researcher-only source comparison; never current evidence or model output |
| WP3 minutes 8 October, decisions/action points; September slides 3–6 | Partner review and forthcoming use cases/report | No approval of this demo inferred; review dates are not completed approvals |
| meeting_notes | Role/city, general-to-scenario workflow, retrieval ideas | One 969-byte plain-text file, not a directory; meeting directions, not approved rules |
| UI guide v1.0, 19 pages; pp.5–9,11–14,17–18 | Existing palette, readable labels, native controls, focus and hub/footer guidance | Existing styling retained; text reviewed and p.12 form visual rechecked. Approved asset kit and browser checks remain outstanding |

Original PDFs/workbook/slides/minutes are present. GA has 87 PDF pages; the FN
concept has nine and the UI guide 19. Original hashes, sections and approval limits
are in `references/source-register.json` and the private corpus. No source content
or approval is inferred from filenames. Broader references without available full
texts were not ingested as research findings.

## Reproduce verification

See [the actual verification results and file-by-file handover](conversation-verification.md)
for completed checks and the specific live/browser blocks.

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not presidio_live'
PYTHONPATH=src .venv-privacy/bin/python -m pytest -q -m presidio_live
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --conversation --fixtures \
  --benchmark eval/conversation_meeting_cases.json --output .runtime/conversation-fixture-meeting.json
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --conversation \
  --benchmark eval/conversation_meeting_cases.json --output .runtime/conversation-live-meeting.json
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --conversation --fixtures \
  --decline-scenario --case enthusiastic_novice --output .runtime/conversation-decline.json
```

`--fixtures` uses authored controlled interpretations through the real controller
and installed privacy detector, not Qwen semantic validation. Live mode uses the
normal extraction/grounding/omission-review/planner/explanation clients. It checks
the configured model endpoint before running. Reports contain code/diff hashes,
configuration/model expectations, actual presented questions/variants, answers,
initial interpretations before correction, diagnostics, latency, final exports
and invariant results. Scripted confirmation is labelled **automation**. Human
semantic review remains pending until someone reads the actual live outputs.

The runner reads the selected question ID and variant at every turn and resolves
only explicit case bindings. An unsupported branch is reported, not answered with
a generic fallback. Do not count an unasked answer as observed evidence. Review
initial omissions/errors even if a later correction succeeds. Historical baseline
benchmark files are retained; the conversation cases are a separate versioned
extension of the existing runner, not replacement expectations.

For manual semantic review: compare the supplied answer with every interpretation;
check actor, actual/intended action, negation, activity/time, unknown outcome and
information context; then review whether the next question was useful, eligible
and non-repetitive. Review support/opposition independently of understanding.

## Privacy and recovery demonstration

Use a synthetic address: `A drone has no pilot on board. My home address is 42
Example Street.` The UI should clear the original widget and offer cleaned text
for explicit confirmation, preserving the conceptual answer. The address-only
version should request a new answer or skip, because no assessment content remains.
A contextual synthetic PIN must be blocked without echo, model call or consumed
question. Never demonstrate this with real credentials or addresses.

Privacy remains mandatory before model/tokenisation/retrieval, record/display and
downloads. A new schema-name false positive was resolved by registering only exact
trusted version strings and workbook locators; arbitrary prose is still screened.
Presidio's English NLP and bounded address recognisers can miss data or raise false
positives. This is not guaranteed anonymisation or GDPR certification. See privacy.md.

On model failure the screened answer is retained, with Retry, Skip and Finish.
The resulting partial summary distinguishes unresolved extraction from absence
of knowledge/experience. An unsafe export remains withheld. No raw rejected output
is retained for debugging, and privacy errors do not lower a score.

## Meeting limits and FN decisions

1. Agree evidence anchors, prerequisites and numerical interpretation; decide the
   role of the original acceptance-oriented example. Variable coverage/length is
   not a comparable readiness total, and no SRL synthesis rule is implemented.
2. Approve question/variant wording, sufficiency, stakeholder evidence scope and
   organisational verification requirements. Current revisions are proposed.
3. Decide how information exposure, independently expressed reasoning, chatbot
   participation and co-design count. Chat completion currently establishes none
   of these automatically.
4. Assign ownership for questions/sources/local facts, privacy governance and
   hub/UI integration. Supply reviewed LL scenarios, the completed FN report/bank,
   relevant full papers, approved assets and institutional DMP/ethics policies.

The verification report accompanying this guide separates executable fixture
checks, real detector checks and unavailable live/browser checks. Before presenting,
manually check 1440px, 390px and 360px widths, 200% zoom, Tab/Shift-Tab focus,
long answers, correction, cleaned-preview confirmation and downloaded files.

## Ready-to-paste synthetic cases

Use only the answer matching the question currently shown; do not paste the whole
script into one answer. Wording can vary within the registry. The following case
definitions are the same versioned data used by the runner.

### Enthusiastic novice citizen (`enthusiastic_novice`)
Choose **Personal view**, **Citizen / resident or civil-society organisation**, **Prefer not to say**.

**Question/answer key: familiarity**

> I had some familiarity

**Question/answer key: concept**

> I have heard the term, but I do not know what a drone is.

**Question/answer key: delivery**

> I heard that drones can carry medicines, but I do not know how that works.

**Question/answer key: understanding**

> I like the idea, but I cannot explain its effects.

**Question/answer key: experience**

> I have not attended a discussion, demonstration or training about delivery drones.

**Question/answer key: needs**

> I want to know how the drones are controlled and whether images are stored.

**Question/answer key: opportunity**

> I have not been invited to a discussion and do not know where to comment.

**Question/answer key: scenario_effect**

> I do not know enough to explain the effects.

**Question/answer key: scenario_information**

> I would want sound measurements and the image-retention policy.

**Question/answer key: scenario_access**

> I do not know how to send comments on this example.

**Question/answer key: scenario_view**

> I support this example because hospital deliveries sound useful, but I do not know what effects it would have.

**Optional reflection — only after requesting information**

> No recording policy is supplied. Flights when people are sleeping could disturb them because the sound may interrupt sleep; I would still need actual sound measurements.

After confirming the initial scenario answer, ask **Are camera images recorded or retained?**. Then request reflection if wanted. Expect a sourced statement of what is unknown, not a fabricated recording policy.

Expected observations: Limited concept knowledge; heard of medicines delivery; Uncertainty about effects without a reasoning probe; No reported attendance; unmet participation opportunity; Support remains separate from readiness; optional reflection is after information.

Must not infer: Verified influence; Automatic co-design or chat readiness gain; A city SRL or organisational/technical score; Known camera policy, measured noise or mitigation feasibility.

Equivalent variant bindings: `familiarity` → `personal`; `concept` → `personal`; `delivery` → `personal`; `understanding` → `personal`; `experience` → `personal`, `contribution_after_exposure`; `needs` → `personal`; `opportunity` → `personal`; `scenario_effect` → `personal`; `scenario_information` → `personal`; `scenario_access` → `personal`; `scenario_view` → `personal`; `scenario_reflection` → `personal`.

### Informed sceptical academic answering personally (`sceptical_academic_personal`)
Choose **Personal view**, **Research or academia**, **Milan**.

**Question/answer key: familiarity**

> I had substantial familiarity

**Question/answer key: concept**

> A drone is an aircraft without a pilot on board; a person can control it remotely or it can follow automated instructions.

**Question/answer key: delivery**

> I have heard of drones carrying medical samples between healthcare sites.

**Question/answer key: understanding**

> I am sceptical of residential routes. Early flights could wake shift workers because they happen while those workers sleep.

**Question/answer key: experience**

> Last year I attended a bus consultation and proposed a clinic stop; I do not know whether my proposal changed the decision.

**Question/answer key: needs**

> I want sound measurements at homes and a clear statement about whether camera images are stored or shared.

**Question/answer key: opportunity**

> I would attend a drone discussion, but I do not know where to comment and evening meetings conflict with caring responsibilities.

**Question/answer key: scenario_view**

> I oppose this route as described. Early repeated flights could disturb rest because people may be sleeping. I would reconsider a route that avoids homes, but I need evidence about noise and camera recording.

**Question/answer key: scenario_information**

> I would want sound measurements and the image-retention policy.

**Question/answer key: scenario_access**

> I do not know how to send comments on this example.

**Question/answer key: scenario_effect**

> Flights when people sleep could disturb rest because their sound may interrupt sleep.

**Question/answer key: domain**

> The consultation was about a bus service, not drones.

**Question/answer key: influence**

> I do not know whether the bus proposal changed the decision.

**Question/answer key: scenario_outcome**

> I do not know whether my bus proposal changed the decision.

Correction exercise: edit the initial scenario answer and append: `This is my view of the illustrative case, not an independently verified result.` Confirm the revised interpretation. The runner explicitly finishes after this correction; it does not invent later answers.

Expected observations: Reasoned concern about rest; Personal bus-consultation contribution is transferable experience; Outcome unknown; willingness and barriers distinct; Opposition with conditions stays separate from understanding.

Must not infer: Verified influence; Automatic co-design or chat readiness gain; A city SRL or organisational/technical score; Known camera policy, measured noise or mitigation feasibility.

Equivalent variant bindings: `familiarity` → `personal`; `concept` → `personal`; `delivery` → `personal`; `understanding` → `personal`; `experience` → `personal`, `contribution_after_exposure`; `needs` → `personal`; `opportunity` → `personal`; `scenario_view` → `personal`; `scenario_information` → `personal`; `scenario_access` → `personal`; `scenario_effect` → `personal`; `domain` → `personal`; `influence` → `personal`; `scenario_outcome` → `personal`.

### Authority representative (`authority_representative`)
Choose **Representing an organisation**, **National, regional or local authority**, **Madrid**.
Optional function: `Transport planning`.

**Question/answer key: familiarity**

> I had substantial familiarity

**Question/answer key: concept**

> A drone is an aircraft flown without a pilot on board.

**Question/answer key: delivery**

> Our team knows of carrying medicines and laboratory samples with drones.

**Question/answer key: understanding**

> Flights while residents rest could disturb sleep because the sound occurs during a sensitive activity.

**Question/answer key: experience**

> Last month our team reviewed draft delivery-drone planning options and I added a request for noise measurements; I do not know whether our review changed a decision.

**Question/answer key: needs**

> We still need local sound data and a documented image-handling policy.

**Question/answer key: opportunity**

> We have not established a public consultation channel for delivery drones yet.

**Question/answer key: scenario_view**

> I cannot endorse this illustrative route without evidence. It is not a project our team has reviewed. We would need measured sound and an image-handling policy.

**Question/answer key: scenario_effect**

> In this case early flights could disturb rest because their sound occurs while residents are sleeping.

**Question/answer key: scenario_information**

> We would need measured sound and a documented camera-retention policy.

**Question/answer key: scenario_access**

> We would want affected groups to have accessible ways to comment; no such local channel is established by this example.

**Question/answer key: influence**

> I do not know whether our review changed a decision.

**Question/answer key: scenario_outcome**

> I do not know whether our review changed a decision.

Expected observations: Reported team planning review and separate personal contribution; Outcome and local evidence remain unknown; No existing participation channel reported; The illustrative proposal was not reviewed by the team.

Must not infer: Verified influence; Automatic co-design or chat readiness gain; A city SRL or organisational/technical score; Known camera policy, measured noise or mitigation feasibility.

Equivalent variant bindings: `familiarity` → `organisation`; `concept` → `organisation`; `delivery` → `organisation`; `understanding` → `organisation`; `experience` → `organisation_authority`, `contribution_after_exposure`; `needs` → `organisation`; `opportunity` → `organisation`; `scenario_view` → `organisation`; `scenario_effect` → `organisation`; `scenario_information` → `organisation`; `scenario_access` → `organisation`; `influence` → `organisation`; `scenario_outcome` → `organisation`.
