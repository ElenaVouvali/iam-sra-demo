# IAM-SRA2 API contract, version 1.1.0

The Flask factory is `iam_sra.api:create_app()`. This API adapts the actual
`ConversationSession` engine (`conversation-1.2.0`); it does not define a new
assessment instrument. `ControllerAdapter` maps operations and projects public
presentation data. `AssessmentService` owns sessions, versions, previews and jobs.

The backend paths are `/v1/...`. The requested browser prefix is
`/api/sra-assessment/v1/...`. Both the adapted Vite proxy and production
`serve_app.py` remove `/api/sra-assessment`, as verified in the actual donor.
The allowlist contains only `sra-assessment`. Cookies, CSRF/version headers,
status codes and export headers pass through both proxies.

## Endpoints

| Method and path | Response |
| --- | --- |
| `GET /v1/health` | 200 with privacy/corpus readiness and single-process deployment identity; 503 when required resources are unavailable |
| `GET /v1/capabilities` | Engine version, onboarding option maps, readiness, CSRF token and only this owner's session summaries; sets the signed HttpOnly owner cookie |
| `POST /v1/sessions` with `{}` | 201 with `session`, starting at `general_welcome` |
| `GET /v1/sessions/<id>` | 200 with the current presentation DTO |
| `POST /v1/sessions/<id>/actions` | 202 with `job_id` and a responsive current `session`; preview/discard/reset return 200 |
| `GET /v1/jobs/<id>` | queued/running/completed/failed status; 410 after result invalidation; 404 after result retention expires |
| `GET /v1/sessions/<id>/export?format=json\|jsonl` | Screened attachment, available after final-summary confirmation; `Content-Disposition` and appropriate JSON/NDJSON content type |
| `DELETE /v1/sessions/<id>` | 204 after owner, CSRF and `X-Session-Version` checks; drops application references and invalidates jobs |

All responses, including errors and exports, use `Cache-Control: no-store`.
Missing or foreign sessions/jobs return 404; recently expired owned sessions return
410. IDs identify records; the signed cookie establishes ownership.

## Action envelope

```json
{
  "action": "answer",
  "expected_version": 2,
  "request_id": "8e7d4bec-949f-4f6a-9404-36ca9de4b32c",
  "data": {"text": "I would like information about noise.", "control": "answer"}
}
```

`request_id` must be a version-4 UUID generated separately for each new operation.
A transport retry uses the same UUID and the same data. Reusing it for different
data returns 409. Duplicate accepted work returns its existing job and never
advances twice. After an old result expires, a duplicate can return the current
session with `duplicate: true, result_expired: true`. Corrections/reset invalidate
old receipts and results. `expected_version` is the API revision, not the engine's
internal version: the latter does not advance on every controller mutation.

| Action | Data | Available state |
| --- | --- | --- |
| `set_context` | `perspective`, `role`, `city`, optional `place`, `function` | general welcome/context; use actual capability keys |
| `answer` | `text` (max 6000), `control`: answer/skip/unsure/decline | general/scenario interview |
| `confirm_answer` | `{}` | interpretation review |
| `correct_interpretation` | `text` (max 1500) | interpretation review; does not silently replace the original answer |
| `finish` | `{}` | interview with no pending interpretation |
| `confirm_general` | `{}` | general summary review |
| `select_scenario` | `scenario_id` from current `scenarios` | scenario offer |
| `accept_scenario`, `decline_scenario` | `{}` | scenario offer |
| `ask_information` | `question` (max 300) | scenario, no pending interpretation, within engine information budget |
| `acknowledge` | `exposure_id` from current information | unacknowledged current exposure |
| `start_reflection` | `{}` | only when a sourced reflection is eligible under the existing engine rules |
| `confirm_final` | `{}` | scenario summary/final review |
| `provisional_estimate` | `{}` | historical global-anchor estimate; final/personal and `IAM_DEVELOPER=1` only |
| `back`, `edit_context` | `{}` | as listed by the current DTO |
| `edit_answer` | `stage`: general/scenario, active confirmed `event_id` | as listed by the current DTO; invalidates dependent scenario/results |
| `confirm_cleaned` | `preview_id` from this exact current preview | current owner/session/version/action/question binding |
| `discard_preview`, `reset` | `{}` | as listed by current DTO; reset also cancels active work |

Only `allowed_actions` authorizes the next UI action. Do not reproduce routing,
eligibility, evidence admission or scores in JavaScript. Submitted controlled
values are validated server-side, and every retained string is screened before
fingerprinting or queueing. Unknown fields are rejected.

## Privacy preview

Redactable input returns 200 with a `session.preview` containing only cleaned
fields and an opaque preview ID. The original is not retained, hashed or queued.
The UI must clear its original draft, display the cleaned text, and request an
explicit `confirm_cleaned` action. That action accepts only the preview ID; it
cannot substitute data. An edit, navigation, reset, new preview or changed API
revision invalidates the old confirmation. A rejected credential has no preview
and returns 422. A private-address-only answer is not assessable.

