# Eva conversational prototype

Implementation on `feature/indicator-assisted-self-assessment`, starting clean at
`80ccba023cc088bab9d274453d64c6c94976dab3`. No deployment or push. Existing snapshot
scaffolding is preserved, remains unwired, and is not used by this mode.

## Sources and methodological decision

All four newly supplied PDFs were read, including branching, result review and
interviewer notes. `references/chat-source-register.json` records exact filenames,
SHA-256 values, end-scale PDF pages and the private derived-file hash.
`scripts/register-chat-sources.py` extracts only the four nine-anchor end scales;
line wraps are joined, wording is preserved. Private PDFs and derived wording
remain ignored. The original source register, v4 bank and questionnaire bytes are
unchanged. Re-registering a revised source is a deliberate review operation, not
an automatic repair for an identity mismatch.

| Source | Locators / use | Behaviour |
|---|---|---|
| SRAA Citizen interview example 20min.pdf | pp.1–11; scale pp.12–13; example/boundary pp.13–14; review pp.14–16; guidance p.16 | Default short citizen conversation, selected priorities, capability/action distinction, whole end scale and separate review |
| SRAA Citizen interview example 35min.pdf | pp.1–16; scale pp.17–18; boundary pp.18–19; review pp.19–21; guidance p.21 | Extended citizen probes and its own exact scale; unfamiliar-issue explanation recorded as exposure |
| SRAA Organisation interview example.pdf | scope pp.2–3; preparation/testing pp.8–15; scale p.16; result/review pp.17–19; guidance pp.19–20 | Own remit only; plans, preparation, realistic tests, integration, operations and sustained monitoring remain distinct |
| SRAA Technology interview example.pdf | object pp.2–5; validation pp.5–15; probes pp.15–17; scale pp.17–18; review/guidance pp.18–23 | Same object/configuration and interfaces; controlled/relevant/operational environments, qualification and operational use |
| IAM-CC_SRA_IAM_indicators_TRL_ORL_CRL_scales_v4.xlsx | generic scale sheet B:E2–10; all profile criteria and 405 exact statements | Legacy reference and separate unreviewed indicator projection. Original workbook import equals the existing bank for all statements and generic scales |
| IAM-CC_Topic_experts.xlsx | SRA IAM indicators H:J2–16 | Open questions and FN distinctions between acceptance/trust and readiness; no opinion bonus |
| IAM-CC_D3.1_Initial_Societal_Readiness_Report_v0.18_with_LL_workshops.docx | §§10.4–10.6, especially §10.5.1 | Profiles and reflective evidence; individual self-assessment and later aggregate reporting remain different. The new generic model judgment is an explicit prototype change from the older per-indicator self-assessment workflow |
| GA.pdf | T3.2–T3.4, technical annex printed p.9; DMP/inclusion provisions | Operationalise framework, individual snapshots and later aggregate project goal; no aggregation implemented here |
| Questionnaire v0.2 and alignment/integration notes | 45 modules / 150 questions / 42 shared probes | Retained for legacy mode and source-linked indicator references; new chat is not the three-question loop |
| October WP3 minutes / September slides | existing registered source sections | Topic questions and concrete use cases; no claim of approval of this implementation |

Background filenames/hashes/locators remain in `references/source-register.json`.
The questionnaire's documented missing July/workshop originals remain unresolved;
new PDFs are now present. Their illustrative respondent answers and example
results (6/6/7) are not production evidence or target outcomes.

Policy `eva-conversation-prototype-1.0.0`, chat schema `iam-sra-chat-1.0.0`, PDF
rubric `eva-interviews-2026-11-04-v1` are distinct from the legacy matching policy.
Short mode uses the 20-minute citizen scale; extended mode uses the 35-minute
scale. The mapping is level-to-corresponding-level for comparison only: descriptions
are not merged. Extended descriptions add explicit consultation, examples of
issues, discussion/simulation and scrutiny of changing decisions. Both PDFs call
Level 9 **Sustained involvement**; v4 calls it **Sustained agency**. PDF middle
anchors emphasise what a citizen *can* do; v4 describes engagement/actions more
explicitly. The PDF example nevertheless distinguishes potential arguments from
actual influence on a changed decision. That tension is supplied to the scorer
as guidance and must be reviewed with FN; no numerical opportunity adjustment or
blanket past-participation gate is added.

## Product mapping

