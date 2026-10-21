# Draft citizen indicator assisted self-assessment

Starting checkout: clean `main`, `be54cea99a533b7ce9a362bc7d77b4d23160f4d2`.
Implementation branch: `feature/indicator-assisted-self-assessment`. This is an
internal methodological-review prototype, not an approved questionnaire,
certification, Living Lab validation or aggregation instrument.

Implementation files are grouped by purpose:

- Shared domain: `readiness_bank.py`, `indicator_assessment.py`,
  `indicator_client.py` and the `ConversationSession` continuation.
- Interfaces: the API adapter/schemas/service, `IndicatorAssessment.vue`, the
  existing Vue page, and `indicator_ui.py` through the existing Streamlit renderer.
- Safeguards and verification: `privacy.py`, focused indicator/domain/API/Streamlit
  tests, synthetic fixtures, the browser journey and `scripts/smoke-indicators.py`.
- Source traceability: the importer reuses the bank validator; the source
  register, API/operator documentation and reference-bank note record the new
  authorised prototype use separately from source approval.

## Sources and authored choices

GA Annex 1 T3.2/T3.3 (printed p.9) supplies the framework/tool remit. D3.1 draft
§§10.4–10.6, Tables 5–7 and “From individual responses to a city-level snapshot”
supply the profile distinctions, indicator-level self-assessment and individual
snapshot concept. The v4 workbook supplies all names, definitions, citizen
criteria and exact nine-level statements; `Read me!A2` states consortium-validation
status. Noise, for example, resolves to criterion `Indicators' assessment
criteria!F8` and statements `Scales per indicator!G56:G64`. H/I are shared row
review status/comment, not three profile approvals. The older workbook's J2 and
I8/I15/I16 distinguish acceptance/trust from readiness. `Meeting_14_10` asks for
participant review. The historical FN concept's user-validation discussion was
read as context; its concern scores and bottleneck formula are not implemented.

The workbook source SHA256 remains
`809ce70aec6444fd59358ac1d79806d7c47fcfce72460c8430cb1dad64882818`.
The imported JSON's SHA256 is
`9fa561bcfd20e847ff9b64353e06b6ac95201903cdc86a49fabffbfd12175695`.
Bank/schema: `fn-v4-1.0.0` / `readiness-scale-bank-1.0.0`.
The bank's original draft/reference metadata is unchanged. Runtime use is
separately authorised by the project owner's current instruction and recorded
in `source-register.json`. D3.1's filename v0.18 versus internal version 0.1
remains a source-version clarification, not approval evidence.

We designed the continuation, question wording, budgets, matching policy,
evidence guards and reporting convention. These are not verbatim FN questions,
approved KVIs or a source-specified executable algorithm. All fifteen citizen
scales are supported by the same code. Personal perspective must be explicitly
selected: profession does not assign a profile. Organisation/withheld interviews
remain available, but receive no invented citizen, organisational or technical
readiness result.

## Journey and provisional policy

After confirming the existing interview summary, the citizen selects one to
three indicators for a round, a general/illustrative/actual-experience context,
and optionally a short use-case description. An illustrative context requires an
example actually discussed. Previously confirmed answers can be explicitly
linked per indicator (up to three); general and scenario contexts cannot be
silently mixed. Their exact words, prior interpretation, ambiguities and
information-exposure context remain available. Topic tags alone are not used as
proof of relevance. Linking an answer does not establish its substantive fit.

The shared controller asks up to three short prototype questions, grounded in
the selected name/criterion and references to its understanding, conditions and
influence statements. It suppresses already captured intents from explicitly
linked evidence, adapts participation wording to reported activity/barriers,
and permits uncertainty, refusal, skip and early finish. The existing 8-general /
4-scenario budgets are unchanged; this is an explicit optional continuation.

Policy `indicator-matching-draft-1.0.0`:

1. A single screened interpretation call records meaning and exact original-answer
   quotations, distinguishing actor, actuality, domain, kind and ambiguity. The
   participant confirms/corrects that interpretation. Correction feedback is not
   new topic evidence; it cannot introduce a quotation absent from the original.
   Both interfaces show the interpretation's actor, kind, actuality and ambiguity
   in plain language. A fluent summary alone is not sufficient for review.
