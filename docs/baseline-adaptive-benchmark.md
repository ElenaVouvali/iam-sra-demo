# Adaptive baseline benchmark

The current executable bank is `eval/benchmarks/baseline_adaptive_v3.json`
(`baseline-adaptive-3.0.0`), targeting instrument `baseline-2.2.0`, export
`iam-baseline-2.2.0` and routing `baseline-routing-1.0.0`. Its recorded configuration
hash must match the current instrument; a mismatch produces
`incompatible_benchmark`, not a run against silently changed criteria.

`eval/benchmarks/baseline_seed_v1.json` is the unchanged historical baseline:
SHA-256 `b35c306764ede2b67f276b68f43addabf564f44dcb2849b3683819cdb415dbcb`.
The earlier `baseline_adaptive_v1.json` is also retained. Neither old bank is
rewritten or silently converted by the runner. Freeze a new bank version when
changing questions, policies or expectations.

## Cases and answer selection

All three original respondents remain. The successor adds the personal academic
and operator variants, organisational authority contribution and organisational
seminar cases for planning, research, operations, regulatory, community and neutral
roles. Dedicated journeys exercise early finish, skip/decline, optional definition
exposure and correction from a bus-consultation contributor to a listener.
The successor adds two saved-session-inspired synthetic regressions. There are 19 cases; these are synthetic authored expectations, not a representative
sample or a validated citizen instrument.

The existing `scripts/smoke-baseline.py` reads this bank by default. It no longer
contains a separate case list, shared probe answers or a generic correction.
At each turn it reads the real controller-selected question ID and variant.
`answer_bindings` points to a case-local `answer_sets` entry; only that entry is
submitted. `equivalent_variants` declares specific aliases, including the case's
role variant. Unknown IDs/variants stop as `unsupported_benchmark_branch` and
retain the actual presented question plus earlier outputs. No default answer is
invented, and expected benchmark content never enters a model prompt.

Each correction has explicit replacement answers/probes. The listener correction
cannot reuse the earlier contributor's probe response. Definitions and early finish
occur only in their authored journeys, rather than being injected into every run.
The old `--definition` flag is replaced by the explicit
`novice_definition_exposure` case.

## Run on the model host

From `~/iam-sra-demo`, with the real local privacy environment installed and the
model service running on port 8000:

```bash
.venv-privacy/bin/python scripts/check-privacy.py
.venv-privacy/bin/python scripts/smoke-baseline.py \
  --benchmark eval/benchmarks/baseline_adaptive_v3.json \
  --output .runtime/baseline-adaptive-v2-live.json
```

Run a specific journey by adding, for example:

```bash
.venv-privacy/bin/python scripts/smoke-baseline.py \
  --benchmark eval/benchmarks/baseline_adaptive_v3.json \
  --case opponent_corrected_to_listener \
  --output .runtime/baseline-adaptive-v2-correction-live.json
```

`--case` may be repeated. For UI/controller plumbing with an explicitly empty
model fixture, add `--mock` and use a different output filename. Mock mode still
uses real privacy screening outside tests. Missing detector resources block the
run. Transport, schema and privacy failures are recorded separately from unsupported
branches. Each case report and the index must pass privacy screening before being written.
The main output is an index. Full per-case reports are stored under its
`case_reports_directory` as `<case_id>.json`; the directory includes a unique run
ID so later runs do not overwrite earlier evidence. The index records each
artifact hash. Separately screening each respondent avoids the NLP engine’s
combined-text size limit. A withheld artifact is explicitly marked in the index,
never silently treated as exported.

The exit code is zero only for completed executions with no structural routing or
invariant failures. It never indicates a semantic pass. A nonzero exit can also
mean incompatible versions, an unsupported branch or a failed service request.
The historical CI `eval/run.py --mock` remains a regression-test wrapper; it is not
this benchmark and does not provide live accuracy results.

## Three separate result groups

1. **Extraction:** expectations reference authored answer IDs actually supplied,
   not hypothetical answers to questions that were never asked. An exercised
   expectation has `result: null`, `review_status: pending`, its source turns and
   candidate claims. An unsupplied/skipped/declined source is `not_exercised`.
   Combined expectations with `sources_all` require every specified source;
   atomic meaning expectations remain separately reviewable. No exact-wording or
   fixed-evidence-ID comparison awards a pass. Inspect the full profile too:
   candidate retrieval does not prove completeness, entailment or absence of
   hallucinations.