Cleaned confirmation re-screens the prepared action. Model output and browser
exports pass the existing engine screening gates. Privacy-resource failure is
503, never a switch to mock mode. Explicit test factories are accepted only by
`create_app(TESTING=True, service=...)`; there is no environment-based mock API.

## DTO, errors and downloads

`SessionView` explicitly exposes state/stage/version, allowed actions, current
question, pending interpretation, respondent context, offered/selected scenario,
read information with citations, confirmed answers, evidence and descriptive
summary. It includes a busy job, cleaned preview and a screened retry draft where
appropriate. Clients must ignore obsolete responses and re-read state after jobs.

Results keep CRL/TRL/ORL/SRL unavailable. A separately requested
`provisional_citizen_estimate` is labelled draft, unapproved and unverified. It
does not turn opinions, supplied information or participation in the interview
into validated readiness. Missing evidence is not low readiness.

Errors are `{ "api_version": "1.0.0", "error": {"code": "...", "message": "...",
"retryable": false} }`. Codes include `stale_action`, `duplicate_conflict`,
`session_busy`, `session_expired`, `job_obsolete`, `queue_full`, `capacity`,
`privacy`, `privacy_unavailable`, `source_unavailable`, `timeout`, `model_failure`,
`csrf`, `origin`, and `deployment`. Never display exception/transport bodies.

The browser export is the documented `browser_evidence` profile, schema `1.0.0`,
with the original `engine_schema_version`. It preserves separate baseline/scenario
evidence, confirmations, corrections, exposure histories, uncertainty, null scores,
provisional labels and source integrity metadata. It omits internal prompts,
transport traces/settings, private source paths and researcher diagnostics. It is
not a byte-for-byte copy of the richer private Streamlit research export. API code
integrity is included in `provenance.file_sha256.api_snapshot`; uncommitted source
is explicitly identified by `working_tree_dirty`.

## Browser security and polling

Bootstrap capabilities using same-origin credentials, retain CSRF only in memory,
and send `X-CSRF-Token` on every mutation. The owner cookie is HttpOnly,
SameSite=Strict and path `/`; set `IAM_SRA_COOKIE_SECURE=1` for HTTPS. Tokens,
answers and results must never enter localStorage, catalogue storage or query
strings. The proxy must preserve Cookie, Set-Cookie, Origin, X-CSRF-Token,
X-Session-Version, status codes and download headers.

All queued actions immediately return 202. Poll the same-origin job endpoint,
then fetch current session state on completion/failure. A pending action disables
duplicate UI submissions. Reset must stop obsolete polling and clear drafts and
exports. A lost response can be retried using its original request UUID; a new
attempt after a model failure needs a new UUID and current version.

## Draft citizen indicator continuation (1.1)

After final-summary confirmation, `SessionView.indicator_assessment` exposes
availability, the pinned bank/policy identity, selected scope, current indicator,
its exact nine citizen statements, confirmed evidence, distinct tool/participant
judgments and fifteen-indicator coverage. Organisation/withheld perspectives
receive a scope notice, not a citizen estimate. No new endpoint is introduced.

| Action | Data | Condition |
| --- | --- | --- |
| `select_indicators` | `profile: citizen`, 1–3 `indicator_ids`, `context`: general_understanding/illustrative_proposal/actual_experience, optional `use_case` (240), `reuse_answers` mapping selected indicator IDs to up to three confirmed answer IDs | Final/personal, valid pinned bank |
| `indicator_answer` | `text` (2000), `control`: answer/skip/unsure/decline | Current indicator collecting |
| `indicator_confirm` | `{}` | Pending indicator interpretation |
| `indicator_correct` | `text` (1500) | Pending interpretation; feedback is not new evidence |
| `indicator_finish` | `{}` | Collecting, no pending interpretation |
| `indicator_suggest` | `{}` | Evidence collection finished; no current suggestion |
| `indicator_review` | `choice`: endorse/select/unsure/decline, assessment `revision`, optional `statement_id` and `explanation` (600) | Ready/review/complete; explicit review, current revisions |
| `indicator_edit` | active indicator `event_id`, `mode`: answer/interpretation | Invalidates active dependent judgments |
| `indicator_next` | selected `indicator_id` | Selected round; resumes that indicator |

The existing owner/CSRF/API revision/receipt/preview/job boundaries apply. Every
new free-text field is screened before retention and queueing. Statements and
levels are resolved server-side; clients send IDs, never source wording.
Both public presentation and JSON/JSONL exports include the separate judgments,
source references, evidence and revision status. Historical global numerical
fields remain unchanged, not aggregates. Export schema 1.0 retains additive
`indicator_assessment` with its own versioned schema. The new matching workflow
is draft and has no second semantic-review pass. See
[indicator methodology and operator commands](indicator-assisted-self-assessment.md).
