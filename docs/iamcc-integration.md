# IAM-CC integration: implementation state and operator handoff

## Starting state and current scope

The current checkout was inspected before editing: HEAD was
`e8ee21012779e0b6980c7f9ea41770f27cad9ed6`, already on
`feature/iamcc-vue-api`, with no newer commits. It was **not clean**:
`README.md` was modified, and `configs/gunicorn_api.py`, both IAM-CC integration
documents, `requirements-api.txt`, `scripts/setup-api.sh`, `scripts/start-api.sh`,
`src/iam_sra/api/` and `tests/test_api_integration.py` were untracked existing work.
That work was preserved and reviewed in place. No applicable `AGENTS.md` was
found in the checkout or its ancestor directories. A source-only starting snapshot
and SHA-256 manifest were saved to `/tmp/iam-sra-integration-start.tar.gz` and
`/tmp/iam-sra-integration-start.json`; these temporary files are not durable backups.
No Git history or unrelated working files were changed.
The Streamlit `app.py`, engine methodology, privacy rules, GPU environment,
model selection, weights and service launchers were preserved.

**The Python API is implemented. The Vue frontend and its proxy integration are
not yet implemented:** access to the actual IAM-IQ donor is required. Do not
describe this branch as a completed Vue application or central hub deployment.

Donor requested: `https://codeberg.org/IAM-CC/IAM-IQ.git`. The sandbox clone failed
with `Could not resolve host: codeberg.org`. A second, network-authorised clone
reached Codeberg but failed with `remote: Unauthorized` / `Authentication failed`.
The configured credential helper also reported an unavailable VS Code Git socket.
No donor checkout was found under the accessible home, temporary or project paths.
An authorised local checkout/archive or working read access to that repository is
required; credentials must not be placed in source files or chat. Exact donor commit: **not yet
available**. No donor source, generated styles, assets or datasets were copied.
No substitute shell is presented as IAM-IQ reuse.

From the normal network-enabled server terminal, obtain the source separately:

```bash
git clone https://codeberg.org/IAM-CC/IAM-IQ.git ~/iam-iq-frontend-donor
git -C ~/iam-iq-frontend-donor rev-parse HEAD
```

Required source includes `app/`, `.claude/skills/iamcc-ui/`,
`.claude/skills/front-end-development/`, both SKILL.md references,
`docs/iamcc-ui-notes.md`, `docs/iamcc-ui-playground-standalone.html`, reuse and
deployment specifications, and applicable licenses/attribution. Record the exact
commit before copying and hash generated `tokens.css`/`components.css` before and
after. Those references still require actual inspection; donor backend endpoint
documents must not be treated as IAM-SRA API specifications.

Node/npm are not on the current shell's PATH. Node 22 remains the donor's
documented prerequisite. Network access and loopback socket binding required
explicit sandbox escalation; that escalation allowed installing Gunicorn and
testing the packaged API over HTTP. It did not supply donor repository access.
No frontend build, proxy, browser or generated-style verification is claimed.

## Implemented API

- `src/iam_sra/api/__init__.py`: Flask factory, versioned endpoints, signed owner
  cookie, CSRF/origin checks, safe errors and no-store headers.
- `adapter.py`: existing controller operations, synchronous input screening,
  explicitly confirmed cleaned previews, public presentation and screened browser
  export projection. No model address is exposed to browser code.
- `service.py`: capacity-limited in-memory sessions, one managed inference thread,
  bounded queue/results, independent transport revisions, idempotent submission,
  working-copy commit fences and expiry/reset invalidation.
- `schemas.py`: strict action data and presentation/job envelope models.
- `configs/gunicorn_api.py`: one threaded worker, no preload, localhost binding.
- `scripts/setup-api.sh` and `start-api.sh`: separate CPU API environment and
  production WSGI launcher.
- `scripts/smoke-api.py`: reproducible HTTP checks with real privacy/corpus gates,
  synthetic context, asynchronous actions, scenario decline, final confirmation,
  owner/CSRF checks and both export formats. It makes no model requests.

See [the API contract](iamcc-api-contract.md) for routes, state/actions, privacy
preview binding, browser-export differences and required proxy headers.

No API endpoint creates organisational or technical scores, city dashboards,
participation bonuses or new aggregation rules. The citizen estimate remains
optional and provisional; TRL/ORL/overall SRL remain unavailable.

## Host installation and API launch

Use Python 3.10–3.12 and the existing pinned `.venv-privacy` resources. This setup
creates `.venv-api`, references the CPU privacy packages read-only, and installs
only the separate Flask/Gunicorn layer there. It does not install anything into
the GPU environment or download weights. Network package access is required for
Flask/Gunicorn if not cached.

```bash
cd ~/iam-sra-demo
bash scripts/setup-api.sh
PYTHONPATH=src .venv-api/bin/python scripts/check-privacy.py
PYTHONPATH=src .venv-api/bin/python scripts/build-conversation-corpus.py
```

