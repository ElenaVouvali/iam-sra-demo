# Synthetic respondent agent before FN review

The existing `scripts/smoke-fn-interview.py` now supports `--respondent agent`.
It reuses `LLMRespondent` and the current Flask API/controller/Qwen transport.
No agent framework, new model service or dependency is introduced.

The agent receives its fictional persona, the current displayed question/options
and the last six visible messages. It does not receive internal coverage goals,
reference answers, expected scores or evaluator instructions. It answers actual
follow-ups rather than matching example answers. Choice questions require one
of their displayed values; other questions remain natural language. The existing
guided JSON, privacy screening and bounded context remain in use.

`eval/fn_agent_personas_v1.json` contains four independently authored fictional
cases, distinct from the registered FN examples:

| Flow | Synthetic situation and human review focus |
| --- | --- |
| Citizen short | Unfamiliar with drones; accepts an explanation; noise and wildlife concerns; no participation opportunity. Check prior knowledge versus supplied information and opportunity versus capability. |
| Citizen extended | Attended a fictional consultation and made suggestions, with no confirmed decision change. Check participation versus influence and deeper evidence/alternative/accountability probes. |
| Organisation | Hospital logistics planning unit with draft requirements, unapproved resources and no tested pilot. Check remit, drafts versus adoption, testing and routine integration. |
| Technology | Container component v0.3, controlled thermal tests, untested flight/interfaces. Check component scope, exact configuration, environment and remaining limitations. |

Profile, broad city and citizen depth are scripted administrative setup. Qwen
generates substantive replies from the persona. Summary continuation and final
review are explicitly automated: the runner chooses **E (uncertain)**, or a
non-numeric uncertainty comment after abstention, and finishes without additional
facts. It never treats same-model agreement as independent respondent validation.
The original provisional suggestion must remain unchanged.

The real-privacy rehearsals also found application faults outside inference:
echoing a city in its acknowledgement could be misread as a person's name;
generated scale IDs and the complete fixed A–E review prompt could also be
misclassified. The acknowledgement now avoids repeating the city while retaining
its context. Only exact bounded scale IDs in reference fields and exact
controller-owned review messages in server message locations are treated as
metadata. Answers, quotations, altered prompts and appended personal data still
undergo mandatory screening. Canonical FN questions, review labels, PDFs and
registered hashes are unchanged. Restart the API/sharing launcher to load these
backend fixes after saving any temporary interview.

## Run on Liono

Export any current interview and stop the **FN sharing launcher** with Ctrl+C
first. Its idle watcher must not run during this separate model benchmark: it
does not see the respondent agent's direct model requests. Agent mode refuses
an active review lock instead of stopping or adopting that service.

Use your normal Liono terminal with GPU/network access, and an available A2:

```bash
cd ~/IAM_CC/iam-sra-demo
# Only needed if the selected pinned checkpoint is not already complete:
IAM_MODEL_VARIANT=awq .venv/bin/python scripts/download-model.py
python3 scripts/model-host.py start liono-a2 --variant awq --port 18003

IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --respondent agent --model-variant awq \
  --base-url http://127.0.0.1:18003 --case all \
  --output .runtime/fn-agent-review-1

# After the benchmark, including a failed run, release your supervised model:
bash scripts/stop-vllm.sh
```

Use a new output directory each time; old reports are never overwritten. Start
with `--case citizen_short` instead of `all` for a smaller first run. Use
`--model-variant fp16` only with the corresponding original-model endpoint.
Neither test mode starts, stops or restarts a model or participant API. The
standalone launch above holds the A2 until you stop it after testing.

Restore the browser review link afterwards, using the normal on-demand launcher:

```bash
.venv-api/bin/python scripts/share-fn-review.py --idle-seconds 60
```

It prints a new FN URL and retains idle GPU release. The agent benchmark itself
uses **isolated in-process Flask APIs**, with actual owner cookies, CSRF,
versioned actions, job polling, controller transitions, interpretation and
scoring. It does not create sessions in the participant API. It does **not**
click through Vue, verify public-link uptime or test browser layout.

## Read the results

The output directory contains:

- `summary.md`: protocol completion and failures by flow.
- `metrics.json`: score/abstention/review status, methodological coverage, gaps,
  fallback frequency, generation calls and timings. Interviewer and respondent
  calls/timings are reported separately.
- `<flow>.json` and `<flow>.jsonl`: normal screened API exports.
- `<flow>.md`: readable screened transcript, including disclosed scales.

All records are synthetic and never Living Lab evidence. Rejected model output
is not logged. Failed runs keep their screened partial exports. A missing or
wrong model endpoint produces exit code 2 and a zero-interview availability
report, not fabricated model results. Private-source/privacy failures remain
failures rather than being replaced with invented sources or answers.

