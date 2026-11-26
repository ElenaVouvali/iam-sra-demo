# FN feedback refinement — A2 validation status

## Provenance and isolation

The refinement worktree is on `exp/fn-eva-feedback-a2`, based on
`30687bccf0c4e762513dccc1b6e86f658d1ea832`, the source commit present in the
V100S checkout when its review launcher started. The serving launcher, API and
frontend processes were verified in `/home/elvouvali/IAM_CC/iam-sra-review-v100s`;
they remain untouched. The checkout later advanced to `4ba9dd81f0b766589b6f2350a54ce90e6688e19c`,
but that commit was not the revision loaded by Eva's running V100S processes.

Private registered references are read through a local symlink and are not
included in this branch. No private PDFs, model files, runtime transcripts,
tokens or review URLs are committed.

## Changes

- `ChatConversation.vue`: keeps the open-text composer beside all selectable
  answers, adds simple pause/skip/finish controls, retry wording, delayed
  processing feedback, and an optional post-review feedback field.
- `chat_session.py`: after a negative or uncertain citizen drone-recognition
  answer, requires the existing FN explanation branch before model-led routing
  can move on. Directly supplied explanations remain exposure records, not
  respondent knowledge. Pause/resume restores the actual last displayed
  question, and the substantive summary is withheld during pause and excludes
  administrative perspective/city selections. Optional UX feedback is stored
  separately and cannot alter evidence, scoring or the participant review.
- `schemas.py`, `adapter.py`, `service.py`: adds a bounded `chat_feedback` action
  that is privacy-screened, CSRF/session/version protected, allowed only after
  participant review, accepted once, and does not construct model clients or
  enter the readiness-interview action path.
- `eval/fn_generalisation_additional_personas_v1.json`: adds the fictional
  `eva_coimbra_extended_multiconcern` persona. It has no target level; the
  synthetic respondent receives participant facts and style, not the expected
  observations or prohibited-inference checks.
- Regression tests cover negative recognition routing, pause/resume and summary
  visibility, feedback separation and one-time API handling, and text entry
  alongside options.

The official FN materials and registered 15-indicator/readiness banks were not
modified. Indicator projection remains internal and conservative.

## Verification

- Selected Python/FN/controller/API regression group: **286 passed, 7
  deselected**. The deselected items require external live-browser or other
  excluded conditions; privacy-specific suites were run separately.
- Privacy and baseline privacy regressions, including the real local privacy
  resources check: **102 passed**.
- The new registered persona was loaded through the existing live-harness
  loader and screened successfully; it contains no target score.
- Vue chat component tests: **19 passed**.
- Vue production build: **passed**.
- A local API/frontend pair started on isolated ports 8096/5096, but Firefox
  failed before the real-browser flow began (`Failed to launch the browser
  process`, exit code 11, during headless GPU/X initialization). The test-owned
  API and UI processes were then stopped. No model request was sent.

## A2 live-test status: blocked by occupied hardware

The installed A2 service is already occupied: `nvidia-smi` reported **12,383
MiB / 15,356 MiB** in use. The resident supervisor/model process belongs to the
older project worktree, serves port 18023, and runs Qwen3-8B-AWQ with thinking,
the DeepSeek R1 reasoning parser and 8,192 context. A separate A2 review
launcher/API is also running from the published checkout on UI/API ports
5022/8022, configured for model port 18021. I did not start another model,
borrow the active service for a long interview, or affect that review instance.

Therefore **no live interview, numerical score, transcript, participant review,
export, latency result or A2 browser acceptance is claimed for this refinement**.
The A2 GPU must be confirmed free and the review owner must confirm the active
instance is not in use before the bounded live run below. This is not an
acceptance pass.

## Reproduce the offline checks

```bash
cd /home/elvouvali/IAM_CC/iam-sra-eva-feedback-a2
TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
PYTHONPATH="$PWD/src" \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python -m pytest -q \
  tests/test_fn_model_led.py tests/test_fn_interview.py \
  tests/test_chat_conversation.py tests/test_chat_choices.py \
  tests/test_api_integration.py -m 'not presidio_live' \
  --deselect=tests/test_api_integration.py::test_api_real_privacy_resources_context_preview

TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
PYTHONPATH="$PWD/src" \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python -m pytest -q \
  tests/test_privacy.py tests/test_baseline_privacy_v2.py \
  tests/test_api_integration.py::test_api_real_privacy_resources_context_preview

cd app
/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin/node \
  --experimental-vm-modules tests/chat_conversation.test.mjs
/home/elvouvali/IAM_CC/.tools/node-v22.23.5/bin/node node_modules/vite/bin/vite.js build
```

## Later A2 interview command

After the A2 GPU is free and the project-owned A2 review instance is confirmed
idle, first verify that the exact endpoint on port 18021 responds at `/health`
and `/v1/models` with the pinned Qwen3-8B-AWQ model, `--enable-reasoning`,
`deepseek_r1` and 8,192 context. Then run one sequential extended-citizen
interview; keep output in a new ignored runtime directory:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-eva-feedback-a2
TLDEXTRACT_CACHE=/tmp/iam-sra-eva-tldextract \
IAM_MODEL_VARIANT=awq IAM_MODEL_THINKING=1 \
IAM_CHAT_INTERVIEW_STRATEGY=model_led_fn IAM_SRA_ON_DEMAND_GPU=0 \
IAM_BASE_URL=http://127.0.0.1:18021 \
IAM_MODEL_TIMEOUT_SECONDS=900 IAM_SRA_JOB_TIMEOUT=1800 \
/home/elvouvali/IAM_CC/iam-sra-demo/.venv-api/bin/python \
  scripts/smoke-fn-interview.py --allow-live --respondent agent \
  --respondent-no-think --case citizen_extended \
  --persona-id eva_coimbra_extended_multiconcern \
  --model-variant awq --thinking --base-url http://127.0.0.1:18021 \
  --save-traces --max-agent-calls 60 --max-turns 100 \
  --case-timeout-seconds 3600 \
  --output .runtime/fn-eva-a2-coimbra-extended-20261126
```

The synthetic respondent is Qwen-generated and is not independent human
validation. Inspect the complete transcript, question repeats, information
exposures, concern evidence, projection, score/abstention, adjacent boundary,
participant review and export before making any review-readiness claim.
