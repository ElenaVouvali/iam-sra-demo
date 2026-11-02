# Simplified Vue onboarding review

Starts from clean `feature/indicator-assisted-self-assessment` at
`51ad9341ac7b697fc98bc802126663fa14962b42`. This focused change updates the two
Vue assessment components, their browser checks, direct-entry/scope API mappings
and focused API/domain regressions. The alternative general conversation stays
collapsed and retains its controller flow, with an optional withheld role.
Streamlit's existing interface and historical API callers remain supported.
Nothing changes the v4 bank, questionnaire, suggestion policy, model service or
aggregation. Existing services and deployment assets are not replaced.

The first screen uses ordinary language and explicit general/service/example
choices. General discussion requires no service name or deployment. Its label is
derived transparently by Python and separately identified in scope provenance.
Examples show source status and significant unknowns before starting and remain
information exposure. Specific organisational responsibilities and technical
objects are confirmed later per indicator. Review, corrections, invalidation,
partial results and screened downloads follow the existing shared controller.
See [the additive API mapping](iamcc-api-contract.md#simplified-onboarding-explicit-discussion-choice).

Changed files:

- UI: `app/src/components/IndicatorAssessment.vue`, `app/src/tools/sra-assessment.vue`.
- Shared mapping: `src/iam_sra/conversation_session.py`,
  `src/iam_sra/api/schemas.py`, `src/iam_sra/api/adapter.py`.
- Focused checks: `tests/test_indicator_api.py`, `tests/test_questionnaire_v02.py`,
  `app/tests/pages/sra-assessment.mjs`.
- Documentation: `docs/iamcc-api-contract.md`, this note.

## Isolated review commands

Use separate review ports 8006/5006 after checking they are free. These commands
use existing environments and the already established model service. They do not
restart vLLM, rebuild `app/dist`, or replace the running deployment. To restart
one of these foreground review processes, press Ctrl+C **in its own terminal**
and repeat that terminal's command. Restarting the API loses its temporary
review sessions; download results first. The separate cookie avoids colliding
with the deployed application's browser ownership cookie.

Terminal 1, review API:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src IAM_BASE_URL=http://127.0.0.1:18000 \
  IAM_CONVERSATION_CORPUS=references/private/conversation-corpus-scenarios-v01.json \
  IAM_SRA_API_PORT=8006 IAM_SRA_UI_PORT=5006 \
  .venv-api/bin/python -m gunicorn --config configs/gunicorn_api.py \
  'iam_sra.api:create_app({"SESSION_COOKIE_NAME":"iam_sra_onboarding_review_owner"})'
```

Terminal 2, rebuild and start/restart only the review UI:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
export PATH="$PWD/.runtime/node/node-v22.23.3-linux-x64/bin:$PATH"
npm --prefix app run build -- --outDir ../.runtime/onboarding-review/dist --emptyOutDir
cp app/serve_app.py app/proxy-routes.json .runtime/onboarding-review/
IAM_SRA_UI_PORT=5006 IAM_SRA_API_TARGET=http://127.0.0.1:8006 \
  .venv-api/bin/python .runtime/onboarding-review/serve_app.py
```

Open `http://127.0.0.1:5006/tools/sra-assessment/app` on liono, or forward port
5006 over SSH. The expanded private corpus already exists in this checkout;
source packages and generated data remain ignored.

## Targeted verification

Completed on 21 October 2026. Counts below overlap; they are not a combined
test total. Browser verification used the existing isolated Firefox 157.0.1 with explicit synthetic
inference/detector fixtures on test ports 18005/5005, never the production model.
This change needs no new inference call or large evaluation.


| Check | Actual result |
| --- | --- |
| Frontend build into `.runtime/onboarding-review/dist` | Passed, 55 modules; final help-copy rebuild also passed |
| Focused onboarding, service stages, general/example provenance, privacy previews, invalidation and legacy-input checks | 25 passed, 46 deselected; 20.67 s |
| Existing direct-profile/API scope, stale-job and Streamlit onboarding-preview compatibility checks | 14 passed, 61 deselected; 17.66 s |
| All 45 module mappings plus invalid/missing direct scope checks | 10 passed, 28 deselected; 1.25 s |
| Existing installed Presidio integration test | 1 passed, 52 deselected; 2.05 s |
| Additional general onboarding and screened export with real installed AnalyzerEngine | All three profiles passed, synthetic source fixtures; no inference |
| New browser onboarding flow | Passed general entry for all profiles, unresolved/no-object states, proposed/existing services, cleaned preview choice preservation, visible example status/unknowns, reload and collapsed alternative route |
| Existing direct browser journeys | All three profiles passed later scope confirmation, interpretations, participant review, continuation, restoration and JSON/JSONL downloads |
| Existing authored legacy browser journey | Passed interpretation correction, sourced information/reflection, indicator continuation and downloads |
| Layout and visual inspection | 360/1200 px page checks passed; actual setup at 360 px passed overflow assertion and screenshot inspection |
| Python compilation, browser-test syntax, `git diff --check` | Passed |
| Documented Gunicorn review factory with separate cookie | Resolves successfully |
| Existing model-list endpoint, 127.0.0.1:18000 | Qwen/Qwen3-8B responds; no generation requested |

Commands used:

```bash
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q tests/test_indicator_api.py tests/test_questionnaire_v02.py -k 'onboarding or direct_scope or particular_service or cleaned_preview or changed_general_discussion or missing_or_incompatible_discussion or new_free_text'
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q tests/test_indicator_api.py tests/test_questionnaire_v02.py tests/test_indicator_ui.py -k 'direct_profile or keyword_onboarding or invalid_direct or missing_or_incompatible or scope_edit or late_suggestion'
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q tests/test_questionnaire_v02.py -k 'all_45_exact_module_mappings or invalid_direct_scope or missing_or_incompatible'
PYTHONPATH=src:tests .venv-api/bin/python -m pytest -q tests/test_privacy.py -k pinned_presidio_integration_when_installed
```

Browser runs used the existing harness, for example:

```bash
PATH="$PWD/.runtime/node/node-v22.23.3-linux-x64/bin:$PATH" \
  ONLY=sra-assessment FLOW='simple onboarding' WIDTHS=360,1200 \
  BASE=http://127.0.0.1:5005 \
  FIREFOX="$PWD/.runtime/browser/firefox/linux-stable_157.0.1/firefox/firefox" \
  SHOTS="$PWD/.runtime/onboarding-review/shots" npm --prefix app run check
```

The same command with `FLOW='direct '` exercised three existing profile flows;
`FLOW='complete authored synthetic interview'` exercised the legacy route.
Those two selections used `WIDTHS=360`. Test services used the documented
`api_browser_fixture:create_fixture()` factory on 18005 with
`IAM_SRA_UI_PORT=5005`, and the isolated static proxy on 5005. They were stopped
after verification. The running deployment, existing review services, model,
GPU allocation and environments were not restarted or altered.

Two test issues were diagnosed and fixed without changing application routing,
privacy or assertions: identical city labels needed a selector scoped to the
alternative form, and the frozen legacy interview needed to explicitly choose
its authored scenario after the prior scenario expansion changed the default
sort. A first sandboxed test-server bind was denied by the environment; the same
isolated service ran with explicit tool approval. There are no remaining failures
in the targeted checks. These checks establish flow and privacy compatibility,
not matching accuracy or methodological validation. No large evaluation or live
model generation was run. No commit, push, merge or deployment was performed.

## Follow-up: real-bank module-ID privacy false positive

The review UI subsequently exposed a real-source difference absent from the
synthetic question fixtures: v0.2 questions include `anchor_context_module_id`.
The installed spaCy recognizer classifies `indicator-01-crl` as PERSON, so API
presentation rejected the first indicator after successful input screening.
This was an application metadata-boundary defect, not private respondent input
or a model generation failure. Earlier real-detector checks used synthetic banks
without this field and therefore did not establish real-questionnaire API success.

The repair recognises only the 45 exact indicator/profile module-ID encodings
in `module_id` and `anchor_context_module_id` reference fields. The same strings
in answers/quotations are still screened, as are names, contacts, credentials,
arbitrary IDs or appended text in reference fields. Questionnaire validation now
checks each anchor-context reference against its own validated module. Synthetic
question fixtures include the field to retain this regression. Source content,
hashes, matching rules and the detector remain unchanged.

Follow-up checks: 12 targeted module/privacy/mapping/direct-API tests passed
(115 deselected; 15.99 s), including the real pinned detector regression; 21
existing and new metadata/secret/privacy invariants passed (34 deselected;
1.91 s). Independent real-bank/corpus/detector checks presented all 15 citizen
indicators and produced a screened API export successfully, without inference.
API job and both download checks are recorded after their completion below.
The fix is backend-only: restart the foreground review API on 8006 using its
existing command; keep the UI on 5006 and Qwen on 18000 running. This restart
clears only that review API's temporary sessions. Refresh the browser afterward.

The follow-up default API factory check also passed with actual jobs, the real
private bank/corpus and installed detector: general citizen entry displayed the
first questionnaire item, JSON and JSONL downloads succeeded, and its temporary
owned test session was deleted. This used an in-process Flask client, no fixture
inference or privacy backend and no model generation. No running service was
restarted by the agent.

## Focused second-screen simplification

The direct interview now leads with “A few questions”, a plain presentation-only
topic title, compact progress and the unchanged source question. Answer controls
are Continue, Skip and I’m not sure. Refusal and early topic completion remain
available under More answer options. Methodology/source names, profile/scope,
optional cases and full topic navigation are collapsed; active supplied cases
remain visible. Technical scope confirmation stays available for its profiles.
Interpretation details are collapsed while the meaning and explicit confirmation
remain visible. A reviewed topic offers Next topic; Finish for now produces the
existing partial report. Downloads are collapsed during the interview and open
with the final report. No questionnaire wording, eligibility or assessment logic
changed, and the duplicate setup/review badges were removed on the direct path.

Rebuilt only `.runtime/onboarding-review/dist` (55 modules; build passed), which
is already served by the user's review UI on 5006; no service restart or deployment
replacement was performed. A separate browser-owned session against that real
review UI passed desktop/mobile display, collapsed technical details and topic
list, unchanged displayed source question, Skip, partial finish and cleanup.
No model generation was requested. Screenshots were inspected; browser check
syntax and `git diff --check` passed. A focused reusable second-screen flow was
added to the existing browser harness; the earlier profile flows' control labels
and explicit disclosure navigation were updated, but those full flows were not
rerun for this presentation-only follow-up. Two initial temporary check-script
imports used the wrong local Puppeteer layout; correcting the script resolved
that test-environment issue without changing application behaviour.

The final layout also removes the nested results-card frame and places context
and technical topic help below the answer, so the question comes first. This
last layout adjustment rebuilt successfully; the browser flow check above was
run before that ordering/padding adjustment.

## Simplified setup and Back navigation (2 November 2026)

The first screen no longer offers broad-area/role fields or the alternative
conversation disclosure. The omitted role retains its existing withheld value;
city, capacity, discussion choice and optional self-report controls remain.
Existing conversation sessions and API callers retain their routes.

Back is disabled on the first setup screen. On the first topic it reopens scope
setup; canceling that screen returns to the topic. Later steps use the screened
`indicator_back` action: a pending interpretation returns its answer for editing,
level review returns to interpretation review, and completed results reopen level
review. Reopening evidence archives dependent judgments through the existing edit
and invalidation paths. A new topic can return to the previously visited topic;
returning from the report preserves recorded choices. Privacy-preview Back discards
the preview through the existing recovery action. No inference call is added.

The review API must be restarted to load the new action (temporary sessions are
lost on restart; download any needed reports first). Rebuild the review UI using
the commands above, then refresh the browser. The model service needs no restart.
