# Faster Liono A2 inference

The existing service log showed FP16 Qwen3-8B with **8 GiB of CPU weight offload**
and recent generation samples of about **0.7 tokens/second**. These are observations
of the old service, not a controlled comparison. Offload transfers weights over
the CPU/GPU connection on each forward pass, which is a likely major bottleneck.

The FN launcher now defaults to the official **Qwen3-8B-AWQ, 4-bit** checkpoint,
Marlin kernels and **zero CPU offload** on Liono A2. The 4,096-token context,
guided JSON, screening, evidence validation, interview progression and scoring
safeguards remain. No additional inference call or dependency is introduced.
Quantization can change answers; this is not a claim of measured speed or
equivalent semantic quality.

## Activate in Liono's normal terminal

Save the current interview export, then stop the old sharing launcher with
Ctrl+C in its terminal. Restart inside your existing `tmux` session:

```bash
cd ~/IAM_CC/iam-sra-demo
.venv-api/bin/python scripts/share-fn-review.py --release-existing-a2 --idle-seconds 60
```

The launcher downloads approximately **6.1 GB once**, using CPU/network only,
before opening the public link. It requires 16 GiB free for an uncached additive
download and 8 GiB runtime disk headroom for AWQ. The original checkpoint is
retained; no cache or environment is deleted. Existing vLLM 0.8.5 and PyTorch pins
are reused. A complete AWQ cache is validated and reused without downloading.

Send FN the new `FN test link` printed by this run. Opening the page and selecting
controller-owned options do not allocate the GPU. The first model-dependent
answer still has a cold-start wait. The model releases after 60 seconds without
model requests; the next answer reloads it. This preserves shared use and never
preempts someone else's workload. GPU fit, startup time and warm response time
must be checked on the host. The current service is unchanged until restarted.

The original deployment remains available explicitly:

```bash
.venv-api/bin/python scripts/share-fn-review.py --model-variant fp16 --release-existing-a2
```

Its original 30 GiB runtime disk-headroom requirement remains. Normal
`model-host.py` commands still default to FP16 on all four GPU profiles. The new
AWQ option currently supports `liono-a2` only; it is rejected for other profiles.
V100/V100S cannot use this Marlin configuration.

## Artifact identity and measurements

`configs/model-awq.json` pins `Qwen/Qwen3-8B-AWQ` at
`4da05a8edb55c6046cce958586c33b61da07bb79`. The original
`configs/model.json` and its FP16 revision are unchanged. Both snapshots coexist.
The served model name, readiness check, request name and exported model provenance
identify AWQ explicitly. A wrong alias or incomplete/wrongly quantized cache is
rejected. Model ownership records also distinguish deployment variants.

Existing observable metrics now include generated token counts, successful
generation HTTP time, and time waiting for model availability separately.
The smoke report derives output tokens per HTTP second where usage is available;
this includes prefill and decoding, so it is not identical to vLLM's interval
generation-throughput metric. Missing usage yields no invented token rate.
Generation calls, fallbacks, interpretation checks, full completion, scoring
and review are still reported.

## Reproduce checks

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_fast_a2.py \
  tests/test_model_launch_selection.py tests/test_model_host.py \
  tests/test_model_readiness.py tests/test_model_lifecycle.py \
  tests/test_fn_review_link.py tests/test_ops_recovery.py \
  tests/test_model_timeouts.py tests/test_fn_interpretation.py \
  tests/test_fn_interview.py tests/test_chat_choices.py tests/test_api_integration.py \
  tests/test_model_diagnostics.py tests/test_transport_recovery.py \
  tests/test_readiness_evidence_client.py tests/test_privacy.py
```

For isolated live measurement, stop the sharing launcher first; do not combine
its idle watcher with an independent benchmark process. Prepare/start your own
model on a free A2, then run the existing synthetic harness:

```bash
IAM_MODEL_VARIANT=awq .venv/bin/python scripts/download-model.py
python3 scripts/model-host.py start liono-a2 --variant awq --port 18003

IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py --allow-live \
  --model-variant awq --base-url http://127.0.0.1:18003 \
  --case citizen_short --opening-only --opening-variant all \
  --output .runtime/fn-awq-opening-1

IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py --allow-live \
  --model-variant awq --base-url http://127.0.0.1:18003 \
  --case all --output .runtime/fn-awq-full-1

# Release only your supervised model in this checkout after the benchmark:
bash scripts/stop-vllm.sh
```

Use a fresh output directory for each run. The full harness exercises all four
FN flows through scoring and respondent review, without targeting illustrative
levels. Check `metrics.json` for interpretation failures, fallback frequency,
completion and timing; controller-fixture success does not prove live Qwen quality.

On 24 November 2026, the final affected regression group above passed **393
tests** (one upstream deprecation warning), including **22 fast-profile checks**,
all four canonical FN fixture replays with AWQ provenance, API/lifecycle checks
and real privacy screening. Python syntax and staged diff checks passed. All
four source PDF hashes and the extracted-rubric hash match their register. No
frontend code changed in this refinement, so the existing build is reused.

This execution environment cannot access the NVIDIA driver or model-download
network. A bounded real download attempt failed; no quantized model was loaded.
**Live AWQ speed, VRAM fit and semantic/scoring quality remain unmeasured.** No
running service, original private source, registered hash or original model pin
was modified by activation here. Run the host checks above before claiming a
specific response-time improvement.

Primary sources: [official Qwen model](https://huggingface.co/Qwen/Qwen3-8B-AWQ),
[pinned revision](https://huggingface.co/Qwen/Qwen3-8B-AWQ/commit/4da05a8edb55c6046cce958586c33b61da07bb79),
[vLLM AWQ support](https://docs.vllm.ai/en/v0.8.5/features/quantization/auto_awq.html),
[CPU offload](https://docs.vllm.ai/en/v0.8.5/serving/engine_args.html).
