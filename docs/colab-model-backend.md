# Temporary Colab inference for IAM-SRA2

The prepared notebook is [notebooks/colab-model-backend.ipynb](../notebooks/colab-model-backend.ipynb). Upload **only that notebook** through Colab's File → Upload notebook. It has no saved outputs, credentials or project source documents. It is an alternative model-host procedure, not a change to the interview, screening or scoring code.

## Requirements

- A paid Colab GPU runtime with an available **L4 or A100** and at least 40 GiB disk headroom. The existing unquantised FP16 Qwen3-8B weights require about 15.27 GiB before activation/cache memory; the normal 16 GB T4 does not fit this configuration. Availability and session lifetime are not guaranteed.
- A davinci SSH endpoint reachable from Colab, a trusted ED25519 server fingerprint and permission for reverse forwarding. An internal/VPN-only `davinci` hostname is not sufficient. The notebook tests connectivity before package/model installation. Ask the administrator for the externally reachable hostname and forwarding policy if necessary; this procedure does not change network/firewall settings.
- Permission to process the chosen synthetic examples and selected source-derived passages in a Google-hosted runtime. Originals, corpus and audit/export files remain on davinci, but screened model prompts can contain selected private source-derived material. The previous entirely local processing description no longer applies to inference. Do not treat screening as guaranteed anonymisation.

Google's [Colab FAQ](https://research.google.com/colaboratory/faq.html) describes restrictions on SSH/web-interface use in free runtimes and their removal for paid plans with a positive compute balance. Paid service still has variable resources and session limits. This is a temporary experiment; it is not a reliable hosting commitment.

## Procedure

1. Open the notebook in Colab and select Runtime → Change runtime type → L4 or A100 GPU.
2. Run its GPU/connectivity cells. Add its temporary **public** key to your davinci account as instructed, preserving existing keys. Never upload an existing SSH private key. Verify the server host fingerprint from your already trusted davinci terminal.
3. Start the private reverse forward. On davinci, verify `ss -ltn 'sport = :18000'` shows **only `127.0.0.1:18000`**. Stop if the server forces a public/wildcard bind. Loopback is accessible to other local users on a shared host, so use synthetic examples.
4. Run the isolated Python 3.10 installation and model cells. They preserve Qwen revision `b968826d9c46dd6066d109eabc6255188de91218`, vLLM 0.8.5, torch 2.6.0, XFormers 0.0.29.post2, transformers 4.51.3, FP16/V0/XGrammar and a 4096-token context. Existing direct pins are retained; transitive packages are recorded, not asserted to be bit-for-bit identical. Nothing is installed on davinci.
5. Once model health passes, run on davinci:

```bash
cd ~/iam-sra-demo
IAM_BASE_URL=http://127.0.0.1:18000 scripts/health-check.sh
scripts/stop-ui.sh
IAM_MOCK=0 IAM_BASE_URL=http://127.0.0.1:18000 \
IAM_ASSESSMENT_MODE=retrieval_grounded_conversation scripts/start-ui.sh
```

Wait a few seconds, then run:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 scripts/health-check.sh
```

Both services must be healthy. Open the existing UI at `http://127.0.0.1:8501` using the same laptop-to-davinci port forward as before, and start a fresh session. Do not run `recover-model.sh` for this endpoint: port 18000 forwards to Colab, so it is not a local project model to restart. The notebook launches vLLM directly because the existing davinci launcher intentionally accepts only A30/V100 hardware.

```text
Browser → Streamlit/privacy screening on davinci
        → davinci 127.0.0.1:18000 → private SSH forward
        → Colab 127.0.0.1:8000 → pinned Qwen3-8B
        → existing output screening/session/export on davinci
```

The model API is not given a public URL. No ngrok/Cloudflare tunnel, cloud PII service or change to shared GPU workloads is introduced. Do not expose its unauthenticated API on the network.

## Verify and finish

Run the existing cases against the forwarded service:

```bash
IAM_BASE_URL=http://127.0.0.1:18000 PYTHONPATH=src \
.venv-privacy/bin/python scripts/smoke-baseline.py --conversation \
  --benchmark eval/conversation_meeting_cases.json \
  --output .runtime/conversation-colab-live.json
```

Inspect initial interpretations, adaptive questions, privacy outcomes and exports. Scripted confirmations are automation. Health/model-list checks are not proof of guided-JSON compatibility or semantic accuracy.

Run the notebook cleanup cell, remove the exact temporary key line from davinci's `~/.ssh/authorized_keys`, and disconnect/delete the Colab runtime. No other authorized keys or server processes should be removed. This does not promise forensic memory/storage erasure. The UI's model endpoint will be unavailable after the tunnel stops; restart the UI with a working endpoint before its next use.

## If `nvidia-smi` is missing

`FileNotFoundError: 'nvidia-smi'` means the selected runtime cannot find NVIDIA's GPU-management executable. It commonly indicates a CPU/TPU runtime or a local runtime rather than a hosted Colab GPU. Select **Runtime → Change runtime type → L4 or A100 GPU**, save, reconnect and rerun the notebook from the first cell. Do not install a similarly named Python package or NVIDIA drivers inside the notebook to solve an unallocated GPU.

Run `!nvidia-smi` in a Colab code cell to check the allocation. If only T4 is offered, it does not have enough VRAM for the current FP16 configuration; an eligible paid plan/compute balance and available L4/A100 hardware are required for this procedure. Paid access does not guarantee availability. The notebook now stops with these instructions when the executable is missing, or a separate safe message when its driver/query fails. Python 3.13 in the notebook traceback is expected on newer Colab images; the later model-installation step creates its own Python 3.10 environment.

## If Colab cannot resolve `davinci`

`gaierror: [Errno -2] Name or service not known` occurs before an SSH connection or authentication. Colab's DNS cannot resolve the supplied hostname. A short university hostname or a `Host davinci` alias in your personal SSH configuration is not automatically a name Colab can use. Changing the port or username cannot fix this DNS error.

On the **computer you normally connect from**, find the `Host davinci` entry in its SSH configuration (usually `~/.ssh/config`) and use the actual `HostName` value. A configured `ProxyJump` or required VPN is an additional access dependency; the current notebook does not reproduce those routes. Even a full hostname/IP must be reachable from Colab. Ask the administrator for an approved externally reachable SSH endpoint if the existing address is private/internal. Do not upload your SSH configuration or private keys into the notebook.

The notebook now reports DNS failure, connection refusal, timeout and other connection errors separately, before key creation or model installation. It cannot create external network access. Stop this setup if no approved route exists rather than repeatedly changing the port or disabling host-key checks.

## Verification status

Prepared on 14 October 2026 against dirty local commit `fc5b69a`. Notebook JSON structure, all code-cell syntax, runtime pins, model revision, localhost bindings and documentation commands were checked locally. The notebook was not run on a Colab GPU; installation, network reachability, server forwarding policy and live model behaviour remain unverified. No host service was restarted and no project data was uploaded or pushed.

The notebook uses an isolated Python 3.10 environment because current Colab's default Python can be newer than this repository's supported versions. See [vLLM 0.8.5 installation](https://docs.vllm.ai/en/v0.8.5/getting_started/installation/gpu.html), [uv environments](https://docs.astral.sh/uv/pip/environments/) and [OpenSSH forwarding](https://man.openbsd.org/ssh#R).
