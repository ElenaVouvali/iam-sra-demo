# Recalibration report · 2026-10-02

Historical recalibration record. Current confirmation-gated numerical reassessment is documented in [the 2026-10-03 report](confirmation-report.md); the original qualitative-only contract below is preserved as history.

This is a synthetic engineering assessment of an experimental FN-aligned scenario profile, not scientific validation. The implementation is on `recalibrate/fn-scenario-readiness`, based on `edbcb22fbc3cd014bfbe6b2293587ad30b166e66`. Main and the working tree matched that baseline before editing. No unrelated local edits existed; nothing has been pushed.

## Source review and diagnosis

The feasibility PDF was re-read in full, including physical pp.1–2 (registry/phases), p.5 (scenario/input), pp.6–7 (scores/arithmetic) and pp.8–9 (validation). The separately requested GA Living Lab table and latest export have not been located; their paths were requested. The reported export is not represented as a directly inspected artifact. Registry IDs and phase mappings remain unchanged pending that additional source review.

Baseline inference was captured before modifications: three FN runs and four comparison cases, including raw structured output and retry feedback, in ignored `.runtime/baseline-calibration.json`. Two FN runs returned privacy1/noise1/infrastructure1 and final1; the other returned only privacy1 and no aggregate. The raw model already proposed the minimum scores. Five excerpts violated the three-excerpt bound in two runs; the bounded schema retry retained score1. Python aggregation averaged the provided integers and did not substitute1.

The causes were the original-route-only prompt and categorical-opposition anchor, stance/score coupling, medical-benefit exclusion, and lexical topic screens admitting routing as infrastructure while excluding welfare. The aggregation itself was not the source of the minimum integers.

## Implemented construct

Readiness now describes the concern-specific position and conditional willingness, while retaining original-route stance separately. All15 concerns have explicit scope, inclusion/exclusion criteria, facets and illustrative anchors. Semantic mapping replaces lexical vetoes. An independent per-concern review checks scope before choosing a provisional integer; Python still retrieves exact numbered passages and validates strict types, nulls, facets and evidence.

Medical-public-benefit support is an FN-compatible welfare facet, without implying distributive equity or equity knowledge. A separate medical-support interpretation can nominate that facet for model review, but never assigns a score. It is counted once. Bare residential rerouting is a condition, not infrastructure planning. Camera surveillance is not automatically visual clutter or technical security. Scores are not automatically raised by conditions, and stance no longer fixes a numeric band.

The unweighted mean remains an illustrative ordinal index. At least three assessed concerns are required; nulls are excluded. The experimental phase1 threshold<=3 and minimum+2 cap are preserved and explicitly distinguished from FN's single example. Every input, blocker, selected minimum, offset, cap application and rounding is exported. A cap cannot raise a result.

Validation records actual question/answer/facet mappings and preserves all original scores. For Q1accept/Q2residential objection/Q3unsure, viewing privacy resolves only under shielding, noise is partially tested, residential routing remains and policy preference is unresolved. No numerical validation update is implemented.

## Frozen live evaluation

Final evaluation uses schema3.5.0, prompt3.3.0, registry2.0.0 and rubric/policy2.0.0-experimental. The [machine-readable summary](../eval/results/recalibration-summary.json) records every final benchmark attempt. Raw outputs/retry feedback remain in ignored `.runtime/` with explicit synthetic capture.

| FN source sample | Baseline, three runs | Final, three runs |
|---|---|---|
| Assessed dimensions | privacy1/noise1/infrastructure1 twice; privacy1 only once | welfare8/noise3/privacy2 in both accepted runs |
| Visual pollution | unassessed | unassessed: no separate aesthetic/visible-aircraft objection |
| Original-route stance | opposed | opposed, kept separate from benefit support/conditional willingness |
| Mean / final | 1/1 twice; unavailable once | 4.3333/4 twice; third attempt failed schema checks |
| Accepted / attempted | 3/3, including incorrect mappings | 2/3; no invented result for the failed attempt |
| Median / maximum latency | 32.327s / 32.398s | 41.085s / 51.699s |

The live mean differs from FN's4.25 because its ambiguous visual4 item is omitted: (8+3+2)/3=4.3333. Privacy2 supplies the experimental cap2+2=4, adjusted4, half-up final4. The four-item arithmetic fixture independently reproduces mean4.25/cap4/adjusted4/final4 exactly. The final failed FN attempt included unsupported/incoherent infrastructure scope and duplicate facets; bounded retries failed validation and saved nothing. The application never replaced a score with1 or substituted reference integers.

