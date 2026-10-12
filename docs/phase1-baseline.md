# IAM-SRA2 Phase 1 — general baseline

Implemented against local commit `592fb2e73b26a96b3516bc88195b4f34d93150df`.
The working tree was clean at inspection; no AGENTS.md was found in the supplied
workspace. Existing scenario modes, private originals and historical arithmetic
are retained. No push, public deployment or unrelated service restart is part
of this change.

## What changed and why

New sessions now start with context → baseline → answer confirmation → baseline
summary confirmation → complete → explicit optional handoff. This is a descriptive,
scenario-free baseline, not a calibrated adaptive readiness test or an organisational
audit. All four numerical readiness fields are null. Support, opposition,
unknown context and withheld answers do not change a level or route selection.

The main new files are:

| File | Purpose |
|---|---|
| `configs/baseline.json` | Frozen instrument, structured context choices, four core questions, organisational variants, two-probe budget and deterministic rule priorities. |
| `prompts/baseline-evidence.txt`, `baseline-grounding.txt` | Short independent extraction/review instructions without scenario facts, acceptance or scoring. |
| `src/iam_sra/baseline.py` | Dedicated evidence schemas, exact passage/scope validation, reviewed classification, coverage and selection rules. |
| `baseline_client.py` | Existing screened Qwen transport, bounded extraction and review; empty mock explicitly labelled. |
| `baseline_session.py` | Confirmation-gated events, corrections, frozen instructions, snapshots, screened exports and handoff. |
| `baseline_ui.py` | Context, lightweight familiarity selection, substantive confirmations, editable summary, downloads and optional continuation. |
| `scripts/smoke-baseline.py` | Synthetic end-to-end cases through the normal controller, correction, export and explicit automation labels. |
| `tests/test_baseline.py`, `test_baseline_ui.py` | Evidence contracts, privacy, correction/invalidation, routing and actual Streamlit component-flow tests. |
| `eval/baseline_sample.json` | Screened synthetic export from the normal controller; no model semantic claim. |

Integration changes: `app.py`, `configs/assessment_modes.json` and the `Session`
factory default to `general_baseline`. Existing scenario tests/runners now select
their original mode explicitly. No saved session is converted when an environment
setting changes. `ui_presentation.py` reuses the current visual system and supplies
a neutral baseline title; the medical subtitle is shown only in the scenario flow.
`privacy.py` recognises narrowly defined controlled labels, schema/backend metadata
and generated B-event IDs; custom text, credentials and financial details remain
screened. `readiness_session.py` adds separate baseline provenance only to an
explicit continuation (schema 6.5.0); standalone scenario exports remain 6.4.0.
The existing workbook estimator does not read the baseline provenance.

## Original sources → questions

Original files were read locally, not substituted by repository summaries. The UI register path had a stale `-2` filename; it now points to the actual private copy, whose bytes match the registered hash and the home-directory `-2` copy. They
remain under ignored `references/private/`. Hashes and references are retained in
`references/source-register.json`. None establishes approval of these new questions.

| Source | What it supports | Phase-1 implementation |
|---|---|---|
| Workbook `Read me!D1:F13,G1:I13,J1:L13,N7:N11` | Operators, authorities and citizens are distinct audiences; SRL synthesises TRL/ORL/CRL, with CRL focused on empowerment and agency. | Separate perspective, stakeholder role and claim subject; no personal-to-organisation inference; no individual city SRL or scoring. |
| `SRA IAM indicators!C15:D15,I15` | Familiarity, understanding, information and participation opportunities are distinct from trust and acceptance. Column I criticises leading, deficit-assuming H15 items. | Neutral familiarity self-report, open understanding, information needs and barriers; no support/trust routing. |
| `C16:D16,I16` | Existing capability, learning needs and evidence of learning/application must be distinguished. Attendance intention is not demonstrated readiness. | Experience question; exposure versus contribution versus intention; optional contribution and influence probes. |
| `C8:D8,I8,J8`; comments at `C8,D8,H8,J8` | Prior awareness/experience, independent reasoning about impacts and feedback are distinct. I8 requests screening before diagnostic noise questions and rejects acceptance/confidence as CRL. D8 comment concerns organisational complaint/feedback processes. | General baseline first; reasons probe only for undetailed effects; supported topics only. No noise facts are taught and no complaint system is assumed. J8 revisions considered alongside I8, not as an approved bank. |
| `Use case(s) per LL!A1:D2` | A citizen-facing template, city headers Madrid/Milan/Coimbra; city case columns are not populated. | Broad structured city field; selected scenario remains null until explicit illustrative continuation. No fabricated local proposal. |
| GA T3.2–T3.4, printed annex p.9 / PDF p.9 | Partner-reviewed methodology, diverse stakeholder inputs, local relevance and iterative baseline work. | Draft instrument, context, auditable snapshots, no claim of complete/approved operationalisation. |
| GA Part B p.5 / PDF p.42 | CRL empowerment/agency within the wider readiness framework; reviewed instruments before digitisation. | Scenario-free descriptive evidence, no level assignment, no inference of city readiness from one person. |
| GA Part B p.16 / PDF p.53 | Distinct individual, organisational and city reporting; stakeholder inputs and local-language scope. | Explicit subject/provenance and handoff; English-only baseline prototype; specialised routes pending. |
| WP3 minutes 8 October, Discussion/Actions 1–3 | Definitions/criteria under review; concrete local cases requested separately. | Draft status, no FN approval asserted. |
| UI guide pp.10–12,18 | Clear tasks, labelled fields, secondary alternatives, confirmation for reset, accessibility checks. | Existing styling retained; one primary action per screen, optional fields only when relevant, secondary Skip/Unsure/Finish/Edit. No new official assets recreated. |

