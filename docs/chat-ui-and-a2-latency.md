# Separate introduction, selectable answers, and A2 response time

The Vue chat now opens on a welcome screen containing the complete existing
FN-adapted introduction, participation rights and privacy link. **Continue to the
conversation** reveals the profile question. This is client-side navigation,
not a new consent assertion, readiness answer, GPU request or interview stage.
Exports retain the original introduction. Existing conversations with respondent
messages resume directly; **New conversation** restores the welcome screen.

Controller-owned A–C perspectives, citizen A/B duration, unfamiliar-citizen A/B
explanation/exit, and profile-specific A–E result validation now provide radio
choices and **Send selected answer**. Nothing is preselected. Choice questions
show only selectable answers; there is no alternate text-reply toggle.
Other questions retain the current open-text composer. Suggestions
and thematic topic lists are not converted into compulsory choice forms.

Each active candidate answer appears only once, inside its selectable card.
Role descriptions appear with their card; the chat bubble retains the question
and non-option guidance. The original complete question remains unchanged in
exports and is displayed once in history after the choice controls disappear.
Open questions are never stripped of lettered examples.

The additive `chat.response_options` field uses existing canonical wording and
controller state. Selection sends the ordinary screened `chat_message` with its
literal choice; the existing controller handles it. Model-generated text cannot
create arbitrary buttons or select a response. Recovery, correction, review
additions and abstentions retain appropriate open-text handling. The PDFs,
registered identities, nine-level scales and scoring logic were not changed.

Citizen depth can be changed during elicitation using the button under
**Privacy, help and conversation options**, or `more detail` / `keep it short`
in an open reply. The existing controller changes the FN flow, retains screened
evidence and covered objectives, and records the depth/source history. The
control is unavailable during result review, where the original scale remains
fixed. The promise to change depth later is therefore retained. This changes
probing depth, not a timed deadline or readiness level.

## Why the current A2 run is slow

Read-only inspection of the existing Liono A2 operational record/log found:

| Observation | Existing run |
| --- | --- |
| Model / dtype | Pinned Qwen3-8B / half precision |
| CPU weight offload | 8 GiB |
| Weight load at 07:03 on 24 November 2026 | 31.014538 seconds |
| Recent generation-throughput samples | About 0.7 tokens/second, one running request |
| Idle release policy | 60 seconds without model requests |

These are existing service-log observations, not a new controlled benchmark.
At 0.7 tokens/second, 150 output tokens take about 214 seconds, before other
processing. Structured interpretation generates evidence annotations as well as
any participant-visible wording. The configured 1,100-token cap is a ceiling;
reducing it blindly can truncate valid structured evidence rather than speed up
an already shorter answer.

The A2 has 16 GB of memory. The current full-precision 8B model plus inference
buffers cannot fit the configured GPU-memory allowance, so the launcher offloads
8 GiB. vLLM documents that offloaded weights are transferred from CPU to GPU on
each forward pass. This is a strong likely steady-state bottleneck; PCIe/CPU/power
profiling has not been performed here. The on-demand policy additionally reloads
weights after idle release. It preserves other users' access but adds cold-start
latency. A longer HTTP timeout prevents premature failure; it does not make
inference faster.

## Practical fixes and trade-offs

**Implemented follow-up:** the FN launcher now defaults to a separate pinned AWQ
artifact with zero CPU offload. See [A2 fast inference](a2-fast-inference.md) for
activation and the explicit limits of offline verification. The observations
below describe the original FP16 run; its weights remain available.

1. **For A2:** evaluate the official 4-bit `Qwen/Qwen3-8B-AWQ` checkpoint with
   weights entirely on GPU and zero CPU offload. The Qwen model card documents
   vLLM 0.8.5+ support. Configure it as a distinct pinned deployment, verify fit
   and backend compatibility, then replay FN semantic/scoring cases before
   adopting it. Quantization changes the numerical representation and may change
   answers; no unmeasured speed or accuracy guarantee is made.
2. **For the existing unquantized model:** use an available A30 or 32 GB
   V100/V100S so weights and buffers fit without CPU offload. A 16 GB V100 has
   the same capacity constraint. The current FN on-demand launcher targets local
   A2; another host requires its corresponding deployment configuration.
3. A longer `--idle-seconds` reduces repeated cold starts but holds the GPU
   longer between answers. The requested **60-second release remains unchanged**.
   Selecting controller-owned answers avoids model calls already; text
   interpretation, clarifications and scoring still need the model.

No model weights, dtype, offload amount, output limits, timeouts or running
services were changed by this UI update. In particular, setting offload to zero
for the current full-precision A2 deployment is not a safe speed shortcut.

Primary references: [vLLM 0.8.5 engine arguments / CPU offload](https://docs.vllm.ai/en/v0.8.5/serving/engine_args.html),
[NVIDIA A2 specifications](https://www.nvidia.com/content/dam/en-zz/solutions/data-center/a2/pdf/a2-product-brief.pdf),
[official Qwen3-8B-AWQ model](https://huggingface.co/Qwen/Qwen3-8B-AWQ).

## Run and verify

```bash
cd ~/IAM_CC/iam-sra-demo/app
npm run check:chat
npm run build
cd ..
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_chat_choices.py \
  tests/test_fn_onboarding.py tests/test_fn_interview.py tests/test_chat_conversation.py
```

`check:chat` compiles the actual Vue component and drives it with Vue's in-memory
renderer and synthetic API snapshots. It tests the welcome transition, radio
selection/submission, optional typed answers, open questions and reset/resume.
It uses existing Vue/compiler packages and Node's test API, with no new testing
dependency. It does not replace real-browser layout or public-network checks.

Export any current interview before restarting its temporary API. Stop the old
review launcher with Ctrl+C, then run the updated launcher inside `tmux`:

```bash
cd ~/IAM_CC/iam-sra-demo
.venv-api/bin/python scripts/share-fn-review.py --release-existing-a2 --idle-seconds 60
```

Share the new printed FN URL. Test the welcome screen, all perspectives, both
citizen durations, the educational exit, and A–E result validation. Verify that
city/description/topic questions remain open-text and that choices do not load
Qwen. All four FN replays retain their canonical order and result review.

The agent environment cannot open browser/server sockets or allocate the GPU.
Actual browser layout, public-link activation, quantized-model inference and
new live-A2 timing were not executed here.

Observed verification for this update: **247** FN/chat regressions (including
all four canonical PDF replays), **137** additional API/interpretation/lifecycle
checks, a targeted back-to-start regression (**385 distinct Python checks**
across these runs), **10** Vue component interaction checks, and the production build
(**58 modules**) passed. The Python groups are disjoint. Real privacy checks
accept the new option metadata and existing introduction. Source PDFs/hashes and
model pins were preserved. No service restart or model replacement was performed.


The duplicate-choice rendering fix passed **16 component interaction checks**
and the production build (58 modules). It changes frontend presentation only;
existing API/model services do not need restarting. Refresh the application to
load the rebuilt frontend. No real-browser layout check was run in this
socket-restricted environment.

The later removal of the optional text-answer toggle passed **18 Vue interaction
checks**, **130 Python onboarding/FN/choice checks** (including all four canonical
replays and real privacy), and the production build (58 modules). The controller
test switches short → extended → short, verifies the actual additional probe,
preserves evidence/coverage, and checks exported depth/source history. Existing
tests keep the scale fixed after result review begins. Vue checks/build used the
available Node 24.22.1; the declared Node 22 runtime was not available here. The
rebuilt frontend needs a browser refresh; no API or GPU restart is required.
