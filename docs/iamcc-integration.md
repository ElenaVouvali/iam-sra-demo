# IAM-SRA standalone IAM-CC integration

## Scope and checkout record

The standalone Vue application is **IAM-SRA**, its assessment is **IAM-SRA2**,
and its only registered tool is `sra-assessment`. The working route is
`/tools/sra-assessment/app`. Browser calls use `/api/sra-assessment/v1/...` on
that same origin. Both proxies remove `/api/sra-assessment`; the Flask API owns
`/v1/...`. This repository does not register or deploy a tool in the central hub.

Initial inspection recorded HEAD `e8ee21012779e0b6980c7f9ea41770f27cad9ed6`,
already on `feature/iamcc-vue-api`, with modified README and untracked API code,
tests and documentation. That existing work was preserved. The Vue continuation
started from `66094455377060511fcd9c84095232c07ff986ae` (`Platform integration`),
with an uncommitted change to this document. Its prior content is preserved at
`/tmp/iam-sra-before-vue-integration.md`; temporary snapshots are not durable
backups. No applicable AGENTS.md was found. Streamlit, assessment methodology,
model selection, GPU packages, weights and model launchers were retained.

The completed integration through commit `4c88bcf` is now included on `main`.
The temporary `feature/iamcc-vue-api` branch is retired; use `main` for new
checkouts and updates.

The actual IAM-IQ donor was inspected at
`bb1ff04913c32f3a0d85ee6b6a34d38c1dd00f2e`, from the separate
`~/iam-iq-frontend-donor` checkout. Both copied reference SKILL.md files were read
explicitly, together with the actual app, design notes, playground, frontend
specification, components, page templates and deployment examples. See
[iam-iq-provenance.json](iam-iq-provenance.json) and
[attribution and licensing](iam-iq-attribution.md). Generated `tokens.css` and
`components.css` remain byte-identical. No donor tool pages or destinations are
registered in IAM-SRA. Reference documents retain their original upstream names.

## Runtime requirements and private sources

Use **Node 22.12+ within Node 22** for frontend development/build and Python
3.10–3.12 for the API. Production frontend serving needs only Python 3.10+.
Dependency versions are pinned in the donor-derived package/lockfile. Leaflet and
Plotly were omitted because this interview has no maps or charts. The copied
offline font avoids third-party font requests.

Keep Flask/Gunicorn separate from inference. The setup script creates the API
environment and references the existing CPU privacy packages read-only; it never
installs into the GPU environment or downloads Qwen weights:

```bash
cd ~/iam-sra-demo
bash scripts/setup-api.sh
PYTHONPATH=src .venv-api/bin/python scripts/check-privacy.py
```

The existing detector pins and English model must pass that check. Provision the
approved private source files listed by the existing source register/build script
under ignored `references/private/`. On a trusted host with those files, build
and review the matching corpus:

```bash
PYTHONPATH=src .venv-api/bin/python scripts/build-conversation-corpus.py
```

The required corpus is `references/private/conversation-corpus.json`. Its loader
validates source hashes, configuration hashes, source membership and grant
scenario provenance. Sources/corpus are not in Git or either image. Missing or
changed resources produce actionable readiness errors. There is no production
mock fallback and no privacy bypass. Respondent records never enter retrieval.

Set `IAM_BASE_URL` to the **existing verified model origin**. The local launcher
record names `http://127.0.0.1:18000`; earlier deployments used 8000. The 18000
health check returned connection refused during this verification, so live Qwen
inference was not claimed and no model service was restarted.

## A. Host development

### Moving to a different server

Clone `main`, which includes the integration, on the authorised destination:

```bash
git clone --branch main --single-branch \
  https://github.com/ElenaVouvali/iam-sra-demo.git
cd iam-sra-demo
git rev-parse HEAD
```

Git does **not** transfer `.venv*`, `.runtime`, model weights, private sources,
assessment sessions or `app/dist`. On the new server:

1. Have the operator allocate a compatible GPU and prepare the pinned model
   environment and approved Qwen3-8B revision from `configs/model.json`. The
   existing launcher supports V100/A30 hardware; other hardware needs a separate
   compatibility review. `scripts/install.sh` is a fresh-server GPU setup script
   that installs the pinned inference stack **and downloads weights**; it is not
   an update command for an existing environment. Do not run it on davinci to
   resolve GPU contention, or overwrite an existing environment.
2. Prepare the separate CPU privacy/API environments with
   `bash scripts/setup-privacy.sh` and `bash scripts/setup-api.sh`. These require
   dependency-download access. Provision approved private documents outside Git
   and build/validate their matching corpus as described above.
3. With Node 22, run `cd app`, `npm ci --no-audit --no-fund`, then
   `npm run build`. The built UI can subsequently be served with Python alone.
