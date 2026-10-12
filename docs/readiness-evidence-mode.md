# Draft citizen evidence mode, instrument 1.0.0

The local baseline was clean `7080248`. Work is on `feat/readiness-evidence-demo`. No deployment, publication, push or methodological approval is implied.

## Method and sources

The draft workbook's “Read me” J1/L5:L13 distinguishes citizen empowerment and agency from TRL/ORL and ecosystem SRL. “SRA IAM indicators” C/D defines thematic areas and readiness perspectives. H contains original candidates; I repeatedly identifies problems with support, comfort, trust and willingness being mistaken for readiness. The application's questions are revisions checked against those comments, **draft_pending_FN**, with **approved_by=null**. Neither the worksheet labels nor this implementation constitute an approved level-assignment rule. It assigns no highest level and assumes no cumulative prerequisites.

The 8 October minutes request review/agreement on C/D by 14 October, and concrete LL use cases by 12 November. The 10 September presentation distinguishes acceptance from societal readiness. GA T3.2–T3.4 requires partner/LL validation before operationalisation; Part B p.16 describes the broader individual/organisation/citizen/city tool. That future scope does not justify synthesising city SRL here. `references/source-register.json` records exact local document hashes and reviewed sections. The source files were found in `/home/evouvali`, copied to ignored `references/private/`; none was missing. The LL sheet contains a template, not completed Madrid/Milan/Coimbra scenarios.

The fixed medical corridor remains illustrative. City, named endpoints, sites, precise hours and existing logistics are unknown. Camera shielding, higher altitude and below-ambient sound are hypothetical mitigations, not established engineering guarantees.

## Modes and executable isolation

`Session()` creates `acceptance_and_readiness_evidence`; `Session(assessment_mode="legacy_fn_acceptance_demo")` creates the historical class. A session cannot change its mode. Old sessions without mode metadata follow the historical UI, never the readiness path. Historical schema 5.4.0 remains with additive mode/method labels; default schema 6.2.0 is separate. No migration of historical scores to CRL is provided.

The default UI calls `ReadinessClient.extract_readiness`, using the existing Qwen3-8B/vLLM transport, 4096-token preflight, structured JSON, thinking disabled, stage deadline and bounded retry. It never invokes acceptance scoring, direct-9, arithmetic, bottlenecks, phase means or progression increments. An extraction failure retains the draft; it never falls back to historical arithmetic. Empty input is retryable; unsure, skip and finish remain available during the interview. Existing numerical evaluators explicitly use `LegacySession`.

`assessment_modes.json` supplies mode labels and the exact numerical unavailability reason. Both numerical fields remain null. Readiness records carry criterion, explicitly evidenced topics, stable passage IDs, neutral interpretation, evidence kind/status, temporal/domain/proposal/elicitation context, evidence basis, confirmation and version. Citizen claims of externally verified events remain self-report. The citizen extraction endpoint rejects the external-verification basis. The typed model reserves that basis for a separately reviewed external-evidence workflow; this change implements no such workflow.

Source-grounded interpretation is a model task: Pydantic checks references and structural distinctions, not the truth of statements or the semantic accuracy of the model. There is no keyword scoring, fixture lookup, learned calibration, RAG or invented topic-by-level rubric.

## Interview and updates

The deterministic registry has five cross-cutting criteria: impacts, information, actual participation/contribution, influence, and opportunities/barriers. Only missing, ambiguous or conflicting evidence is queried. Explicit absence of prior experience is evidence of absence, not incapability. Hypothetical willingness leaves actual participation unresolved. Reported participation in another domain remains transferable experience. Influence is queried only after a supported past/current contribution. Unknown influence remains unknown.

The default total budget is five readiness questions including clarifications; a criterion can get at most one follow-up clarification. Unsure or skip stops that question's loop. Finishing records a stop reason and retains gaps. Question count is distinct from readiness. The current chat is recorded only as assessment participation; it awards no engagement/co-design/influence or level.

Each interpretation is confirmed before entering the profile. Initial confirmed evidence is stored as an immutable copy. Follow-ups build the final profile from applicable active confirmed records. Edits preserve original snapshots and superseded passages, deactivate affected confirmations and dependent answers, invalidate the final profile, and require new confirmation. Corrected-first-answer snapshots are retained alongside the first snapshot. No personal improvement is inferred merely because an interview collected more evidence.

Reported availability and a practical access barrier may coexist. A bus-consultation experience does not contradict lack of IAM experience. Direct conflicting claims within the same domain/context remain flagged; neither the more positive record nor a later unsupported claim wins automatically.

Optional mitigation exploration is separate, limited to two user-selected aspects from explicitly named proposal topics. Existing mitigation texts are reused with an unverified-feasibility note. Choices record descriptive conditional acceptance only. Optional explanation can add confirmed readiness evidence in the hypothetical context; accepting a mitigation is never itself a readiness record. No combined-proposal acceptance is inferred.

