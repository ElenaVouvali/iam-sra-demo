# Conversational meeting candidate — actual verification, 13 October 2026

This is a historical 1.1 verification report. It does not validate the v1.2
planner; current v1.2 checks and limitations are recorded in
[adaptive conversation v1.2](adaptive-conversation-v1.2.md).

Historical verification for version 1.0. See [the 1.1 update](conversation-update-1.1.md) for the current implementation and new checks.

## Delivered scope

`retrieval_grounded_conversation` / `conversation-1.0.0` is selectable without
developer access and can be launched directly. All three synthetic cases complete
the real controller and Streamlit element flow with controlled interpretations.
This is an executable meeting candidate with specific limitations, not a claim
of live semantic accuracy, scientific validation, FN approval or production readiness.

The actual starting checkout was `fc5b69a0aa207e7fe840b573eb0195667517aad6`,
with existing local recovery work. No applicable AGENTS.md was present. Existing
changes were preserved; nothing was reset, stashed, committed or pushed. No model
weights, dependency pins, shared services, existing scenario facts, historical
arithmetic or historical benchmark expectations were changed.

Before: the general and fixed-scenario interviews were separate components.
The general route handed citizens to another interview and did not provide a
retrieved, model-selected cross-stage conversation for organisational respondents.
After: a new coordinator preserves both components' evidence context/history,
offers the same retrieved illustrative card to relevant personal/organisational
routes, follows confirmed gaps, and produces one final confirmed export. The
existing deterministic general and scenario modes remain available.

## Files and reasons

| Files | Change and benefit |
|---|---|
| app.py; configs/assessment_modes.json; src/iam_sra/session.py | Explicit selectable mode, fresh-session confirmation, actionable missing-collection errors; existing modes retained |
| configs/conversation.json; prompts/conversation-planner.txt; prompts/conversation-context.txt | Versioned budgets, proposed wording, criteria/source locators and strict planner/context boundaries |
| scripts/build-conversation-corpus.py | Reproducible small private source collection and coverage report; original draft/feedback/comment comparison kept outside retrieval |
| src/iam_sra/conversation_corpus.py | Metadata-filtered lexical retrieval, original/configuration hash checks, fixed scenario fact checks and source/code provenance |
| src/iam_sra/conversation_planner.py | Model choice among eligible retrieved items and authored natural variants; validated IDs/wording/gap references, bounded repair and deterministic fallback |
| src/iam_sra/conversation_session.py | General→scenario→final coordinator; confirmed profiles, context-separated evidence, decline, partial finish, corrections, exposures, screened exports and optional draft citizen judgement |
| src/iam_sra/conversation_ui.py | Complete short Streamlit journey, visible initial scenario, optional sourced explanation/reflection, clear correction/retry/edit/download controls, researcher-only historical reference |
| baseline.py; baseline_client.py; baseline_routing.py; baseline_session.py | Additive proposal claim types limited to the new scenario context; scoped server validation; eligible shortlist reuse; context/evidence-prefix/elicitation metadata. Original default deterministic routing retained |
| readiness_score.py | Only for the new explicit estimate scope: own confirmed claims/exact quotations, context and exposure limits; existing scenario estimate behaviour retained |
| privacy.py; privacy_ui.py | Exact trusted schema/locator metadata reviewed after demonstrated false positives; new widget/action identities in stale-preview protection. No bypass or arbitrary text exemption |
| eval/conversation_meeting_cases.json; conversation_benchmark.py; scripts/smoke-baseline.py | Three consistent synthetic scripts, ID/variant-bound answers, actual initial/final outputs, automation labels, safe partial/failure reports and live preflight. Existing runner extended |
| tests/test_conversation.py; tests/test_readiness_evidence_ui.py; tests/test_interpretation_review.py | Whole-journey, scope, policy, recovery, privacy, role/activity, exposure and UI checks; mode-count and current-schema assertions updated |
| README.md; docs/conversational-meeting-demo.md; docs/privacy.md; docs/readiness-ui-guidelines-review.md; references/source-register.json | Launch/walkthrough, source mapping, implemented boundaries, source inventory and honest remaining checks |

The earlier local baseline recovery changes remain in the working tree, including
the named-effect clarification guard, safe-answer retry behaviour, simplified
controls and benchmark v4 successor. They are documented separately in
baseline-recovery-2.3.1.md; they were not replaced by this mode.

## Executed checks

| Check | Actual result / meaning |
|---|---|
| Full existing and new regression suite, `.venv/bin/python -m pytest -q -m 'not presidio_live'` | **421 passed**, 39.23s. Declared detector doubles and controlled extraction; not model semantics |
| Installed-detector suite, `.venv-privacy/bin/python -m pytest -q -m presidio_live` | **17 passed**, 216.20s, plus **one additional focused optional-estimate envelope/export test passed**, 27.58s. Real Presidio/spaCy; model responses are controlled where used |
| Final three-case real-detector fixture runner | **3/3 completed**, no withheld final exports, all recorded structural/context/budget/snapshot invariants passed |
| Synthetic case A | General 7 items, initial scenario view + requested optional reflection; no actual participation/influence inferred; support separate from unknown understanding; two exposure events |
| Synthetic case B | General 7 items, initial scenario view and explicit correction; bus consultation contribution remains transferable, outcome unknown, opposition separate; initial snapshot retained |
| Synthetic case C | General 7 items, initial scenario view + contextual effect question; team review and personal contribution stay distinct, no organisational score; local evidence gaps retained |
| Streamlit AppTest | All three full routes, final downloads, editable history, optional source display/reflection, privacy preview invalidation and retained-answer partial finish exercised |
| Actual pinned local Qwen tokenizer, controlled full three-case requests | **70 requests**: 22 planner, 24 extraction, 24 grounding. Maximum prompt + reserved output **3652/4096**. No model generation; not proof of semantic accuracy or long-answer capacity |
| Source builder / real detector | 51 question variants, one scenario, 10 passages; eight citizen-allowlisted, two researcher-only. Source/config hashes verified; private outputs ignored |
| `git diff --check`, compileall, shell syntax | Passed. Historical seed/v2/v3 benchmarks, model config, scenario facts, dependency pins and UI theme/CSS unchanged |