The four English core questions and organisational variants are authored prototype
wording guided by the user's latest meeting direction. They are **not FN-approved
verbatim questions**. The forthcoming FN report and complete approved “135 × 3”
bank are not supplied. Their contents or exact structure are not manufactured.

## Evidence, confirmation and budget

Familiarity is a structured self-report and requires no LLM. Three text items use
existing two-attempt, 4096-token, thinking-disabled transport and independent
classification review. At most six claims per answer are accepted. Each claim
retains question/event/passage IDs, dimension, supported topic IDs, subject,
quoted time/activity or unknown scope, IAM/transferable/unknown domain, actual
experience or intention, basis, source/version, confirmation and information context.
No confidence value is used as validity. Statements are reports or expressed
reasoning, not externally verified facts. No stance is assigned.

Core items already clearly covered can be omitted. There are at most two probes,
prioritised as scope ambiguity, undetailed reasoning, contribution after exposure,
unknown experience domain, then outcome after an actual contribution. Selection
records contain the rule, reason and confirmed event IDs used. Skip, unsure,
decline and refusal suppress repeat probes for that dimension. Influence is never
asked solely because someone attended a seminar or would attend in future.
A scope question retains both reports and does not declare a proven contradiction;
explicitly IAM versus other-domain experience remains distinguishable.

The first confirmed observation creates the immutable initial baseline snapshot.
It is a partial evidence snapshot, not an initial score. Final snapshots are added
only after summary confirmation. Edits deactivate the edited event and later
dependent events, invalidate the completed profile and handoff, and re-ask relevant
items with the same frozen instructions. Context corrections invalidate dependent
answers; prior events, contexts and snapshots remain in history. Pending corrections
require fresh confirmation. Old exports are never rewritten.

No FAQ, RAG, educational explanation or rubric is displayed during baseline.
Help wording offers skip/unsure or finishing before optional information. Therefore
baseline information exposures are empty; answer context remains before_information.
This is not evidence that respondents had no outside prior information.

## Manual walkthrough

1. Start the UI and select personal/organisation/withheld perspective, stakeholder
   category and broad city/region. Another region enables an optional broad name;
   organisation perspective enables an optional function. No identity is requested.
2. Select familiarity, then answer understanding, experience and needs (or use
   Unsure, Skip or Prefer not to answer). Confirm each substantive interpretation;
   correct it if needed. Supporting words are expandable.
3. Answer up to two eligible probes, or finish early. Confirm the editable baseline
   summary. Missing/withheld evidence remains distinct from an explicit absence.
4. Download JSON/JSONL. Personal respondents may explicitly choose the illustrative
   medical corridor; organisational/withheld perspectives see a specialised-stage
   pending notice. The scenario's own answers and scoring remain separate.
5. Privacy test: use only a synthetic address, e.g. `My address is 42 Example Street`.
   Review the cleaned preview before processing. A synthetic `My PIN is 1846`
   must be blocked, consume no question and never reach tokenisation/model calls.

`eval/baseline_sample.json` is a synthetic, screened controller export with
structured familiarity and skipped open items. Its confirmations are automation,
not citizen validation. The smoke runner saves fuller actual outputs privately
under `.runtime/`; an empty mock is not a semantic pass.

## Run and reproduce

```bash
cd ~/iam-sra-demo
scripts/setup-privacy.sh                 # only if pinned local resources are missing
.venv-privacy/bin/python scripts/check-privacy.py
scripts/stop-ui.sh
IAM_ASSESSMENT_MODE=general_baseline scripts/start-ui.sh
# Open http://localhost:8501

# Explicit developer route to preserved scenario/historical modes:
scripts/stop-ui.sh
IAM_DEVELOPER=1 IAM_ASSESSMENT_MODE=acceptance_and_readiness_evidence scripts/start-ui.sh
# Choose either scenario evidence mode or historical mode before starting.

.venv/bin/python -m pytest -q
.venv-privacy/bin/python -m pytest -q tests/test_baseline.py -m presidio_live
.venv-privacy/bin/python scripts/smoke-baseline.py --mock --output .runtime/baseline-mock.json
.venv-privacy/bin/python scripts/smoke-baseline.py --output .runtime/baseline-live.json
```

