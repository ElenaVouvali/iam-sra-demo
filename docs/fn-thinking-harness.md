# FN thinking profile and live publication checks

This refines the existing FN harness; it adds no orchestration dependency or
parallel questionnaire. Default inference remains non-thinking. The opt-in A2
AWQ profile is experimental until the live tests below pass on the actual host.

## What the submitted live run found

The preserved `.runtime/fn-agent-review-1` contains four incomplete interviews;
none reached scoring. Short citizen, organisation and technology failed the
response contract. Extended citizen failed privacy before that turn's inference.
The three contract failures ended with `stop`, not output truncation/timeouts.
Old diagnostics retained only `field=response`, so their exact rejected JSON
cannot be reconstructed. Rejected output was deliberately not retained.

The extended failure was reproduced with the real detector/private corpus.
Retrieval joined the current answer with previous evidence, including the city,
into new prose. That combined query triggered PERSON although the individual
answers passed. Retrieval now ranks the actual screened answer; city, priorities
and previous exchanges stay in separate structured fields. No detector rule or
privacy check is bypassed, and retrieved records remain screened/source checked.

Contract handling now accepts exact original-answer-length quotations, with the
existing substring/active-ID/allowed-objective checks. Invalid optional topic
hints are discarded with diagnostics; invalid core interpretation still fails.
Safe field locations/types now identify schema failures. Unused model wording
when Python advances no longer falsely counts as a question fallback. The
respondent agent is reminded to preserve unknown facts as uncertainty and not
reselect its profile in response to an ordinary role/context question. Persona
consistency remains a human review task, not guaranteed by that instruction.

## Structured output, context and thinking

The harness includes prompt construction, grounded evidence memory, structured
decoding, validation, controller routing, retries, scoring and review. Internal
JSON lets Python distinguish an interpretation, evidence citation and transition
proposal from participant-facing prose. Removing it would remove those checks.
It is not a visible participant questionnaire or a model training technique.

Context is the token capacity shared by instructions, selected evidence and the
generated response. Authoritative screened originals remain in session/export
memory even when not selected for an interview prompt. Scoring supplies **all**
active originals and all nine anchors or abstains/fails honestly; it never drops
evidence to obtain a numeric result. Thinking mode removes the old coarse
5,000-character scoring guard and lets exact tokenization enforce its larger
budget. Non-thinking behaviour is retained.

`IAM_MODEL_THINKING=1` coordinates:

- Existing pinned Qwen3-8B-AWQ, zero CPU offload, V0/XFORMERS, one sequence.
- vLLM 0.8.5 `--enable-reasoning --reasoning-parser deepseek_r1`.
- 8,192 context tokens and 1,536 extra output tokens by default; this is a
  combined generation reservation, not a forced reasoning cutoff. If the model
  uses it all before valid JSON, the answer is rejected as truncated.
- Matching `enable_thinking=true` for tokenization and generation; temperature
  0.6, top_p 0.95, top_k 20. Do not mix non-thinking clients with this endpoint.
- Separated `reasoning_content` is discarded immediately. It is never placed in
  the UI, cache, export, evidence, retry prompt or developer trace. All delivered
  fields still undergo privacy/evidence/schema checks. Think tags in final JSON
  are rejected. Exports/metrics retain mode, budgets and reasoning character
  counts, not thought text.

`IAM_MODEL_REASONING_TOKENS` may reserve 512–4,096 extra tokens. Increasing it
reduces the remaining prompt budget and increases possible latency. A2 VRAM fit,
end-to-end speed and interpretation benefit must be measured live; thinking is
not a speed fix or an assured improvement. No dependencies/checkpoints were
upgraded and no source PDF, source hash, FN scale or v4 statement changed.

For an audit, the model can return `decision_summary`: a brief interpretation
and evidence limit, not raw deliberation. Existing authenticated developer
traces expose that justification, accepted/rejected actions, exact evidence IDs
and controller postconditions. Enable only in a private development API with
`IAM_CHAT_ENV=development`, `IAM_CHAT_DEV_TRACE_ENABLED=1` and a private
`IAM_CHAT_DEV_TRACE_TOKEN` of at least 32 characters. The existing
`GET /v1/dev/sessions/<session-id>/trace` requires that token as Bearer auth.
It remains disabled by default and is not a participant reasoning display.

## Run from Liono's normal terminal

Save any current interview download, then Ctrl+C the **existing sharing launcher**
in its terminal/tmux. An independent benchmark refuses to race its idle watcher.
Do not kill processes just because they own a port.

```bash
cd ~/IAM_CC/iam-sra-demo
# Build if source changed; use the existing Node environment.
cd app
npm run build
cd ..
tmux new -s iam-sra-check
.venv-api/bin/python scripts/share-fn-review.py --thinking --validation-only
```

