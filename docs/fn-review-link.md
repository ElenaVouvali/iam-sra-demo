# FN browser review on Liono A2, with automatic GPU release

The public HTTPS link can remain running in `tmux` for days **without keeping
Qwen loaded**. The frontend, Flask API, session memory and Cloudflare tunnel run
on CPU. The review now opts into on-demand inference; the normal application
and other model launchers retain their existing always-on behaviour.

## Start or upgrade

If the old sharing launcher is running, press Ctrl+C in its terminal first.
Run the updated launcher in Liono's normal terminal, preferably inside `tmux`:

```bash
cd ~/IAM_CC/iam-sra-demo
.venv-api/bin/python scripts/share-fn-review.py --release-existing-a2
```

### Davinci V100 preview

The same launcher can serve the current Vue/Flask application from Liono while
forwarding inference to a separately prepared Davinci V100. Use FP16 without
thinking; do not select or stop an occupied device. The launcher performs a
real generation probe, then releases its model lease before it prints the
Cloudflare URL. During review, inference starts on demand and is released after
the configured idle interval.

```bash
.venv-api/bin/python scripts/share-fn-review.py \
  --gpu-profile davinci-v100 \
  --model-port 18020 \
  --remote-dir iam-sra-v100-fn-review \
  --idle-seconds 300
```

Copy the printed `FN test link` to the reviewer. The URL is temporary, publicly
reachable and relayed by Cloudflare; use fictional answers only unless
institutional approval and suitable data controls are in place. The launcher
uses a separate remote inference directory and does not use or stop the A30 or
Liono GPUs. Keep the launching terminal/tmux session open while the link is in
use. A V100/non-thinking preview is a different inference configuration from
the A30 FP16/thinking evaluation, so do not compare its score stability or
latency as though they were the same experiment.

Startup now runs **four full live synthetic interviews, including model scoring
and review, before opening a public API/tunnel**. This occupies the A2 during
validation and can take a long time. Failures prevent publication; the reports
are preserved under `.runtime/fn-review/live-*`. A valid model abstention is
allowed only after an actual scoring call. Fixture success cannot pass this gate.
After validation the model is released and ordinary review remains on demand.

Experimental thinking and the administrator-provided stable address are
documented in [FN thinking and live validation](fn-thinking-harness.md). To test
without publishing anything:

```bash
.venv-api/bin/python scripts/share-fn-review.py --thinking --validation-only
```

The default is now the pinned **4-bit Qwen3-8B-AWQ** A2 profile with Marlin and
zero CPU weight offload. First use downloads about 6.1 GB without reserving the
GPU; subsequent starts reuse the validated cache. Original FP16 weights remain
available with `--model-variant fp16`. See [activation, measurements and live
checks](a2-fast-inference.md). Restart the old launcher to activate this change.

`--release-existing-a2` explicitly releases the previous always-on review A2
model at the configured model port (default 18003), after checking its exact
checkout, A2 profile, endpoint, owner UID, PID start time, command and process
group. It never stops another user's workload, another GPU profile or a different
model endpoint. It is unnecessary on later clean runs and harmless when no
matching old review model exists. The launcher otherwise refuses to adopt an
unmarked already-running model automatically.

The script prints **`FN test link: https://…trycloudflare.com/iam-sra-fn-review`** only after
passing live interview/scoring checks and checking the public page, local and public API, Secure ownership cookie, CSRF,
and blank interview creation/deletion. Copy that actual URL to FN. FN needs only
a browser, with no commands, SSH or VPN. The link is also written to
`.runtime/fn-review/chat-url.txt` while active. Startup validation uses real
inference; page/ownership/CSRF checks themselves do not request a model.

Share it with the label **IAM-SRA — FN Review**. The descriptive review path
opens the same chat as `/chat`. Cloudflare assigns the temporary hostname;
a chosen hostname requires a configured domain and named tunnel.

Keep the launcher running. Detach `tmux` with Ctrl+B then D, and reconnect with
`tmux attach -t YOUR_SESSION_NAME`. Ctrl+C in the launcher stops its API/frontend/
tunnel and releases its marked review model. An old temporary URL normally
changes after a new tunnel starts. Sessions still follow the existing temporary
retention policy; a long-lived link does not promise cross-day interview resume.

## GPU behaviour

1. After startup validation releases its model, opening the link, selecting
   perspective/depth, reading status and other controller-only answers do not load Qwen.
2. The first screened answer that actually needs Qwen starts the existing pinned
   model on an available **Liono A2**, using `model-host.py` and existing guards.
   The additional compute-process check also rejects small foreign GPU jobs
   below the legacy 2 GiB occupied-memory threshold. It never preempts them.
3. FN sees “Starting the model” while a cold start waits. Loading can take minutes.
   If the A2 is busy or startup fails, the original answer is kept for **retry**;
   no uncertainty/low readiness is attributed to the participant.
4. After **60 seconds without a model request**, the idle watcher starts shutting
   down this review's vLLM process group, releasing its GPU allocation. It never
   interrupts an active model request. Releasing the process can take additional
   shutdown time. Status/page polling does not extend the idle interval.