4. Verify the existing model endpoint, set `IAM_BASE_URL`, and use the API and
   built-frontend launch commands below. Keep all host services on loopback;
   connect from your workstation through the documented SSH tunnel.

For a stopped project-owned model on an allocated compatible GPU, start and wait
as one conditional sequence so a failed launch does not cause a pointless wait:

```bash
cd ~/iam-sra-demo
IAM_VLLM_PORT=18000 bash scripts/start-vllm.sh &&
IAM_VLLM_PORT=18000 .venv/bin/python scripts/wait-model.py --timeout 600
```

If the launcher cannot uniquely select an idle GPU, run the read-only
`IAM_VLLM_PORT=18000 .venv/bin/python scripts/diagnose-model.py` and obtain an
allocation. Set `IAM_GPU_UUID` only to the allocated, available supported GPU;
do not stop other users' workloads or substitute a different model endpoint.
If an existing approved endpoint uses a different port, use that verified origin
in `IAM_BASE_URL` instead of starting a duplicate service.

Check `ss -ltn` before launching. Ports 5001 and 8001 were free at inspection;
all ports remain configurable and binds fail if occupied.

Terminal 1, API:

```bash
cd ~/iam-sra-demo
export IAM_BASE_URL=http://127.0.0.1:18000  # only after verifying the existing service
export IAM_SRA_API_PORT=8001
export IAM_SRA_UI_PORT=5001
export IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5001,http://localhost:5001
bash scripts/start-api.sh
```

Terminal 2, Node 22 frontend:

```bash
cd ~/iam-sra-demo/app
npm ci --no-audit --no-fund
npm run dev
```

Open **http://127.0.0.1:5001/** for the catalogue, then IAM-SRA2 → Open tool.
The direct working link is **http://127.0.0.1:5001/tools/sra-assessment/app**.
Browser refresh restores the current owner's server session without storing
interview content or credentials in URLs or browser storage.

The server-side default is `127.0.0.1:8001`. Override with
`IAM_SRA_API_TARGET=http://<approved-api-origin>:<port>` in the UI process.
Never use a `VITE_` variable for backend/model configuration. `K8S_HOST` and
`IAMIQ_IN_CLUSTER=1` remain supported: the latter selects `iam-sra-api:8001`
from `app/proxy-routes.json`. This table contains exactly one tool destination.

## B. Built frontend and production API

Use the same API command above. Gunicorn runs one gthread worker, eight request
threads, no preload, and one managed inference lane. Flask debug/development
serving is not used in the packaged deployment.

After stopping only the development UI process, build and serve:

```bash
cd ~/iam-sra-demo/app
npm run build
HOST=127.0.0.1 PORT=5001 python3 serve_app.py
```

`serve_app.py` serves dist and SPA deep links. It proxies GET/HEAD/POST/DELETE,
JSON bodies, cookies, Origin/CSRF/version headers, status codes and attachment
headers. Unknown tools and missing assets return JSON 404; backend unavailability
returns a safe JSON 502 without private addresses or exception bodies. Both
proxy modes have a 30-second transport timeout; model actions return 202 promptly
and continue as jobs. API assessment responses use `Cache-Control: no-store`.

```bash
curl --fail http://127.0.0.1:5001/api/sra-assessment/v1/health
.venv-api/bin/python scripts/smoke-api.py \
  --base-url http://127.0.0.1:5001/api/sra-assessment/
```

Run that second command from `~/iam-sra-demo`, not from `app/`. It uses real detector/corpus
gates and synthetic onboarding on the decline path, makes no model calls, and
checks ownership, CSRF, jobs, final confirmation and both downloads. It deliberately
rejects a synthetic test API. See [the versioned API contract](iamcc-api-contract.md).

## Privacy and session/job lifecycle

Each session owns a controller; every job works on a private copy with fresh
model clients and isolated caches/metrics. The service does not acquire the
existing non-reentrant LLM transport lock around clients that already acquire it.
One controlled inference lane serves a bounded queue. Reads and polling remain
responsive while inference runs. Expected revisions reject stale actions;
request UUID receipts make retries idempotent. Reset, corrections, end and expiry
invalidate obsolete work and dependent results.

Text is screened before retention, hashing or queueing. Cleaned previews require
explicit confirmation bound to the exact owner/session/action/question/revision.
A new submission invalidates an earlier preview even when the replacement is
blocked. The browser clears original drafts on submission and recovers state
rather than storing an unsafe retry payload. Model failures can return the
server's screened retry draft. Output and downloads pass the existing gates.

An HttpOnly, SameSite=Strict owner cookie establishes ownership; session IDs alone
do not grant access. Mutations require a CSRF token retained only in browser
memory. Configure `IAM_SRA_COOKIE_SECURE=1` for HTTPS and set the exact deployed
UI origins in `IAM_SRA_ALLOWED_ORIGINS`. Set an operator-managed
`IAM_SRA_API_SECRET` of at least 32 characters for stable cookie signatures.
Do not store that secret in Git, commands checked into source or query strings.