If the script identifies an old always-on **project A2 review model**, its
existing `--release-existing-a2` option explicitly releases only that verified
model. Do not add it to preempt someone else's GPU work. Busy A2 means retry later.
The new check starts an owned model only when A2 is available; no public API or
tunnel opens during validation. Ctrl+C stops its child and releases its owned
model. It runs all four agent cases through the real isolated Flask API, real
model interpretation and scoring, full scale, review and JSON/JSONL export.

The publication gate requires actual interviewer/respondent/scoring calls,
complete non-partial journeys, no interpretation failures, preserved initial
judgment after review, and evidence/boundary checks for numeric suggestions.
Honest model abstention may complete review, but a pre-model abstention cannot
pass as a scoring call. Thinking tests also require separated reasoning to have
been observed. Controlled fixtures are rejected. This proves execution and
grounding contracts, not independent judgment accuracy or FN approval. Inspect
each transcript/persona/result before official review.

For a standalone model, without a sharing launcher:

```bash
.venv-api/bin/python scripts/model-host.py start liono-a2 --variant awq --thinking --port 18003
IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=1800 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --respondent agent --model-variant awq --thinking --require-scoring \
  --base-url http://127.0.0.1:18003 --case all --case-timeout-seconds 7200 \
  --output .runtime/fn-thinking-agent-review-1
```

Use a fresh output directory on every run. This direct model-host command is
always-on; it has no automatic review idle release. Prefer the validation-only
launcher when the GPU must be released automatically after tests.

## A readable public address

No named Cloudflare configuration was found in the current user's home. That
does not establish whether the institution can supply a hostname. Ask Microlab
or IAM-CC's IT/web administrator for **an approved public HTTPS name for the
IAM-SRA research application on Liono**, with a reverse proxy to its loopback
frontend (for example port 5018) over an approved route. Proxy the whole app,
including `/api/sra-assessment/`, and allow long-running research requests.
The administrator must configure DNS, TLS and routing. An SSH hostname alone
does not establish a public web service or permission to create subdomains.

After that setup, replace the example origin with the address actually provided:

```bash
.venv-api/bin/python scripts/share-fn-review.py --thinking \
  --ui-port 5018 --public-origin https://iam-sra.example.org
```

This runs the live gate, then starts the original Vue/Flask stack without a Quick
Tunnel, verifies public HTTPS/API/cookies/CSRF, and only then prints the real FN
link ending `/iam-sra-fn-review`. It does not create DNS or a proxy. Without
`--public-origin`, Cloudflare issues a random temporary hostname; a descriptive
path does not make that hostname stable. No clean working address is invented.
After validation the model returns to the existing 60-second on-demand release
policy, so an idle website does not keep Qwen loaded.

Validation-only mode does not require a frontend build or check frontend/API
ports. It retains the exclusive sharing lock and exact GPU ownership guards.
If another sharing launcher holds that lock, it reports the conflict explicitly
and leaves the existing service/link untouched. Host-enforced GPU/network
restrictions still require execution from an appropriately permitted host session.

## Verification status

Offline transport/controller/security tests include separate reasoning channels,
private final-output rejection, budget overflow, exact long quotes, optional
metadata, real-corpus privacy reproduction, all four canonical replays, score
evidence preservation, publication-gate rejection of fixtures/missing calls and
review state. The Vue build is checked separately. These do not prove GPU fit.

Run the focused controller/transport/golden/privacy checks from the repository:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q \
  tests/test_fn_thinking.py tests/test_fn_interview.py tests/test_fn_onboarding.py \
  tests/test_fn_interpretation.py tests/test_transport_recovery.py \
  tests/test_model_lifecycle.py tests/test_fn_review_link.py
cd app
npm run check:chat
npm run build
```

On 24 November 2026 live preflight refused an active sharing lock, preserving
the existing service. The agent execution environment also cannot access the
NVIDIA driver or open the model's loopback connection. No new live interview or
public link was verified here. Run the host commands above; failed validation
leaves reports and withholds the FN link. Actual semantic deviations, fallback
frequency, latency and score outcomes remain pending those runs.

Final offline verification: **581 Python tests passed** in the affected
FN/chat/API/privacy/model/sharing suite. One long legacy meeting/privacy replay
was excluded from that final rerun after already passing in the earlier broad
run. The two failures in that earlier run (a test fixture below its intended
size and an overbroad unused-wording filter) were corrected and passed again.
All four canonical FN replay cases passed. The separate chat component tests
passed **18/18**, and the Vue production build passed with **58 modules** using
the available Node v24.22.1. The package declares Node 22; the declared-version
build was not separately run here. These are controlled checks, not live Qwen
results. Saved logs and execution limitations are in the ignored
`.runtime/fn-thinking-verification-20261124-1/` directory.

Sources: [Qwen/vLLM modes and parser compatibility](https://qwen.readthedocs.io/en/latest/deployment/vllm.html),
[vLLM 0.8.5 reasoning outputs](https://docs.vllm.ai/en/v0.8.5/features/reasoning_outputs.html),
[Cloudflare Quick Tunnel hostname limitations](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