## Representative before/after behaviour

| Response | Historical mechanism | Default evidence mode |
|---|---|---|
| “Yes, I accept everything”, with no explanation | Could produce a direct 9 after confirmation | Descriptive support; no understanding/participation inferred; missing-evidence interview available; numerical CRL/SRL null |
| Opposes noise and private viewing, explains impacts, requests evidence | Concern scores, assessed mean and minimum-plus-two cap | Opposition and conditions recorded independently; explained impacts and evidence needs can be recorded; participation/opportunity gaps remain |
| “I cannot decide” or refusal without a reason | No assessed concern or score clarification | Uncertainty/refusal retained; stance does not block the same short readiness interview |
| “I would attend a workshop” | Could be confused with support or competence | Hypothetical intention; not an actual contribution or demonstrated influence |
| “I attended a bus consultation, proposed a clinic stop; outcome unknown” | Acceptance-oriented facets insufficient to describe agency | Actual transferable self-reported contribution; influence explicitly unknown; not IAM experience or external verification |

Illustrative trace (a controlled test, **not a live model output**): an initial opposing answer supplies no participation evidence. Its confirmed snapshot records participation as not asked. A follow-up says “I spoke at a local drone consultation and proposed a quieter schedule.” Stable follow-up passage IDs anchor a confirmed self-reported action record. The initial snapshot remains unchanged; the final profile records that contribution. Influence remains unknown and is eligible for a conditional question. The change explanation is: “The follow-up added a reported consultation experience. Whether that contribution influenced a decision remains unknown.” It is assessment refinement, not demonstrated personal improvement.

## Validation and limitations

New tests cover supportive/opposing/uncertain/no-concern answers; actual versus intended participation; transferable experience; unknown influence; barriers versus interest; self-report versus external verification; conflicting records; corrections, skips and emptiness; immutable snapshots and invalidation; stance/policy invariance; optional hypothetical contexts; default nulls and legacy isolation; UI/export agreement; bounded transport/retry/context failures. Existing historical arithmetic assertions are retained; their session imports are explicitly historical. UI label assertions reflect the new historical label.

Run:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke-readiness-evidence.py --output .runtime/readiness-live-smoke.json
```

The live smoke attempt in this environment was blocked at `/v1/models` with `[Errno 1] Operation not permitted`; no model output was received. `.runtime/readiness-live-smoke.json` records `live_model_used=false`. Mock/structural tests do not establish live semantic accuracy. The smoke script preserves actual outputs when run on a host with endpoint access and does not mark them scientifically validated.

## Decisions still required from FN and partners

- Approved numerical CRL criteria and any operational level-assignment rubric.
- Whether, and which, level prerequisites are cumulative.
- Aggregation and any justified weighting, including how CRL relates to ecosystem SRL.
- Verification requirements for reported participation, influence and agency.
- Whether this interview counts as engagement or co-design, and under what conditions.
- Approval/localisation of questions, definitions and concrete LL scenarios.

## Run modes

```bash
# Default; existing Qwen/vLLM runtime, no numerical citizen score:
scripts/start-ui.sh

# To change the UI process mode, stop the project UI first:
scripts/stop-ui.sh
IAM_ASSESSMENT_MODE=legacy_fn_acceptance_demo scripts/start-ui.sh

