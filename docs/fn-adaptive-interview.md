# FN-guided adaptive IAM-SRA2 interview

Prototype `fn-adaptive-interview-1.0.0`, chat/export contract `iam-sra-chat-2.0.0`.
Base: `cb892a8954e45b93746adce44c8403e2643f065a`; implementation branch:
`feat/fn-adaptive-interview`. No automated scoring policy is represented as FN-approved.

## Sources and progression

All pages of the four PDFs, including interviewer guidance, alternative branches,
scales and disagreement sections, were read. Their SHA-256 identities and the
extracted scales match `references/chat-source-register.json`. The PDFs,
register, exact scales, v4 workbook/bank and private questionnaire are unchanged.
Canonical question sentences were checked against the actual PDF text. The
specification records page locators; generic prompts such as “Why?” retain the
locator of their particular stage. Privacy introduction, unknown-topic probes,
configuration clarification and unsupported-contact notice are transparent
adaptations. Profile-option separators use dashes to avoid a demonstrated
Presidio PERSON false positive across consecutive lettered options; literal
`A. Citizen`, `B. Organisation or institution`, and `C. Technology expert or
researcher` remain valid inputs.

| Flow / source under `references/private/` | Source-to-stage mapping | Important branches |
| --- | --- | --- |
| Citizen short — `SRAA Citizen interview example 20min.pdf` | §§1–4: chosen perspective, city, recognition/prior awareness. §§5–7: open discussion, suggestions, priorities and understanding. §§8–12: engagement, co-design, evaluation, influence and accountability. Separate opinion, full scale, result and validation; interviewer guidance closes the document. | Recognition yes → own description/known uses; no/unknown → permission to explain. Prior healthcare awareness yes → what was heard. Reported local activity → basis, without verification. Demonstration/participation yes → actual experience; no → hypothetical evaluation/capability. Sustained involvement is a selective boundary probe. |
| Citizen extended — `SRAA Citizen interview example 35min.pdf` | Recognition → awareness → understanding → critical engagement → co-design → informed evaluation → influence → empowerment → sustained involvement; separate opinion and result review. The source places previous participation before co-design. | Adds other known uses, contextual noise, fairness trade-offs, meaningful involvement, selective unfamiliar-airflow explanation with consent, formal channels, monitoring and changed conditions. Selected noise/fairness and relevant spontaneously raised topics activate appropriate examples; it does not traverse every societal topic. No previous participation skips questions presupposing a consultation and permits the source's hypothetical influence probe. |
| Organisation — `SRAA Organisation interview example.pdf` | §§1–5: unit, actual remit and prior familiarity/local knowledge. §§6–8: relevance, open requirements/priorities and assessment. §§9–14: planning → preparation → validation → integration → operational readiness → sustained institutionalisation. Then ORL scale/result/review. | Qualified planning/preparation/testing answers retain their limits. No testing skips questions presupposing pilot lessons. Pilot permission is not routine preparedness. Explicit outside-remit clarification ends a partial, unscored record. Sustained monitoring/adaptation is selectively probed; intended processes are not established capability. |
| Technology — `SRAA Technology interview example.pdf` | §§1–5: organisation type, technical role, specific object, expertise limits and local context. §§6–8: principles/concept → experimental proof → controlled validation. §9: open technical issues and priorities. §§10–14: representative validation → integrated demonstration → actual operational prototype → qualification → proven operational use. Then TRL scale/result/review. | Representative, integrated and operational environments remain distinct. Explicitly no experiments permits the source's low-boundary focus rather than presupposing later tests; this is routing, not a score/prerequisite formula. The aircraft-specific noise example requires an aircraft scope. Operational safety probes require an actual operational-prototype claim. Routine use is a selective boundary probe, not inferred from a successful flight. |

D3.1 §10.5 distinguishes the three response capacities and the fifteen
indicator-specific dimensions. Its city aggregation proposals are not implemented
here. The unchanged v4 bank and questionnaire v0.2 remain the distinct reference
and existing per-indicator workflow. FN's nine-level example scales govern this
conversation's profile judgment. There is no individual/city SRL or indicator average.

## Controller and model

`configs/fn_interview.json` is the single declarative source of stages, canonical
questions, conditions, evidence goals, optional guidance and review wording.
`fn_interview.py` holds compact coverage, branch facts, gaps and next-action state;
it is composed into the existing `ChatSession`, not a second interview engine.
The existing Flask actions/jobs, Vue composable, Qwen/vLLM transport and privacy
boundaries remain in use. No orchestration dependency or additional per-turn
model is introduced.

For a substantive answer, the same Qwen response supplies a proposed action and
semantic interpretation. Every coverage annotation must name an allowed goal,
an available original evidence ID and an exact quote. Python authorizes scope,
branching, priority selection and advancement. Clear literal choices, broad city,
consent and separate opinion administration do not require model interpretation.
Nonliteral/qualified answers use Qwen. A profession alone never selects a profile.

