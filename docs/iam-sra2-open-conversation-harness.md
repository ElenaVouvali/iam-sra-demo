# Open conversation and enforceable harness

This is the historical open-conversation design. The FN-guided controller
replaces its soft-only navigation and answer-count completion; see
[the current FN interview specification and verification](fn-adaptive-interview.md).

Status: prototype implementation on `feat/open-conversation-harness`. The four
Eva/Future Needs PDFs are source-authored interview examples, not an approved
automated scoring policy. Their registered hashes are unchanged.

## Control boundary

The first three questions are controller-owned: chosen perspective, optional
city/urban area, and a profile-specific opening. Citizens are asked whether they
know what a drone is; organisational respondents describe their organisation or
unit without needing its name; technical respondents describe their technical
role before the assessed object is explored. Afterwards, Qwen proposes a participant-facing message
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


## Eva opening adaptation (eva-opening-1.0.0)

The 20-minute and 35-minute citizen PDFs (pp.2–3), organisational PDF
(pp.2–3) and technical PDF (pp.2–3) supply the opening sequence. Questions
are authored adaptations with source metadata in the screened message export.
City may be withheld or skipped; it is unverified and never establishes local
operations. A citizen's yes leads to an own-words description; no/uncertainty
leads to permission for an explanation. Supplied information remains an exposure,
not prior knowledge. Organisations are asked for their type/unit, not a required
name. At the owner's request technical role is the third question: the technical
PDF first asks organisation type within its role section, so this compressed
ordering is an authored adaptation. Technical role does not establish the
assessed object, version, expertise beyond that role, or a TRL.

These opening questions use no model calls. Ordinary conversation after the
opening remains adaptive. Opening metadata alone cannot trigger a model-proposed
wrap-up. The Vue chat renders these messages directly; restart the API and begin
a new conversation to see the revised opening. Existing sessions are temporary.

## Discussion pacing and context recovery (2026-11-09)

A reviewed local participant export stopped at the first adaptive turn with
`call_or_context_budget_partial`: its failure record reported `context_budget`
and zero model-generation calls. It was not a model decision to conclude.
The export itself remains untouched and is not copied into fixtures or Git.

Navigation now packs up to two whole retrieved passages (1,400 characters in
sum), short guidance, up to 1,200 characters of whole earlier answers, and four
recent questions. Source hashes/filenames and duplicate search text stay in the
controller, not the model context. The current answer is never truncated. The
model still has free choice of relevant follow-up; the fifteen indicators do not
constrain topic selection. Actual included/omitted evidence IDs are recorded.
One smaller retry on a tokenizer-budget failure omits earlier navigation and
retrieval explicitly. If that also cannot fit, the original answer is retained
and an authored recovery question keeps conversation available. Call-budget
exhaustion still offers an honest partial finish. The 4,096-token transport
ceiling and privacy checks remain enforced.

Independent of that bug, the former model-wrap minimum of three discussion
answers was too short. The pacing guard now allows a model-proposed wrap only
after ten substantive answers in short mode or sixteen in extended mode. The
same guard applies to both `propose_conclusion` and `act=finish`. These are
engineering pacing choices, not evidence-sufficiency or scoring thresholds.
User-requested stop/withdrawal remains immediate. The model receives flexible
profile-specific guidance about relevant evidence distinctions, with no list of
mandatory questions. Longer records can still exceed the bounded scoring
request and honestly abstain; this change does not manufacture a score or hide
omitted scoring evidence.

PDF filenames/page labels and document references are removed from participant
scale/message presentation. The original exact scales and provenance remain
in screened exports and developer traces. Both summary and result review now
explicitly invite “no changes”. At summary this proceeds to the result; at
result review it records the participant response separately and ends without
inventing additional evidence or changing the model suggestion.

A separate narrow privacy regression covers first-person city statements that
continue with a more precise numbered residential detail, using fictional
text. This is not evidence of perfect address or person detection.

