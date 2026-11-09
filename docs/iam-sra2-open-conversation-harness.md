# Open conversation and enforceable harness

Status: prototype implementation on `feat/open-conversation-harness`. The four
Eva/Future Needs PDFs are source-authored interview examples, not an approved
automated scoring policy. Their registered hashes are unchanged.

## Control boundary

The participant chooses one perspective in the welcome turn. That choice is
the only closed opening. Afterward, Qwen proposes a participant-facing message
and a small typed action (`ask_question`, `provide_information`,
`record_concern`, `offer_comparison`, or `propose_conclusion`). It can follow
any relevant concern, including a concern with no direct match in the fifteen
v4 indicators. Interview objectives in `chat_policy.py` are retrieved as soft,
source-located guidance; they are not an eligible-question list or a required
sequence. The exact model request contains no `eligible` or `objective_ids`
navigation fields.

Python retains authority over profile, lifecycle, evidence, scope, exposure,
source identity, permissions and persistence. The action contract rejects
unknown action values. Optional evidence, context, source and indicator
annotations are separately checked against active evidence, exact original
text, retrieved source IDs and the trusted v4 bank. Invalid optional
annotations are dropped while the screened answer is retained. Questions are
checked for empty text, echoes, repeats, multiple questions, disclosed levels
and unsupported local operation claims. Unsafe questions use a source-mapped
fallback. A plain city answer to an assistant's city/area question is stored as
unverified context by code, independent of Qwen's context extraction.

The model cannot invoke shell, filesystem, database or arbitrary network
operations. Source-information proposals can only cause the controller to
display the exact retrieved passage; the model's paraphrase is not treated as
verified fact. Conclusion proposals can only lead to a respondent-facing
summary/review stage. A provisional judgment is made only through the bounded
scoring operation after the respondent proceeds from the summary.

## Retrieval and source authority

`chat_retrieval.py` reuses the checked local conversation corpus and lexical
ranking. Per substantive turn it retrieves up to three relevant explanatory
passages plus up to three profile/depth interview-guidance records. It does not
send all PDFs on every turn and does not retrieve externally. Returned records
retain source ID, document, page/locator, source hash, source status/type and
permitted use. The four PDF-derived objectives are labelled methodological
guidance; source-corpus examples remain illustrative and cannot become
respondent evidence. Retrieved passages and respondent text are untrusted data
inside the Qwen prompt. They cannot change profile, authorize an action, revise
scoring policy, or approve storage.

The corpus is validated by the existing `conversation_corpus` source register.
Interview guidance and exact PDF scales are registered in
`references/private/chat-rubrics-v1.json`; the source identity register is
`references/chat-source-register.json`. The existing v4 workbook bank remains
the only source of the fifteen indicator statements. No PDF example answer or
example score is used as participant evidence or a target.

## Evidence and judgments

Original privacy-screened respondent text is authoritative and remains
revisioned. Model topic/context/evidence annotations are marked unreviewed and
are not quotations. The concern ledger distinguishes information requests,
opinion-only entries, existing-indicator candidates and emerging topics; a
topic mention is not readiness evidence. Candidate indicator IDs remain
private, unreviewed projections. No indicator average, individual SRL or city
SRL is calculated.

The generic result remains a separate provisional CRL, ORL or TRL match against
the applicable exact PDF scale. The scorer must cite active respondent words,
provide a different comparison anchor or abstain, and keeps supplied
information distinct from prior knowledge. Its result is not independently
validated; participant agreement is a separate review record. Organisation
and technology judgments require scoped context, and component/lab evidence is
not transferred to a complete system. Source examples are not target scores.

## Decision traces

Every chat submission adds a chronological, in-memory trace. It contains
safe proposal fields, the proposal's concise justification (not hidden
chain-of-thought), retrieved provenance, validated context fields, concerns,
candidate indicator mappings, validation results, fallback/error category,
observed model call/latency metrics, accepted action and state before/after.
Postcondition checks are computed from the actual session messages, exposures,
profile, stage and result rather than copied from Qwen. The trace intentionally
does not store raw rejected JSON, respondent answer text, raw privacy findings,
secrets or model prompts. It is temporary and is not included in participant
downloads.

The developer endpoint is off by default and has no participant UI route:

```text
GET /v1/dev/sessions/<session-id>/trace
```

It is served only when `IAM_CHAT_ENV=development`,
`IAM_CHAT_DEV_TRACE_ENABLED=1`, and `IAM_CHAT_DEV_TRACE_TOKEN` is at least 32
characters. A matching bearer token is required; participant owner cookies do
not authorize access. Use a dedicated development token, not a participant
session token. Traces are not sent to external observability providers.

## Privacy, storage and limits

The application continues to screen user input before mutation/model work,
screen generated model output, and screen views/exports. The source passage is
screened before use. The existing Presidio/spaCy and contextual checks remain
enabled. Synthetic privacy tests cover harmless place/technical text and
synthetic identifiers; they do not establish perfect name detection or a
production privacy release.

Ordinary sessions and decision traces remain temporary in-memory data.
Download remains available. Snapshot helper code exists but is unwired:
capabilities report `saving_enabled=false`, no Save control or save route is
exposed, and there is no database-write path through a model action. Database
storage remains disabled pending data-governance approval. Saving would not
authorize model training; exports remain `training_eligible=false`. There is
no resumable-session or durable review service.

The existing short/extended, call, context and processing limits remain
operational safeguards, not methodological rules. On invalid model output,
the answer remains recorded once and the controller uses a safe fallback or
honest partial stop. Inference/scoring failures are visible in developer
diagnostics without respondent-facing stack traces.

## Verification

Focused deterministic checks:

```bash
PYTHONPATH=src .venv-api/bin/python -m pytest \
  tests/test_chat_conversation.py tests/test_chat_retrieval.py -q
```

The test suite uses synthetic fixture clients for controller boundaries; that
is not live-Qwen evidence. Live Qwen checks must use the existing operator-run
API/model services and synthetic inputs only. Do not restart GPU/API/UI
processes as part of these checks.