Qwen can clarify an unresolved goal or propose a relevant neutral follow-up.
Python allows one recovery/follow-up per unresolved question before explicitly
retaining a gap and moving on. At most two model-nominated optional boundary
probes supplement the applicable progression. Canonical branches retain FN
wording; emerging topics can be explored through neutral adaptations. Coverage
means a question/evidence goal was explored, declined, inapplicable or left
uncertain; it is not verified competence or evidence sufficient for a level.
Exact-quote checks cannot independently validate semantic interpretation.

Topic history distinguishes spontaneous mentions, interviewer suggestions,
respondent-selected priorities and subsequent exploration. Mentions do not select
priorities; only an actual selection answer or an explicitly grounded earlier
choice may do so. Opinions are excluded from readiness evidence. Corrections
supersede original support and invalidate dependent coverage/results. Scope
annotations cannot silently change an already established object/unit/remit.

The model sees the current goal/purpose, scoped facts, selected priorities,
covered capabilities, gaps and bounded original question/answer exchanges.
Existing lexical RAG supplies bounded, source-checked context. Source information
and permissioned definitions are recorded separately from prior knowledge.
All original screened answers remain authoritative. The 4,096-token budget,
whole-current-answer handling and explicit navigation omissions remain enforced;
normal navigation has one lean retry if necessary.

There is no minimum/target answer count for methodological completion. Applicable
coverage plus acknowledged uncertainty authorizes the end. The existing call,
processing-time and configurable 96-answer limit are only operational safeguards.
Skip, pause/resume, correction, early stop and withdrawal remain available. An
early stop or exhausted/failed interpretation path is visibly partial.

## Judgment and validation

Normal progression ends with full relevant scale → provisional result → A–E
validation. Early termination offers the existing summary confirmation before a
partial result. Explicit early scale requests remain available and are recorded.
The Vue chat renders the scale/result at their chronological message positions.

The reused `chat_score.py` compares all nine exact profile anchors using every
active readiness answer, scope and information-exposure links. It requires exact
active quotations and a distinct relevant comparison anchor, or abstains. Long
complete evidence is never silently shortened to manufacture a score: character
and actual tokenizer limits can produce an honest abstention. Self-reported
claims are not externally verified. The unchanged internal indicator projection
is explicitly provisional and does not drive the interview or a fifteen-topic assessment.

A records explicit agreement. B (missing information), C (higher), D (lower) and
E (uncertain) invite the appropriate short explanation; profile-specific factual
clarifications follow where relevant. Additional evidence and preferred levels
remain separate from the initial model suggestion and its evidence revision.
There is no automatic reassessment. A correction to old supporting evidence
invalidates the current judgment while preserving its initial version. Abstention
allows uncertainty/comments and completion without any invented numeric result.

“Review pending” is a recorded disposition, not a staffed review service or a
promise of contact. Progress remains temporary/downloadable. The separate
approved contact form mentioned by FN is unavailable; no contact details are
requested in chat and no database/contact service was added.

## Reproduce verification

Use the existing environments, private sources and Node installation. The
`TLDEXTRACT_CACHE` setting below only relocates an email-detector dependency's
cache into a writable directory; privacy screening stays enabled.

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
TLDEXTRACT_CACHE=/tmp/iam-sra-fn-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_fn_interview.py

# Existing chat/API/privacy/QR regressions; real detector tests require resources.
TLDEXTRACT_CACHE=/tmp/iam-sra-fn-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q \
  tests/test_chat_conversation.py tests/test_chat_retrieval.py \
  tests/test_chat_qr.py tests/test_api_integration.py tests/test_privacy.py

# Full suite in an environment that permits local test sockets:
TLDEXTRACT_CACHE=/tmp/iam-sra-fn-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q

# Build with the declared Node 22.12+ within Node 22:
cd app
npm run build
```

`eval/fn_golden_paths.json` contains the actual FN-authored fictional respondent
answers and explicitly identified synthetic branch inputs where a source has an
implicit yes branch. Production code never imports these answers. Golden tests
check each applicable canonical question/order/branch against the independent
fixture and actual hashed PDF, then replay through both the session and owned
Flask API/jobs/JSON and JSONL downloads. The arbitrary score transport double is
not a semantic assessment or a target FN label; illustrative CRL 6/ORL 6/TRL 7
are never asserted as expected scores. All A–E outcomes are tested separately.

Run live rehearsals only against the existing verified model; this command uses
isolated in-process APIs and synthetic inputs, not a participant API:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-fn-tldextract PYTHONPATH=src \
  .venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --base-url http://127.0.0.1:18000 \
  --case all --output .runtime/fn-live-NEW-UNIQUE-RUN
```

The runner never starts/stops services and refuses to overwrite run directories.
It records completion, coverage/gaps, score/validation, generation calls, fallback
frequency, timings and failures. Passing deterministic doubles or local
tokenization does not establish live Qwen quality.