The three fixture runner durations were 64.5s, 63.0s and 60.1s including real local
screening and export checks. These are **not GPU inference latency**. The live
runner records actual model call/token/retry/latency diagnostics when it can run.

Artifacts (private, ignored):

- `.runtime/conversation-meeting-final-fixtures.json` and three referenced per-case
  screened exports: actual case outputs, questions, initial interpretations and
  invariant results. Human semantic review remains pending for live outputs.
- `.runtime/conversation-context-check.json`: local-tokenizer counts with controlled
  interpretations; all 70 recorded requests fit the configured context.
- `.runtime/conversation-live-final.json`: **blocked_model_endpoint_unreachable**,
  semantic status **not_run**, zero live cases. The environment could not reach
  the host's localhost service; this does not prove the host service was down.
- The earlier `.runtime/conversation-fixture-meeting.json` is preserved: its three
  export failures identified the new schema-name false positive. Later successful
  runs are separate files; the failed attempt was not erased.

## Problems found and corrected

- The installed NLP detector initially interpreted the new schema version as a
  person's name. Only that exact trusted application version and fixed workbook
  locators were registered as metadata. Positive secret/address tests still pass.
- The planner's system instructions triggered a PERSON false positive before HTTP.
  Rephrasing the application-authored instructions resolved it; screening stayed
  enabled. A real-detector test now reaches planner, extraction and grounding
  through synthetic HTTP responses. Fallback diagnostics retain safe finding
  metadata rather than rejected prose.
- The new optional citizen-judgement prompt was also checked with the real
  detector. This explicit scope uses natural instructions, faithful draft anchor
  descriptions and compact own-evidence quotations; it does not inherit an
  assumed cumulative highest-level rule. Existing scenario scoring instructions
  are retained for their original scope. No data are dropped from the full audit.
- A team's reported exposure followed by an explicitly linked personal contribution
  could prompt a redundant question. A conservative same-answer/activity link now
  recognises the supplied contribution while preserving distinct subjects.
- Unknown influence for one activity must not close another activity's gap.
  Routing now checks the particular compatible activity; unknown scope stays unknown.
- The scenario phase originally loaded fresh defaults at handoff. It now inherits
  the session's frozen prompts/instrument; edits preserve exposures and earlier
  snapshots instead of relabelling post-information answers as prior knowledge.
- Proposal categories are permitted only in the new scenario context, both in
  decoding schemas and server checks. General evidence cannot become acceptance.

## Blocked and unverified

**No live Qwen generation was possible from this execution environment.** The
configured alias/revision are recorded expectations, not an observation of the
running host. Run the guide's live command on davinci and review the initial
interpretations, question relevance, omissions, subject/modality and final claims
before presenting them as model results. The optional provisional citizen estimate
also remains live-unverified. No forced score or approved numerical result exists.

No browser/Playwright is installed. A temporary Streamlit launch on test port 18502
failed at socket creation with `PermissionError: Operation not permitted`.
AppTest exercises Streamlit controls but does not verify desktop/mobile pixels,
keyboard focus, 200% zoom or produce actual rendered screenshots. Use the guide's
manual checklist. The host UI/model were not restarted or replaced by this check.

Longer answers, repeated explanations and retries can exceed 4096 tokens; the
existing transport refuses oversized requests without truncating evidence. Retry,
Skip and partial Finish remain available. The 70-request context inspection covers
only the supplied short synthetic journeys and no generation-time repair expansion.

Presidio supports English NLP plus bounded contextual address patterns, not
universal multilingual privacy detection. False positives and misses remain possible.
No real citizen data were used. There is no anonymity guarantee, secure-erasure
claim, institutional privacy approval or GDPR certification.

All listed original sources are present. Still missing are the completed approved
FN report/statement bank, reviewed populated LL cases, relevant full paper texts,
completed institutional data/ethics policies, approved branding kit and WP2 hub/
privacy ownership decisions. The private meeting_notes source is a single file,
not a populated directory. No absent content or approval was manufactured.

## Scope freeze and handover

The implementation is frozen at the bounded demonstration scope. Follow
conversational-meeting-demo.md for launch, fresh sessions, the three copy-paste
scripts, synthetic privacy example, human review protocol and exact live commands.
Priorities after the meeting are approved evidence/level rules and comparable
reporting, validated local content, live semantic evaluation, and institutional
privacy/UI integration. Broad corpus ingestion, embeddings, multiple real local
scenarios, training and production storage are deferred.