| Final benchmark group | Accepted / attempted | All declared checks / attempted | Median / maximum latency |
|---|---|---|---|
| FN reference repeats | 2/3 | 0/3 | 41.085s / 51.699s |
| Development regressions, six cases twice | 12/12 | 10/12 | 18.902s / 25.765s |
| All15 individual topics, once each | 12/15 | 6/15 | 16.581s / 27.463s |
| Four fresh held-out paraphrases, twice each | 8/8 | 2/8 | 19.094s / 34.933s |
| Combined | 34/38 | 18/38 | 18.671s / 51.699s |

These full-check denominators include all four controlled schema errors. Literal passage retrieval/schema validation passed for the34 accepted outputs; **literal fidelity does not establish semantic correctness**. The semantic checks are provisional developer expectations, not calibrated ground truth. Source score deltas, missing dimensions, unexpected topics and each failed check are in the summary. FN's accepted three scores match the corresponding source integers; the fourth source dimension is missing, so there is no full four-dimensional live match.

Compared with the four baseline comparison cases, conditional paraphrases now retain medical welfare8 with noise3/privacy2; negation now yields noise3/privacy2 rather than1/1; explicit categorical refusal remains noise1. Qualified support still misses noise and treats a preference as an acceptance requirement. This is a material remaining failure, not an improvement claim. Two repeats showed no integer variation within accepted final case pairs, but topic/annotation variation and controlled failures remained; this tiny sample does not establish repeatability.

Both accepted FN profiles and the fresh medical-benefit paraphrases returned8/3/2, but incorrectly attached route conditions/willingness to welfare. This fails the full FN profile check even though the three numerical labels agree. The fresh qualified-support cases missed noise, and explicit visual acceptance received4 instead of the developer's support band7–9. Only categorical-refusal cases passed every fresh held-out check. Other topic errors include energy being mapped to cost, unsupported medical support in a planning answer, and missed accessibility/transport integration. The technical-controls answer scored7, outside the explicitly provisional3–5 band. These remain research-demo limitations requiring interpretation review, not evidence of general assessment reliability.

Earlier schema3.4 experiments exposed medical endorsements inferred from scenario context. After auditing this error, the final general prompt explicitly distinguishes background facts from citizen testimony; the independent scorer now receives only the requested ID and complete citizen passages. The earlier four held-out cases then became development cases (`eval/development-heldout.json`); `eval/heldout.json` contains separately frozen new texts, with no subsequent semantic prompt tuning. Some development outputs were regraded after adding medical-absence checks and broad topic anchor bands. This retrospective grading is disclosed and must not be represented as preregistered validation.

## Application, non-thinking and resources

**212 offline tests passed**, including fixture arithmetic, nulls/caps/coverage, evidence retrieval, malformed/truncated/instruction-injected outputs, state transitions, isolation, original/corrected snapshots and validation combinations. Python compilation, shell syntax and dependency checks passed.

A live Streamlit renderer session completed Q1accept/Q2residential objection/Q3unsure and rendered JSON export. Original scores and aggregate were preserved; numerical update stayed null. Q1 resolved personal privacy under shielding. Qwen also tagged a perceived-safety facet, which appropriately remained untested, leaving the combined privacy/safety concern partially tested. Noise remained partially tested, routing remained, and the policy gate remained unresolved. After the live checks, default Q1 selection was additionally restricted to evidenced route opposition and a privacy/data-security objection (validation3.1); explicit all-reference mode labels the original premise without asserting opposition. Offline regression checks cover positive/unknown stances. The first verifier incorrectly expected whole-concern resolution; its assertion was corrected to preserve untested facets, and the repeated live renderer check passed. This checks rendering/state behavior, not actual laptop-browser interaction.

Two additional CLI assessment smokes failed schema checks and saved no assessment; both are disclosed outside the38-attempt benchmark. The recorded normal and `/think` requests passed the no-visible-thinking checks (0.250s/0.997s). CLI failure reporting now saves those results even when the subsequent assessment fails. Across all seven final FN assessments including the two CLI and two renderer attempts, four were accepted and three failed safely. This is a significant reliability limitation; the successful renderer session does not erase the failed attempts.

Deployment stayed Qwen3-8B revision `b968826d9c46dd6066d109eabc6255188de91218`, vLLM0.8.5/torch2.6.0+cu124, FP16, V0/XFORMERS, concurrency1, context4096. Temperature0.2/top_p0.8, no fixed seed, thinking disabled, legacy guided_json with XGrammar fallback disabled. Full-chat prompt plus reserved output reached3121 tokens in the final benchmarks, below4096; no evidence was truncated. Per-stage usage and retries are recorded.

