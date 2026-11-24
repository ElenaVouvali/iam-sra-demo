# Davinci A30 live FN review

The live check uses Davinci's A30, with the application/API/privacy environment
on Liono. It does not use Liono's A2. The existing FN sharing launcher was
identified by PID, user, working directory and exact script before the
user-authorised SIGINT; its sharing lock was confirmed released.

## Deployment

- GPU: NVIDIA A30, `GPU-ac0112df-7098-6c59-5c4f-a57fa666f808`.
- Model: full-precision `Qwen/Qwen3-8B`, revision
  `b968826d9c46dd6066d109eabc6255188de91218`, half dtype, zero CPU offload.
- Existing vLLM 0.8.5, Torch 2.6.0, Transformers 4.51.3, XFormers 0.0.29.post2.
- V0 engine, `deepseek_r1` reasoning parser, 8,192-token context, one sequence.
- Private model port 18004 on both hosts, forwarded over SSH.
- Isolated remote directory `~/iam-sra-fn-a30-review`. Only inference helpers
  are uploaded. Its environment and Hugging Face cache link to the existing
  `~/iam-sra-inference` installation; dependencies are checked without upgrades.
  The original inference directory/service record is preserved.

The model-host launcher now permits thinking on A30/FP16 as well as A2/AWQ.
Other GPU profiles retain their previous behaviour. This does not configure
remote A30 on-demand hosting for the public sharing launcher, which remains
A2-specific.

## Initial actual-model probes

`fn-a30-thinking-opening-20261124-1` exposed a semantic failure: valid JSON
labelled the FN drone definition and known-use list as declined. No schema,
privacy or timeout failure was reported. Explicit definitions for the six
answer categories were added to the existing interpretation prompt, including
the distinction between a substantive concise answer and an explicit refusal.
No reference respondent answer was added as a production matching rule.

`fn-a30-thinking-opening-20261124-2` then passed: both answers were interpreted
as substantive/explored and the controller reached healthcare awareness without
fallbacks or failures. This used two real interviewer generations, 1,170 total
output tokens, 33.979 seconds of generation HTTP time and 56.569 seconds overall.
The separated reasoning channel was observed (3,877 characters, discarded).
These two probes demonstrate a specific correction, not general semantic accuracy.

## Full synthetic interviews

The first full four-case live agent run is saved under
`.runtime/fn-a30-thinking-agent-20261124-1/`, with progress in the adjacent `.log`.
All four stopped before scoring. Short citizen failed priority coverage and
also exposed wrong knowledge branches. Extended citizen, organisation and
technology failed an irrelevant optional `topic_intent_quote` length bound.
Their respective interviewer/respondent call counts were 9/10, 4/3, 2/1 and 5/4.
All four retained JSON, JSONL, Markdown and screened decision traces.

The corrections distinguish answer polarity from whether a question was
addressed, constrain generated goal/evidence identifiers, inherit the current
answer disposition consistently, ignore irrelevant optional topic-intent hints,
and require selected issues to survive topic validation before advancing.
Focused live probes now recognise the original unfamiliar/negative answers
correctly and preserve both noise and wildlife as priorities. Ordinary agent
text is retained even when its separate control hint contradicts it; unknown
knowledge must not be replaced by a fabricated refusal.

The repaired four-case run is saved separately under
`.runtime/fn-a30-thinking-agent-20261124-2/`; its final results are pending.
Its fictional respondent uses Qwen's soft `/no_think` mode, while the interviewer
and scorer retain thinking and the server's reasoning parser. This changes the
test simulator, not the application interviewer. The API hard thinking switch
remains enabled for compatibility with the pinned parser.
The harness uses the real isolated Flask API, privacy, interviewer, scorer and
Qwen respondent, with fictional personas and no target readiness levels.
`--save-traces` saves screened controller decisions and concise model summaries
for those owned synthetic sessions; it never retains raw reasoning. Trace files
are private (0600). The production developer API remains separately authenticated.

Same-model respondent simulation is not independent semantic validation. Inspect
the answers against persona facts, and inspect the selected level, exact evidence
and boundary explanation. Automated E review choices are not FN agreement.

## Reproduce

From Liono, using the already prepared isolated remote directory:

```bash
cd ~/IAM_CC/iam-sra-demo
.venv-api/bin/python scripts/model-host.py start davinci-a30 \
  --variant fp16 --thinking --remote-dir iam-sra-fn-a30-review --port 18004 \
  --gpu-uuid GPU-ac0112df-7098-6c59-5c4f-a57fa666f808
```

Keep that tunnel terminal open. In another Liono terminal, without a sharing
launcher, use a fresh output directory:

```bash
IAM_SRA_ON_DEMAND_GPU=0 IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
IAM_CHAT_PROCESSING_SECONDS=7200 IAM_CHAT_MAX_CALLS=96 \
TLDEXTRACT_CACHE=/tmp/iam-sra-publish-tldextract \
  .venv-api/bin/python scripts/smoke-fn-interview.py \
  --allow-live --respondent agent --respondent-no-think --model-variant fp16 --thinking \
  --require-scoring --save-traces --base-url http://127.0.0.1:18004 \
  --case all --case-timeout-seconds 7200 \
  --output .runtime/fn-a30-thinking-agent-review-next
```

Limits are operational safeguards, not interview completion or score thresholds.
The model-host command is always-on until explicitly stopped; closing its SSH
tunnel alone does not release the GPU. Stop only this isolated model after tests:

```bash
ssh evouvali@davinci.microlab.ntua.gr \
  'cd ~/iam-sra-fn-a30-review && .venv/bin/python scripts/ops.py stop vllm'
```

The stop helper checks the exact recorded process identity. Do not kill arbitrary
GPU PIDs. No public FN link or institutional DNS name is created by this test.
