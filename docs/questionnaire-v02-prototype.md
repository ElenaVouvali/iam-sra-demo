# Questionnaire v0.2: three-profile review prototype

This local iteration starts from clean branch `feature/indicator-assisted-self-assessment`,
commit `178d805152c5981d985f815bc24a34887ce97bac`. No deployment, GPU service,
environment or remote branch is replaced. The earlier citizen-only workflow is
historical; the shared assessment controller now administers citizen/CRL,
organisational/ORL and technical/TRL modules. This is a prototype for partner
review, not an approved instrument or unattended scorer.

## Sources and what they authorise

| Basis | Verified locator / status | Application boundary |
| --- | --- | --- |
| GA | Annex 1 T3.2/T3.3 and Part B IAM-SRA2 description; contract | Framework operationalisation and individual stakeholder inputs; this implementation does not complete validation or T3.4 |
| D3.1 v0.18 | §§10.4–10.5.1 and surrounding §§10.5–10.6; draft | Explicit response capacity, indicator statements, reflective assessment and participant-owned individual levels |
| FN v4 workbook | `Scales per indicator!E:G`, shared H/I review rows; draft | Exact profile-specific definitions, criteria and nine statements; no executable matching algorithm |
| Noise citizen example | `Indicators' assessment criteria!F8`; `Scales per indicator!G56:G64` | All nine statements are resolved from the bank, not reproduced in source code |
| Topic workbook | Relevant cited cells; J2, I8/I15/I16; working draft | Acceptance/trust/profession do not define readiness; action, contribution and influence remain distinct |
| October WP3 minutes and Meeting_14_10 | Available local records; partner review pending | No invented approval or missing local authorisation |
| July concept | Cited in supplied questionnaire reports; originals absent locally | Open-ended/Likert/review/Read more design is package-reported context, not independently verified July documentation |
| Historical FN concept | Local original, historical | Earlier system-scoring/validation questions are historical proposals, not the v4 matching policy |
| Questionnaire v0.2 | `2026-10-21-v0.2`, `iam-sra-provisional-questionnaire-0.2.0`; authored draft pending partner review | Question order, conditional probes, optionality and routing are prototype design, not official KVIs |

D3.1 proposes profile/indicator aggregation using medians and cross-dimensional
SRL synthesis, expressly pending finalisation/testing. This task supplies traceable
individual inputs. It does not decide official aggregation input, calculate city
statistics or implement a headline SRL, average, bonus or historical global CRL.
Participant confirmation verifies intended meaning, not external factual accuracy.

The questionnaire ZIP SHA256 is
`b116dbe5c58093fa67e0af4cd9e25818cb9d1b9d1f6d1f81888efd876849e61e`;
JSON SHA256 is
`837dbc9dab3b767cda86c6a2825e33a91f52aa3af7677921aabe358259858de2`.
The v4 workbook SHA256 remains
`809ce70aec6444fd59358ac1d79806d7c47fcfce72460c8430cb1dad64882818`.
The registered private bank remains `fn-v4-1.0.0` / `readiness-scale-bank-1.0.0`.

All 45 module mappings and 405 statements match the bank exactly. The 135
shared review rows remain “To review”, with blank comments; these are not three
independent profile approvals. JSONL is an equivalent header plus 45 modules,
not training data. All 20 items marked extracted verbatim (12 questions and
8 Likert items) match the selected text of the cited local Topic workbook cells.

Source discrepancy: package v4, D3.1, October minutes and historical FN hashes
match local originals despite filename prefixes. Package GA, Topic workbook and
Meeting_14_10 binary hashes differ from local files. Relevant local GA text and
Topic-cell selections were checked; binary identity is not claimed and existing
hashes were not changed. Referenced July slides/minutes, September minutes and
Madrid/Milan workshop originals are absent locally. Obtain these versions from
partners before treating their cited content as independently verified.

## Shared journey and scope

The normal Vue and Streamlit route is: explicit capacity and general use case →
indicator scope → questionnaire → checked interpretation → draft suggestion or
unavailable/abstention → explicit participant review → individual profile report.
The old general/scenario interview remains optional. Its confirmed answers can
be explicitly linked to an equivalent indicator opening within compatible scope.
A topic tag never establishes criterion sufficiency.

