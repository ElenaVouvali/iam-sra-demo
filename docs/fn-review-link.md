# Temporary FN browser review on Liono A2

FN needs only a browser link. The operator starts the review once on Liono;
FN does not run commands, SSH, port forwards or a VPN. A Cloudflare Quick Tunnel
provides a temporary public HTTPS URL, forwarding to the existing local Vue
server. Vue's bounded same-origin proxy forwards API calls to local Gunicorn,
which calls the project-managed Qwen on **Liono A2**.

No public Liono hostname, inbound firewall opening, sudo, Cloudflare account,
DNS change or new application environment is required. Outbound access to GitHub,
Cloudflare and the tunnel service must be permitted by Liono's network.
This launcher uses HTTP/2 on outbound TCP port 7844; it does not alter firewall rules.

## Start

In Liono's normal terminal (not the restricted agent execution environment):

```bash
cd ~/IAM_CC/iam-sra-demo
.venv-api/bin/python scripts/share-fn-review.py
```

The script prints **`FN test link: https://…trycloudflare.com/chat`** only after
checking the public page/API, Secure ownership cookie, CSRF and blank interview
creation/deletion. Copy the actual printed URL to FN. It is also written to
`.runtime/fn-review/chat-url.txt` while active. No preassigned URL is available;
a new tunnel normally gets a new address. These checks do not run a model
interview or prove semantic quality.

Keep this terminal open. Ctrl+C (or termination/hangup) stops **only** the review
API, frontend and tunnel created by the script and removes its active-link file.
The existing project-supervised A2 model stays running for normal use. If the
normal terminal may disconnect, run the command in an existing `tmux` session.

## What it changes

- Model default: `127.0.0.1:18003`. Review API prefers port 8018 and
  automatically searches 8018–8117 when busy; Vue/proxy prefers 5018 and
  searches 5018–5117. The selected ports are printed at startup. Explicit
  `--ui-port`/`--api-port` choices are honoured or rejected with the conflicting
  port number. None of these listeners is made public directly. Existing
  Davinci forwarding and application ports 18002/8017/5017 are left alone.
- Starts A2 through `model-host.py` and the existing GPU identity/workload guards.
  It will not use another GPU or stop a busy workload. It reuses only this
  checkout's live recorded A2 supervisor at the requested endpoint. An existing
  project model with a different profile/port is not stopped to make room.
- Uses the existing model environment/cache, API environment, built `app/dist`,
  private sources, source checks, privacy screening and existing one-worker API.
  Missing resources remain a startup error. No dependency reinstall/model
  download is attempted; normal A2 startup may be slow with weight offload.
- Uses installed `cloudflared` when available. Otherwise downloads the official
  Linux release into ignored `.runtime/tools`, checks GitHub's release SHA-256,
  and disables binary auto-update. It refuses a missing/mismatched digest.
  Existing Cloudflare account configuration is not read or changed.
- Sets only the issued HTTPS origin as allowed, enables Secure cookies, and
  checks the real cookie/CSRF flow before publishing the link. It keeps current
  session ownership, retention, queueing, correction and export protections.

Cloudflare relays the web traffic, including text before local privacy screening.
This is a **public temporary test link**: anyone with the URL can open it. Use
fictional/general answers for FN's prototype review. Original private PDFs and
model endpoints are not published. This is not a permanent or access-controlled
hosting arrangement. Quick Tunnels are for testing, with no availability SLA.

## Troubleshooting

The startup message identifies failed checks. A busy A2/model or port is retained;
no competing service is killed. Busy default API/UI ports are skipped
automatically; rerun the ordinary command without explicit port flags. Optional
port changes must use three distinct
ports; an already supervised model's endpoint must still match:

```bash
.venv-api/bin/python scripts/share-fn-review.py --dry-run
.venv-api/bin/python scripts/share-fn-review.py --gpu-uuid GPU-YOUR-ALLOCATED-A2-UUID
```

If GitHub downloads are blocked, install `cloudflared` through the university's
approved mechanism, then rerun. If outbound tunnel traffic is blocked, the lab
administrator must provide an authorised HTTPS reverse proxy instead; changing
`HOST=0.0.0.0` cannot bypass that restriction. For a permanent address or restricted
FN access, use an institutional HTTPS address or a configured named tunnel.

## Verification record

The focused launcher, GPU-selection and QR checks passed **56 tests**. They
use controlled downloads/process records and an in-process
real Flask cookie/CSRF flow. They create no real public tunnel or GPU allocation:

```bash
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract PYTHONPATH=src \
  .venv-api/bin/python -m pytest -q tests/test_fn_review_link.py tests/test_model_host.py
```

On 24 November 2026 this agent execution environment could not access the NVIDIA
driver, create network sockets (`Operation not permitted`), or resolve GitHub.
Activation therefore requires the normal Liono terminal. No live URL, A2 inference
or public-network reachability has been claimed for this launcher here.

References: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
[official cloudflared downloads](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/),
[Flask deployment guidance](https://flask.palletsprojects.com/en/stable/deploying/).