Exit code 0 means protocol checks passed: the interview ended without operational
failure or partial termination, applicable stages were explored, the full
nine-level scale and review were reached, the score is suggested or honestly
abstained, JSON/JSONL exports succeeded and review did not overwrite the initial result.
It does **not** establish semantic correctness, persona fidelity, justified
scores or FN approval. These remain explicitly pending human review even after
a successful run. The same Qwen acting as both respondent and interviewer can
share biases.

Long generated answers can exceed the existing bounded scorer context. In that
case the application may abstain before making a scoring request. Inspect the
exported suggestion's gaps and the `generic_profile_match` observable metrics;
do not count an abstention as a successfully exercised numeric judgment. The
runner never truncates evidence or forces a level to make the test pass.

Operational bounds default to 100 submitted turns, 60 respondent generation
calls and 3,600 elapsed seconds per case. They stop testing loops and do not
determine interview readiness. Repeated identical questions and interpretation
failures stop the case. Generating a respondent answer adds model calls, so this
benchmark is more expensive than replaying fixed source answers.

Use the existing reference mode separately to check FN question/branch fidelity:

```bash
IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --respondent reference --model-variant awq \
  --base-url http://127.0.0.1:18003 --case all \
  --output .runtime/fn-reference-review-1
```

Run this before stopping the standalone model. Agent mode tests adaptability;
reference mode checks the supplied source path. Neither has target score labels.

## Thinking mode

The default remains **off** with a 4,096-token context. An experimental coordinated
`--thinking` A2/AWQ profile now configures the vLLM reasoner, separated response
channels, 8,192-token context and larger output reservation. See
[thinking integration, observed failures and live publication checks](fn-thinking-harness.md).
The pinned vLLM 0.8.5 has documented reasoning-parser versus non-thinking
compatibility limitations; every client of a thinking endpoint must use the
same mode. Real A2 compatibility, latency and semantic improvement still need
host-run verification.

Most reference-path questions are controller-owned FN wording, so extra model
reasoning would not automatically make those questions more conversational.
First inspect live agent failures and exact respondent evidence. A separate
controlled comparison could then assess complex interpretations, false
clarifications, evidence validity, fallback rate and response time before any
default is changed. No claim is made here that thinking improves this interview.

Sources: [Qwen3 modes](https://huggingface.co/Qwen/Qwen3-8B-AWQ#switching-between-thinking-and-non-thinking-mode),
[Qwen vLLM deployment and parsing](https://qwen.readthedocs.io/en/latest/deployment/vllm.html#parsing-thinking-content).

## Automated verification

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_fn_agent.py \
  tests/test_fn_interview.py tests/test_fn_onboarding.py \
  tests/test_fn_interpretation.py tests/test_chat_choices.py \
  tests/test_model_timeouts.py tests/test_adaptive_conversation_v12.py \
  tests/test_fast_a2.py
```

Controlled-model API tests prove all four paths, automation labels, unchanged
results after uncertainty review, transcript/report exports, privacy, operational
bounds and failure handling. They use reference-response doubles and do not
measure actual persona interpretation by Qwen. Real-detector tests screen the
new persona content and complete controlled API reports without privacy bypasses.
This execution environment cannot access the NVIDIA driver or the live model
endpoint; actual live completion, answer quality and timing must be recorded
using the commands above.

## Verification record, 24 November 2026

Final focused runs passed **445 distinct Python checks**: 355 existing FN/API/
conversation checks, 63 existing privacy checks and 27 agent checks. Counts are
deduplicated across overlapping runs. The complete four-flow owned-API test with
real privacy screening passed in 721.78 seconds. All four ended with uncertainty
review, preserved their original suggestions, and produced JSON, JSONL and
readable transcripts. Model responses in this test were controlled doubles;
the fixture score is arbitrary and proves transport/state handling only.

The first real-detector run exposed the city acknowledgement, scale-ID and fixed
review-prompt issues described above. A separate fixture issue cut `vans` to
`van`, producing a spurious name detection; test quotations now end at word
boundaries while the complete original FN answers remain unchanged. Markdown
is rendered from the screened semantic record, preserving approved control-text
provenance instead of treating its formatting as new participant prose.
Negative tests verify that personal data and modified/embedded control text
are still rejected. All 166 controlled response annotations separately passed
real screening. One upstream spaCy/Click deprecation warning remains.

The controlled report and transcripts are retained under ignored
`.runtime/fn-agent-controlled-20261124-1/`. They are not live-model results.
Read-only checks could not reach the model at ports 18003 or 18002, and
`nvidia-smi` could not access the driver in this execution environment. An actual
agent-mode launch attempt exited before inference because the existing FN
sharing lock was active. No model was started/stopped, no production interview
was used, and no service was restarted. The four registered PDF hashes and
extracted-rubric hash match their original register. Model pins, dependencies,
thinking settings, scales and the existing frontend build remain unchanged.
