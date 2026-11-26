# Experimental model-led FN interview on Davinci V100

## Purpose and status

This isolated branch adds the opt-in `model_led_fn` interview strategy. The baseline `controller_fn` remains the default. The experiment reuses the existing Vue, Flask, Qwen client, FN specification, privacy screening, evidence validation, scorer, review flow and exports.

The official, locally registered Future Needs interview examples define the methodological stages and profile-specific boundaries. The registered readiness bank remains the source for all nine CRL, ORL and TRL anchors. The interview PDFs and their identities are not changed. The A30 G2/G5/G7/G10 findings in the development report are diagnostic examples, not answer templates or scoring targets.

## Model-led controller

Onboarding and role/scope establishment remain stable. Once the respondent's profile-specific scope is established, the existing Qwen interpretation request also proposes the next goal, action and participant-facing question. The request includes a compact FN stage ledger, applicable objectives, current evidence references, priorities, scope and unresolved gaps. It does not send the PDFs or their full text.

Qwen can select any registered, applicable, uncovered objective, including one in a later stage, and can reuse exact respondent evidence for several objectives. Python verifies objective identity and applicability, exact evidence IDs and quotations, the current answer's required coverage, active evidence after corrections, question quality, repetition, profile scope and operational limits. It accepts or rejects the proposal and records a screened decision trace without hidden reasoning. A rejected proposal gets one bounded model retry; if still invalid, the controller asks one FN-mapped bridge question for the first unconsidered stage. It does not resume the old first-uncovered question scheduler.

An FN stage is considered when at least one applicable objective in that stage has grounded evidence, an explicit negative/uncertain/refused answer, or a valid inapplicable disposition. This is a methodological coverage state, not evidence of readiness. Unasked objectives remain individually visible in the structured record and can be selected by Qwen where they add useful evidence; optional/detail objectives are not an automatic checklist. A conclusion proposal is accepted only after every applicable FN stage is considered. An acknowledged unknown remains an uncertainty and does not make an otherwise complete interview an early/partial interview.

## Evidence and scoring

Original screened answers remain authoritative. Semantic labels are annotations, not replacements. Corrections invalidate evidence-derived coverage from superseded answers while retaining revision history. The priority mode is still respondent-specific.

The existing scorer compares active evidence with the full registered nine-anchor scale for the selected profile and assessed scope. It must cite active original answers, justify the selected anchor, and explain the substantive adjacent boundary. The scorer now has a structured consistency field for contradictions between its explanation and active evidence. A detected contradiction or unchecked consistency result is rejected for one bounded revision; persistent failure produces an unavailable result, not a fabricated score. Existing citation, scope, anchor-identity and participant-review validation remains in force. No individual SRL or cross-profile average is produced.

## Before and after

**Before (observed A30 G7 pattern):** a respondent reported a completed supervised pilot, assigned responsibilities and tested procedures; the conversation continued probing preparation, and the proposed ORL explanation said preparation was absent.

**After (experimental behavior):** the ledger allows that one answer to support the relevant planning, preparation and validation objectives while retaining “no routine operations” as a separate limit. Qwen may next ask whether pilot lessons entered regular procedures. The scorer must compare its claims with the cited pilot evidence and distinguish pilot activity from routine integration. This is a regression target, not a claim that the live V100 behavior has passed.

## V100 browser preview

The deployment path keeps Vue and Flask on Liono and uses the existing SSH forward to Davinci V100. The launcher has an added model-led prepublication gate: after the existing real-generation probe, it runs one complete Qwen-powered synthetic citizen interview through score, review and exports using the selected model-led strategy. No public link is opened if that gate fails. The synthetic respondent does not receive a target score. A successful gate is not a substitute for manual semantic review or FN approval.

The supported launch command, from this worktree on Liono, is:

```bash
IAM_CHAT_INTERVIEW_STRATEGY=model_led_fn \
../iam-sra-demo/.venv-api/bin/python scripts/share-fn-review.py \
  --gpu-profile davinci-v100 \
  --model-variant fp16 \
  --thinking \
  --model-port 18020 \
  --remote-dir iam-sra-v100-fn-model-led \
  --idle-seconds 300 \
  --interview-strategy model_led_fn
```

`--thinking` selects the repository's FP16 thinking parser and 8,192-token context. Omitting it selects non-thinking mode with the model-host's standard context; those are distinct configurations and must not be compared as if identical. The launcher pins the registered Qwen checkpoint, prepares an isolated marked remote directory, tracks its model lease, runs the live gate, then starts the existing Vue/API and temporary HTTPS tunnel. It prints the actual URL only after health, origin, CSRF and link checks succeed. This document does not assert that a URL has been generated.

The temporary Cloudflare hostname is publicly reachable by anyone who receives it; the URL itself is not access control, and browser traffic is relayed through Cloudflare before application-side screening. Use only authorised fictional/general test content unless institutional review has approved the data flow. Do not enter identifiable participant data, credentials, or medical records. The existing server-side screening remains active but cannot prevent third-party relay exposure before the request reaches Liono.

Keep the launcher terminal or its `tmux` session open. Inspect authenticated developer traces on the private server filesystem, not through the participant UI. Download the session JSON/JSONL/Markdown using the app's existing export controls. Stop only this launcher with Ctrl+C; its ownership-aware cleanup handles services it started. Do not stop another launcher or GPU process. The baseline checkout and review deployment are separate; to return to the baseline code, use its existing worktree and branch (`feat/fn-v42-citizen-adaptive`) rather than switching this experimental checkout under a running service.

## Validation and limitations

On the experimental worktree at base `57f8235010f280ae4fda3c48a9e41dcfbd55eee8`, the focused Python regression group passed **409 tests** across model-led routing, FN interview/interpretation, scoring, privacy, review-link prepublication validation and exports. The Vue production build passed under Node 22.23.5; all **18** existing chat-component tests passed. Python compilation and `git diff --check` passed. Two earlier priority-annotation retries are now bounded to one model retry before the existing participant clarification; the regression tests verify no selected issue is silently dropped.

The read-only Davinci preflight reported a 32 GiB V100 with 0 MiB in use and the registered Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`. The first isolated setup stopped before creating a model environment because the home filesystem had about 43 GiB free while the supported installer requires at least 60 GiB. At the user's request, three inactive, marked V100 inference installations were removed; the active manual-review deployment directory was preserved. Davinci home storage then reported about 123 GiB free. The baseline manual-review launcher is still active and owns the preserved V100 review path, so this experimental branch has **not** started a model, run live Qwen validation, driven a browser-backed interview, or generated an experimental review URL. Starting a second on-demand service on the same V100 would risk contending with that review deployment.

The V100 generation probe, the full live prepublication interview and Cloudflare/browser checks must run only after the current V100 preview has been deliberately closed or its operator confirms a coordinated idle window. Use the command below from this experimental worktree then. Do not describe controlled fixtures as live inference, or synthetic-agent agreement as independent validation.

Important remaining limitations: semantic validity of Qwen's proposed question and evidence mapping still requires human review; one-evidence-per-stage is a prototype completion criterion requiring FN/IAM adjudication; a numerical suggestion is provisional and may legitimately abstain when evidence is insufficient; the temporary link is not a production participant service; and the V100 configuration must be evaluated separately from A30 thinking-enabled runs.
