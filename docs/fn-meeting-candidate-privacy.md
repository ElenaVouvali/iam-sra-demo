> Privacy screening is mandatory for every case, including demo fixtures. There is no runtime bypass. Missing local detector resources block processing. Run `scripts/setup-privacy.sh` and `.venv-privacy/bin/python scripts/check-privacy.py`. Screening can miss private information; use synthetic examples.

# FN meeting candidate — 12 October 2026

Instrument 1.4.0; privacy contract 1.0.0; readiness export 6.4.0. Local work builds on 525dc19 and preserves the existing header positioning and removal of the extra scenario caption. No push or service restart was performed.

## Scope and source basis

IAM-SRA2 is the overall tool. This demo implements the citizen component: separate proposal views and evidence relevant to CRL. SRL is a broader societal assessment informed by TRL, ORL and CRL; one person's interview is not a city SRL. GA Part B pp.5/16 and the topic-experts workbook Read me sheet support this distinction. Five interview dimensions offer partial coverage, not an operationalisation of nine CRL levels or all 15 thematic topics. Numerical CRL/SRL remain null. The historical FN concept illustration remains separate: mean 4.25 and example privacy cap 4, never inserted into current citizen results.

Originals inspected: GA.pdf, IAM-CC_Topic_experts.xlsx (Read me, indicators and review comments), SRA_LLM_FN_concept.pdf, WP3_IAM-CC_Minutes_20261008.docx, IAM-CC_WP3_2026.09.10.pptx and IAM-CC_UI_guidelines_for_tools-2.pdf. They remain private. The workbook and proposed questions remain drafts, not approved numerical criteria. Separate completed D1.2 DMP and WP13 D13.1 ethics material are unavailable. Approved logo/font assets, a responsible privacy contact/URL and hub-integration decisions remain unresolved. Existing guide-derived presentation is retained; full branding/accessibility compliance is not claimed.

## Changes and rationale

- `privacy.py`, `privacy_ui.py`, `requirements-privacy.txt`, `setup-privacy.sh`, `check-privacy.py`: central local Presidio screening, fail-closed resources, explicit cleaned-preview confirmation, contextual secret recognition, final export checks and real-detector preflight. See [privacy data flow and limitations](privacy.md).
- `assessment.py`, `conversation_client.py`, `llm_client.py`, `inference.py`: screen before tokenization/cache/inference and before outputs enter audit records; replace raw-output traces and unsafe transport details with structural metadata. Existing semantic/evidence/citation checks still apply.
- `readiness_session.py`, `session.py`, `reporting.py`, `readiness_report.py`, `readiness_retrieval.py`: guard direct controller paths, optional information, historical paths, corpus loading, imports and exports; preserve confirmed histories and refuse unsafe/older sessions rather than rewrite them.
- `app.py`, `readiness_ui.py`, `ui_presentation.py`, start/stop UI scripts: safe retry and resubmission, clear rejected widget references, synthetic-demo notice, download withholding, CPU privacy environment selection and concise CRL/SRL scope explanation. Existing UI styling and historical arithmetic are preserved.
- `readiness.py`, `configs/readiness.json`: where reported experience and explicit absence have unknown activity/time scope, preserve both passages and request neutral scope clarification within the existing budget. This is uncertainty, not a proven contradiction or readiness penalty. Known distinct periods/events and intention versus action remain separate.
- Replay/manual/smoke runners now screen their inputs and reports. The existing meeting runner supports `--baseline` for the no-information path. Regression fixtures are synthetic and isolated from prompts/corpus.

## Before → after

A secret could reach application drafts/tokenization or an old export; now screening blocks it before those paths, and no question is consumed. Maskable contact details require confirmation of the cleaned text. Output leaks and unsafe downloads are withheld. Missing detector resources block processing explicitly.

A report of participation and a report of no participation with unknown scopes could be treated as inconsistent without enough context. Both quotations now remain visible with a scope-clarification need; no personal deficit or falsehood is inferred.

Opposition, unconditional support and uncertainty retain their original meaning. Neither optional explanation display nor chat completion creates readiness gains. Exposure logs, corrections, historical comparisons and immutable initial snapshots remain intact.

## Meeting walkthrough

1. **FN response:** use the exact case in `eval/meeting_cases.json`. Explain noise/privacy views separately from understanding and information needs. Medical-purpose support is not equity knowledge; rerouting is not participation. Open the historical FN reference only in presenter controls.
2. **Enthusiastic support:** agreement without reasoning must not establish understanding, actual participation or influence. Answer only the actual selected question using the criterion-keyed variants.
3. **Reasoned opposition:** preserve reasoning and reported consultation contribution, while influence remains unknown unless the person reports an outcome. Scripted confirmations are automation, not citizen validation.
4. Repeat with optional sourced information/reflection. Show exact exposure provenance and explain that repetition alone does not demonstrate learning. Inspect the researcher quotation → interpretation → criterion → context report and perform one correction to demonstrate invalidation/recomputation.
5. **Synthetic privacy demonstration:** enter a contextual synthetic PIN. It must be rejected without echo, inference or consumed question. Then submit a general answer. Use synthetic email/address examples to demonstrate explicit cleaned-preview confirmation.

## Verification status