V100 memory before/after every final benchmark assessment sampled27080MiB (26.45GiB). These are samples, not measured peaks. The unrelated active A2 workload was not used or modified. Both localhost health endpoints passed after restarting the project UI; vLLM remained running. The pinned grammar was separately checked to accept unassessed dimensions, confirming that the earlier false endorsements were semantic errors rather than an impossible null branch. SSH forwarding/laptop-browser checks and remote GitHub Actions were not executed. The GA table/latest export source review remains pending their paths.

## FN questions and operational commands

FN feedback is needed on the p.7 mean4.25 versus p.9 mean6.0 inconsistency, nine score anchors, bottleneck eligibility/offset, ordinal averaging and minimum coverage, medical-benefit versus equity scope, visual attribution, overlapping validation outcomes, missing numerical update policy, leading/bundled hypotheticals and coverage of the other topics. See [methodology](methodology.md) for page-level requirements and deviations.

The model revision and working V100 FP16/V0/XFORMERS vLLM deployment are preserved. No packages, drivers, other environments or unrelated GPU workloads were changed. The project vLLM process was restarted once after an abandoned large-grammar experiment stalled compilation; final schemas use a small verified grammar. UI restart clears in-memory sessions; historical exports are untouched.

On liono, restart only the UI to load this change:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
scripts/stop-ui.sh
scripts/start-ui.sh
scripts/health-check.sh
```

If vLLM is stopped, use `scripts/start-vllm.sh` and wait for its health endpoint; do not start a duplicate server. On the laptop:

```bash
ssh -N -L 8501:127.0.0.1:8501 -L 8000:127.0.0.1:8000 elvouvali@liono.microlab.ntua.gr
```

Open `http://localhost:8501`. Verification commands:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python eval/run.py --ids fn_reference --repeats 3 --capture-raw --sample-gpu --output .runtime/fn-repeat.json
PYTHONPATH=src .venv/bin/python eval/run.py --held-out --repeats 2 --capture-raw --sample-gpu --output .runtime/heldout-repeat.json
PYTHONPATH=src .venv/bin/python scripts/smoke.py
PYTHONPATH=src .venv/bin/python scripts/smoke-ui.py
```

`--capture-raw` is explicit synthetic-evaluation capture, not routine logging. Every HTTP call budgets the full chat against4096 tokens; mapping reserves1400 output tokens and each review300. Up to15 reviews and one retry per call are bounded by180 seconds overall. Extra calls add latency. No silent input truncation, canned FN output, individual-score offset or live mock fallback is used.

## Evidence transport repair (2026-10-03)

Interactive FN assessments failed on too many excerpts and subsequently a
root-level consistency error. Live reproduction identified the latter as
`Duplicate facet`, not an arithmetic or citizen-input failure. The pinned
backend cannot enforce the removed `maxItems` bound; prompt-only limits and
generic retry feedback were insufficient.

The scoring transport now uses literal array enums for one strongest evidence
passage (or empty for exclusions) and zero to two distinct canonical facets.
The full original citizen text remains the interpretation input and conditions
are retrieved separately. This limits displayed supporting-excerpt selection,
not the evidence available to the model. Local evidence/null/type/score checks
remain intact. Consistency failures now include the violated rule in bounded
retry feedback and the user error, without echoing citizen text.

After repair, three consecutive real Qwen/V100 FN-reference assessments
completed: two returned welfare8/noise3/privacy2 (31.59s, 30.96s); the third also
scored infrastructure/land-use2 (39.24s). That extra mapping remains an empirical
scope discrepancy: rerouting alone should not establish infrastructure planning.
These runs verify successful execution, not calibrated scores or stable semantic
mapping. Diagnostic traces of these explicitly synthetic checks are ignored
under `.runtime/evidence-fix-repeats.json`. All214 offline tests passed.

The pasted version with original line breaks and joined `orsee` then exposed
an assessed record with missing facets/evidence. The scoring schema now has
separate retained/excluded branches: retained requires nonempty canonical
facets and evidence, supported scope, assessed status and an integer1–9;
excluded/needs-clarification requires unassessed status and a null score.
These enforce existing invariants, rather than supplying missing model evidence.
The exact pasted version then completed live in30.03 seconds with
welfare8/noise3/privacy2 and no additional assessed concern. The final repaired
schema passed all214 offline tests. This single successful exact-input run does
not guarantee future semantic agreement; traces are in ignored
`.runtime/fn-pasted-repaired-trace.json`.
