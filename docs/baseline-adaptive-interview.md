# Role-aware general interview — proposed baseline 2.1.0

Implemented from clean checkout `820feaa57eaa5aab12020111efdc1204d3abe48f`.
No AGENTS.md was found in the workspace. An edit to the existing benchmark guide
appeared during the work; its changes are preserved. This is an evidence interview,
not a calibrated adaptive CRL test, organisational audit or city SRL assessment.

## Sources, directions and choices

The original GA, workbook and FN concept are available in ignored
`references/private/` and were read directly (PDF text and workbook XML, including
comments). No source content is invented or labelled approved questionnaire text.

| Source | Implication | Proposed implementation, not source-prescribed policy |
|---|---|---|
| GA Part B p.16 / PDF p.53, IAM-SRA2 | Individual, organisational and societal reporting have different scopes. | Separate answering perspective, claim subject and role-specific wording; no organisational/city score. |
| GA Part B §2.2.1 p.30 / PDF p.67 | Eight canonical stakeholder groups. | Explicit role mappings; Other/withheld stay interface responses. Profession alone changes no evidence requirement. |
| Workbook Read me, CRL/ORL/TRL and CRL descriptions | Knowledge, participation and influence are distinguishable; technical/organisational capability is separate. | Shared descriptive evidence objectives, actual/intention/domain/subject provenance, all numerical baseline fields null. |
| SRA IAM indicators D8/H8/I8 and comments | Draft acceptance/noise-confidence questions are criticised as CRL evidence. Factors influencing impacts should be independently expressed. | Neutral effects item and a bounded reasoning clarification; no supplied noise/privacy answer or stance routing. |
| D15/H15/I15 | Awareness, trust, information access and influence are different; leading deficit/trust assumptions criticised. | Information needs and participation access remain separate; unknown opportunity is not inability. |
| D16/H16/I16 | Learning needs, existing capabilities and applied participation differ; willingness/training attendance are not maturity. | Attendance is exposure; actual contribution is separate; outcome needs an explicitly reported link. |
| FN concept PDF pp.1–9 | Historical scenario-oriented acceptance example and proposed gates, not an approved baseline branch algorithm. | Retain the separate reference/scenario mode; no source scores, diagnoses, scenario facts or psychological labels enter this interview. |

The latest user meeting direction sets the role-awareness and eight-question/two-probe
scope. Registry wording, sufficiency rules, interleaving, slot reservation and stop
rules are authored prototype choices: `draft_pending_FN`, `approved_by=null`.
The complete FN v4 draft indicator-specific anchor bank is now available as
[private reference data](readiness-scale-reference-bank.md). Approval of a
questionnaire and operational evidence-to-level/verification rules remains
separate. The current interview and optional estimate still use their existing
configuration. No private original or generated source text is added to Git.

## Registry and role wording

`configs/baseline.json` remains the single question bank. Items include a stable ID,
target requirement, applicability, prerequisites, variants, response format,
completion/probe rule, priority, source, review status, version and locale.
`baseline_routing.py` validates a restricted rule vocabulary; there is no eval,
model-generated question, executable configuration or selection model call.

All personal/withheld respondents retain personal wording, including academics,
operators and public officials. Professional actions voluntarily described are
retained with their actual subject. For an organisational perspective the experience
item is replaced, not extended, using these mapped branches:

| Category | Experience variant |
|---|---|
| Citizen/community | Community discussion/contribution |
| Authority | Planning consideration/actions |
| Planning | Planning/design work |
| Research | Research/evaluation |
| Logistics, aviation, technology | Trials, operation, development/evaluation |
| Regulator | Regulatory review/consultation |
| Other, withheld | Neutral own/organisation activity question |

Each asks whether an activity happened and what the person did; none assumes
experience or establishes ORL/TRL. Role and city remain structured, privacy-screened
context. Function/other-place strings retain mandatory free-text screening.

## Exact selection and stopping policy

1. Use confirmed active records and the frozen instrument only. Unconfirmed model
   interpretations cannot select the next question.
2. Exclude answered items, inapplicable items, sufficiently covered requirements
   and objectives already addressed by explicit absence/unknown. Unknown/absence
   complete an interview objective without satisfying its positive evidence anchor.
3. Respect skip/decline/unsure and related clarification controls. Do not reopen
   that topic automatically. Editing is an explicit reopening.
4. Consider material subject/activity/time/meaning ambiguity first. Mere missing
   dates are not automatically ambiguous. Opposite statements with different
   subjects, stated activities, periods or IAM/other domains are not presumed to
   contradict one another. Preserve unresolved accounts and their source IDs.
5. Otherwise permit one immediately relevant eligible clarification from the
   previous answer. Priority/tie-breaking: scope, reasoning, contribution, domain,
   outcome; ties use stable question IDs.
