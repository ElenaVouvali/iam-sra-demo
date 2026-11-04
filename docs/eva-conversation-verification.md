# Conversational redesign delivery and verification

Date: 4 November 2026. Starting checkout: clean
`feature/indicator-assisted-self-assessment` at
`80ccba023cc088bab9d274453d64c6c94976dab3`. Final HEAD is unchanged; implementation,
source manifest, fixtures and documentation are local and uncommitted. No push,
merge, production restart, deployment or model/GPU change was performed.

See [implementation, source mapping and launch commands](eva-conversation-redesign.md).
All four requested interview PDFs are now present and registered. Their original
bytes, v4 source bank and questionnaire v0.2 were preserved.

## Files

| Purpose | Files |
|---|---|
| Conversation policy, state, one-turn generation and generic scoring | `src/iam_sra/chat_policy.py`, `chat_session.py`, `chat_client.py`, `chat_score.py` |
| Existing API integration, typed input, jobs and screened partial exports | `src/iam_sra/api/__init__.py`, `schemas.py`, `adapter.py`, `service.py` |
| Explicit original-message admission for optional v4 projections | `src/iam_sra/indicator_client.py` |
| Exact structural exception for the new schema identifier | `src/iam_sra/privacy.py` (respondent prose remains screened) |
| Actual chat UI, minimal shell, route and existing request lifecycle | `app/src/components/ChatConversation.vue`, `AppChrome.vue`, `app/src/router.js`, `app/src/tools/sra-assessment.vue`, `app/src/composables/useAssessment.js` |
| Preserved old participant interface | `app/src/components/LegacyAssessment.vue`, accessible at `/legacy` |
| Private-source extraction and public identity metadata | `scripts/register-chat-sources.py`, `references/chat-source-register.json`; derived anchors remain in ignored `references/private/chat-rubrics-v1.json` |
| Optional QR tool | `scripts/chat-qr.py`, `requirements-chat-tools.txt` |
| Authored rehearsal inputs and evaluator-only expectations | `eval/chat_rehearsals_v1.json`, `eval/chat_review_expectations_v1.json`, `scripts/rehearse-chat.py` |
| Focused checks and fixture compatibility | `tests/test_chat_conversation.py`, `test_chat_qr.py`, `chat_fixture.py`, `api_browser_fixture.py`, `app/tests/pages/sra-assessment.mjs` |
| Delivery/source/operational explanation | This file and `docs/eva-conversation-redesign.md` |

The sibling evaluator is unchanged. The rehearsal script reuses its API adapter,
owner cookie, CSRF and action polling; it is a fixed-input rehearsal, not a new
respondent agent or competing evaluation framework.

## Actual verification

Counts overlap; do not add them into a claimed combined total.

- Broader affected Python run: **230 passed** across chat/QR, indicator API,
  indicator assessment, API integration and privacy suites. Further boundary fixes
  were followed by focused runs rather than claiming the earlier result verified
  later changes.
- Final focused source/state/QR and existing v0.2 mapping run: **93 passed** in
  approximately 5.3 seconds. This includes all 45 legacy module mappings and the final new
  original-evidence, correction, review, preference, scope, source, budget and
  ownership boundaries.
- API integration plus chat/QR run after the API/source compatibility adjustment:
  **74 passed**. One dependency deprecation warning was emitted; it was not a
  failed assertion.
- Frontend production build: **passed**, 58 modules, isolated output
  `.runtime/chat-review/dist`. `app/dist` was not replaced.
- Existing isolated Firefox: direct `/chat` and tool alias, reload, three profiles,
  optional explanation, comparison, end-scale/review, privacy preview/draft
  retention and keyboard multiline checks **passed** through both static server
  (5015) and Vite (5016), with 360/1200-pixel widths.
- Expanded static browser flow at 200% text size, including the whole disclosed
  scale, **passed** after fixing footer-image/help-button overflow. No dedicated
  screen-reader, real IME or non-English usability study was performed.