Final full regression: **1180 passed, 1 skipped** (164.84 seconds). The skipped test requires real Presidio resources. Final focused UI/privacy run: **62 passed, 1 skipped**. Python compilation, shell syntax and `git diff --check` passed. All six original source hashes matched the register; private originals and runtime/venv artifacts are ignored. Project launcher inspection confirmed localhost binding and disabled vLLM request-content logging. Existing logs were inspected structurally (historical UI tracebacks remain); this is not retrospective certification of their contents.

The regression suite and focused privacy tests exercise controller/client/UI/export boundaries with a synthetic detector. The real Presidio resource preflight and both three-case live runs were attempted and blocked by missing detector resources. This environment also cannot reach localhost model/UI services; no actual Qwen output or semantic live pass is claimed. Dependency installation failed on external DNS. The implementation is a candidate, **not yet a verified live meeting build**.

Rendered desktop/mobile (390px/360px), 200% zoom and keyboard/focus checks remain unverified because browser tooling is unavailable. Before presentation, check these layouts manually, including long text, errors, cleaned previews, skip/unsure/finish, correction, reset confirmation and downloads. No new screenshots are claimed. Retain the checklist in `readiness-ui-guidelines-review.md`.

## Launch and reproduce on the model host

```bash
cd ~/iam-sra-demo
scripts/setup-privacy.sh
.venv-privacy/bin/python scripts/check-privacy.py --output .runtime/privacy-preflight.json
scripts/health-check.sh
IAM_DEVELOPER=1 IAM_ASSESSMENT_MODE=acceptance_and_readiness_evidence scripts/start-ui.sh
.venv-privacy/bin/python scripts/smoke-readiness-evidence.py --meeting --baseline --output .runtime/fn-meeting-baseline-privacy.json
.venv-privacy/bin/python scripts/smoke-readiness-evidence.py --meeting --output .runtime/fn-meeting-information-privacy.json
.venv/bin/python -m pytest -q
```

Use the localhost URL printed/configured by the launcher. Historical demo: set `IAM_ASSESSMENT_MODE=legacy_fn_acceptance_demo` when starting a new UI session, with developer controls enabled. Do not reuse old sessions under the new privacy contract. If the existing UI supervisor is already running, stop only the project UI before switching its environment. Start the project model only if its health check requires it; do not restart shared services.

## Decisions for FN / project owners

1. What should a numerical result measure, and what role remains for the acceptance-oriented FN historical example? Which evidence anchors, prerequisites and synthesis rules define CRL/SRL?
2. How should information exposure, post-information reasoning and this chatbot's participation count, with what verification requirements?
3. Who approves and maintains questions, rubrics, local explanation material, model interpretations and UI/hub requirements?
4. Who owns privacy governance, lawful basis, retention, rights, special-category handling and deployment access? Supply the completed DMP/WP13 material before real-citizen use.

Feature scope is frozen at this bounded candidate. Remaining work is host verification, source/asset approval and methodological decisions, not another scoring formula or interface redesign.


### Interpretation review refinement — instrument 1.4.1 / prompt readiness-1.3.2

The first-answer review no longer says an answer adds no further readiness details when its proposal concerns are missing. Extraction instructions explicitly preserve stance, medical-purpose support, concerns and alternative conditions separately from readiness evidence. A secondary Re-read my answer action reruns the unconfirmed answer without consuming an interview question or changing confirmed snapshots. A stance-only initial summary clearly invites correction rather than presenting missing details as an established absence. No legacy participation/influence misclassifications were restored. Live semantic accuracy remains unverified in this environment.

### Three-case reliability checks after real detector installation

All 27 initial/follow-up/reflection/query/correction texts from the three meeting cases passed real Presidio screening individually. A new real-detector regression runs all three cases through the existing controller/meeting runner in baseline and information/reflection modes, including correction, final export and researcher report. Its extraction/composition responses are controlled doubles, not actual Qwen results: this establishes application/privacy plumbing only. Four real-detector tests passed (including full extraction/grounding request envelopes); 107 focused regressions passed with four real-detector tests skipped in the original environment.

False positives fixed without case-specific interpretation rules: controlled topic labels misidentified as names, standard machine field keys, generated evidence/event IDs, reviewed workbook citations and the static draft-information label. Exact metadata exceptions do not exempt surrounding prose or private names. Citizen/free-text and generated interpretations remain screened; secrets and contact details retain blocking/masked-confirmation behavior. No expected case answers or scores were injected into production extraction.

Both live three-case commands were attempted again. They reached service preflight but were blocked by the execution environment's `Operation not permitted` network error. No model output or semantic live success is claimed. Re-run both smoke commands on the actual host and inspect the resulting interpretations before presenting. The ordinary UI process must be restarted to load updated Python modules.

Final full regression for this three-case fix: **1182 passed, 4 skipped** in 141.70 seconds. The four real-detector tests skipped in the original test environment were run separately in `.venv-privacy`: **4 passed**, including all six controlled end-to-end meeting paths. Python compilation, whitespace checks and real 11-fixture privacy preflight also passed. These are not live Qwen semantic results.

### Fourth case: synthetic private address

Use `eval/meeting_privacy_case.json` in a new session. Copy:

> I live at 42 Example Street. Repeated early flights could interrupt my rest, so I would want noise measurements before deciding.

The address must be removed in the preview. Confirm the cleaned version to continue; the rest/noise concern must remain. Inspect the final export to verify that the raw address is absent. This is a separate privacy demonstration, not a fourth readiness benchmark. Screening remains enabled for all three assessment cases; their synthetic context is not a permission to bypass output/export protection.
