# Baseline interpretation reliability update

This update addresses defects observed in a prior live adaptive-baseline run. It does not change the readiness construct, routing objectives, question bank, privacy policy, or scores. It adds no approved CRL/SRL rubric.

## What the saved run established

The saved report `.runtime/baseline-adaptive-gpu.json` is run `484f8096-0c40-43eb-817f-a8012ad832fa`, generated from commit `820feaa57eaa5aab12020111efdc1204d3abe48f` with a dirty tree. It recorded Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`, model identity unverified, Python 3.10.12, instrument/prompt 2.2.0, schema `iam-baseline-2.2.0`, routing 1.0.0, benchmark 3.0.0, and the pinned XGrammar configuration. It completed 7 of 19 cases and failed 12: 7 schema failures (`intention`/`actual` cross-field mismatch) and 5 privacy failures. Fifteen case artifacts were written and four withheld. One failed export invariant (`session_export_screening`) occurred in `seminar_organisation_other`. Semantic review remained pending for every case. A passing structural route check did not establish extraction correctness.

The artifacts for `authority_actual_contribution`, `seminar_organisation_regulator` and `personal_possible_benefit_without_reason` show:

- The authority answer explicitly reported that a planning team reviewed drone options, the respondent drafted comments, and the outcome was unknown. Extraction returned no claims for that answer. A later future consultation/access suggestion was misclassified as an actual contribution, which led to an unnecessary influence question.
- A regulator’s definition-only answer was used to infer non-need and non-attendance. The later “we listened but did not contribute” answer returned no claims, losing both attendance/listening and explicit non-contribution.
- “Deliveries might arrive sooner” was classified as delivery-use knowledge rather than a possible effect without explanation. A missing comment channel and difficulty attending evening meetings were reduced to an information need, losing the participation-access barrier.

The prior report did not retain recognizer names, confidence or field paths for privacy blocks. Therefore its five privacy cases cannot all be adjudicated from that artifact alone. The saved `authority_seminar_no_contribution` answer was rechecked with the installed local detector: one synthetic transport phrase was marked `PERSON` at confidence 0.85 and safely previewed with that phrase removed. The span was the common vehicle word “van” immediately before “trips”; this is an adjudicated false positive, addressed by a narrow context rule. The other old privacy-trigger values are not reconstructed or labelled false positives. The benchmark runner also failed to follow its cleaned-preview confirmation path for that case; this is corrected through an explicit synthetic fixture expectation and automated preview confirmation only where authored. No original raw-to-masked mapping is retained.

## Implemented controls

The current instrument is 2.3.0. Its model-facing schema uses one constrained claim type that maps to the established dimension, kind and time status. The model no longer has to independently generate redundant labels that can contradict each other. Server-side Pydantic checks remain strict. An invalid reviewed reclassification now stops with a safe unresolved error instead of being silently dropped.

Each current claim has a short exact answer span checked against its cited passage; scope quotes are also checked. The existing grounding pass now reviews candidates and independently checks up to three omitted claims, including when extraction is empty. The extraction and review prompts explicitly separate listening, contribution, intention, actual activity, unknown outcomes, information needs and access barriers, and distinguish delivery purpose from a claimed effect and an explained effect. These remain model-assisted meaning checks: exact quotation does not prove entailment, and human semantic review remains required.

Routing now requires an explicit matching activity quotation before using one activity’s contribution/outcome to close another activity’s gap. Missing activity identity remains unresolved. An explained impact suppresses a clarification only when its exact answer span contains the unsupported effect’s span; separate effects remain eligible for clarification. The policy remains deterministic and within the existing question/probe budget.

Privacy screening remains mandatory. Safe block metadata now carries the field path, entity type, recognizer and confidence without matched text or offsets. A benchmark export that fails screening can produce a separately screened minimal failure record; the case export remains withheld. The one observed answer false positive is handled only for the generic transport noun in its immediate trips/journeys context; names and the rest of the answer are still screened. The runner keeps authored expected wording in the versioned benchmark and writes expectation IDs/outcomes into case reports, avoiding duplicate screening of evaluator prose as though it were respondent content. Application-generated relative source paths and SHA-256 values are exempted only at their fixed provenance fields; identical values elsewhere remain screened. The curated corpus’s exact source-version strings are treated as registered bibliographic metadata, not arbitrary text.

The current executable benchmark is still `baseline_adaptive_v3.json`, versioned 3.1.0 to target instrument/schema 2.3.0. Its authored cases and semantic expectations are unchanged; the historical seed bank is unchanged. A run made with this modified working tree must record `working_tree_dirty: true` and its file-hash fingerprint. Do not compare it as a clean commit run.

## Source and methodological status

The local topic-experts workbook was available and read. Its “Read me” sheet distinguishes SRL synthesis from citizen CRL, and its draft CRL descriptions include recognition, awareness, understanding, engagement, co-design, active participation, influence, empowerment and sustained co-governance. The corrective comments for noise (I8) warn that concern is not readiness and assumes enough knowledge; the comments for awareness/trust (I15) distinguish being informed, institutional trust and empowerment; the comments for competence building (I16) say it is not technical competence, willingness to attend training, or the ability to educate others. These are partner-review comments, not an approved operational rubric. The existing no-score baseline remains appropriate.

The registered GA, FN concept, WP3 records and UI guideline originals remain in `references/private/` and are Git-ignored. The interview implementation is a proposed instrument. No omitted or unapproved project source was used to invent criteria.

## Validation status

Automated tests cover the canonical output contract, exact spans, listener/non-contribution separation, empty-extraction omission review, intention/actual reclassification safeguards, separate-effect routing, activity-specific outcome matching, privacy metadata without echoed values, benchmark artifact withholding, and UI correction after empty interpretation. Mock results establish schema/state/routing behaviour only. Installed Presidio tests exercise the real local detector; they do not establish universal PII recall.

The current environment has no GPU driver and both localhost services are unavailable. Therefore this update has not been validated with live Qwen output. Focused mocked checks pass for a case report export; a 19-case empty-extraction replay completed its session/routing checks but the initial artifact export exposed a false positive in authored expectation prose. The report now stores those references by stable expectation ID, and a single-case post-fix replay wrote a complete screened artifact. A full post-fix 19-case report was not completed within this environment’s command runtime. Neither empty-extraction mocks nor structural routing results establish model semantic accuracy. The earlier live semantic errors are observations from the old dirty tree, not proof that instrument 2.3 resolves them. Human semantic review remains pending until the model-host rerun is completed.

Run on the model host after starting the local Qwen service:

```bash
cd ~/iam-sra-demo
scripts/health-check.sh
PYTHONPATH=src .venv-privacy/bin/python scripts/check-privacy.py
PYTHONPATH=src .venv-privacy/bin/python scripts/smoke-baseline.py \
  --benchmark eval/benchmarks/baseline_adaptive_v3.json \
  --output .runtime/baseline-adaptive-v3-1-live.json
```

The report records model revision, prompt/config hashes, inference settings, request diagnostics, timings, per-case outputs and semantic expectations. It does not mark semantic expectations passed. Review the three cases above first, then inspect all 19; report unsupported claims, omissions and remaining ambiguity separately from execution success.
