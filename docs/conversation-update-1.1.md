# Conversational interview 1.1 — 14 October 2026

Implemented locally on the existing dirty `main` checkout. Unrelated baseline,
model-recovery and notebook work was preserved. No model restart, dependency update or external deployment was part of this
implementation. Private source documents and runtime artifacts are excluded from
the GitHub update. Separate Colab and model-service diagnostic work remains local.

## Sources and retrieval

The private corpus now contains **65 question variants, nine scenarios and
18 reference passages**. The FN corridor remains available. The eight new
source-described planned routes are two Madrid routes (GA PDF pp.56–57 / Part B
pp.19–20), two Milan hospital routes (PDF p.58 / Part B p.21), and four Coimbra
pharmacy-to-village routes (PDF p.59 / Part B p.22). These plans are not evidence
of current operations or authorisations. Fixed public route labels remain
separate from respondent details. Approximate distance units are expanded in
prose without changing values.

Examples are ordered by the selected city and confirmed topics. The respondent
can select another example before proceeding. Scenario display is recorded as
information exposure. FN camera, altitude and noise details cannot enter
explanations for a GA route; only relevant route passages and common workbook
construct explanations are available there. Original source/configuration hashes
and source-checked scenario contents are validated on load.

New thematic questions cover noise, safety/privacy information, accessibility,
equity, environmental comparisons and infrastructure. A conditional question
explores an existing contributor's role in ongoing decisions. Wording is an
authored prototype adaptation of the workbook definitions and feedback, not an
approved questionnaire. The private notes sidecar preserves original drafts,
feedback and J2/J8 revisions for the reviewed rows.

## Question adaptation

The model chooses the next objective from up to **five eligible retrieved
records**. It may freely paraphrase or ask an answer-specific neutral clarification
within that objective. A separate bounded model request checks criterion meaning,
neutrality, source grounding, actor and uncertainty. New wording is bound to its
review; invalid or unavailable planning uses an authored eligible fallback.

The controller still enforces prerequisites, exact source and trigger references,
topic suppression and the eight-general/four-follow-up budgets. The first
familiarity selection and stage transitions remain controlled. Optional reflection
uses a follow-up slot. Original item, actual displayed question, model review and
selection diagnostics are exported. Semantic model review is fallible and adds
latency; it is not independent validation.

## Workbook-aligned draft scoring

The workbook's `Read me!J1:L13; N6:N11` and `SRA IAM indicators!J2; I8/I15/I16`
govern the interpretation: understanding, participation and agency are distinct
from trust, support and acceptance. All nine CRL descriptions are retained.

After final confirmation, a personal respondent can request an assessment of each
anchor: **supported, insufficient or conflicting**, with a short reason and exact
supporting claims. Distinct claims from one passage receive distinct identifiers.
The selected optional CRL must cite the answers supporting its assessed anchor.

Server checks reject unsupported identifiers, ambiguous/third-party evidence,
attendance or intention used as contribution, unrelated activity used as IAM
readiness, and influence without a reported contribution-to-change link. These
are evidence-admission checks, not proof that an anchor's whole meaning is met.
A separate model request reviews every positive anchor judgement against the
full workbook description and cited respondent words. Failed review saves no new
estimate; missing evidence is not low readiness. Exact quotations, information
context and the full audit remain available.

No average, acceptance bonus, bottleneck cap, cumulative prerequisite formula or
overall SRL synthesis was invented. Organisational respondents receive an evidence
profile. The main CRL/ORL/TRL/SRL numerical export fields remain null; any draft
citizen estimate is stored separately. External verification, scientific validation
and an approved evidence-to-level method remain outstanding.

## Run and verify

With the existing model service available on port 18000 (the current davinci
setup; use port 8000 instead if that is where your service runs):

```bash
cd ~/iam-sra-demo
.venv-privacy/bin/python scripts/build-conversation-corpus.py
scripts/stop-ui.sh
IAM_MOCK=0 IAM_BASE_URL=http://127.0.0.1:18000 IAM_ASSESSMENT_MODE=retrieval_grounded_conversation scripts/start-ui.sh
```

