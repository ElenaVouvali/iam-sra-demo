# FN meeting demonstration — instrument 1.3.0

**Meeting-ready means a working, traceable demonstration with accurately reported
limitations. It does not mean methodological approval or production readiness.**
Local baseline f451bec; no unrelated changes were present. No AGENTS.md was found
in the checkout or parent source directory. No push, deployment, model download,
new service, scoring formula or historical arithmetic change is part of this work.

## What changed, and why

Previously, opening the optional-information expander could display the explanation
without recording exposure. Now an explicit **Show explanation** or **Show sourced
answer** action records exactly what is displayed, its version/source, sequence and
UTC time. Acknowledgement is a separate event. The first pre-information profile is
preserved. Later citizen answers carry after_information_exposure context. Neither
retrieval questions nor explanations enter citizen evidence or the interview budget.
The existing optional reflection uses the same five-question interview budget.

The small RAG prototype searches eight allowlisted citizen explanation passages and
two separate researcher references. It normalises plurals and example/scenario,
uses transparent BM25-style ranking with a +2 topic-metadata match boost, requires two matched content terms and returns
at most three passages. This gate indicates lexical relevance, **not proof that a
question is fully answerable**. For that reason all answers disclose limited coverage.
The existing Qwen model composes 1–3 exact sourced excerpts. Citation IDs, quotation
text and complete-sentence boundaries are checked. A model cannot drop the beginning
of a sentence to turn “does not establish X” into “X”. No free factual prose or model
memory completion is accepted. Failure yields relevant sourced excerpts; no relevant
passage yields an explicit unavailable/unknown state. Four short information requests
per session; 300 characters per question; 600 reserved output tokens; existing
transport context/retry/deadline checks remain in force.

This extractive approach is deliberately limited. It can be less fluent and can
retrieve an adjacent passage rather than fully answer a question. It supplies no
noise measurements, local policies, retention rules, approved participation channel
or verified mitigation guarantee. Source metadata distinguishes scenario facts,
draft explanations and historical hypotheses. Allowlisted drafts are visibly marked;
permitted demo use is not approval. Historical scores and internal review minutes
cannot enter citizen retrieval. No transcripts, expected answers, workshop baselines,
contacts or administrative records are indexed.

A separate developer comparison shows the source's fixed numbers, its arithmetic
and limitations alongside a separately requested, **unconfirmed** model interpretation
of the exact FN response. It never injects numbers into a citizen session. The
researcher report traces quotations to interpretations, criterion/topic, status,
context, confirmation and uncertainty, showing initial/final evidence and corrections.
It flags exact repetition of displayed sentences; different words do not prove
independent prior knowledge either. These are audit annotations, not a correctness
rubric or learning gain. The prompts now explicitly require belief/report attribution
for unverified factual claims. A valid quotation alone does not establish external truth.

## Three cases and walkthrough

Structured definitions: `eval/meeting_cases.json`. Keep them out of prompts and the
retrieval corpus. The FN case is the source's simulated citizen example; the other
two are authored synthetic examples. Follow-up variants are keyed to the actual
question ID (reflection) or criterion. No positional list of answers is replayed
against unrelated questions. Expected outcomes are semantic invariants, not exact
wording or numerical targets.

| Case | What to inspect initially | What must not be inferred |
|---|---|---|
| Exact FN example | Original route opposition with conditions; medical-purpose support; noise/rest reasoning; unanswered recording question | Consultation, influence, participation opportunity, equity expertise, airspace capacity or infrastructure knowledge from rerouting |
| Enthusiastic support | Support and explicitly unclear knowledge of effects | Demonstrated understanding from enthusiasm, prior participation, direct 9 or any readiness number |
| Reasoned opposition | Rest-impact explanation, requested measurements, reported bus consultation contribution, unknown influence, willingness and access barrier | Actual drone participation, independently verified influence, co-design award or a CRL level |

1. Start the default mode. Paste one case's initial answer; inspect supporting words
   before confirming. A human presenter should correct a wrong interpretation rather
   than confirming it because the model produced valid JSON.
2. After initial confirmation, open **Optional: learn more about this example**.
   Nothing factual is displayed solely by opening the expander. Ask “Are camera
   images recorded or retained?” with **Show sourced answer**. Inspect source IDs,
   locations and draft labels. The collection says the policy is unspecified.
3. Optionally acknowledge the answer. Use **Show explanation**, then the existing
   **Read and reflect** action if desired. Explain a possible effect and what remains
   uncertain. Keep your stance. This elicits post-information evidence, not a gain.
4. Answer only relevant interview questions, using the matching variants. Unsure,
   Skip and Finish retain their distinct controller/export meanings. Influence is
   asked only when prior participation is supported. No missing answer is a deficit.
5. Review the two distinct final sections. Numerical CRL/SRL remain null with the
   methodological-approval reason. Download JSON/JSONL.
6. Use **Edit an earlier answer** once. The final profile is invalidated; reconfirm
   and finish. The immutable first snapshot remains; superseded events stay audited.
