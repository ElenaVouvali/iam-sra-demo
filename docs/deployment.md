# Current deployment

The application uses an isolated Python 3.10–3.12 environment and a separate localhost vLLM server. Principal pins are vLLM 0.8.5, PyTorch 2.6.0, XFormers 0.0.29.post2 and Transformers 4.51.3. The complete GPU lock is `requirements-lock.txt`; `requirements-app.txt` supports GPU-free UI/tests. Do not overwrite the existing `.venv` during routine development.

## Model and device selection

`configs/model.json` pins `Qwen/Qwen3-8B` to revision `b968826d9c46dd6066d109eabc6255188de91218`. `scripts/download-model.py` stores the snapshot under `.runtime/huggingface/`. Keep this cache; deleting it requires downloading the model again.

Set `IAM_GPU_UUID` to the intended GPU for the host. The operational launcher verifies the UUID and selects its numeric physical index, because this pinned vLLM NVML path requires numeric device IDs. The V100-compatible launch uses `half`, V0 engine and XFormers. The selected device appears as logical GPU 0 to the worker. `scripts/start-davinci.sh` retains the existing host-specific convenience setup; use it only on the host matching its configured UUID.

## Service lifecycle

From the repository root:

```bash
scripts/preflight.sh
scripts/start-vllm.sh
scripts/health-check.sh
scripts/start-ui.sh
scripts/health-check.sh
```

If services already run, check their health instead of starting duplicates. Preflight checks device identity, workload, ports, package versions and disk headroom. Supervisors use dedicated process groups, PID start times and exact commands to identify owned project services. Logs rotate under `.runtime/`; PID records are operational state.

Stop with `scripts/stop-ui.sh` and `scripts/stop-vllm.sh`. Cleanup of historical reports does not require restarting services, changing drivers or reinstalling packages.

The model server binds `127.0.0.1:8000`; Streamlit binds `127.0.0.1:8501`. Configure ports with `IAM_VLLM_PORT` and `IAM_UI_PORT`, and the client endpoint with `IAM_BASE_URL` for direct UI runs. `.env` is not loaded automatically. Follow the port-forwarding instructions in [README](../README.md).

## Inference contract

Launch arguments include the pinned snapshot and served model name, `--dtype half`, `--max-model-len 4096`, `--max-num-seqs 1`, `--tensor-parallel-size 1`, `--enforce-eager`, `--disable-log-requests` and XGrammar guided decoding. GPU-memory utilization defaults to 0.80 and can be configured with `IAM_GPU_MEMORY_UTILIZATION`.

The client disables Qwen thinking and uses `guided_json` with `xgrammar:no-fallback,disable-any-whitespace`, the transport supported by the pinned server. Transport schemas retain structure, types, enums and required fields. Full strict Pydantic validation enforces local numeric, string and array bounds even where XGrammar cannot.

Requests tokenize the complete system/user chat before generation. The 4096-token budget includes reserved output; no citizen evidence is silently truncated. Sampling is temperature 0.2/top-p 0.8. Current output limits are mapping 1400, scope review 300, discovery 500, modified-facet mapping 1200 and scoring 500 tokens. Each request retries at most once within its stage deadline. See [implementation contract](implementation-contract.md).

## Fresh setup

`scripts/install.sh` creates a new `.venv`, installs the full pinned binary lock and downloads the model. It requires Python 3.10–3.12 and 60 GiB disk headroom, and refuses to replace an existing environment. Set `IAM_PYTHON` to the intended interpreter if needed. For an existing checkout, retain its environment and weights and run the checks in [README](../README.md).