# Optional developer mode selector, before creating a session:
IAM_DEVELOPER=1 scripts/start-ui.sh
```

Open http://localhost:8501. The scripts do not source `.env` automatically. Start over after selecting a different mode; existing sessions keep their instrument. Changing an environment variable does not alter an existing session.

## Executed checks

- Final full suite: **1,074 passed in 50.43 seconds**, including 48 new evidence-mode tests. Existing historical arithmetic tests still pass.
- `git diff --check`: passed.
- `python -m compileall -q src app.py scripts eval`: passed.
- 64 local pinned-tokenizer context checks (32 existing inputs, initial and follow-up request shapes): all fit. Largest request used 1,616 prompt tokens + 1,200 reserved output tokens = 2,816, below 4,096. This is a context check, not semantic validation.
- Live smoke preflight: blocked with `Operation not permitted`, no generated outputs. A future successful endpoint check still requires reviewing the actual extracted meanings.
- All five documents under `references/private/` verified ignored by Git. No source documents are staged or committed.

In the controlled initial-to-final trace, `R1_1.p001` identifies the original passage; `R2_2.p001` identifies the later consultation report. The initial profile has no participation record. The final profile adds `criterion_id=participation`, `kind=action`, `temporality=past_current`, `experience_domain=IAM_specific`, `evidence_basis=self_report`, `confirmation_status=confirmed`, with `R2_2.p001` as its source. Influence remains not established. Numerical CRL and SRL remain null in both snapshots. These are traceable workflow-test results, not live Qwen outputs.

## Changed-file inventory

| Files | Purpose |
|---|---|
| `app.py` | Default evidence UI dispatch; fixed-at-creation developer selector; visible historical label. |
| `configs/assessment_modes.json` | Versioned modes, shared labels and numerical-unavailability policy. |
| `configs/readiness.json` | Five controlled draft criteria/questions, candidates/revisions, source cells, review status and budget. |
| `configs/concerns.json` | Marks phases as historical metadata only; existing facet definitions and scores unchanged. |
| `configs/scenario.json` | Structured illustrative corridor facts, unknowns and feasibility limitations. |
| `src/iam_sra/session.py` | Default-mode factory and explicit historical class; additive historical export identity. |
| `src/iam_sra/readiness.py` | Typed records, citation/basis checks, descriptive coverage, deterministic question selection and profile differences. |
| `src/iam_sra/readiness_session.py` | Confirmation hashes, immutable initial snapshots, active-evidence ledger, revisions, optional exploration and schema-6 export. |
| `src/iam_sra/readiness_client.py` | Source-first Qwen extraction plus bounded blind classification batches; application-owned provenance. |
| `src/iam_sra/readiness_ui.py` | Plain-language review, adaptive questions, corrections, final findings and downloads. |
| `src/iam_sra/readiness_mock.py` | Explicit empty fixture for UI plumbing; no semantic evaluation claim. |
| `prompts/readiness-evidence.txt` | Stance-independent extraction instructions and safeguards against invented experience/verification. |
| `src/iam_sra/llm_client.py` | Adds a bounded output allowance for the new extraction stage. |
| `src/iam_sra/reporting.py` | Mode-aware reporting and explicit historical export identity. |
| `src/iam_sra/assessment_review.py` | Prevents historical progression calculations for evidence sessions. |
| `scripts/smoke-readiness-evidence.py` | Five-case live smoke report with actual outputs, failures and provenance. |
| `references/source-register.json` | Curated source locations, hashes, reviewed sections and unapproved status. |
| `.gitignore` | Excludes all private partner source documents. |
| `.env.example` | Documents explicit assessment-mode selection. |
| `README.md`, `docs/readiness-evidence-mode.md` | Default flow, limitations, commands, source interpretation and deliverable details. |
| `docs/methodology.md`, `docs/implementation-contract.md`, `docs/fn-followup-update-policy.md` | Label earlier documentation historical and direct readers to the current instrument. |
| `eval/run.py`, `scripts/run-initial-manual-tests.py`, `scripts/smoke-discovery.py` | Explicit historical sessions for existing numerical evaluation scripts. |
| `scripts/replay-fn-evidence.py` | Explicit historical session and local package-path setup for standalone execution. |
| `manual-tests/initial-assessment-manual-tests.md` | Labels existing expected numerical fixtures historical rather than CRL criteria. |
| `tests/test_readiness_evidence_mode.py` | Evidence, independence, coverage, corrections, confirmation, uncertainty and historical-isolation regressions. |
| `tests/test_readiness_evidence_client.py` | Transport, structured output, citation retry, provenance and context-limit regressions. |
| `tests/test_readiness_evidence_ui.py` | Default end-to-end UI, retained drafts, mode selection and UI/export agreement. |
| `tests/test_attribution_confirmation.py`, `tests/test_confirmation.py`, `tests/test_direct_interpretation.py`, `tests/test_discovery.py`, `tests/test_evidence_repair.py`, `tests/test_followup_manual_pack.py`, `tests/test_passage_mapping.py`, `tests/test_single_followup_flow.py`, `tests/test_updates.py` | Existing historical tests now explicitly import the historical session; arithmetic expectations unchanged. |
| `tests/test_ui.py` | Existing historical UI helper explicitly selects historical mode. |
| `tests/test_final_assessment_review.py`, `tests/test_live_ui_flow.py` | Historical headline-label assertions updated; numerical assertions unchanged. |

### Provisional workbook score screen

After finishing the interview, choose **View readiness score**, then **Calculate
readiness score**. The local model assigns a provisional CRL (1–9 or insufficient
evidence), with a short explanation and supporting answer IDs. The rubric in
`configs/readiness_levels.json` transcribes `IAM-CC_Topic_experts.xlsx`, Read me
K5:L13 and B5:C13, and records the workbook hash. SRL remains unassessed because
the workbook requires synthesis of TRL, ORL and CRL; a citizen interview cannot
supply this broader evidence. The provisional judgement is separate from approved
numerical fields, included as `provisional_workbook_score` in session exports,
and invalidated by changed answers/profile/rubric. Failed requests allow retry
without changing answers. Existing privacy gates apply when enabled.

This screen is a local change, not a GitHub publication. Live model judgement
requires host verification; automated tests check boundaries, not scoring accuracy.
