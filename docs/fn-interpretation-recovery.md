# Citizen interpretation and technical recovery

The reported definition and list of drone uses are the short FN PDF's example
answers. Their repeated clarification was an error path, not evidence that the
respondent lacked knowledge.

## Reproduced causes and changes

The actual installed privacy detector labels `JSON` and `Mark` in the previous
chat instructions as PERSON. Screening those server instructions therefore fails
before tokenization or generation. The replacement FN prompt avoids that wording;
screening remains mandatory. The rehearsal report's old classification string
also triggered PERSON and was replaced with `synthetic` plus explicit boolean
provenance fields.

`chat_client.py` now uses a smaller FN response contract: grounded interpretation,
optional question wording, scoped facts and source references. The prompt focuses
on whether the current answer addresses the current question. It does not grade a
definition against all later readiness capabilities. The current answer remains
complete; bounded context, exact-quote checks and the 4096-token budget remain.
Prompt revision: `fn-adaptive-interview-1.0.0:interpretation-v2`.

Valid interpretation survives rejected optional wording. Python selects the next
canonical question after accepted coverage. A genuinely ambiguous answer can
still receive one relevant follow-up. Invalid quotations, unknown evidence IDs
and missing required interpretation trigger the existing bounded retry; they
cannot become coverage. Empty-answer rephrasing/comparison requests retain their
separate wording task and do not fabricate respondent evidence.

Admitted uncertainty/refusal is recorded consistently as unknown/declined rather
than substantive coverage. A negative answer may still mean a question was
explored: saying no examples come to mind supplies no examples and demonstrates
no knowledge by itself. The recorded answer kind and original words remain
separate from coverage and any readiness judgment. Live checks test that
distinction, not coverage status alone.
Internal goal identifiers such as `drone_uses` are discarded as topic labels
unless the respondent actually used that label. This does not exclude emerging
themes such as wildlife or impose the fifteen-indicator bank on the interview.

`chat_session.py` retains an answer after technical failure and offers retry,
skip, pause or stop. A second technical failure does not advance or mark the
respondent uncertain. `retry` reuses the original evidence ID and actual question;
resending the identical answer is also idempotent. Changed wording is interpreted
against the actual interview question, not the technical notice. Exports expose
`answer_processing.status`, failure codes, whether inference started and bounded
structural transport diagnostics. Logs contain codes/goals, not answers or raw
rejected model output.

The existing privacy exception for generated `m<N>` references now covers the
actual FN request/response nesting. It applies only to bounded ID syntax in
structural reference fields. Names, answers and quotations still undergo
screening; the client checks referenced IDs against original evidence. Tests
explicitly retain those boundaries, including privacy rejection of unused wording.

## PDF fidelity and regression checks

Both original citizen PDFs were reread, including conditional questions, scales,
validation and interviewer guidance. Their hashes match the unchanged source
register. Neither PDF, the register, exact scales, v4 bank nor canonical question
specification was edited. Golden replay still exercises the complete short and
extended citizen paths, and regression tests preserve organisation/technology
flows and end review. Fixture passes establish integration/fidelity, not live
Qwen accuracy.

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python -m pytest -q \
  tests/test_fn_interpretation.py tests/test_fn_interview.py \
  tests/test_chat_conversation.py tests/test_chat_retrieval.py \
  tests/test_chat_qr.py tests/test_api_integration.py tests/test_transport_recovery.py
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python -m pytest -q \
  tests/test_privacy.py tests/test_baseline_privacy_v2.py tests/test_model_timeouts.py
```

## Actual-model verification

The existing `smoke-fn-interview.py` now checks canonical questions, admitted
coverage and technical failures rather than just reaching a final screen.
`--opening-only` stops before healthcare awareness and performs no scoring.
`--opening-variant all` checks the PDF answers plus independently authored
paraphrases and explicit uncertainty from `eval/fn_interpretation_cases.json`.
These examples are evaluation data, never production matching rules.

Run against the already running Qwen endpoint:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract IAM_SRA_JOB_TIMEOUT=1800 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_CHAT_PROCESSING_SECONDS=3600 \
.venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --base-url http://127.0.0.1:18002 \
  --case citizen_short --opening-only --opening-variant all \
  --output .runtime/fn-opening-qwen-check
```