Rebuild the corpus only on the trusted host that already has approved-to-use
sources in ignored `references/private/`. Its existing loader checks source
hashes, configuration hashes, membership, grant scenarios and privacy. The API
preflights the corpus at startup, caches the checked static source content, and
rehashes its source/configuration inputs on readiness/action checks. Source
changes require a valid rebuilt corpus and new/reset sessions; citizen answers
are never added to retrieval.

Before starting, verify the existing model endpoint from the project/service
configuration. This checkout's `.runtime/vllm.pid.json` launch record configures
`127.0.0.1:18000`; the historical `run-iam-apps.sh` targets `8000`. The loopback
18000 health check returned connection refused on the current host. A PID record
is configuration evidence, not proof that the model is running. The API launcher
requires an explicit address. Do not start another model or change GPU pins.

```bash
# Example only, after verifying this is the existing service address:
export IAM_BASE_URL=http://127.0.0.1:18000
export IAM_SRA_API_PORT=8001
export IAM_SRA_UI_PORT=5001
export IAM_SRA_ALLOWED_ORIGINS=http://127.0.0.1:5001,http://localhost:5001
bash scripts/start-api.sh
```

The foreground process is Gunicorn, never Flask debug/development serving. Ctrl+C
stops this API process and loses its in-memory sessions. The model and Streamlit
processes are not restarted by this launcher. No access-content log is enabled.
Use `IAM_API_PYTHON` for an explicitly selected compatible API interpreter.

Check port availability first (`ss -ltn`); 5001 and 8001 were unused during this
verification, and Gunicorn successfully bound `127.0.0.1:8001`. Recheck before
each launch. Gunicorn binds strictly and will fail if its port is occupied. Verify
health after startup:

```bash
curl --fail --max-time 15 http://127.0.0.1:8001/v1/health
.venv-api/bin/python scripts/smoke-api.py --base-url http://127.0.0.1:8001/
```

Readiness failures are safe/actionable and do not turn assessment into a fixture.
The API has no `IAM_MOCK` production fallback. Health checks do not generate model
answers. A live assessment action needs the configured existing Qwen/vLLM service.

## Session/job deployment limits

This is an initial internal, single-process deployment, not persistent or
horizontally scalable hosting. Restart loses sessions and signed owner cookies
unless a stable operator-managed `IAM_SRA_API_SECRET` is configured; even with a
stable secret, the assessment store is still lost. Keep secrets out of Git and
URLs. Do not enable preload, extra Gunicorn workers or multiple replicas.
The Gunicorn configuration rejects multiple workers/preload; the API also rejects
WSGI requests marked multiprocess.

Defaults and bounds are defined in the factory:

| Variable | Default | Meaning |
| --- | --- | --- |
| `IAM_SRA_MAX_SESSIONS` | 32 | Live session capacity |
| `IAM_SRA_QUEUE_SIZE` | 8 | Waiting actions, plus one executing action |
| `IAM_SRA_JOB_TIMEOUT` | 600 seconds | Total accepted-job deadline including queue wait |
| `IAM_SRA_SESSION_TTL` | 3600 seconds | Idle expiry |
| `IAM_SRA_SESSION_MAX_AGE` | 14400 seconds | Absolute expiry even while polling |
| `IAM_SRA_RESULT_TTL` | 300 seconds | Finished-job retention |
| `IAM_SRA_MAX_RESULTS` | 128 | Finished-result capacity |

Each job receives a private controller copy and fresh model clients, with the
existing `external_deadline` bound. The service never takes the non-reentrant
global model lock around client methods that already take it. A timed-out or
cancelled candidate cannot publish state after reset/correction/expiry. Reads and
polls use cached presentation snapshots rather than waiting for inference.

Python cannot safely kill a blocked thread. The public job fails on its deadline;
an unresponsive underlying call continues to occupy the sole execution lane until
it returns or the API process is shut down. It cannot spawn a second inference
lane or commit a late result. If the lane is stuck, stop/restart only the owned
API process, accepting loss of its in-memory sessions. Do not restart unrelated
model services to recover an API session. Existing Streamlit traffic can also use
the configured model service; its own process lock is not a cross-process lock.

## Frontend development and built serving: pending donor access

The target standalone application is IAM-SRA, assessment IAM-SRA2, suite IAM-SRA,
one tool `sra-assessment`, work route `/tools/sra-assessment/app`, browser prefix
`/api/sra-assessment`, and component `app/src/tools/sra-assessment.vue`.

The actual donor must be inspected before adapting its tool registry, shared API
wrapper, useAsync/AsyncState, forms, router, shared chrome, lockfile, proxy allowlist
and serve_app.py. Generated styles must remain byte-identical. Retain compatible
upstream infrastructure variables rather than renaming them blindly.

