# CPU benchmark

The existing adaptive benchmark can run the pinned local Qwen3-8B snapshot entirely on CPU. It uses Transformers and XGrammar with the existing privacy screening, extraction/review prompts, context limits and validators. No model server is started and no GPU workload is stopped. The historical seed bank remains unchanged.

Run from the project directory:

```bash
cd ~/iam-sra-demo
CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
  .venv/bin/python scripts/smoke-baseline.py --cpu --cpu-threads 4 \
  --cpu-generation-seconds 900 --output .runtime/cpu-benchmark.json \
  > .runtime/cpu-benchmark.log 2>&1
```

This runs all cases in `eval/benchmarks/baseline_adaptive_v3.json`. Add `--case personal_possible_benefit_without_reason` to run a pilot. Use `tail -f .runtime/cpu-benchmark.log` in another terminal to see case start/completion messages. The model loads once and is shared across cases. CPU loading and generation can take substantial time; the generation limit is per model call and is checked between generation steps. A truncated response is a recorded execution failure, never accepted as a valid assessment.

The adapter uses CPU float32 weights, four computation threads by default, seed 42, temperature 0.2 and top-p 0.8. It loads only the locally cached pinned snapshot. The model alone needs roughly 32 GB RAM, plus runtime overhead. Existing `.venv` inference libraries and `.venv-privacy` screening resources are reused without modifying either environment. Missing privacy resources still fail closed.

The main JSON index links to individually screened case records in `cpu-benchmark_cases/<run-id>/`. Records include presented question IDs/variants, exact synthetic answers, automated confirmations, original/corrected phases, per-turn latency and per-call generation timing/token counts. Runtime metadata records CPU device, precision, thread count, seed, library versions, generation limit and model load time. Initial turn timing includes model loading; later calls are warm. Code, model, instrument, benchmark and policy provenance are retained by the existing runner.

CPU results are a separate runtime condition. They cannot establish GPU latency or bit-for-bit GPU output equivalence. Scripted confirmations are automation. Semantic review remains pending; a completed execution is not an accuracy pass. Unsupported answer branches, privacy withholding, routing failures and unexercised expectations remain explicit. Exit status 2 means an incomplete run, withheld artifact or failed routing/invariant check; inspect the case records before retrying.

When GPU capacity becomes available, run the existing GPU benchmark separately and use the manual UI protocol in `manual-ui-checks.md` for user experience and response-time checks.