All fifteen indicators are planned by default, presented in three sections of
five. Navigation resumes existing results; it does not reopen them. A partial
finish preserves unresolved coverage. Deliberate answer, interpretation,
profile/context or technical-object edits invalidate dependent active judgments.
Linked snapshots are invalidated when their source answer/scope changes.
Superseded judgments and screened revisions remain in history. API revisions,
request receipts and job generations retain stale-write protection; edits are
blocked during a running job except deliberate reset. Reload restores the
in-memory session; there is no durable cross-day resume guarantee.

ORL requires the broad unit and its responsibilities per indicator; TRL requires
a relevant object/concept, with version/environment/component scope where known.
Outside-role, no-object and not-applicable dispositions produce no fabricated
level. Profile is never inferred from profession. Use-case cards contain only
participant-confirmed descriptions, source-backed illustrative text or explicit
unknowns. Scenario retrieval has no fixed medical-corridor preference.

## Questionnaire administration: authored engineering choices

`questionnaire.py` loads the private registered JSON once per process, verifies
its hash and all mappings, and pins it with the bank in each session. Missing or
incompatible inputs block this workflow with an actionable message; they never
activate old global anchors. Private text and original packages stay outside Git.

An opening is asked unless the participant explicitly links equivalent confirmed
evidence. At most **three open answers per indicator**, plus an optional citizen
Likert category, are administered. The interpretation call may nominate one
unresolved conditional question with a real answer quotation as its basis.
The routing shortlist retains the next two ordered module questions and up to
three shared probes retrieved by lexical relevance to the complete answer.
These are routing candidates, not statement/evidence eligibility rules. Null
routing means no further question selected, not sufficient evidence or readiness.
All candidate text retains purpose, ask_when, wording provenance and source refs.
Skip, uncertainty, refusal and early finish remain available.

Optional Likert items retain exact categories, including unsure/not applicable/
refusal, separately from skip. They are self-report administration records and
are excluded from matching evidence; agreement numbers are never CRL. No ORL or
TRL Likert items are invented. Read more records source information exposure;
post-information reasoning is not automatically prior competence or development.

Full screened answers, questions, latest confirmed annotations and clarification
history are the matching input. Annotations are fallible; missing observations
are explicitly recorded as extraction absence and do not mean no evidence.
New facts in correction feedback are offered as an ordinary answer addition,
screened, interpreted and confirmed before use. Correction text cannot supply
quotations absent from the answer.

## Matching policy `indicator-matching-draft-2.0.1`

1. Consider exactly the nine trusted statements for the current indicator/profile
   independently, using complete active confirmed screened answers and scope.
2. Return supported/insufficient/conflicting for each statement with exact answer
   quotations and real evidence IDs. Missing evidence is insufficient, not false.
3. Suggest a statement only when its full meaning best describes the established
   situation; there is no highest-supported, cumulative, count, weight, confidence
   threshold or acceptance adjustment rule.
4. A current proposed safeguard can demonstrate the capability of a statement
   permitting it. It does not establish historical demonstration, formal co-design,
   influence or sustained governance. Willingness, attendance, contribution,
   demonstrated influence, actor and time must be distinguished per statement.
5. Explain the selection and a materially plausible alternative concisely. If
   several statements are marked supported, selection requires a valid different
   alternative and a nonempty distinction. Unresolved alternatives or material
   contradiction require abstention; no low-level default is supplied.
6. Python validates all IDs, profile/indicator/scale membership, the exact nine
   assessments, active scope/revision, citations in actual answers and consistency
   with the selected assessment. It resolves source text itself. Categories,
   ambiguity annotations and statement keywords never pre-exclude support or
   selection. There is no second model reviewer or old blanket ≥4 activity gate.
7. Transport/schema/evidence/privacy failures are failures, not abstentions or low
   levels. After an unavailable suggestion the participant can still select an
   exact source statement or remain unsure. No participant result is prefilled.