Verification for this refinement: the API/chat/retrieval suite passed 128 tests
(one existing warning); after final context-metric and display changes the
focused chat/retrieval suite passed 107 tests. The targeted privacy subset
passed 25 tests; the real pinned detector also rejected the fictional precise
residential expression and preserved the city-only version. The frontend built
successfully (58 modules). A synthetic first-adaptive-turn request using the
registered corpus and pinned local Qwen tokenizer measured 1,075 prompt tokens
plus 1,100 output reserve (2,175 total); the lean retry measured 713 + 1,100
(1,813 total). Both fit 4,096. This is local tokenizer verification, not a live
Qwen conversation or independent assessment validation. The supplied export was
reviewed read-only; no real respondent text was sent to inference.

## Follow-up, prior knowledge and score ordering repairs

A later read-only review of the updated local `iam-sra2.json` showed 35 messages
with repeated impact questions, an unraised privacy/safety inference, repeated
identical recovery prompts, and an unrecognised request to finish. The exported
words are not copied into the regression fixtures. Tests use authored synthetic
variations of those interaction patterns.

Each screened answer now references its actual preceding assistant message.
The interviewer receives a bounded set of complete question/answer pairs,
its current question and the latest answer, instead of trying to reconstruct
which question each answer addressed. Older originals remain authoritative and
omitted navigation evidence is explicit. Question checks detect closer
paraphrases and repeated impact probes. They reject obvious personal
privacy/safety assumptions without corresponding respondent evidence, and
attributed participation when the available words describe only a hypothetical
or denied activity. These checks are fallible language heuristics, not proof
that every question is semantically correct. New topics can still be introduced
neutrally as optional discussion; topics are not restricted to the indicators.

The existing bounded model-output repair now applies to question-quality
failures. If repair fails, recovery chooses a distinct source-located neutral
probe rather than repeating the same fallback. This recovery path is not the
normal interview router. “I just answered”, “next question” and “please finish
this” are recognized as interaction controls and do not become readiness
evidence. Negated or quoted stop language remains separate. The engineering
discussion target is 14 substantive answers (short) or 22 (extended), after
which the controller offers the evidence summary. A target is not an approved
scoring rule or evidence-sufficiency threshold; users can stop sooner.

Citizen knowledge elicitation uses limited typed goals, not fixed question
wording: description, known uses, at most one optional additional-use follow-up,
prior healthcare awareness, what was heard when useful, local awareness and its
basis when reported, then open concerns. Qwen phrases those questions; authored
wording is used for safe recovery. Examples are not supplied before recording
prior uses. The neutral drone explanation no longer supplies healthcare use
examples. Uncertainty about local operations is retained as uncertainty.
After open concerns, prompt guidance invites selective follow-up around chosen
priorities, safeguards, evidence and trade-offs, participation opportunity,
influence and accountability. There is no obligation to traverse the fifteen
indicators or every PDF example. Organisation and technical scope remain distinct.

For a city answer containing a numbered address detail and a separate literal
city, `ControllerAdapter.prepare` screens the complete input first, screens the
extracted city again, and offers the existing cleaned-preview confirmation.
Only the city is retained after confirmation; rejected address text is not
hashed into receipts, queued, sent to inference, or saved. Secret/privacy-resource
failures cannot be bypassed by this extraction. The extraction is enabled only
for the city question, so numeric technical descriptions in other turns are not
silently converted into locations.

The scoring attempt occurs after summary review. A personal level choice is
accepted only after a validated numeric model suggestion; it never changes the
model suggestion. When the model abstains or is unavailable, the view exposes
`self_assessment_available=false`, explains the gap, and offers added factual
evidence or finishing without a score. Writing `additional facts: ...` records
screened new evidence and returns to summary review before a new judgment.
No numerical choice is manufactured from an abstention, and incomplete or
invalid citations cannot be overridden merely to ensure a number is displayed.

The bounded live follow-up check and both observed outcomes are documented in
`docs/eva-live-verification.md`. Its CRL 6 was produced before the simulated
participant response; the number was not prescribed. On the final optional
additional-facts question, “no changes” now completes the session without adding
fake evidence or invalidating the model suggestion.
