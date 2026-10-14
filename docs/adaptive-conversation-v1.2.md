# Adaptive conversational assessment v1.2

This branch advances the existing retrieval-grounded interview. New sessions use `conversation-1.2.0`; the default question budgets remain eight general questions and four scenario follow-ups. Each planner call receives only the controller's currently eligible shortlist. It returns an objective ID, proposed wording and a bounded strategy. Python resolves the choice to the existing eligible item and supplies source, criterion, trigger evidence, stage and provenance. Invalid candidates, schema output, wording, semantic review, privacy and transport failures are recorded separately, then use a valid authored fallback. Fallback is labelled as such.

The wording can now be original within the selected objective. The controller stops on explicit respondent choice, the fixed budget or no eligible objective; the planner does not override stopping rules. The optional retrieval explanation remains respondent-requested through its existing control. A bounded model review checks criterion, neutrality, context and actor/uncertainty. That review is fallible and not an independent authority. Eligibility, repetition limits, question budgets, evidence references, scenario facts, respondent confirmation, privacy, and all readiness methodology remain controller-owned. Version `1.1` remains selectable by the evaluator with the former wire schema and prompt; commit `4934cfd` is the recoverable pre-change checkpoint.

Planning context includes the three most recent confirmed question/answer turns, selected exact-quote claims, and a compact topic-memory view. Topic memory separates respondent-expressed topics from topics present only in a question or scenario. Its workflow statuses are not readiness levels. Claims remain in the authoritative session and retain their original evidence IDs and quotations. The existing request tokenizer and 4096-token transport budget reject overflow; the planner falls back and records the request failure rather than truncating evidence.

The existing lexical RAG and local source hash checks remain in place. Retrieved items restrict eligible candidates and provide source-backed scenarios and optional explanations. The model cannot add sources or candidate membership. The thematic topic registry still contains all 15 topic distinctions. A topic label introduced by scenario context is not a respondent concern without supporting respondent evidence.

The export adds versioned `topic_memory`, `planner_metrics`, `objective_registry_version` and `qualitative_assessment`. The qualitative profile uses evidence-status labels and source IDs, reports no readiness level, and notes that self-reported evidence was not externally verified. Existing numerical CRL, ORL, TRL and SRL fields retain their meaning; no overall SRL synthesis or approved CRL decision rule is introduced. The optional workbook-grounded citizen estimate remains provisional and separate.

## Source and decision traceability

| Behaviour | Authority locator | Implementation | Tests | Status |
| --- | --- | --- | --- | --- |
| Reflection, inclusion, anticipation, responsiveness; assessment and advancement tasks | Grant Agreement T3.2–T3.4, PDF p.9 per `references/source-register.json` | Existing baseline, scenario, and objective registry | Existing conversation/baseline suite | Contractual scope; does not establish validation or T3.4 deployment |
| Citizen anchors and separation from acceptance/trust/technical/organisational readiness | Workbook `Read me!J1:L13`; relevant comments and `SRA IAM indicators!I8/I15/I16`, per source register | `readiness_levels.json`, `citizen_score.py`, qualitative profile | `test_readiness_score.py`, conversation tests | Workbook descriptions are draft; no operational numerical rule approved |
| Fifteen thematic areas | Workbook `SRA IAM indicators` topic rows as recorded in source register; current registry `configs/concerns.json` | `conversation_objectives.py`, claim topic validation | objective-registry and topic-memory tests | Topic names preserved; raw workbook unavailable in this checkout, so no new interpretation is claimed |
| Dynamic follow-up concept | FN concept pp.1–9 per source register | Objective planning constrained by eligible shortlist | planner tests | Historical concept; no concern score, average, cap or bottleneck formula adopted |
| Local route cases and stakeholder categories | Grant Agreement Part B pp.19–22 and §2.2.1 per source register | source-checked local corpus builder and existing route filters | corpus and scenario tests | Grant describes plans; local operation and relevance await review |
| Review status and pending criteria | WP3 minutes 8 October, action points per source register | `draft_pending_FN`, `approved_by: null` preserved | config and export invariants | No partner approval inferred |
| Accessibility, participant control, simple interview | IAM-CC UI guide per source register | existing one-question UI and correction/finish flow | Streamlit UI tests | Partial alignment recorded; raw guide is not present in this checkout |

The explicitly requested originals under `references/private/` and the two conversation sidecars were not present in this workspace. The source register contains prior review notes and hashes, but those are not a substitute for the originals. The Grant Agreement, workbook, WP3 minutes, slide deck, FN concept and UI guideline therefore were not independently reopened during this implementation. No private corpus was regenerated. The local corpus must be rebuilt on the model host from the reviewed private sources after pulling this branch, then checked using the existing hash validation. The absent completed D1.2 and D13.1 deliverables remain absent; the source register does not establish their contents or approval.

The questionnaire, evidence mappings and registry are engineering adaptations of draft materials. They remain pending partner review. This implementation is an internal T3.3 prototype contribution; it does not claim consortium validation, multilingual deployment, demographic aggregation, or Living Lab baseline deployment under T3.4.

## Synthetic respondent evaluation

`eval/synthetic_personas_v1.json` defines 19 fictional personas. The agent has a deterministic scripted backend and an optional LLM backend using the already configured service. It runs the real `ConversationSession` controller, preserves confirmation actions, exports synthetic-labelled sessions and JSONL, and reports completion, planner/fallback, latency and call metrics. The offline synthetic collection uses authored test fixture questions and `MockBaselineClient`; it can test controller flow and privacy boundaries but cannot measure evidence-extraction or semantic accuracy. The live mode needs the local private source corpus and a healthy existing Qwen endpoint. The LLM respondent is not independent validation when it shares Qwen with the interviewer.

```bash
# Fast offline flow check: first two personas, deterministic answers, no model calls
.venv-privacy/bin/python scripts/evaluate-conversation.py

# Small live smoke on the existing endpoint, after confirming it is healthy
.venv-privacy/bin/python scripts/evaluate-conversation.py --live \
  --base-url http://127.0.0.1:18000 \
  --persona madrid_drone_novice --persona coimbra_privacy_noise

# Full exploratory run: 19 personas × 3 repetitions × 3 fixed seeds
# This can require hundreds of serial inference requests; launch deliberately.
.venv-privacy/bin/python scripts/evaluate-conversation.py --live --all \
  --repetitions 3 --seeds 11 23 47 --base-url http://127.0.0.1:18000
```

Reports and per-session artifacts go under ignored `.runtime/synthetic-evaluation/`. Privacy screening can withhold an artifact; the agent records a minimal screened failure record rather than bypassing the gate. `eval/conversation_adaptive_regressions_v1.json` is a reconstructed synthetic version of the reported Madrid interview, not the original complete export. Expectations are authored review labels, not measured evaluation results until run and reviewed.

## Current verification limits

At implementation start, the existing suite passed 464 tests with 19 skips. The live endpoint `127.0.0.1:18000` was unreachable in this workspace. The private source corpus and private originals were also unavailable, so live question planning, Qwen interpretation, private corpus rebuilding, and a matched live v1.1/v1.2 comparison cannot be claimed here. Offline report outputs are stored locally under ignored `.runtime/`; they are not committed.