2. One matching call independently assesses all nine exact citizen statements
   against the selected indicator, scope and confirmed observations. It returns
   supported/insufficient/conflicting, citations, a selection or null, a concise
   explanation and a gap summary. IDs are constrained to the supplied bank;
   Python resolves all source text, level labels, cells and review statuses.
3. Python rejects unsupported IDs, wrong profiles, duplicate/missing statements,
   fabricated quotations, absent evidence, and support based only on stance,
   intention, barriers, uncertainty or bare claims. Ambiguous observations do
   not independently establish support. Wording-specific guards require reported
   actual influence for “demonstrably”, actual agency for “sustains”/“uses
   established”, and actual activity for “takes part” or evaluation through/during
   demonstrations. These are conservative prototype guards, not a complete
   semantic verifier and not a universal numeric-level participation gate.
4. The model chooses a best descriptive fit only when it can explain the full
   statement. Multiple plausible matches that cannot be distinguished or material
   same-actor/activity/time contradictions require abstention. There is no
   highest-mentioned-level rule, cumulative prerequisite, numerical confidence
   threshold, weighting or tie-breaking formula. Insufficient evidence does not
   mean a statement is false or the respondent incapable.
5. A justified safeguard proposed here may demonstrate a capability where the
   actual statement permits it. It cannot establish historical co-design,
   influence or sustained governance. Participation barriers are retained; they
   neither confer readiness nor force a low level. Supplied definitions and
   post-information reasoning are not independent prior competence or development.
6. No observations produces an explicit no-evidence abstention. Transport,
   privacy, schema or context-budget failure produces no suggestion, not a low
   level. The existing transport allows at most two attempts, 4096 context tokens
   and bounded calls. Evidence is never silently truncated. Repeated suggestion
   requests after a saved suggestion require revised evidence. A failed request
   may be retried explicitly; the participant can still choose a
   statement independently after an abstention or unavailable suggestion.

The wire response deliberately omits nine repetitive free-text reasons; Python
supplies fixed evidence-status descriptions. The model supplies the selection
explanation and gap summary. All nine statement IDs are required object keys in
the inference schema; normalized stored results retain the ordinary list shape.
Generated citations are constrained to the available evidence IDs and exact
observation text, then validated against the cited answer. The same conservative
actual-action guards constrain generation and validate its output; they do not
establish semantic support for any remaining statement. There is no extra model-review pass. Model semantic
matching and schema checks are fallible and are not empirical validation.

## Participant choice, revision and exports

The participant can read all nine exact statements, explicitly endorse the
suggestion, select another statement, remain unsure or decline. No choice is
prepopulated from a suggestion or earlier summary confirmation. An optional
review explanation is recorded separately and is not fed back as new evidence.
Adding facts requires editing an answer, interpretation and confirmation again.

The participant's explicit selection is the displayed individual result; the
tool suggestion or abstention remains separate. This is a prototype reporting
convention, not an agreement on official aggregation input. Level 1, unassessed,
insufficient evidence, unsure and declined are distinct; none is zero. Coverage
shows all fifteen indicators without unsupported numbers. There is no overall
citizen score, city aggregate, ORL/TRL workflow or ecosystem SRL formula.

The bank is loaded/validated once per process against the registered source and
bank digests, then privately pinned for the session. Updates require an operator
rebuild/review and process restart. Missing/incompatible data prevents this
continuation with an actionable message, without global-anchor fallback.

Answer/interpretation edits invalidate both dependent judgments and retain small
superseded judgment records plus immutable answer revisions. Interview/context
edits conservatively invalidate all indicator judgments. Scope changes supersede
old-scope results. An API review carries both API and assessment revisions. The
existing copied-controller job lane, generation/version checks, receipts,
privacy-preview binding and reset cancellation fence out late/stale writes.
Changes after correction are assessment refinement, not evidence of development.

API 1.1 adds `indicator_assessment`; normal JSON/JSONL downloads keep both
judgments, evidence, context, gaps, history and source/version references. Common
bank identity is stored once, not the full 405-statement bank. Both API and normal
Streamlit downloads exclude operational paths, prompts and model endpoints.
Historical `numerical_crl` is not repurposed. The old global estimator requires
`IAM_DEVELOPER=1` and is labelled historical in Streamlit; it is absent from the
normal Vue journey. Existing historical sessions are not rewritten.

## Build and local review on liono