- Actual private v4 workbook import compared with existing bank: **all 405
  statements and all generic scales identical**. All four PDF end scales loaded
  with their pinned identities: 36 exact anchors, nine per source scale.
- Real installed privacy detector: initial chat export and both conversational/
  generic-score input envelopes **passed**. These were screening checks without
  model generation, not accuracy tests of the detector or assessor.
- Actual separate source/privacy-backed API on 8015: capabilities **200**, chat
  creation **201**, queued action completed with an honest model-unavailable
  message, screened partial export **200**, classification **synthetic**. Its
  private export is `.runtime/chat-live-unavailable-partial.json`. The synthetic
  session was deleted afterward.
- Model availability was checked against the actual running API environment:
  `IAM_BASE_URL=http://127.0.0.1:18000`. Connection was refused; no vLLM process was
  present. Existing API 8006 was ready but was not restarted or used as a new-mode
  participant dataset. Live conversational/scoring quality remains **untested**.
- That failed real transport attempt recorded **0 generation calls**, **0.497
  seconds** in its observed generation-stage wall-time record. This is not a
  successful inference latency measurement.
- QR URL tests reject loopback/session-bearing links. The CLI rejected a localhost
  URL as expected. No canonical `PUBLIC_CHAT_URL` or optional QR dependency is
  configured, so a usable public QR asset is **not yet generated**.
- `git diff --check`: passed.

Relevant commands actually run:

```bash
PYTHONPATH=src .venv-api/bin/python -m pytest -q \
 tests/test_chat_conversation.py tests/test_chat_qr.py \
 tests/test_indicator_api.py tests/test_indicator_assessment.py \
 tests/test_api_integration.py tests/test_privacy.py tests/test_baseline_privacy_v2.py

PYTHONPATH=src .venv-api/bin/python -m pytest -q \
 tests/test_chat_conversation.py tests/test_chat_qr.py tests/test_questionnaire_v02.py

npm --prefix app run build -- --outDir ../.runtime/chat-review/dist --emptyOutDir

ONLY=sra-assessment FLOW='free chat' WIDTHS=360,1200 \
 BASE=http://127.0.0.1:5015 \
 FIREFOX="$PWD/.runtime/browser/firefox/linux-stable_157.0.1/firefox/firefox" \
 node app/tests/browser_check.mjs
```

The existing isolated Node 22.23.3 path was prepended for frontend commands.
Vite used the same browser command with `BASE=http://127.0.0.1:5016`.
The test API used `api_browser_fixture:create_fixture()` on 18015 with explicitly
synthetic inference/detector fixtures. Review services created during verification
are separate from deployment services.

## Preserved attempts and actual outcomes

Seven authored synthetic cases ran sequentially through the actual test API,
using the sibling evaluator adapter. Initial reports/logs remain in
`.runtime/chat-fixture-rehearsal-v1/` and the matching `.log`. Several long scripts
sent a redundant stop after automatic wrap-up and therefore ended before score
review. These early finishes were retained, not relabelled as successful scoring.

The runner was corrected to avoid submitting that redundant scripted stop;
respondent facts and scoring policy were not tuned to obtain a desired result.
The replay is preserved in `.runtime/chat-fixture-rehearsal-v2/` and its `.log`:

| Case | Final recorded stage | Judgment |
|---|---|---|
| Unfamiliar citizen | review addition | Fixture abstention; supplied explanation separated from prior knowledge |
| detailed_multitopic | review addition | Fixture abstention; no invented local operation or participation |
| Denied opportunities | review addition | Fixture abstention; one correction retained, no opportunity penalty |
| Organisation pilot | review addition | Fixture abstention; remit and pilot/routine boundary retained |
| Technical laboratory | review addition | Fixture abstention; component/configuration and laboratory boundary retained |
| Result disagreement | partial summary after additional facts in this replay | Initial abstention retained in history; preferred level separate. A subsequent regression fix ensures additional facts remain pending review without automatic reassessment |
| Optional comparison | review addition | Wording preference/reason separated from substantive answer |