6. Otherwise choose the highest-priority missing core objective (stable ID tie).
   Possible cores: familiarity → concept → delivery uses → effects → experience →
   information needs → participation opportunities. Earlier answers can cover
   later items only against their specific requirement and relevant subject scope.
7. Defaults: eight confirmed active substantive items, two probes. Before selecting
   a probe, reserve one slot for each remaining core objective. Between probes,
   ask a remaining core. With no cores remaining after a probe, stop rather than
   start another clarification loop. Role wording replaces an item and adds no burden.
8. Influence requires actual contribution, no participation-absence report and no
   already supplied outcome/unknown outcome. Attendance, plans or willingness
   never qualify. Mere later change has `sequence_only`; an explicitly linked
   outcome is still self-reported and not causal verification.
9. Stop on user finish, total budget, or no useful eligible item within probe policy.
   `stop_reason` preserves compatibility (`user_finish`, `question_budget`,
   `completed`); `routing_stop_reason` additionally distinguishes objectives
   addressed/no eligible useful item. Completion is not evidence sufficiency.

The controller records exact wording, variant, requirement, rule, triggering
confirmed evidence IDs, routing version, omissions and stop reason. It does not
claim statistical information gain or directly comparable totals across branches.

## Evidence versus interview disposition

Claim kinds remain the evidence vocabulary: conceptual/use explanation, recognition,
undetailed assertion, explained impact, actual exposure/contribution, intention,
linked/unlinked reported outcome, need, opportunity/barrier, absence and unknown.
Additional typed ambiguity/outcome-relationship fields distinguish unresolved
meaning from unsupported causation. Supported means grounded in the answer,
not independently true. First-party, organisation and third-party reports are retained
separately; organisation/third-party accounts cannot satisfy personal objectives.

Exports add requirement status and per-core disposition: answered, already covered,
skipped, declined, unknown, not applicable, not asked or budget limited. Evidence
status is separate. For example, an answered effects item may still lack a reasoned
explanation. Coverage and varying interview lengths are not readiness totals.

## History and optional information

New sessions freeze `baseline-2.1.0`, `baseline-routing-1.0.0` and both prompt texts.
1.x and 2.0 frozen instruments continue through their old selectors and schemas.
Existing schema-1.0/2.0 fixtures remain unchanged. New exports are additive/versioned
`iam-baseline-2.1.0`; scoring/scenario inputs are unchanged.

Edits reuse the exact earlier wording, invalidate dependent active records/final
profiles/handoff and archive superseded pending interpretations. Original confirmed
snapshots and history remain. Perspective changes deactivate rather than relabel
personal claims. Retries/corrections do not add active substantive question items.
Privacy previews remain bound to action/state/question/version and expire on changes.

Definition display is an explicit action, not a question. Existing exact exposure
logging and pre-information snapshots are preserved. Editing cannot undo exposure;
later answers stay after_information, including a restarted context within the same
session. Definition repetition does not establish independent prior knowledge or a
learning/readiness gain. No baseline FAQ/RAG or scenario facts are introduced.

## Three short journeys

The versioned successor `eval/benchmarks/baseline_adaptive_v2.json` is keyed to actual
question IDs and contains optional-probe answers. These expectations are not model
outputs. Keep the original seed bank as a versioned comparison.

- **Novice citizen:** personal/citizen/withheld city; heard the term; cannot define
  a drone or explain deliveries/effects; no experience; wants information; interested
  but never invited. Expect unknown/absence, information needs and access barrier,
  no invented contribution or score. Uncertainty is not repeatedly probed. Optionally
  run a separate definition-exposure variant.
- **Informed sceptical academic, personal:** personal/research/Coimbra; defines
  drones and delivery uses; explains rest disruption with conditional reasoning;
  reports a bus consultation contribution; drone consultation absent; outcome
  unknown; caring/access barriers. Expect personal wording, transferable activity,
  no drone attendance or verified influence. If outcome is omitted, ask it after
  the contribution if budget permits. Opposition and academic title add no points.
- **Authority with actual experience:** organisation/authority/Milan; explains
  conditional road-trip substitution; team reviewed delivery options and submitted
  comments, respondent drafted them; outcome unknown; organisational needs/access.
  Expect authority experience wording and distinct team/person subjects; no ORL,
  operational trial or influence inferred. Unknown outcome already supplied means
  no repeated influence question.

## Reproduce

```bash
cd ~/iam-sra-demo
scripts/start-ui.sh
# Open localhost:8501. Use a NEW session for 2.1; old sessions remain frozen.
.venv/bin/python -m pytest -q
.venv-privacy/bin/python -m pytest tests/test_baseline.py tests/test_baseline_v2.py tests/test_baseline_privacy_v2.py -m presidio_live -q
.venv-privacy/bin/python scripts/smoke-baseline.py --mock --benchmark eval/benchmarks/baseline_adaptive_v2.json --output .runtime/adaptive-mock-smoke.json
.venv-privacy/bin/python scripts/smoke-baseline.py --benchmark eval/benchmarks/baseline_adaptive_v2.json --output .runtime/adaptive-live-smoke.json
.venv-privacy/bin/python scripts/smoke-baseline.py --mock --benchmark eval/benchmarks/baseline_adaptive_v2.json --case novice_definition_exposure --output .runtime/adaptive-definition-smoke.json
```