The same existing Qwen3-8B service handles interpretation and matching, with
bounded retries, thinking disabled and structured JSON. Complete request token
counts must fit 4096 including reserved output. Duplicate bookkeeping is omitted;
answers, conflicting evidence and nine statements are never silently truncated.
An overflow is an explicit unavailable suggestion, not a manufactured result.

This is a fallible semantic matching policy, not an empirically validated
algorithm. Structural/citation correctness cannot establish semantic support.
Participant result and tool suggestion remain separate in display and both
screened JSON/JSONL export paths (`indicator-self-assessment-2.0.0`). Common bank
and questionnaire identity is stored once. `numerical_crl`/`numerical_srl` retain
their previous meaning; no aggregate is inserted into them.

## Liono review commands

Use the existing environments/model. These commands start separate review
services; first ensure their ports are free. They do not update the running UI.

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
python3 scripts/import-readiness-scales.py inspect --indicator Noise --profile citizen
curl -fsS http://127.0.0.1:18000/v1/models
IAM_BASE_URL=http://127.0.0.1:18000 IAM_SRA_API_PORT=8004 IAM_SRA_UI_PORT=5004 scripts/start-api.sh
```

In a second terminal:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
export PATH="$PWD/.runtime/node/node-v22.23.3-linux-x64/bin:$PATH"
npm --prefix app run build -- --outDir ../.runtime/questionnaire-review/dist --emptyOutDir
cp app/serve_app.py app/proxy-routes.json .runtime/questionnaire-review/
IAM_SRA_UI_PORT=5004 IAM_SRA_API_TARGET=http://127.0.0.1:8004 .venv-api/bin/python .runtime/questionnaire-review/serve_app.py
```

Open `http://127.0.0.1:5004/tools/sra-assessment/app` on liono, or forward port
5004 from your machine. Alternative Streamlit view:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 IAM_MOCK=0 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation PYTHONPATH=src .venv-api/bin/python -m streamlit run app.py --server.address=127.0.0.1 --server.port=8504
```

Bounded synthetic live checks (outputs are private, not Living Lab responses):

```bash
PYTHONPATH=src .venv-api/bin/python scripts/smoke-questionnaire.py --base-url http://127.0.0.1:18000 --output .runtime/questionnaire-smoke
PYTHONPATH=src .venv-api/bin/python scripts/evaluate-indicator-questionnaire.py --base-url http://127.0.0.1:18000 --output .runtime/questionnaire-comparison
```

`--case` selects one case. Comparison accepts `--baseline-results` and
`--resume-from` to retain completed records from the same policy and retry failures without rerunning
passing cases. Frozen authored expectations in `eval/indicator_questionnaire_cases_v02.json`
are provisional review references, never sent as desired levels to the model.
The old matching code is recoverable at the starting Git commit; its private
snapshot was used only for this controlled comparison, not as a runtime fallback.

## Demonstration and decisions still needed

Citizen: choose citizen/proposed healthcare delivery; continue to Noise; explain a
possible disturbance and a justified safeguard, check the interpretation, request
a draft suggestion, read nine statements and explicitly choose or disagree.
Organisation: select organisational capacity and planning unit; confirm Noise
responsibility; describe actual planning arrangements and what remains untested.
Technical: select technical capacity; confirm Technical Safety object/version and
laboratory/intended environment; distinguish completed tests from intended use.
For each, finish a partial profile, reload, return to a completed indicator and
download both exports. A model failure must remain visible; manual selection is
available after collection, with no invented tool suggestion.

FN/ISCTE still need to agree questionnaire/routing/optionality, evidence
sufficiency and material-alternative distinctions, scope-specific ORL/TRL
interpretation, use of reported versus externally checked evidence, burden and
accessibility, and which participant/tool records feed future official
aggregation. Empirical evaluation with independent reviewers and actual partners
is required. Synthetic agreement and working UI are not methodological validation.

The subsequent [six-case scenario addendum](scenario-expansion-v01.md) supplies
optional context through the same controller and budgets. Its review corpus is
isolated from the deployed nine-card corpus. [Verification results](questionnaire-v02-verification.md)
separate deterministic checks from exploratory model observations.
