# Select Liono or Davinci for Qwen

The Vue frontend, Flask API, screening, private sources and interview state stay
in the existing checkout on **Liono**. Only inference moves. Davinci's Qwen
endpoint binds to loopback; an SSH local forward connects it to Liono's API.
No application/source transfer or retraining is required.

Run these commands **on Liono**:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
python3 scripts/model-host.py list
```

| Profile | Host | GPU / compute capability | Automatic CPU weight offload |
| --- | --- | --- | --- |
| `liono-v100s` | Liono | V100S / 7.0 | 0 GiB on a 32 GiB card |
| `liono-a2` | Liono | A2 / 8.6 | 8 GiB on its 16 GB card |
| `davinci-v100` | Davinci | V100 / 7.0 | 8 GiB if <=18 GiB; otherwise 0 |
| `davinci-a30` | Davinci | A30 / 8.0 | 0 GiB on a 24 GiB card |

Profiles live in `configs/gpu-profiles.json`. Device indices/UUIDs are discovered
on the target host. Host identity, product name and compute capability must all
match. The existing >2 GiB occupied-memory guard, unique-device requirement,
port checks and process ownership checks remain. A busy selected GPU is never
replaced with a different GPU class.

## One-time Davinci preparation

First establish normal SSH access from Liono. If this is a first connection,
verify the server fingerprint through your usual trusted route.

```bash
ssh evouvali@davinci.microlab.ntua.gr
hostname -s
nvidia-smi
exit
```

Then prepare the model environment:

```bash
python3 scripts/model-host.py prepare davinci-v100
```

This uploads an explicit allowlist of inference helpers and existing dependency/
model pins into **`~/iam-sra-inference` on Davinci**. It creates a separate `.venv`
and downloads the pinned Qwen snapshot under `.runtime/huggingface`. It starts no
service and copies no PDFs, transcripts, credentials or application environments.
It refuses an existing unmarked directory. If necessary, append
`--remote-dir iam-sra-inference-2` to every command.

Repeating preparation updates managed helpers, validates existing dependency
versions and resumes/checks downloads. An interrupted initial dependency install
can be resumed. Incompatible existing environments are reported and retained.
Other checkouts, drivers, environments and running services are not changed.

Davinci needs its existing NVIDIA driver to support the pinned CUDA/PyTorch
stack, Python **3.10–3.12** with `venv`, `tar`, Internet access for downloads and
60 GiB free before a fresh install. Setup finds a compatible Python executable;
an explicit choice is also supported:

```bash
python3 scripts/model-host.py prepare davinci-v100 --python /path/to/python3.10
```

This preparation serves **both Davinci GPUs**. Liono can immediately reuse its
existing pinned model environment/cache. If absent, run
`python3 scripts/model-host.py prepare liono-a2` once on Liono. Model setup never
installs into `.venv-api` or `.venv-privacy`.

Existing SSH config/ProxyJump is honoured. To use an SSH alias, append
`--ssh davinci` to Davinci commands, or export `IAM_DAVINCI_SSH=davinci`.
Liono profiles invoked from another host require
`--ssh YOUR_LIONO_USER@YOUR_LIONO_HOST`; the Liono login is not guessed. The
application must run on the machine holding the local model forward and its
approved sources/environments. The instructions here use the current Liono app.

## Choose a GPU each time

Choose **one** command. Port **18002** leaves an existing 18000 service alone;
the CLI default is 18000.

```bash
python3 scripts/model-host.py start davinci-v100 --port 18002
# Other choices on subsequent runs:
python3 scripts/model-host.py start davinci-a30 --port 18002
python3 scripts/model-host.py start liono-v100s --port 18002
python3 scripts/model-host.py start liono-a2 --port 18002
```

The command uses the existing supervisor and waits up to 600 seconds for health
and the expected model alias. For Davinci, **leave this terminal open** after
readiness: it holds the private SSH forward
`127.0.0.1:18002 -> davinci 127.0.0.1:18002`. Ctrl+C closes the forward; the remote
model stays running. Reconnect without starting another model:

```bash
python3 scripts/model-host.py tunnel davinci-v100 --port 18002
```

A local model remains supervised after the command exits. Existing scripts also
support profiles on their actual GPU host:

```bash
IAM_GPU_PROFILE=liono-a2 IAM_VLLM_PORT=18002 bash scripts/start-vllm.sh
```

If multiple idle cards match, inspect `nvidia-smi` on the target host and add
`--gpu-uuid GPU-...`. Optional overrides are `--cpu-offload-gb 8` and
`--gpu-memory-utilization 0.80`. The wrapper clears stale GPU UUID/offload choices
unless passed as arguments; avoid globally exporting other GPU-specific settings.

Inspect commands without connecting, installing or starting anything:

```bash
python3 scripts/model-host.py prepare davinci-v100 --dry-run
python3 scripts/model-host.py start davinci-v100 --port 18002 --dry-run
```

`check PROFILE --port 18002` runs read-only preflight **before** starting. It
refuses occupied cards/ports; use curl below to check a running service instead.

## Start the current Vue/Flask application

In a second **Liono** terminal:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
curl --fail --noproxy '*' http://127.0.0.1:18002/health
curl --fail --noproxy '*' http://127.0.0.1:18002/v1/models
IAM_BASE_URL=http://127.0.0.1:18002 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
IAM_CHAT_PROCESSING_SECONDS=3600 \
IAM_SRA_API_PORT=8016 \
IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5016,http://localhost:5016 \
bash scripts/start-api.sh
```