## Manual launch on separate review ports

Check ports 8016/5016 are free and verify the existing model first:

```bash
curl --fail http://127.0.0.1:18000/v1/models
```

Terminal 1, from the repository root:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 IAM_SRA_API_PORT=8016 \
IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5016,http://localhost:5016 \
bash scripts/start-api.sh
```

Terminal 2, using the current frontend build:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo/app
HOST=127.0.0.1 PORT=5016 IAM_SRA_API_TARGET=http://127.0.0.1:8016 \
../.venv-api/bin/python serve_app.py
```

Open `http://127.0.0.1:5016/tools/sra-assessment/app` or `/chat`. Short citizen mode
is the default; the conversation options or “extended conversation” selects the
longer mode. Choose A/B/C, give a broad city or skip it, and answer naturally.
Try an unfamiliar citizen, a draft organisational plan, or a laboratory component;
none should manufacture experience or an overall SRL. Try stopping, correcting,
A–E validation and both downloads. With abstention, use E/comments/no changes.
Existing QR/direct entry and owner/CSRF/version/job protections remain intact.
Remote browsers can forward port 5016 over SSH. No model launch or service
restart was performed by this implementation task.

## Verification record and FN decisions

See the results recorded below for this implementation; the older
`eva-live-verification.md` records historical behaviour and does not validate
this version.

FN review is still needed for operational semantic coverage/sufficiency criteria,
selection of optional probes/boundary clarifications, capability versus actual
influence without opportunities, automated evidence-to-anchor judgments and
human disagreement/reassessment procedures. The example PDFs are not an
approved scoring algorithm. Language heuristics, exact quotations and structured
decoding cannot prove factual correctness, neutrality or methodological validity.
All interface/time estimates and bounded recovery choices remain prototype
engineering decisions, not readiness thresholds.

### Observed verification, 23 November 2026

| Reference flow | Applicable canonical question/answer turns, excluding profile and review | Session replay / owned API / JSON+JSONL | Local scoring request, including 1,250-token output reserve |
| --- | ---: | --- | ---: |
| Citizen short | 35 | Passed | 3,180 / 4,096 |
| Citizen extended | 50 | Passed | 3,876 / 4,096 |
| Organisation | 40 | Passed | 3,389 / 4,096 |
| Technology | 41 | Passed | 3,295 / 4,096 |

- The full offline regression run passed **847 tests** (31 real-resource tests
  deselected; the three socket-dependent proxy tests excluded). After the final
  progression and provenance refinements, the focused chat/API/retrieval/QR run
  passed **230 tests**; the final FN-specific offline suite passed **68 tests**.
  These are separate, overlapping runs, not additive counts.
- Existing selected real privacy/API tests passed **12 tests**. The final FN
  real-detector opening/export checks for all four flows and interpretation
  metadata passed **5 tests**. One test overlaps those runs. Input, output and
  exports continue to use real Presidio/spaCy in those checks.
- Real screening exposed false positives in consecutive dotted profile options,
  a generated `canonical_FN` metadata value, compact page-locator formatting,
  and one slash-separated purpose description. They were corrected through
  equivalent formatting/plain metadata wording, preserving canonical question
  sentences, page coordinates and screening. No detector bypass was added.
- Lossless score-request packing preserves every original record and all nine
  exact anchor texts, verified by round-trip tests. It removes repeated JSON
  field names and repeated per-anchor provenance from model input; original
  provenance remains in the session/export and validation uses original records.
  The extended reference request originally required 4,488 tokens; it now fits
  at 3,876 without removing respondent evidence. Larger real records can still
  exceed the limit and abstain.
- Local tokenization used the pinned Qwen tokenizer, real source corpus and
  synthetic responses. Navigation requests, including the 1,100-token output
  reserve, peaked at **3,248 tokens** in the four replays. This is tokenizer
  verification, not a live generation test.
- Vue production build passed: **58 modules**. The available Node runtime was
  **24.22.1**; the declared Node 22 build environment was not separately tested.
  CPU/API tests used the existing Python 3.13 environment; inference environment,
  downloaded weights and dependency installations were left intact.
- The three production-proxy tests were attempted and blocked at socket creation
  by `PermissionError: [Errno 1] Operation not permitted`. No browser journey was
  executed in this socket-restricted sandbox. They need rerunning on the normal
  host; do not interpret their infrastructure errors as passing transport tests.
- Live runner: **unavailable, zero cases executed**. The existing model origin
  `http://127.0.0.1:18000` could not be reached from this environment. Live
  generation calls, fallback frequency, semantic quality and scored interview
  completion therefore remain unmeasured for this implementation. The runner
  command above is reproducible; no production service was restarted to obtain
  a result.
- Source identity checks, Python compilation and `git diff --check` passed.
  Original PDFs, extracted scales, source registers, v4 statements and model
  configuration were preserved. No service process was started/stopped or
  reconfigured, and nothing was pushed or deployed.