For complete citizen PDF replays including scoring/review, omit the opening
flags, use `--case citizen_short` or `--case citizen_extended`, and choose a new
output directory for each run. Reports distinguish completion, interpretation
checks, partial results, fallback frequency, model calls and scoring failures.
Illustrative PDF levels are never enforced as target scores.

The optional `--backend cpu --opening-only` runs the same pinned Qwen weights
through the existing Transformers/XGrammar CPU benchmark. A private pipe worker
uses `.venv/bin/python` (or `--cpu-python`), while screening/API/validation stay in
the main `.venv-api` process. No packages, GPU allocation or HTTP service change
is required. It loads FP32 weights, needs substantial available RAM (about 40 GiB
of headroom is sensible), and may take minutes per answer. This checks actual
model semantics but does not verify FP16/vLLM GPU compatibility or speed.

## Retest the browser

Save any wanted download before restarting your API: its sessions are in memory.
In the terminal running your API on 8017, use Ctrl+C and then:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
IAM_BASE_URL=http://127.0.0.1:18002 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
IAM_CHAT_PROCESSING_SECONDS=3600 \
IAM_SRA_API_PORT=8017 \
IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5017,http://localhost:5017 \
bash scripts/start-api.sh
```

Keep the model/tunnel and existing frontend on 5017 running. No frontend rebuild
is needed. Refresh `http://127.0.0.1:5017/tools/sra-assessment/app` and start a new
conversation. Enter A, Madrid, yes, the definition, then the uses. Each clear answer
should lead directly to the next FN question. Repeat with your own paraphrases.
If a technical problem occurs, it should say so and retain the answer for retry;
downloaded diagnostics should reveal whether a model call started.

## Verification record — 23 November 2026

- Chat/API/retrieval/QR/FN/transport regression run: 274 passed. This includes
  full canonical PDF replays, source-hash checks, branches, scales and A–E
  review for both citizen depths and the organisation/technology regressions.
- Dedicated interpretation tests after the final topic/uncertainty change: 31 passed,
  including the real local detector through the complete client/controller path.
- Existing privacy/baseline-privacy and model-timeout tests: 106 passed.
- Actual pinned Qwen, CPU/FP32, full privacy and API job path: the short PDF
  definition/uses passed with 2 generations, 0 fallbacks and no recorded failure
  (391.5 s including setup). Independent paraphrases also passed with 2
  generations and 0 fallbacks (285.1 s). Prompt budgets were 1140–1246 tokens
  plus 1100 reserved output, within 4096. These are opening checks, not complete
  live interviews or readiness-scoring validation.
- Screened synthetic reports remain ignored under
  `.runtime/fn-interpretation-fix-short-cpu-v2/` and
  `.runtime/fn-interpretation-fix-paraphrase-cpu/`. The initial failed CPU check
  was preserved; it recorded a privacy failure and **zero** generation calls.
- The first novice replay exposed inconsistent uncertainty/coverage and internal
  goal IDs appearing as topics. Those outputs are preserved under
  `.runtime/fn-interpretation-fix-uncertain-cpu/` and the subsequent `-v2/` run.
  The checker now inspects answer kind together with coverage and rejects
  invented topic annotations; a negative answer and admitted uncertainty are
  distinct acceptable readings, with no numerical readiness implication.
- The final novice rerun (`.runtime/fn-interpretation-fix-uncertain-cpu-v3/`)
  passed: both answers were recorded as unknown/uncertain, with no topics,
  2 generations, 0 fallbacks and no processing failures (296.8 s including
  setup). The two genuine knowledge gaps remained explicit; no level was
  assigned. Across all five inference runs there were 10 actual generations:
  2 reference, 2 paraphrase, 2 initial novice, 2 intermediate novice and 2 final
  novice. Earlier unsuccessful checks were preserved, not relabelled as passes.
- The actual vLLM probe to `http://127.0.0.1:18002` reported inference unavailable
  from this restricted session (0 cases executed). Davinci DNS also failed here.
  No GPU/vLLM throughput or complete live 20-/35-minute scoring run is claimed.
  The live commands above reproduce those checks from the normal host terminal.

No private source identities, registered hashes, model weights, installed
environments or running model/API/frontend services were modified. CPU inference
used temporary owned worker processes and left no inference service running.
