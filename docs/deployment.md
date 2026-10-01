# Deployment stack and provenance
Observed liono: Ubuntu 20.04.1, driver 550.163.01. Physical GPU 0 A2, 15356 MiB, CC8.6; physical GPU 1 Tesla V100S-PCIE-32GB, 32768 MiB, CC7.0. Verified UUID `GPU-cea3d9e4-d189-a5b9-cf2e-9bd77b8218fb`. Initial usage 1 MiB on each device. Before installation / had 27 GiB available, /home 142 GiB. Host default Python 3.13.13 is unsuitable for this vLLM release; isolated `.venv` uses an existing Python 3.10.20 interpreter without modifying its parent environment. Existing HF cache held DeepSeek Coder snapshots, no Qwen3-8B.

## Official support evidence
- [vLLM 0.8.5 GPU installation](https://docs.vllm.ai/en/v0.8.5/getting_started/installation/gpu.html): Python 3.9–3.12, Linux, CC≥7.0, CUDA12.4 default wheels. The page also contains older introductory CUDA text; actual installed torch reports 12.4.
- [vLLM 0.8.5 CUDA requirements](https://github.com/vllm-project/vllm/blob/v0.8.5/requirements/cuda.txt): torch2.6.0, torchvision0.21.0, torchaudio2.6.0, xformers0.0.29.post2. Binary wheels were installed; no source build.
- [vLLM 0.8.5 CUDA backend implementation](https://github.com/vllm-project/vllm/blob/v0.8.5/vllm/platforms/cuda.py): Volta uses XFormers rather than FlashAttention-2; device-id NVML conversion requires integer indices.
- [Qwen vLLM deployment](https://qwen.readthedocs.io/en/latest/deployment/vllm.html): Qwen3, `chat_template_kwargs={"enable_thinking": false}`, `/think` disablement, and guided_json. Reasoning parsing must be disabled for this non-thinking mode on 0.8.5.
- [vLLM 0.8.5 structured outputs](https://docs.vllm.ai/en/v0.8.5/features/structured_outputs.html): `guided_json`, rather than modern `structured_outputs`.

## Exact principal pins and launch
vLLM0.8.5, torch2.6.0+cu124, XFormers0.0.29.post2, transformers4.51.3. Model `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`. All packages recorded in `requirements-lock.txt`; model identity in `configs/model.json`. Driver is unchanged. The installed CUDA runtime, rather than nvidia-smi's maximum supported CUDA banner, is used for compatibility verification.

`scripts/start-vllm.sh` verifies the UUID and uses its physical numeric index, with `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `CUDA_VISIBLE_DEVICES=1`, `VLLM_USE_V1=0`, `VLLM_ATTENTION_BACKEND=XFORMERS`. This release rejects UUID strings in its NVML path. The worker sees only logical GPU0, the V100. Arguments: local pinned snapshot, served name Qwen/Qwen3-8B, dtype half, host127.0.0.1, port8000, max-model-len4096, max-num-seqs1, tensor-parallel-size1, gpu-memory-utilization0.80, enforce-eager, disable-log-requests, guided-decoding-backend xgrammar. No quantization, BF16, FP8, FlashAttention-2 or reasoning parser. CPU thread environment limits are two.

## Structured output compatibility
On this pinned release the CLI accepts xgrammar. XGrammar0.1.18 does not implement JSON-schema numeric/string/item bounds, causing a fallback to Outlines for the full schema. That first compilation stalled. The final client selects `xgrammar:disable-any-whitespace` per the pinned decoder’s Qwen warning and sends a structural transport schema retaining required fields, types, canonical ID enums and additionalProperties=false, with bounds removed; **the full strict Pydantic schema still enforces every bound locally**. Invalid outputs are controlled errors/retried once, never accepted. Concern-position/score consistency and versioned conservative evidence-topic/acceptance screens run locally after schema validation; this is fail-closed output verification, not numerical score substitution. This is a documented transport compatibility choice, not a relaxation of saved assessment validation.

Budget is measured using the server's `/tokenize` endpoint and non-thinking chat template, including system prompt, source scenario, registry, anchors, full schema and citizen text. Reserve1600 output tokens and reject if total>4096. Sampling temperature0.2/top_p0.8; model generation_config also supplies top_k20. No truncation or raw text request logging.

## Operations
Scripts bind localhost, check ports and existing GPU load, refuse >2 GiB existing GPU usage and insufficient /home headroom, create owned supervisors with dedicated process groups, record PID start-time and exact command, and verify identity before stopping. Logs rotate (2 MiB plus two backups), sessions are memory-only and exports explicit. A failure never starts mock mode. From laptop use the forwarding command in README.

Do not change drivers, use sudo, patch other environments, or select the A2. If future wheel installation fails, retain the offline UI/tests and use the pinned supported binary stack on an accessible V100 host; do not begin an expensive source build automatically.