| Setting | Default |
| --- | --- |
| `IAM_SRA_MAX_SESSIONS` | 32 |
| `IAM_SRA_QUEUE_SIZE` | 8 waiting jobs, plus one running |
| `IAM_SRA_JOB_TIMEOUT` | 600 seconds including queue wait |
| `IAM_SRA_SESSION_TTL` | 3600 seconds idle |
| `IAM_SRA_SESSION_MAX_AGE` | 14400 seconds absolute |
| `IAM_SRA_RESULT_TTL` | 300 seconds |
| `IAM_SRA_MAX_RESULTS` | 128 retained completed results |

This initial deployment is **single-process and in-memory**. Use one API worker
and one API replica; never preload. Restart loses sessions even with a stable
cookie secret. Python cannot safely kill a blocked thread: a timed-out call keeps
the sole lane until it returns, while its late result is fenced out. Restart only
the owned API process if necessary, accepting session loss. Existing Streamlit
traffic has its own process lock; it is not a cross-process inference scheduler.

Confirmation is self-report, not independent verification. Acceptance remains
separate from readiness, missing evidence from low readiness, and prior knowledge
from reasoning after information. Corrections retain history and invalidate
future results. The optional personal citizen estimate is draft, unapproved and
provisional. TRL, ORL and overall SRL remain unavailable.

## C. Frontend container and backend connectivity

The adapted `app/Dockerfile` follows the donor's Node 22 build / Python serving
stages. Build locally:

```bash
docker build -t iam-sra/frontend:local app
```

For a Linux host API bound to loopback, the deliberate host-network option keeps
both API and model on host loopback. Stop the host UI first to release 5001:

```bash
docker run --rm --name iam-sra-ui --network host \
  -e HOST=127.0.0.1 -e PORT=5001 \
  -e IAM_SRA_API_TARGET=http://127.0.0.1:8001 \
  iam-sra/frontend:local
```

This is a Linux host-network example, not a promise about Docker Desktop.
Container localhost normally means the container itself. A host-gateway alias
does not make a host service bound only to 127.0.0.1 reachable from a bridge.
For bridge/cluster networking, provision an explicitly approved reachable API
origin or service DNS, then test its health from the UI container. Do not rebind
vLLM publicly to solve frontend connectivity.

`deploy/Dockerfile.api` is an optional CPU-only API image recipe. It requires
network dependency installation, poppler and pinned privacy resources. It copies
only allowlisted source/configuration files through the root `.dockerignore`;
private sources/corpus are mounted read-only under `/srv/iam-sra/references/private`.
The recipe is supplied for platform review; the host deployment reuses the current
CPU environment. No GPU stack or weights are included.

## D. Cluster and central onboarding handoff

`deploy/iam-sra-ui.yaml` adapts the donor's Deployment/ClusterIP convention and
`IAMIQ_IN_CLUSTER=1`. `deploy/iam-sra-api.yaml` is a preparation example with one
replica and Recreate strategy. It refers to operator-created image, PVC, runtime
ConfigMap and cookie-signing Secret. These are repository deployment examples,
not invented central hub registry fields. Requests/limits are initial planning
values requiring measurement; no capacity certification is implied.

Before applying anything, the platform owner must provision approved sources and
matching corpus, a reachable existing model origin, compatible API CPU image,
exact UI origins/HTTPS cookie settings, and sufficient resources. The API may
bind `IAM_SRA_API_HOST=0.0.0.0` inside its pod; the default host launch remains
127.0.0.1. Both Services remain ClusterIP. Do not add NodePort or public ingress
without separate approval. No cluster was accessed or changed here.

On an authorised cheetara deployment, use a personal project directory such as
`/SSD_500GB/<authorised-user>/iam-sra`, avoid IAM-IQ port 5000, and follow the
verified donor loopback/ClusterIP/SSH-tunnel policy. No cheetara access or partner
dataset transfer is part of this handoff.

```bash
kubectl port-forward --address 127.0.0.1 svc/iam-sra-ui 5001:5001
# From your workstation, with the host UI or port-forward already running:
ssh -L 5001:127.0.0.1:5001 -L 8501:127.0.0.1:8501 <user>@<authorised-host>
```

Central IAM-CC onboarding still needs agreement on tool ID `sra-assessment`, work
route `/tools/sra-assessment/app`, runtime proxy origin, health
`/v1/health`, one API process/replica, resource measurements, source provisioning,
model connectivity, retention/privacy ownership, redistribution terms and any
platform authentication requirements. No central API, SSO claim or registration
has been assumed.

## Verification and reproducibility

