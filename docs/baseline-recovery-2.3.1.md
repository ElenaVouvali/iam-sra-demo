# Baseline 2.3.1: response handling and shorter controls

This is a prototype refinement, not approved FN questionnaire wording or a new
readiness scale. All numerical baseline results remain null.

## Question screen

The citizen screen retains Continue (Retry this answer after an assessment
failure), Skip, Finish now and Back. Separate Unsure and Prefer not to answer
buttons and the optional drone-definition expander were removed at the user's
request. Familiarity still has structured uncertainty/withheld responses.
Respondents can write uncertainty or refusal in their answer. The confirmed
interpretation records these distinctly and suppresses repeated probes; an empty
answer is still not automatically treated as uncertainty or refusal.

When the interpretation has no claims but explicitly identifies uncertainty,
refusal or confusion, the review page explains that meaning plainly. It does not
present this as a failed summary or invent evidence.

The definition controller and existing exposure history remain available for
historical/API compatibility. Removing a UI control does not undo prior exposure.

## Effects prerequisite

New sessions freeze instrument/prompt/schema 2.3.1 and routing 1.0.1. An additive
`effect_quote` field identifies a specifically named effect within the exact
supporting answer span. Source and review validators check the quotation. An
effects-reasoning probe requires a confirmed unexplained effect with that field;
the question quotes the effect it refers to. Omissions record
`no_named_unexplained_effect` when no such prerequisite exists. Frozen earlier
instruments retain their original routing flag and records.

Approval, opposition or not knowing what difference deliveries would make is not
itself an asserted effect. Both extraction/review prompts distinguish this from
knowing an effect but being unable to explain its cause. The quoted-effect check
reduces unsupported probing; meaning still requires model review and respondent
confirmation, and is not externally verified.

## Privacy recovery

The reported answer about liking deliveries but not explaining their effects
passes the installed Presidio detector, as do the current context, question,
prompt and provenance controls. The original rejected live model response and
its detector field were unavailable, so its trigger has not been adjudicated and
no recognizer was weakened or arbitrary text allowlisted.

Generated content that fails screening gets a fresh attempt only within the
existing two-attempt/deadline limit. Rejected content is never copied into retry
feedback, traces, caches or audit records. Detector unavailability fails closed.
If model output or a derived assessment record remains unsafe, the screened
answer is retained for retry; no interpretation/question is committed. Actual
input rejection still clears rejected widget text or offers the existing cleaned
preview. Exports remain independently screened and unsafe exports stay withheld.

Baseline failure logs contain screened structural metadata: boundary, request
stage and detector entity/recognizer/confidence/field path where available. They
do not contain the rejected text or model response. Infrastructure logging remains
subject to the limits documented in `privacy.md`.

## Reproduction

`tests/test_baseline_answer_recovery.py` covers opinion/unknown effects, a named
effect, reviewer correction, written uncertainty/refusal, output rejection/retry
and real-detector positive/benign controls. A real-detector round trip uses mocked
model responses and checks final export; this is not live Qwen semantic validation.

`baseline_adaptive_v3.json` is unchanged. Its successor
`eval/benchmarks/baseline_adaptive_v4.json` inherits the original answers and
expectations without relaxation, targeting the new frozen versions/config hash.
Definition-exposure cases now exercise the compatibility API rather than a
citizen UI feature. The existing smoke runner defaults to this successor.

The UI disables source watching, so restart only the project UI on the actual
host to load the changes. This clears the in-memory interview; begin a fresh
session to use the new instrument. Keep a healthy vLLM service running.

## Verification for this change

- 299 baseline, UI, routing, benchmark, transport, privacy-flow and scenario
  regression tests passed with `-m 'not presidio_live'` (15 detector tests
  deselected). These use the declared detector/model doubles.
- Three focused installed-detector tests passed: benign/private controls,
  uncertainty through the complete mocked-model/export path, and the adaptive
  registry/request/export path. Earlier broader testing also exercised real
  detector scenarios; its two UI/version assertion failures were corrected and
  covered by the final focused runs.
- `git diff --check` passed. Historical seed and v3 benchmark files are unchanged;
  all 19 inherited v4 case answers/expectations are equal to v3.
- Live Qwen generation and an actual browser layout check were not performed.
  This execution context cannot access the host's localhost model service or
  control its running Streamlit process; no service was restarted here.

Run the new benchmark on the GPU host when ready (semantic review remains
separate from successful execution):

```bash
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py \
  --benchmark eval/benchmarks/baseline_adaptive_v4.json \
  --output .runtime/baseline-2.3.1-live.json
```
