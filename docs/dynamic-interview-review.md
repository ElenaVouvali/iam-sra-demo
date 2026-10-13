# Dynamic interview review and improvements — 13 October 2026

The three local `iam-session-1.json`, `iam-session-2.json` and `iam-session-3.json`
files were reviewed, including their questions, submitted answers, claims,
omissions, routing dispositions, confirmations and inference diagnostics. The
original files remain private and unchanged; they are not evaluation ground truth
or material added to model prompts.

## Findings and implemented changes

- Session 1 expanded one delivery-unfamiliarity statement into six absence claims.
  This incorrectly closed understanding, experience and information questions.
  Repeated identical interpretations also concealed that category spread in the UI.
  Extraction/review instructions now limit negative scope. The reviewer receives
  original passages and proposed meanings without extractor category/subject
  labels, classifies independently, and can correct subject/domain/temporality.
  Equivalent classifications are deduplicated. The review screen groups claims by
  their human-readable dimension so one paraphrase cannot hide several claims.
- In sessions 2 and 3, an undetailed possible delivery benefit was treated as use
  knowledge rather than an impact assertion. The revised instructions preserve
  it as `understanding/claim_without_detail`, enabling the existing neutral
  reasoning clarification when eligible; they do not treat it as a measured gain.
- Session 3 assigned an individual belief to the organisation and lost reported
  organisational discussion because no deployment plan was produced. The reviewer
  can now correct subject labels and distinguishes discussion, contribution and
  operational implementation. A professional role remains no proof of capability.
- Generic unfamiliarity/definitions attracted airspace/planning topic tags, and
  lack of explanation became an inferred participation barrier. Revised guidance
  requires explicit topic/access evidence; no fixed case-to-answer lookup or
  numerical readiness rule was introduced.
- The saved successful events contain schema retry failures. Their rejected raw
  outputs were intentionally not retained, so their exact malformed fields cannot
  be reconstructed from these exports. New diagnostics retain safe field
  locations/types. Optional topic/scope/reason fields have defaults; essential
  categories, evidence references, privacy and evidence validation remain required.
- The model log records **engine process death at 2026-10-13 10:09:37** followed by
  service shutdown. This explains current unavailability independently of JSON
  formatting. The original cause of engine death is not established by that log.

## Navigation and interpretation review

The earlier-answer editing block and sector widget have been removed. **Back**
reopens the actual answer with its wording restored; existing invalidation/history
rules still apply. The optional scenario follows the same separation.

Review now shows the actual question, original answer and interpretation.
**Correct this interpretation** collects a separate request to re-read that
original answer. It never substitutes that request for the answer or adds it to
citizen evidence. Revised claims require confirmation. Prior interpretations,
feedback and confirmation revisions are recorded separately, with only the final
accepted revision marked confirmed. A failed revision leaves the pending review
intact. The summary-review screen can reopen an interpretation for the same
original answer and preserves superseded history.

The UI shows the current question number without “up to 8”. The internal
question/probe budgets remain as bounded interview policy; hiding the total does
not imply unlimited questions or change readiness criteria. Backend sector fields
remain readable for frozen exports and historical benchmarks; new UI context uses
the neutral default and no longer asks for sector.

## Model requests and recovery

The internal JSON schema enables reliable evidence references and adaptive
routing; it imposes no answer-format requirement on the respondent. Removing it
would allow malformed/misclassified structures to change routing silently.

Brief connection failures and temporary gateway/unavailable responses receive
one safe retry. Timeouts, overload, rejected requests, invalid tokenization and
invalid model envelopes are distinguished. Model/schema retries stay bounded by
the existing deadline; original answers are never truncated or replaced by a
fallback assessment. Service bodies and rejected raw outputs are not shown or
logged. Error messages use plain language and retain the visible answer; a retry
button reuses that answer rather than suggesting uncertainty because the model
failed.

The GPU/model service cannot be restarted from this editing environment:
`nvidia-smi` is unavailable to its GPU runtime. Run on davinci:

```bash
cd ~/iam-sra-demo
scripts/recover-model.sh
# Once model loading has finished:
scripts/health-check.sh
scripts/stop-ui.sh
scripts/start-ui.sh
```

Recovery reuses a healthy model, otherwise stops only the project-owned process
using existing identity checks and requests the pinned launch. It never kills
arbitrary GPU or port owners. Restart the UI and start a fresh session to load the
new instrument; frozen sessions/exports are not silently rewritten.

## Versions and evaluation

New interviews use `baseline-2.2.0`, prompts `baseline-2.2.0` and schema
`iam-baseline-2.2.0`. The deterministic routing policy and numerical baseline
policy are unchanged. A versioned successor, `baseline_adaptive_v3.json`, preserves
the older benchmark banks and adds synthetic cases for an undetailed possible
benefit and organisational discussion without deployment. The old seed file is
unchanged. Expectations stay separate from production prompts and semantic review
remains pending.

Tests exercise original-answer immutability, screened feedback, failed revisions,
summary reopening, Back/navigation, blind review and category deduplication,
subject correction, bounded transport recovery and response validation. These
controlled outputs demonstrate application behaviour, not live Qwen accuracy.
The original three sessions should be re-run on the recovered model and reviewed
for the specific errors above before claiming semantic improvement.

Verification: **358 repository tests passed**, with 10 detector-dependent tests
skipped in that environment. The installed privacy environment separately passed
**10 real-detector checks** (4 baseline, 5 shared request/output boundaries, and
1 original-answer-bound interpretation revision). Model responses in those checks
were controlled; they establish privacy/application plumbing, not Qwen semantics.
Python compilation, shell syntax, local documentation links and whitespace checks
passed. The historical seed checksum is unchanged. No live service restart or
live-model semantic success is claimed.