The source bank, source originals, generated conversation corpus, environments,
model cache, built UI and reports remain ignored by Git. Use the existing
`.venv-api` with its read-only CPU privacy dependency link. The actual local
Qwen alias/origin must be checked; the existing origin used for this verification
is `http://127.0.0.1:18000`. No inference service or GPU configuration is replaced.

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
python3 scripts/import-readiness-scales.py build
python3 scripts/import-readiness-scales.py inspect --indicator Noise --profile citizen
PYTHONPATH=src .venv-api/bin/python scripts/build-conversation-corpus.py
PYTHONPATH=src .venv-api/bin/python scripts/check-privacy.py
```

To review without replacing a running API or UI, use free ports in two terminals:

```bash
# Terminal 1: actual controller, sources and model; no fixture factory
IAM_BASE_URL=http://127.0.0.1:18000 IAM_SRA_API_PORT=8004 IAM_SRA_UI_PORT=5004 \
IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5004,http://localhost:5004 \
bash scripts/start-api.sh
```

```bash
# Terminal 2: build isolated assets so app/dist used by a running UI is preserved
export PATH="$PWD/.runtime/node/node-v22.23.3-linux-x64/bin:$PATH"
npm --prefix app run build -- --outDir ../.runtime/indicator-review/dist --emptyOutDir
cp app/serve_app.py app/proxy-routes.json .runtime/indicator-review/
IAM_SRA_UI_PORT=5004 IAM_SRA_API_TARGET=http://127.0.0.1:8004 \
.venv-api/bin/python .runtime/indicator-review/serve_app.py
# Open http://localhost:5004/tools/sra-assessment/app
```

Streamlit uses the same domain methods:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation \
.venv-api/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Live synthetic smoke (starts no model/service; outputs are visibly synthetic):

```bash
PYTHONPATH=src .venv-api/bin/python scripts/smoke-indicators.py \
  --base-url http://127.0.0.1:18000 --output .runtime/indicator-live-smoke
```

The disagreement smoke checks the proposed-safeguard interpretation against an
authored synthetic expectation and requests at most one ordinary participant
correction. It records whether that was needed, retains the revision, and fails
if the proposal is still lost or the required disagreement is not observed.
It does not send a desired level to the model.

For browser checks, this checkout pins Puppeteer 25.13.0, whose own revision
metadata specifies Firefox `stable_157.0.1`. The system Firefox 136 is incompatible:
unsupported orientation commands, unreliable response events and intermittent
reload stalls were observed. Install the compatible binary only in ignored test
storage; do not replace system Firefox or change application dependencies:

```bash
node app/node_modules/@puppeteer/browsers/lib/main-cli.js install \
  firefox@stable_157.0.1 --path .runtime/browser
FIREFOX="$PWD/.runtime/browser/firefox/linux-stable_157.0.1/firefox/firefox" \
BASE=http://127.0.0.1:5003 ONLY=sra-assessment \
SHOTS="$PWD/.runtime/indicator-browser-shots" npm --prefix app run check
```

Port 5003 in that command is the explicitly isolated browser-fixture server. Its
authored model replies and synthetic detector test controller/UI integration,
not live inference or privacy detection. Live smoke and real-detector checks are
separate. The production API startup command above never selects this fixture.

Manual synthetic demonstration: choose personal/citizen, finish and confirm the
baseline, decline the example and confirm the summary. Select Noise/general
understanding. Explain how recurring flights could affect rest, confirm the
interpretation, describe a safeguard if asked, then finish indicator questions.
Request a suggestion. Read all nine statements and choose another one, or remain
unsure. Download JSON/JSONL; check that the two judgments remain separate. Reopen
an answer/interpretation and verify that both active judgments disappear. Repeat
with “I do not know” and check abstention rather than a forced low level.

FN/ISCTE agreement and empirical work are still needed on evidence sufficiency,
capability versus opportunity per statement, semantic matching ambiguity and
bias, questionnaire/KVI design, accessible explanations, reported versus verified
activities, the participant-result reporting convention and any future official
aggregation input. D3.1's proposed aggregation is not activated here.

## Observed verification, 21 October 2026

The earlier broad offline run passed 513 tests with 24 dependency-dependent skips.
It was not repeated during completion of the live/browser work. Overlapping,
focused runs passed 141 API/conversation/import checks, 45 indicator/API/Streamlit
checks after the matching-schema change, and finally 131 privacy/indicator/API
checks after the metadata-screening corrections. The latter includes the real
Presidio tests; identifying text and credentials remain blocked. These counts
must not be added as if they were distinct tests. Commands for the final focused
runs were:

```bash
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q \
  tests/test_indicator_assessment.py tests/test_indicator_api.py tests/test_indicator_ui.py
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q \
  tests/test_privacy.py tests/test_baseline_privacy_v2.py \
  tests/test_indicator_assessment.py tests/test_indicator_api.py