| FN direction | Implementation / checks |
|---|---|
| Warm free-text chat, fewer controls | `/chat`, one labelled multiline composer and Send. No indicator forms, counters, skip/unsure buttons or routine interpretation gates. Existing tool URL redirects to chat; `/legacy` preserves the old journey |
| Gentle context and familiarity | Explicit answering capacity, optional broad area, profile scope, familiarity and healthcare awareness. Profession never chooses capacity. Organisation/technical objectives are distinct |
| Selective depth, no examination | Spontaneous concerns first; then two/three priorities. Eligible objective shortlist and grounded coverage avoid compulsory traversal of fifteen indicators. Short/extended limits are engineering limits, not time guarantees |
| Corrections/uncertainty/withdrawal | Original screened words are respondent-provided evidence, interpretations remain unreviewed. Targeted corrections preserve supersession; results are archived/invalidated. Natural commands handle pause, skip, back, finish and withdrawal; negated/quoted stop is not a command |
| End-scale/result/review | All nine exact PDF anchors at wrap-up; semantic generic match with original quotations or abstention; preferred level/review/additional facts separate; no automatic upgrade after disagreement |
| Optional “1 or 2?” | Explicit request, frozen objective/context, randomised variants and recorded mapping. Preference/reason are not evidence, preferred level or training permission. Mixed substantive answer is retained separately |
| Inclusion / QR | Plain language, keyboard/multiline/IME-safe composer, stable focus, no auto-scroll/timing test; optional facilitator provenance; ordinary canonical link and local QR generator |
| Traceability | Existing jobs/privacy/owner/CSRF/revisions/receipts; partial screened JSON/JSONL exports. Generic and indicator judgments have separate scopes and review status |

## Controller and inference

`ChatSession` is a composed evidence-admission state inside the existing
`ConversationSession`, not a new service or agent framework. The existing API
service owns sessions, jobs, expiry, CSRF, owner checks, revision checks,
idempotency, queueing and late-result fencing. Legacy engines and evaluators use
the unchanged default API creation mode; the new frontend explicitly creates
`mode=chat`. The sibling evaluator's `APIAdapter` is reused by the fixed rehearsal
script; its respondent agents/persona banks are unchanged.

Code owns scope, stages, allowed objectives, quotations, references, supersession,
exposures, preferences and limits. The LLM annotates original meaning, proposes an
eligible objective and natural wording in one bounded call. Pydantic and local
checks reject invented citations/objectives, malformed output and leaked level
language during elicitation. These structural checks cannot prove semantic
neutrality or correctness. Authored questions provide a safe fallback; malformed
requests retain the screened original and offer finish/download recovery.

Authoritative turns are retained outside prompts. Navigation sends selected
originals, the current answer once, and the last selected priority within a combined
4,500-character evidence bound, recording included/omitted IDs; it does not
claim omitted originals were considered. Generic reporting uses all active
originals up to a 5,000-character preflight bound; larger complete records abstain
rather than silently omit contradictory evidence. Existing tokenization enforces
the actual 4,096-token transport ceiling, including schema/output reservations.
Output reserves: 650 chat tokens, 1,250 generic matching tokens; the existing
indicator matching reserve remains 1,550. Actual transport budgeting can abstain
below the character bound. There is no evidence replacement by generated summary.

Short/extended allow 30/50 substantive respondent turns; default generation cap
64; processing-time cap 600 seconds, excluding participant reading time. The
existing transport has bounded repair/transient retries (up to four observable
generation attempts reserved per operation). Extra inference occurs only for
explicit simplification/comparison and bounded reporting: one generic match and
at most two substantively indexed indicator matches. There are never fifteen
calls per turn. Metrics distinguish observed generation counts from unobservable
fixture costs. These are operational settings, not approved methodology.

Generic scoring compares all full PDF anchors against original quotations. It
uses no legacy `citizen_score.admissible()` gates, averaging, automatic
highest-supported rule, trust/acceptance/profession/literacy bonus, or individual
SRL. The same model may interview and score: correlated errors are possible and
this is not independent validation. Uncertainty, opportunity, proposed capability,
real activity, demonstrable effect, scope and sustained processes remain distinct.

At reporting, v4 indicator matching admits explicit `respondent_provided` evidence
through an added contract; no fake `indicator_confirm` or `confirmed=True` is
manufactured. Matching uses all scoped originals or abstains on budget. The
legacy contract still requires its existing confirmed evidence. The relevance
map is not an automatic score: mentions are indexed, unsupported/unvisited topics
remain unmatched. Hidden indicator projections are always individually unreviewed.