2. **Routing:** independent structural checks examine earlier confirmed records,
   actual variants, probe prerequisites, core accounting, question/probe limits,
   interleaving, core-slot reservation and stopping. They do not call the production
   selector to grade itself. An unjustified missing core is a routing failure even
   when its extraction expectation is `not_exercised`. Structural justification
   from an extracted claim is conditional on that claim passing semantic review;
   a fabricated or misclassified claim can still invalidate an apparent omission.
3. **Invariants:** check general-baseline context, null numerical fields, actual
   evidence/event relationships, privacy contract, versions, confirmation actors,
   logged definition provenance and correction invalidation/history. Privacy
   contract checks do not establish detector recall or anonymisation.

Execution status, routing results, invariant results and semantic judgement remain
separate. `semantic_pass` and `interpretation_errors` stay null until human review.
Every scripted review confirmation is labelled `automation`; structured familiarity
selection is recorded as `structured_selection`, not citizen validation.

## Simple manual semantic protocol

1. Run each case in a fresh session. Keep the original index and its case reports unchanged.
   Verify its bank/config hashes and code, model and policy provenance. Code
   provenance includes the commit, dirty-tree flag and actual source-file hashes;
   model provenance records the configured model/revision, not independent proof
   of the server's loaded weights (`model_identity_verified: false`).
2. In a separate review copy, record reviewer identity, timestamp and the report's
   `run_id` and bank hash. For each phase and expectation, inspect the supplied
   answer(s), original source passages, pending interpretation, confirmed profile
   and final summary. Compare meaning, subject, time, transport domain and the
   evidence relationships. Paraphrases, merged/split claims and different generated
   IDs are allowed. Do not grade against an answer that was never supplied.
3. Enter `pass`, `partial`, `fail` or `not_exercised` per extraction expectation,
   with a source quotation/turn, observed claim and reason. Record missed facts,
   invented participation/influence, wrong subject/domain, unsupported verification,
   privacy issues and routing failures separately. Keep unreviewed rows pending.
4. Review the **initial** interpretation before the **corrected** phase. Enter
   initial errors in the initial phase's `interpretation_errors`; report correction
   success separately. A faithful final correction never turns the earlier error
   into an initial success. Confirmations in the generated run are automation,
   not an assertion that the interpretation was faithful.
5. Report denominators by case, phase and expectation group. Exclude
   `not_exercised` from extraction accuracy denominators; show pending review and
   routing failures separately. A completed execution or valid export is not
   semantic success. Save actual outputs and reviews under ignored `.runtime/`;
   never commit real respondent data.

For a manual UI run, select the case context, read the selected question/variant
from the export, and submit only its bound answer. Request the definition, finish
or edit only when that case's journey specifies it. Record errors before correcting.
If no binding matches the presented branch, stop and record it as unsupported.

## Detector observations

The original authority case retains its historical “van trips” answer. The
installed detector can misclassify that phrase as a name and reject it. This is
a recorded privacy false positive, not permission to bypass screening or replace
the answer silently. Newly authored role variants use “road vehicle journeys”;
the original case remains available to expose the detector limitation.

The exact relative filename `eval/benchmarks/baseline_adaptive_v2.json` is reviewed
report metadata in the existing source register. It is not an exemption for any
answer, expectation prose, model output or arbitrary file path. Initial capitalisation
of reviewer prose in the new bank was normalised after false PERSON findings;
respondent answers were not changed by that metadata fix.

## Earlier benchmark verification (instrument 2.1)

- Repository regression: **338 passed, 10 skipped**; benchmark-specific tests:
  **40 passed** with explicitly synthetic detector/model doubles.
- The historical bank's SHA-256 remains unchanged. Compilation and whitespace
  checks passed.
- A final real-detector/empty-model `novice_early_stop` run completed, including
  separately screened case artifact, versioned directory, index and hash links.
  Its semantic judgement remains pending.
- Broader real-detector attempts exposed the historical authority input false
  positive and export false positives/size limits. These motivated independent
  case screening and explicit failure/withholding records. They are not a claim
  that all real-detector journeys pass.
- The live model attempt failed with `transport`; no live extraction accuracy or
  human semantic review is claimed. Rerun the documented live command on the
  model host and review each phase before publishing benchmark performance.

The v1/v2 banks remain historical and unchanged. The current instrument and review changes are described in [dynamic interview review](dynamic-interview-review.md).