```

The production frontend build passed (55 modules). Firefox 157.0.1, matching
Puppeteer's revision, passed all eight working/detail layout checks and all four
interactive journeys. These include the actual controller's indicator question,
interpretation confirmation, suggestion, alternative selection, reload, explicit
endorsement, stale-review rejection, correction invalidation and JSON/JSONL
downloads. Mobile privacy previews, blocked credentials, recoverable model
failure, reset during work, navigation cancellation and organisational scope
also passed. Authored fixtures were used for browser model responses, not passed
off as live inference. The independent proxy transport check and IAM-CC donor
asset provenance check passed. All fifteen real-bank citizen indicators were
also selected through the default Flask controller with real privacy screening,
resolving 135 distinct citizen statements without injected banks or clients.

Failures were investigated as follows:

| Classification | Finding and disposition |
| --- | --- |
| Application | Streamlit's selection callback captured an old dropdown value. It now reads current widget state; the actual AppTest journey passes. |
| Application | Confirmation hid classifications used by matching. Both interfaces now expose their plain-language meaning and ambiguities. |
| Application / detector integration | Presidio tagged fixed workbook coordinates, shared-row IDs and hexadecimal completion IDs as people. Only bounded syntax in the exact metadata fields is exempt; identifying prose and arbitrary values remain screened. All fifteen real scales and identifying-text regressions pass. |
| Model output | Excess prose, missing statement rows, string `"null"`, invented citations and hypothetical-action support caused rejection. The wire format now requires all nine trusted keys, real JSON null, exact observation citations and the existing admissibility restrictions. Python still independently rejects invalid output. No failed response creates a score. |
| Test environment | System Firefox 136 is incompatible with Puppeteer 25.13.0. The matching Firefox binary in ignored storage passes the original response-monitoring harness and all assertions. Experimental old-browser workarounds were removed. |
| Model output, remaining limitation | A nuanced proposed safeguard was initially classified as intention. Participant correction repaired the final run. Similar substantively useful answers still received different-quality matches; semantic accuracy is not established. |

Live Qwen/Qwen3-8B on the existing vLLM 0.8.5 service produced these actual runs:

| Synthetic run | Observed result | Calls / duration |
| --- | --- | --- |
| Uncertain | Abstention, no level; participant remained unsure. | 2 / 50.585 s |
| Explicit safeguard | Tool suggested Noise CRL 1; participant selected 2; both survived export. The reasoning inadequately addressed the proposed safeguard, so this is a workflow pass with a semantic concern. | 2 / 52.236 s |
| Nuanced safeguard, final rerun | Initial misclassification, then one participant correction; tool suggested Noise CRL 5 and a separate participant selection was preserved. | 3 / 54.680 s |

The last two runs used the same recorded code snapshot
`7a4949983b84dff9283f0c6d4e5b7de989c089ed973103044e87b8df26f9f3c3`.
The uncertain run preceded the final metadata-only privacy correction. These are
small exploratory checks, not an accuracy estimate or comparative benchmark.
Live semantic checks cover Noise only; bank resolution across all fifteen
indicators does not establish matching accuracy for the other fourteen.
Earlier failures and partial sessions remain in ignored `.runtime/` reports;
they were not relabelled successful. Final live artifacts are in
`.runtime/indicator-live-bounded-wire/`, `.runtime/indicator-live-explicit/` and
`.runtime/indicator-live-nuanced-final/`. Consolidated results are in
`.runtime/indicator-verification/summary.json`.

The checkout is ready for a **guided methodological-review demonstration**, with
active interpretation checking and explicit participant choice. It is not ready
for dependable unattended level assignment or validated readiness reporting.
The deployed service was not replaced; use the separate review launch commands
above. A final read-only probe returned HTTP 200 for the existing model, API and
UI. An initial five-second health-probe timeout did not recur; its precise cause
was not established. No inference service, environment or GPU workload was
restarted. Only isolated test servers were used and stopped after verification.