Open localhost:8501 and start a fresh session. The existing default remains the
general interview; the enhanced mode can also be selected under **Choose interview
mode** after restarting. File watching is disabled, so browser refresh alone does
not load changed modules. Other modes and their existing scoring behaviour remain
available.

The original benchmark is preserved. The successor bank explicitly supplies
route-neutral answers and responses to new branches:

```bash
.venv/bin/python -m pytest -q -m 'not presidio_live'
.venv-privacy/bin/python -m pytest -q -m presidio_live
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --conversation --fixtures --output .runtime/conversation-v11-final-fixtures.json
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py --conversation --output .runtime/conversation-v11-live.json
```

## Actual verification

- Final full offline regression: **464 passed**, 19 installed-detector tests
  deselected, 47.29 seconds. Controlled interpretations and detector doubles;
  this includes all nine scenario-controller routes and Streamlit journeys.
- Installed detector broad run: **17 passed, two failed**. The failures exposed
  an instruction-word false positive and random UUID audit recognition. After
  fixing these and the new scoring-reference false positive, the final affected
  set passed **3/3**, including positive-anchor and abstention envelopes/exports.
  All 19 distinct installed-detector tests have passed across the broad and
  focused runs; the final focused run took 40.76 seconds. Model replies are
  controlled, not live Qwen outputs.
- Private source builder: **65 questions, nine scenarios, 18 passages** passed
  the installed detector. Eight workbook comparison rows and J2/J8 feedback are
  retained privately. Source documents were not modified.
- Real-detector fixture runner: **3/3 completed**, all recorded invariants true,
  final screened exports available. The selected examples were the FN corridor,
  first Milan GA route and first Madrid GA route. Report:
  `.runtime/conversation-v11-final-fixtures.json` and its three case exports.
- Actual pinned local tokenizer, controlled complete journeys and draft scoring:
  **128 requests**, all within 4096 tokens including reserved output. Maximum
  **3652/4096**; anchor assessment maximum **3248/4096**. This checks request sizes,
  not generation accuracy or every possible long answer. Report:
  `.runtime/conversation-v11-context.json`.
- Live model preflight: **blocked_model_endpoint_unreachable**, semantic status
  **not_run**, zero live cases. Report: `.runtime/conversation-v11-live.json`.
  This environment cannot verify the running host or model quality.
- Compile checks and `git diff --check` passed. Source-derived corpus and private
  runtime artifacts remain Git-ignored. Existing baseline benchmark banks and
  the original conversational bank remain intact.

The initial aggregate fixture report was blocked by a false positive on the new
benchmark filename; its successful case exports were preserved. A separate final
run completed and saved the full report. Other demonstrated false positives were
fixed route labels/identifiers, approximate-distance notation, prompt imperative
words, scoring claim identifiers and generated request UUIDs. Text was rephrased
where possible; metadata exceptions are restricted to exact controlled labels or
validated identifier syntax in reference fields. Positive name/credential controls
still block processing. No arbitrary respondent/model prose is exempted.

Live question relevance, omissions, wording neutrality, scoring consistency and
latency remain unverified. Separate model review is not independent verification;
human semantic review of real outputs remains necessary. Desktop/mobile browser
rendering was not inspected. No claim of scientific validation or FN approval is
made.

## Publication candidate check

The selected source-only snapshot was tested in a fresh temporary checkout with
no private documents or generated corpus. It passed the repository's CI commands:
**445 passed, 19 skipped** for the complete suite (installed detector unavailable
in that environment), and **69 passed, one skipped** for `eval/run.py --mock
--repeats 1`. The earlier 464-test local result also includes separate backend
diagnostic tests which are intentionally not part of this publication.

Private sources, runtime data, model weights and environments are excluded. The
separate Colab notebook, its guide and model-service diagnostic/recovery changes
remain local. The published conversational guide uses the existing backend setup
and documents the current port-18000 launch without requiring those local changes.