7. In developer mode, open **FN historical reference comparison**. Show the fixed
   `(8+3+4+2)/4=4.25`, privacy cap `2+2=4`, illustrative result `4`. Separately select
   **Interpret reference answer** for current model findings, explicitly unconfirmed.
   This reference is distinct from the legacy live acceptance mode.
8. Open **Researcher evidence report**; compare initial/final quotations and contexts.
   Download the report. Explain new findings as additional evidence/correction or
   post-information reasoning, not personal development.

Example trace (expected structure, **not a fabricated live result**): initial FN
answer contains a noise/rest explanation and a recording question but no attendance.
A follow-up reporting no prior consultation adds explicit absence. Optional information
states retention is unknown. Reflection is marked post-information. The initial
snapshot remains unchanged; any new participation claim remains self-report and
influence unknown unless separately evidenced. No number is assigned at any step.

## Original sources rechecked and their role

All six required original documents are locally available under ignored
`references/private/`, with user-provided copies in `/home/evouvali`. No missing
original is being replaced by a repository summary. Hashes are in the source register
and individual retrieval passages. Private documents and runtime traces stay ignored.

| Original | Use and limitation |
|---|---|
| UI guide v1.0, all 19 pages and rendered contact sheets | Existing palette/layout/actions retained. See the page checklist in readiness-ui-guidelines-review.md; this task does not redesign the interface |
| SRA_LLM_FN_concept.pdf, pp.1–9 | Fixed scenario p.5; historical numbers pp.6–7; hypothetical gates pp.8–9. Not verified engineering evidence or approved CRL scoring |
| Topic-experts workbook | Read me citizen empowerment/agency; C/D definitions; H candidate questions versus I critique; I8/J8 and comments C8/D8/H8/J8, I14–I16; use-case template. Draft under review; no approved operational formula |
| WP3 minutes 8 October 2026 | Discussion/decision and action points: criteria review due 14 October and use cases due 12 November; no demo approval |
| WP3 presentation 10 September, slides 3–6 | Acceptance/readiness distinction, planning/calibration/UAT context; no approved interview or source-publication permission |
| GA T3.2–T3.4, printed p.9; Part B pp.5,16 | Review/validation obligations, empowerment/agency and self-assessment/reflection. No universal numerical citizen formula inferred |

The source PDF's p.9 “average (6.0)” is inconsistent with its initial 4.25. Its cap
wording refers to a lowest phase score while its example uses privacy 2. Both remain
source limitations; no silent universal rule or exact follow-up score is invented.
Psychological/archetype labels are not citizen diagnoses. Medical-purpose support
does not establish equity knowledge; camera/altitude concerns need not be aesthetics;
rerouting preferences do not establish participation or infrastructure expertise.

## Reproduce

```bash
cd ~/iam-sra-demo
scripts/health-check.sh
# If already running, stop only this project's UI before loading new code:
scripts/stop-ui.sh
IAM_ASSESSMENT_MODE=acceptance_and_readiness_evidence scripts/start-ui.sh
# Open http://localhost:8501; forward port 8501 if connecting remotely.
```

Presenter controls (restart only project UI):

```bash
scripts/stop-ui.sh
IAM_DEVELOPER=1 IAM_ASSESSMENT_MODE=acceptance_and_readiness_evidence scripts/start-ui.sh
```

Select the default mode and **Start selected demo**. Historical mode is available
through that selector, labelled Historical experimental acceptance index. It retains
legacy arithmetic; neither it nor the reference view is the default readiness result.

On **liono**, or the host with the existing configured model service:

```bash
cd ~/iam-sra-demo
.venv/bin/python scripts/smoke-readiness-evidence.py --meeting \
  --output .runtime/fn-meeting-live.json
# If the existing service is at a different accessible URL:
# ... --base-url http://127.0.0.1:8000
.venv/bin/python -m pytest -q
```

The runner confirms automatically and labels this automation, **not citizen validation**.
It records actual initial/final outputs, optional exposure, relevant follow-ups, a
correction, provenance/versions, latency, errors and a researcher report. Structural
success is not semantic accuracy. Human-inspect all three cases using their invariants
and record pass/partial/fail plus quotation evidence, especially FN privacy/noise,
support without reasoning, and transferable participation with unknown influence.
Do not tune extraction to fixture wording or manually insert reference numbers.

To report a downloaded session without model calls:

```bash
.venv/bin/python scripts/replay-readiness-session.py \
  --input .runtime/iam-evidence.jsonl --report-only \
  --output .runtime/iam-researcher-report.md
```

Replay without `--report-only` requires matching question ID AND criterion. It refuses
to replay post-information answers without recreating the exact exposure, rather than
mislabel them as prior knowledge. Full exports, including complete source content,
remain available. Reports and sessions should stay under ignored .runtime/exports.

## Version compatibility and implementation map

- `configs/readiness_corpus.json`, `readiness_retrieval.py`,
  `prompts/readiness-explanation.txt`: small versioned allowlist, lexical retrieval,
  bounded existing-model extractive composition, citation checks and sourced fallback.