Host development (Vite) and built serving (serve_app.py) commands cannot yet be
reproduced because their actual CLI/env/rewrite definitions have not been read.
Do not present guessed npm commands, fabricated registry fields or an invented
proxy schema as verified donor conventions. The intended UI port is 5001 if free,
with strict binding to 127.0.0.1. All browser calls must use the shared wrapper and
same-origin prefix; no browser request may target the model or raw API host.

Pending browser checks: catalogue/detail/working deep link and refresh, full
synthetic interview, cleaned preview, job polling/reset/navigation cancellation,
ownership cookies, CSRF, errors/download headers, unknown-tool rejection,
desktop/mobile and keyboard operation. No browser storage may retain answers,
results or session credentials. None of these frontend checks is claimed complete.

## Container and cluster handoff

No frontend Docker image or cluster manifests are labelled donor-compatible until
the donor's actual Dockerfile and deployment conventions are verified. Do not
assume a container's localhost reaches `davinci` or another container. Merely
adding host-gateway does not expose a host service bound only to loopback.

The first working deployment should remain host-based so the existing loopback
model service can be reused. On Linux a deliberately selected host-network API
container could use host loopback, but it still needs explicit source mounts,
verified connectivity, one API process and compatible security settings. Do not
rebind vLLM publicly. A bridge-network deployment needs an explicitly approved
reachable backend; that platform decision remains open.

Before any future cheetara/cluster work, choose an authorised personal directory
under `/SSD_500GB/<authorised-user>/<project>` and verify the donor's loopback,
ClusterIP and SSH-tunnel rules. No cheetara connection, dataset transfer, cluster
change, endpoint publication or repository push was performed for this task.

SSH example for an authorised host deployment, once its UI/API ports are running:

```bash
ssh -L 5001:127.0.0.1:5001 -L 8501:127.0.0.1:8501 <user>@<authorised-host>
```

Then the preserved Streamlit app is on local port 8501 when launched; the Vue UI
will be on local port 5001 only after donor adaptation is completed and launched.

Central onboarding handoff still needs: reviewed tool registry fields, tool ID
and route above, runtime origin/secure-cookie configuration, verified proxy prefix
rewrite and header forwarding, `/v1/health`, one API worker/replica, CPU/memory and
queue capacity measurements, approved source provisioning, existing model service
connectivity, institutional privacy/retention decisions, and any hub authentication
or SSO requirements. No central registry API or SSO claim is invented here.

## Preserved Streamlit path and rollback

To run the existing Streamlit experience with the verified current model endpoint:

```bash
cd ~/iam-sra-demo
IAM_BASE_URL=http://127.0.0.1:18000 IAM_MOCK=0 \
  IAM_ASSESSMENT_MODE=retrieval_grounded_conversation bash scripts/start-ui.sh
```

Use `18000` only if verified for that host; this is the pre-existing path.
Open `http://localhost:8501` through the appropriate SSH forwarding.

For rollback, stop only the new API/UI foreground processes or their dedicated
operator service units. They do not own the existing model or Streamlit services.
Keep `.venv-privacy`, `.venv`, source documents and weights. Preserve this feature
branch and its changes before switching away: commit the reviewed integration or
stash its tracked and untracked source changes, then `git switch main`. The
starting rollback commit is `e8ee21012779e0b6980c7f9ea41770f27cad9ed6`.
To reverse only this continuation, compare against the saved starting manifest
and restore only reviewed integration files from the source snapshot. Do not
restore the entire directory over newer work. The starting snapshot contains the
pre-existing uncommitted API work; `main` does not contain that work.
Do not use `git reset --hard`, remove runtime data or delete environments to roll
back this interface layer. A safe separate old-source checkout is also possible:

```bash
git worktree add --detach ~/iam-sra-before-vue e8ee21012779e0b6980c7f9ea41770f27cad9ed6
```

That separate checkout needs explicit references to the existing environments and
approved private sources; it does not automatically copy them. Switching the
clean original checkout back to `main` is simpler after preserving feature work.

## Verification record

The focused synthetic API suite exercises the actual controller, with explicit
authored corpus/model/detector fixtures rather than live semantic validation.
It covers confirmation/correction/back, accepted/declined scenarios, information
and reflection, final review, abstaining provisional estimate, null scores,
ownership/CSRF, stale/duplicate/invalid actions, capacity, timeout/expiry, reset
fencing, cleaned previews, blocked credentials before retention and JSON/JSONL.
An additional marked check uses the real pinned detector and reviewed local
corpus for onboarding/preview without calling Qwen.

Run locally after API dependency setup:

```bash
PYTHONPATH=src .venv-api/bin/python -m pytest -q tests/test_api_integration.py
PYTHONPATH=src .venv-api/bin/python -m pytest -q
PYTHONPATH=src .venv-api/bin/python eval/run.py --mock --repeats 1
```

Observed results and final diff review will be recorded after the checks finish.
Frontend build/proxy/browser/container/cluster and live model checks remain
explicitly unverified because their prerequisites are unavailable here.