`--mock` checks state/confirmation/correction/export with an explicitly empty
extractor, not semantics. Real detector checks and mock extraction are distinct.
Scripted confirmations remain labelled automation. Actual exports/traces belong
in ignored `.runtime/`; no real participant data is a committed fixture.

## FN decisions

Approve role-specific evidence requirements and question wording; agree positive
sufficiency versus merely addressed/unknown; decide verification and organisational
claim scope; agree information exposure and chatbot-participation interpretation;
determine any numerical anchors/synthesis separately; define comparable descriptive
reporting across branches. No numerical rule is proposed here.

## Verification

Actual final results are recorded below after execution. Browser screenshots,
mobile layout, keyboard focus and live extraction are not established by AppTest.

A confirmed scope clarification can link a newer grounded statement to an earlier
ambiguous account. The final profile records `scope_clarifications` and the original
passage's `clarified_by_evidence_ids`; original event claims are unchanged. The
citizen summary uses the clarified account. Mere confirmation, an unrelated answer
or an unsure response cannot resolve a contradiction. Reports still lacking a clear
relationship remain unresolved and never incur a readiness penalty.

### Changes by file

- `configs/baseline.json`: version 2.1 registry, role variants and restricted policy.
- `baseline_routing.py` (new): pure sufficiency, context matching, dispositions,
  ambiguity handling, deterministic interleaving and budgets.
- `baseline.py`: typed ambiguity/outcome relation, model-review support and
  version-aware profile/selector dispatch.
- `baseline_session.py`: frozen routing provenance, exact-question edits,
  superseded pending/event history and versioned additive export.
- `baseline_client.py`, both prompts: scope-aware grounded extraction/review,
  including candidate context and no timing-as-causation inference; old schemas
  omit new optional fields.
- `baseline_ui.py`: truthful “Question N · up to 8”; clarified summary account.
  Existing styling, controls, privacy boxes and optional definition are retained.
- `privacy.py`, source register: exact new schema ID and reviewed citation metadata
  avoid demonstrated Presidio false positives without bypassing citizen screening.
- `scripts/smoke-baseline.py`, `eval/benchmarks/baseline_adaptive_v1.json`: reuse the
  normal session path with question-keyed synthetic role cases and an optional
  definition path. Old seed fixtures are retained, not silently upgraded.
- Adaptive/UI tests plus frozen-2.0 regressions; README and current/previous interview
  documentation point to the right policy. The separately edited existing benchmark
  guide was preserved rather than rewritten.

### Earlier instrument checks and limitations (before benchmark runner 2.0)

- Final full repository regression suite: **298 passed, 10 skipped** (13.01 s).
- Installed pinned Presidio/spaCy suite: **5 passed, 120 deselected** (19.85 s), with mocked model transport
  explicitly distinguished from actual NLP screening.
- Real screening plus empty mock extraction: all three role-bank sessions completed,
  including correction/export/handoff; optional definition case also completed.
  These are structural smoke passes, **not semantic extraction passes**.
- Live attempts: all three failed with `transport` (1.579/0.466/0.447 seconds).
  `127.0.0.1:8000/v1/models` is unreachable. No live semantic outputs are claimed;
  rerun the commands above on the model host.
- Streamlit AppTest checks normal and organisational journeys, interleaved outcome,
  confirmation, navigation, correction, privacy and downloads. No browser/Playwright
  is installed: actual mobile/desktop pixels, keyboard/focus and screenshots remain
  unverified. Existing UI-guide limitations and missing approved assets persist.
- Detector checks exposed false PERSON matches on workbook cell IDs, the new schema
  ID and one prompt word. Exact metadata registration and neutral prompt rephrasing
  address those controlled cases. A synthetic “van trips” sentence was paraphrased
  to “road vehicle journeys” after a false PERSON match; no general word or case
  bypass was introduced. Arbitrary-text false positives and misses remain possible.
- Compilation, whitespace, original-source hashes and bank IDs/config hash checked.
  Originals and runtime outputs remain ignored; no dependency, service, deployment,
  numerical method or legacy-branch change was made.
- Existing CI evaluation entry point (`eval/run.py --mock --repeats 1`): **70 passed**
  (12.37 s). It is offline flow verification, not live model accuracy.

### Versioned benchmark successor

The executable successor and manual protocol are in
[adaptive benchmark](baseline-adaptive-benchmark.md). Use
`baseline_adaptive_v2.json` with the existing `scripts/smoke-baseline.py`; the earlier
v1 bank and historical seed are retained read-only. The successor replaces the
older smoke commands above; definition/correction are explicit named case journeys.