- `readiness_session.py`: explicit display/acknowledgement, pre-information snapshot,
  frozen session corpus, separate information budget; additive export schema **6.3.0**.
  Existing histories/snapshots are not rewritten. Older sessions lacking new fields
  retain their frozen instrument and export safe empty additions; any newly displayed
  corpus is individually versioned in its exposure record.
- `readiness_ui.py`: secondary optional display/question controls; developer-only
  comparison and evidence-report views; citizen results/nulls unchanged.
- `readiness_report.py`: source-to-evidence report and fixed historical reference;
  exact repetition annotation is lexical, not a learning/independence judgment.
- `configs/readiness.json`: instrument **1.3.0**, records optional-information revision;
  existing question text, eligibility and five-question budget unchanged.
- `readiness_client.py`, evidence/grounding prompts: prompt version **readiness-1.3.0**,
  explicit unverified belief/report attribution; source-first and blind review unchanged.
- `eval/fn_reference.json`: original numbers preserved, source hash/version/limitations
  recorded. `eval/meeting_cases.json`: source/synthetic case definitions and invariants.
- Existing smoke/replay scripts extended; no second assessment pipeline. Focused tests
  cover retrieval boundaries, citations/qualifiers, exposure, budgets, corrections,
  exports, old sessions, question-context safety and researcher/citizen separation.
- Source register, this guide, README and UI review notes document actual source roles,
  partial branding compliance, verification and remaining FN decisions.

## Four decisions for FN

1. What should the numerical result measure, and what role remains for the original
   acceptance-oriented concept example? Individual CRL and city SRL are not equivalent.
2. Which evidence anchors, prerequisites and verification requirements define CRL levels?
   Are they cumulative, and how should missing/conflicting/opportunity evidence be handled?
3. How should information exposure and participation in this chatbot count? Distinguish
   display, acknowledgement, demonstrated reasoning, reported action and actual influence.
4. Who approves and maintains questions, rubrics, source use and UI/hub requirements?
   Supply approved assets/privacy URL and agree WP2 integration and review ownership.

## Verification recorded in this editing environment

- Final full regression suite: **1,137 passed in 56.82s**. Includes historical
  arithmetic, default mode/nulls, readiness/session/UI, retrieval, citation,
  qualifier-preservation, exposure, exports, corrections and old-session checks.
- Focused readiness/session/retrieval/UI run: **82 passed** before the final added
  developer-isolation/default-corpus checks; all additions are in the full run.
- Python compileall, runner `--help` and `git diff --check` passed.
- All six original source files exist and match their registered SHA-256 hashes.
- Independent CPU retrieval was executed for all four suggested questions. Relevant
  IDs: MC-SCENARIO (plus adjacent privacy unknowns), MC-NOISE-UNKNOWN,
  MC-PRIVACY-UNKNOWN and MC-PARTICIPATION. Without a model client these correctly
  produce sourced fallbacks, not generated answers. Runtime artifact:
  `.runtime/fn-retrieval-check.json`.
- Report-only CLI executed on an explicitly labelled deterministic synthetic session;
  `.runtime/fn-report-fixture.md` was generated. This tests report plumbing, not
  actual model interpretation or citizen confirmation.
- The three-case **live** command was actually attempted. This host is `davinci`,
  not `liono`. Access to the configured localhost service failed with
  `[Errno 1] Operation not permitted`. `.runtime/fn-meeting-live.json` records all
  three as blocked, null actual outputs, no live model use and no semantic validation.
  Therefore there are **no new live FN/support/opposition outputs to human-inspect**
  and no measured live-case latency. The pinned intended model revision is
  b968826d9c46dd6066d109eabc6255188de91218; instrument 1.3.0, extraction prompt
  readiness-1.3.0, explanation prompt retrieval-extractive-1.0.0 and corpus 1.0.0
  are recorded in the runner and individual exports/exposures.
- No actual application screenshots or browser accessibility checks were possible.
  Desktop/390/360px, 200% zoom and keyboard/focus checks remain manual and unverified.
  See the UI review's explicit checklist. AppTest is not a screenshot or WCAG audit.
- Private PDFs, originals and runtime artifacts remain Git-ignored. No service was
  started/restarted, no model was downloaded, and nothing was pushed or deployed.

Before presenting, run the live three-case command on liono/the actual model host,
inspect all outputs against the case invariants and complete the browser checklist.
Keep disagreement/error evidence visible; a successful request is not a semantic pass.

### Live scope reliability patch

Readiness prompt 1.3.1 omits optional free-text activity/date scopes from generation. Missing scopes are stored as empty (unknown), not inferred or repaired from model paraphrases. Explicit scopes in imported/typed claims still require exact source fragments. Existing snapshots are unchanged. Scope-based automatic contradiction detection requires explicit shared activity and time; new live records with unknown scope do not establish such a conflict. Explicit contradictions and citizen corrections remain available. This is a conservative extraction limitation, not a change to numerical policy or interview questions.