The replay took **20.682 seconds** across seven cases (2.619–3.195 seconds/case).
Those are fixture/API times, not Qwen generation performance. Fixture costs are
not observable model calls. **No semantic accuracy estimate** follows from these
runs. The fixture scorer deliberately abstains; supported model judgments require
a live rehearsal and separate human assessment against the recorded source
expectations.

Meaningful failures found and fixed during this task:

- A legacy test matching fixture assumed confirmed interpretation observations;
  it now explicitly abstains under the new original-message contract. The legacy
  fixture behaviour remains for legacy tests.
- Cleaned-preview submission cleared the original local draft too soon; returning
  to editing now retains it, and explicit acceptance clears it after success.
- Large-text narrow layouts overflowed in the funding emblem/help button; chat-only
  styles were corrected while preserving funding text.
- The real detector misclassified the new schema identifier and the word “JSON”
  in authored instructions. An exact structural schema exception and neutral
  prompt rephrasing fixed these without exempting respondent prose.
- A correction fixture pointed at capacity rather than the explicitly mentioned
  city; the fixture was corrected, preserving the earlier attempt.
- Additional facts after disagreement could re-enter scoring; this now remains a
  pending review with the initial result retained. No automatic upgrade occurs.

## Opening and example transcript

Default opening: truthful AI/research welcome, privacy/temporary-progress reminder,
then one question choosing personal, organisational or technical capacity.
Next: optional city/area; own responsibilities/object for the non-citizen paths;
then familiarity/context, spontaneous concerns and selected priorities. Later
questions adapt within source-backed objectives instead of displaying indicators.

**Fixture-labelled excerpt, not a live model dialogue:**

> AI: Are you sharing your personal views, speaking about an organisation's
> responsibilities, or discussing a technology you work with?
>
> You: My personal views.
>
> AI: Which city or area would you like to discuss? You can keep this general.
>
> You: Prefer not to say.
>
> AI: What have you heard about drones and what they are used for?
>
> You: I have no idea what a drone is.
>
> AI: Would you like a brief explanation of what a drone is? You can say no and continue.

The actual browser chat is observable in its own browser session. A CLI rehearsal
has a different owner cookie and does **not** appear in that browser session.
Saved exports/logs are transcripts, not equivalent to observing the UI.

## FN review before a pilot

- Are questions neutral, understandable and genuinely one question at a time?
- Do spontaneous priorities drive the conversation without repetitive basic probes?
- Is capacity chosen rather than inferred from profession, and are remit/object
  boundaries faithful throughout?
- Are unknowns, no opportunity, hypothetical capability, actual activity,
  demonstrated effects and supplied information distinguished?
- Are the two citizen scales' differences and the Level 7 capability/action tension
  methodologically acceptable? Are higher ORL/TRL boundaries defensible?
- Do quoted supporting words actually establish the selected full anchor, rather
  than merely relate to it? Are abstentions and alternatives appropriate?
- Can users correct meanings, disagree, stop or withdraw without pressure?
- Are narrow/large-text layouts, assistive technology, facilitator entry and the
  project's non-digital participation pathway acceptable?
- Who will review downloaded feedback, under what permissions/retention policy,
  and without implying a durable review queue or contact follow-up?

Internal review preview: available with labelled fixtures and source-backed startup.
Supervised live FN demonstration: requires the model service and frozen live
rehearsals plus human semantic review. Partner pilot: pending that review and FN/DMP
permission/retention decisions. Unattended scoring: **not validated**.

After verification, the isolated static server (5015), Vite (5016), synthetic
fixture API (18015) and source-backed review API (8015) created for this task were
stopped. The existing deployment/API processes and model configuration were left
running/as configured. Use the launch commands in the implementation document to
open a new review preview.