## Data and remaining facilities

Sessions, feedback and pending review are in memory only, subject to existing API
TTL/max-age. Download before leaving; no cross-day resume or durable review queue
is implemented. Snapshot-saving code from `80ccba0` is preserved but unwired;
no Save button, database migration or training export is added. New exports set
`training_eligible=false`. Synthetic classification comes from the trusted fixture
factory or the isolated server setting `IAM_CHAT_SYNTHETIC_REHEARSAL=1`, never a
browser-supplied classification. Other sessions are labelled unverified/unlabelled,
not assumed authentic participants. Optional assisted entry (`/chat?assisted=1`)
records facilitator-entered respondent words, not invented answers.

No approved separate contact form is configured: contact follow-up is unavailable,
email is not requested in chat and normal privacy screening still applies.
Only English has been implemented/tested. There is no voice input or claimed
multilingual validation. FN/DMP owners must settle permissions, retention,
review ownership, withdrawal of externally downloaded copies and any later
storage/contact facility before a partner pilot.

For shared devices: explain the study and assistance, use the participant's chosen
capacity, type only their words with assisted entry, offer download, then use
End and clear session before the next respondent. Do not share a live session URL
or cookie. A readable link accompanies any QR. A future paper/facilitated
non-digital pathway needs project design; QR alone does not provide it.

## Isolated local review commands (Liono)

Use free review ports, leaving production processes running. The existing model
endpoint is `http://127.0.0.1:18000`; verify it first:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
curl -fsS http://127.0.0.1:18000/v1/models
```

If that endpoint is unavailable, the chat cannot provide live model responses.
The implementation task does not restart vLLM. To run an isolated synthetic live
review API (no real participants), in one terminal:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src IAM_BASE_URL=http://127.0.0.1:18000 \
 IAM_CONVERSATION_CORPUS=references/private/conversation-corpus-scenarios-v01.json \
 IAM_CHAT_SYNTHETIC_REHEARSAL=1 IAM_SRA_API_PORT=8015 IAM_SRA_UI_PORT=5015 \
 .venv-api/bin/python -m gunicorn --config configs/gunicorn_api.py \
 'iam_sra.api:create_app({"SESSION_COOKIE_NAME":"iam_sra_chat_review_owner"})'
```

Build and serve the isolated UI in another terminal:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
export PATH="$PWD/.runtime/node/node-v22.23.3-linux-x64/bin:$PATH"
npm --prefix app run build -- --outDir ../.runtime/chat-review/dist --emptyOutDir
cp app/serve_app.py app/proxy-routes.json .runtime/chat-review/
IAM_SRA_UI_PORT=5015 IAM_SRA_API_TARGET=http://127.0.0.1:8015 \
 .venv-api/bin/python .runtime/chat-review/serve_app.py
```

Open `http://127.0.0.1:5015/chat`. Each browser receives its own owned session;
there is no shared demo session. For a browser on another machine, use the
existing authorised SSH access to forward this review port. This is a local
preview, not a phone-accessible public origin.

For Vite instead of the static server, use a free UI port with the same configured
API allowed origin:

```bash
IAM_SRA_UI_PORT=5015 IAM_SRA_API_TARGET=http://127.0.0.1:8015 npm --prefix app run dev
```

Fixed authored rehearsal through the sibling evaluator adapter, without an agent:

```bash
.venv-api/bin/python scripts/rehearse-chat.py --api-url http://127.0.0.1:8015 \
 --allow-live --case detailed_multitopic --output .runtime/chat-live-rehearsal-1
```

Omit `--case` for the seven-case suite. Existing output directories are rejected,
so failed rehearsals are preserved. Reports are screened API exports; scripted
answers are authored synthetic facts, never claimed human responses. This CLI
session does not appear in the normal browser UI because it has a different owner
cookie; the actual browser chat can be watched directly when used in the browser.

No canonical `PUBLIC_CHAT_URL` is configured in this checkout. QR setup is
incomplete until an authorised reachable origin exists. Generate locally after
configuration (do not put secrets/session IDs in the URL):

```bash
.venv-api/bin/python -m pip install -r requirements-chat-tools.txt
PUBLIC_CHAT_URL=https://YOUR-AUTHORISED-HOST/chat \
 .venv-api/bin/python scripts/chat-qr.py --output .runtime/chat-entry
```

The QR encodes the ordinary `/chat` URL, and a readable link is written beside the
SVG. No external QR service, deployment or public tunnel is created.