Use Node 22 and the API environment:

```bash
PYTHONPATH=src .venv-api/bin/python -m pytest -q tests/test_api_integration.py tests/test_frontend_proxy.py
cd app
npm ci --no-audit --no-fund
npm run build
BASE=http://127.0.0.1:5001 FIREFOX=/path/to/firefox \
  SHOTS=/tmp/iam-sra-shots npm run check
```

For deterministic browser tests, run the explicit **test-only** WSGI fixture in
place of the API, with `PYTHONPATH=src:tests .venv-api/bin/python -m gunicorn
--workers 1 --threads 8 --bind 127.0.0.1:8001 'api_browser_fixture:create_fixture()'`.
It uses authored synthetic corpus/model/detector fixtures, displays a clear fixture
notice, cannot call Qwen and is never selected by the production launcher. The
browser checks exercise desktop/mobile layouts, keyboard focus, Back/refresh,
interpretation review/correction, scenario selection/acceptance/decline,
information/acknowledgements/reflection, final review, null scores, provisional
abstention, screened previews, blocked credentials, retryable errors, downloads,
reset/end and absence of browser requests to raw backend/model origins.

Observed verification:

- Node 22.23.3: `npm ci` and `npm run build` passed using the donor-pinned packages.
- The final Python suite passed **523 tests** in 305.87 seconds, including the
  generated-session-ID privacy regression (one upstream deprecation warning).
- Development and production HTTP checks passed for prefix rewriting, cookies,
  CSRF, duplicate actions, jobs, status forwarding, JSON/JSONL attachments, DELETE,
  unknown-tool rejection and SPA deep links. Three production-proxy Python tests
  also passed independently.
- Firefox 158.0.1: the adapted donor harness passed catalogue/detail/working/privacy
  layouts at 360, 768, 1200 and 1440 pixels; keyboard focus and all four authored
  synthetic browser journeys passed. Screenshots were inspected, including narrow
  mobile and final organisation scope. These are flow tests, not live semantic
  validation.
- The frontend Docker image built successfully and its health check passed. An
  explicit Linux host-network container reached the host-loopback API and served
  the working-page deep link and proxied health. Observed idle container memory
  was about 30 MiB; this is not a load/capacity benchmark. The optional API image
  recipe and cluster examples were not deployed or built as an API image.
- The normal single-worker API and built frontend were then started on loopback
  ports 8001 and 5001. `scripts/smoke-api.py` passed through the frontend proxy
  using the real local privacy detector and reviewed corpus, with synthetic
  context and no model calls. Both JSON and JSONL exports passed.
- A generated UUID PERSON false positive was reproduced and fixed only in known
  generated ID locations. Tests retain screening for UUIDs in answers/respondent
  JSON, and for names/credentials in ID fields. Privacy remains mandatory.
- Generated styles, fonts, logo sprite and EU emblem match the recorded donor
  SHA-256 values; the separate donor checkout is clean. Diff whitespace, Python
  compilation, shell syntax and deployment YAML parsing passed.

After initial verification, the normal local interface was left at
http://127.0.0.1:5001/; the synthetic fixture, development UI, alternate production
UI and verification container were stopped. Those were foreground tool-managed
processes, not installed system services; follow the launch commands to establish
current availability. Live semantic validation was unavailable because the model
service at port 18000 did not respond. A later read-only GPU diagnostic found both
davinci GPUs occupied by another user's service; no workload was stopped or
model service restarted.
See [the simple catalogue handoff](iamcc-catalogue-handoff.md) for adding a tool
box/link after an approved shared address is provided.

## Streamlit and rollback

The existing Streamlit path is preserved:

```bash
cd ~/iam-sra-demo
IAM_BASE_URL=http://127.0.0.1:18000 IAM_MOCK=0 \
  IAM_ASSESSMENT_MODE=retrieval_grounded_conversation bash scripts/start-ui.sh
```

Use that model address only when verified for the intended host. Open
http://127.0.0.1:8501/ directly or through the SSH tunnel.

To roll back, stop only the new UI/API foreground processes with Ctrl+C, or stop
the dedicated `iam-sra-ui` container. Restart loses API sessions. Preserve all
source work before switching: commit reviewed changes or stash tracked/untracked
source changes. The preserved Streamlit interface can be used on current `main`
without a checkout change. To inspect the pre-integration version, use
`git switch --detach e8ee21012779e0b6980c7f9ea41770f27cad9ed6`;
return to the integrated version with `git switch main`. Switching to `main`
alone is no longer a rollback because it now includes the integration.
The API-only checkpoint is `66094455377060511fcd9c84095232c07ff986ae`; it can
also be inspected in a separate detached worktree without overwriting this one.
Do not reset hard, delete environments/weights/private sources, or restart model
services as part of UI rollback. No hub deployment needs to be undone.