5. The next model-dependent answer loads Qwen again, if the A2 is still available.
   The same link and in-memory interview remain usable. Unloading weights does
   not erase or rescore interview evidence.

An optional shorter/longer interval is available:

```bash
.venv-api/bin/python scripts/share-fn-review.py --idle-seconds 60
```

Supported range: 10–3600 seconds. A shorter interval releases resources sooner
but can add cold-start waits between answers. There is no exclusive scheduler
reservation: other users can take the released A2, in which case FN must retry
later. The existing project launcher also refuses a competing project model;
this review does not stop it to make room.

## Implementation and process safety

- `model_lifecycle.py` adds an **opt-in**, single-process inference lease to the
  existing screened HTTP transport. It activates only with
  `IAM_SRA_ON_DEMAND_GPU=1` in the review API subprocess. No second model/proxy,
  orchestration dependency, new scoring technique or extra generation is added.
- Defaults: model `127.0.0.1:18003`; API searches 8018–8117 and Vue/proxy searches
  5018–5117 for free ports. Explicit port choices are honoured or named as busy.
  All listeners stay private; no institutional firewall/DNS change or sudo.
- Every review start carries a unique `IAM_SRA_MODEL_LEASE_ID`, preserved in the
  existing operational PID record. `.runtime/fn-review/model-owner.json` binds
  automatic release to that start. PID/command/start time/UID/group/profile/port
  are verified before any signal. A changed/reused process record is retained.
- Failed partial starts are cleaned up only if they are proven review-owned.
  If release cannot be verified, status becomes **unavailable**, not “idle”.
  Launcher shutdown has a second verified cleanup path after its API exits.
- `GET /v1/inference-status` and capabilities expose only mode/state/idle seconds.
  The browser displays loading/unavailability and polls status without waking
  the GPU. These GET routes cannot start or stop a model.
- Private sources/hashes, original inference pins/environments, screening, ownership,
  CSRF, deadlines, correction, evidence/scoring and JSON/JSONL remain in use.
  Existing answered interview content is not sent during resource checks.

## Tunnel and privacy

Cloudflare relays web traffic **before** local privacy screening. Anyone with the
public test link can open it; use fictional/general answers. The original PDFs,
model endpoint and operational owner records are not published. Quick Tunnels
are temporary test hosting with no availability SLA, not permanent or
access-controlled hosting.

The launcher uses installed `cloudflared`, or downloads its official Linux
release into ignored `.runtime/tools` and verifies GitHub's release SHA-256.
Binary auto-update is disabled. Existing Cloudflare account configuration is not
read/changed. Liono must permit outbound GitHub/Cloudflare access and TCP 7844
(HTTP/2 tunnel). If blocked, obtain an authorised institutional HTTPS reverse
proxy; binding `0.0.0.0` cannot bypass a network restriction.

## Verify on the real host

1. Start the launcher, then open the FN link. Confirm inference status is idle
   and the review has not allocated an A2 model.
2. Answer through recognition to the first semantic answer. Check the loading
   notice, then the normal next question. A review-owned model process should
   exist while it is generating.
3. Leave the page open without model requests for over 60 seconds plus shutdown
   time. The review-owned model should exit, and status should return to idle.
   Other people's A2 processes/memory may remain; this feature releases only ours.
4. Send another answer and check reload/continuation. Test a busy A2 by a
   coordinated existing workload, confirming preserved answer/retry and no
   interference with that workload. Do not create a workload just to occupy
   someone else's allocation.
5. Stop the launcher. Confirm its public link closes and its marked model exits.

Local read-only inspection: `nvidia-smi` and the private operational PID/owner
records. Do not infer GPU release solely from a browser label.

## Automated checks and actual limits

Focused lifecycle tests exercise cold starts, idle expiry, active requests,
concurrency, busy/retry, model restart, privacy-before-start, partial failure,
exact process ownership, PID reuse, replacement records, legacy migration,
small foreign compute jobs and status polling:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_model_lifecycle.py \
  tests/test_fn_review_link.py tests/test_model_host.py tests/test_ops_recovery.py
```

These are controlled lifecycle/process/download checks and in-process real
Flask/HTTP-client cookie/CSRF/interview paths, not live GPU or tunnel tests.
On 24 November 2026 the focused run passed **81 tests**, the separate affected
chat/FN/API/model regression run passed **337 tests**, and the Vue production
build passed (**58 modules**). Existing privacy checks are included in the chat
regressions; no privacy bypass was added.

This agent environment cannot access the NVIDIA driver or open network sockets.
**Actual A2 cold-start latency, physical VRAM release, live inference and public
link uptime remain unverified here.** No GPU process was started/stopped by this
implementation. Run the host checks above before treating this as a verified
multi-day FN service.

References: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
[Cloudflare tunnel network requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/),
[Flask deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/).

The chat now has a separate welcome screen and selectable lettered answers.
See [UI changes and the measured A2 latency diagnosis](chat-ui-and-a2-latency.md).