Privacy is mandatory, with no new switch or exception for demo cases. It runs
before text retention, tokenisation/generation, model audit retention and downloads.
Only the explicit confirmed cleaned version is processed after a masking preview.
The existing local-resource fail-closed behaviour remains. Browser/widget transient
memory still receives input; this is not anonymity, forensic erasure or certification.

## Verification and limits

See the accompanying implementation report below for actual test counts and live
status. AppTest inspects real Streamlit component/controller flow but cannot prove
rendered mobile layout, browser focus, keyboard or screen-reader behaviour. No
browser automation tool is available in this session. Manual checks remain: desktop,
390px, 360px, 200% zoom, Tab/Enter/Space, visible focus, long text, masking preview,
error recovery, edits, download content and handoff. Existing font/logo/hub/privacy
ownership decisions remain open; no full UI-guideline compliance is asserted.

## Phase 2 inputs still needed

- FN-reviewed question/statement bank and forthcoming report, with stable IDs,
  subject/role rules, evidence anchors, translations and approvals.
- Reviewed populated Madrid, Milan and Coimbra local cases: operations, endpoints,
  timings, uncertainties, source versions, applicability and mitigation feasibility.
- Evidence-to-level prerequisites, verification requirements and synthesis rules;
  how prior learning, information exposure and chatbot participation should count.
- Specialised organisational/operator scope and questions; reporting and sharing
  permissions. The baseline alone is not an ORL/TRL audit.
- Responsible privacy owner/contact, retention, lawful basis, access and rights
  procedures, plus WP2 assets and agreed hub integration.

No full bank, automatic scenario generation, new training, database, authentication,
production deployment, city synthesis or new numerical formula is included.

## Actual verification — 12 October 2026

- Full regression suite: **1,225 passed, 7 skipped** in 157.65 seconds. Skips
  require real Presidio resources in the core test environment.
- New baseline/controller and Streamlit tests: **31 passed, 2 skipped** in
  4.52 seconds. Includes partial core-item wording, corrections, early finish,
  structured context, privacy preview, no scenario injection, and handoff isolation.
- Dedicated real Presidio baseline checks in `.venv-privacy`: **2 passed** in
  5.72 seconds. Covers controlled cities/roles, full screened exports and extraction/
  review request envelopes using controlled transport responses. This is real NLP
  screening with a transport double, not live Qwen validation.
- Synthetic end-to-end smoke: all three cases completed with the explicitly empty
  mock extractor, including confirmation, a correction and final export. They
  establish workflow execution only; no semantic pass is claimed.
- Live smoke: all three cases failed with `transport` because the configured local
  service is unreachable from this execution environment. No model interpretation
  was returned or human-validated. Actual reports are private under `.runtime/`.
- The committed synthetic sample passed real local screening. Python compilation
  and `git diff --check` passed. All six original source hashes match; originals,
  runtime traces and virtual environments remain Git-ignored.
- Streamlit AppTest exercises component flow, conditional fields, confirmation,
  corrections, masking preview and downloads. No browser automation tool or
  Chromium executable is available: real screenshots, mobile layout, keyboard
  focus, 200% zoom and screen-reader checks remain unverified.

A successful mock, schema check or detector test is not proof of live semantic
accuracy or methodological approval. No numerical formula or level assignment
was introduced; the optional existing scenario estimator remains isolated.

### Session review: baseline 1.1.0

Reviewed the privately supplied first-session export locally; the transcript is
not a committed fixture. It showed a real information need about airborne safety
lost after disagreement over classification, an attendance answer incorrectly
labelled already answered, and free-text uncertainty displayed as unclear.
The reviewer can now supply a supported, corrected interpretation/category;
server-side kind/temporality validation still prevents reasoning being converted
into actual experience. Supported retained claims count as substantive. Free-text
unsure/declined responses remain visible in coverage. Extraction/review instructions
explicitly preserve distinct needs, uncertainty and attendance, using ordinary
language. No external factual truth, contribution or influence is inferred.
New instrument/prompt version: baseline-1.1.0. Existing frozen sessions and
snapshots are not rewritten; use a new session to obtain revised extraction.

Citizen presentation removes supporting-words panels and small caption notes,
uses everyday headings/actions and omits implementation-stage/baseline labels.
Question counts remain normal-sized navigation text. Full evidence references,
questions, answers and confirmations remain in screened downloads. Funding text
is retained at normal size. The summary still has no numerical readiness result.
These changes do not establish that every future answer is semantically complete.
Regression fixtures use authored synthetic examples, not the uploaded transcript.