In a third **Liono** terminal:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo/app
HOST=127.0.0.1 PORT=5016 IAM_SRA_API_TARGET=http://127.0.0.1:8016 \
../.venv-api/bin/python serve_app.py
```

Open **http://127.0.0.1:5016/tools/sra-assessment/app**. When using your laptop's
browser, forward its port 5016 to **Liono** using your usual SSH destination:

```bash
ssh -N -L 127.0.0.1:5016:127.0.0.1:5016 YOUR_LIONO_USER@YOUR_LIONO_HOST
```

Keep that connection open and use the same browser URL. If `app/dist` is absent
or outdated, follow the README build instructions first. Keep the existing
API/privacy environments and approved private-source preparation. QR/direct
entry and export continue to use the existing API.

Start a synthetic interview, select a profile and submit several answers to
verify generation. Finish, review and export JSON to exercise scoring as well.
Health/model-list checks alone do not establish guided JSON/scoring compatibility
or interview quality.

## Switching and troubleshooting

There is **one supervised model per inference directory**. Switching never stops
one automatically. If your own model still runs in that directory, stop it
explicitly on its host before selecting another GPU:

```bash
# Only your model in the isolated Davinci directory:
ssh evouvali@davinci.microlab.ntua.gr \
  'cd ~/iam-sra-inference && bash scripts/stop-vllm.sh'
# Only your model in this Liono checkout:
bash scripts/stop-vllm.sh
```

These verify PID, start time and exact project command. Do not delete PID records
to bypass a refusal or stop unrelated workloads. Close an old tunnel with Ctrl+C
before reopening the same local port. If the model endpoint changes, restart your
API with the new `IAM_BASE_URL`; this loses its in-memory sessions. A different
free `--port` can coexist with another host/directory's service. The app-side
port is checked before remote launch. SSH uses loopback-only bindings and
`ExitOnForwardFailure=yes`.

Inspect the model host's log for startup failures:

```bash
ssh evouvali@davinci.microlab.ntua.gr \
  'tail -n 60 ~/iam-sra-inference/.runtime/vllm.log'
# Or on Liono:
tail -n 60 .runtime/vllm.log
```

All profiles retain Qwen3-8B revision
`b968826d9c46dd6066d109eabc6255188de91218`, FP16, V0/XFormers, XGrammar,
4096 tokens and one active sequence. A2 has
[16 GB GPU memory](https://www.nvidia.com/en-eu/data-center/products/a2/).
[vLLM CPU offload](https://docs.vllm.ai/en/v0.8.5/serving/engine_args.html#cacheconfig)
keeps the same weights but transfers some on each forward pass. The 8 GiB default
is an initial setting, **not a measured fit/performance guarantee**. Preflight
requires at least 12 GiB available host RAM for it; loading/runtime may need more.
A2/16 GiB V100 generation may take minutes. Prefer a free A30 or 32 GiB V100/V100S
for interactive use.

`IAM_MODEL_TIMEOUT_SECONDS=900` allows longer but bounded stages/HTTP requests,
still capped by the API job deadline. Supported values are 15–1800 seconds.
Without it, the existing 120-second HTTP and 180-second stage limits remain.
Privacy, evidence/context limits, retries and rejection of late results remain
unchanged. A startup readiness timeout leaves the model available for log
inspection; it does not kill it automatically.

## Verification

```bash
.venv-api/bin/python -m pytest -q \
  tests/test_model_launch_selection.py tests/test_model_host.py \
  tests/test_model_timeouts.py tests/test_ops_recovery.py \
  tests/test_model_readiness.py tests/test_model_diagnostics.py \
  tests/test_transport_recovery.py tests/test_baseline_answer_recovery.py
bash -n scripts/setup-inference.sh scripts/start-vllm.sh scripts/stop-vllm.sh
```

These offline tests check selection, forwarding order, collisions, failures,
upload preservation, offload settings and bounded deadlines. They do not prove
GPU fit or live inference quality. Verification on this branch:

- 98 launcher, orchestration, timeout and existing recovery/transport tests passed.
- The broader chat/retrieval/QR/API/FN/indicator run had 270 passes and one real
  privacy integration failure (`privacy_unavailable`) with the default cache in
  this restricted environment. The failing test passed when rerun with writable
  `TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract`.
- That rerun included all four real-detector FN opening/export cases and existing
  readiness-client, CPU-benchmark and baseline-reliability checks: 48 passed.
- Python compilation, shell syntax and `git diff --check` passed. No frontend
  files changed; the existing build is reused.

To repeat the broader checks with a writable privacy cache:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract .venv-api/bin/python -m pytest -q \
  tests/test_chat_conversation.py tests/test_chat_retrieval.py tests/test_chat_qr.py \
  tests/test_api_integration.py tests/test_fn_interview.py tests/test_indicator_api.py
```

During implementation this session could not
resolve `davinci.microlab.ntua.gr`, and local `nvidia-smi` could not access the
driver. No remote installation, GPU launch, service restart or live generation
was executed. Run the preparation/start and synthetic interview checks above
from your normal terminal/VPN/SSH route to establish live compatibility.
