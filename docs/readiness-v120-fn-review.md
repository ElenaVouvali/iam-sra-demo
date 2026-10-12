# Readiness demo 1.2.0: understanding, learning and evidence integrity

## Citation reliability patch 1.2.1

The live extraction schema now asks for a listed passage ID rather than copied
quotation text. Python retrieves the complete original passage for the blind review
and audit. Unknown IDs are rejected; an explicitly supplied quotation is still
validated rather than silently repaired. This removes exact-copy generation failures
without equating a valid citation with semantic support. The reviewer must still
classify the meaning and criterion independently. Activity/time scope validation is
unchanged. This patch does not establish live semantic accuracy.

This is a draft instrument pending FN review, not an approved SRL/CRL measurement.
Default numerical fields remain null. Historical acceptance scoring is unchanged.

## Source alignment

The workbook's Read me J1/L5:L13 concerns citizen empowerment and agency.
SRA IAM indicators I8 recommends diagnostic, non-leading understanding questions
before supplying noise factors and warns against framing communication as persuasion.
I15 distinguishes information, trust and opportunities to influence decisions.
I16 separates existing capabilities, competence-building needs and evidence of using
what was learned. It explicitly rejects treating willingness to attend training as
demonstrated readiness. The revised explanation and reflection question follow those
distinctions; they are application proposals, not FN-approved wording.

The scenario facts come from the FN concept p.5. Camera shielding and changes in
altitude/noise remain hypothetical (pp.8–9), not verified technical solutions. No
actual city, data governance or public consultation process is invented. Minutes,
presentation and GA references remain recorded in references/source-register.json;
they supply context and review obligations, not approval of this instrument.

## Changes prompted by the exported session

- Extraction no longer receives earlier model interpretations, which contaminated
  a short participation denial with invented route conditions and policy preferences.
- Source claims contain an exact passage citation and quotation. Activity/time scopes
  must themselves be source fragments or empty; missing scope does not imply a match.
- The second request does not see the extractor's classification. It separately checks
  the proposed meaning and classifies the evidence. A claim is retained only when
  meaning is supported and classifications agree. Recognition is not explained impact;
  proposed rerouting is not participation opportunity. No blanket acceptance approval
  remains: stance, medical purpose, concerns, conditions and preferences are individual
  claims. The reviewer independently supplies their stance and thematic attribution.
- Only reviewed concern claims nominate optional mitigation topics AND facets. The UI
  and session API both enforce those facets; a parent topic does not automatically
  nominate its other facets. Generic topics cannot create a reliability question.
- Contradiction checks compare the same kind, activity, period, domain and proposal.
  Intention to attend and absence of past attendance can coexist. Explicit conflicting
  evidence remains reportable. Differently phrased or unspecified scopes are not
  automatically equated; this is conservative, not a complete semantic contradiction
  detector.
- Change reports now include new explicit absence and post-information evidence, not
  just positive supported records. Initial snapshots and confirmations stay immutable.

## Optional learning

After initial confirmation, citizens can read a controlled draft explanation, then
choose one reflection question: explain a possible effect and what remains uncertain.
The explanation distinguishes supplied facts, potential effects and missing evidence.
It does not promise safety, sound reduction or data protection, or ask for support.

Reading records an acknowledgement and the exact module/version; it adds no readiness
record. Reflection uses the existing total budget of five questions and can be skipped.
Later answers are marked after_information_exposure. Repeating supplied facts is not
equivalent to independent reasoning, prior knowledge, verified learning or a CRL gain.
The module can still be read when the budget is exhausted, without another question.

For the exported FN answer, the target interpretation is: opposed route; supported
medical purpose; explained possible disturbance to rest; unanswered recording question;
no participation or opportunity evidence initially. After the participation denial,
record explicit absence without inventing conditions or a contradiction. The next
missing dimension is participation opportunities, rather than another denial question.
These are methodological targets, not a claim of live-model success.

## Code and checks

- readiness_grounding.py: typed source claims, exact quotation validation, blind-review
  contract and deterministic assembly into existing acceptance/readiness records.
- readiness_client.py and the two readiness prompts: one extraction plus blind review batches of at most six claims, shared
  180-second deadline, source-first payloads, per-claim audit and no silent fallback.
  Reserved output budgets are 1,600/1,400 tokens, with each full request checked against
  4,096. No review is needed for an empty claim list. Review batches increase work relative to a single extraction call.
- readiness.py: scoped contradiction checks and more complete change reporting.
- readiness_session.py: immutable initial profile, bounded optional learning, exposure
  provenance, prompt hashes and export schema 6.2.0.
- readiness_ui.py and configs/readiness*.json: revised draft questions, controlled
  explanation, optional reflection, plain-language review and old-instrument warning.
- scripts/replay-readiness-session.py: replay actual source answers only when the new
  question has the same criterion. It never uses an old denial to answer a new question
  about opportunities. The old JSONL is read locally and not committed as a fixture.

Run the relevant tests or all tests:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/replay-readiness-session.py \
  --input /home/evouvali/iam-evidence.jsonl \
  --output .runtime/readiness-v120-session-replay.json
.venv/bin/python scripts/smoke-readiness-evidence.py \
  --output .runtime/readiness-v120-live-smoke.json
```

In this editing environment, both live commands were blocked before inference by
network restrictions (Operation not permitted). Mocked review tests prove filtering,
contracts and UI behaviour, not Qwen's semantic accuracy. An ungrounded interpretation
could still be misclassified by both calls; the FN demonstration needs a successful
live replay and human inspection before presenting it as validated.

The presentation update uses instrument 1.2.2 for the neutral initial invitation.
See [UI source checklist and verification](readiness-ui-guidelines-review.md).
Restart only the UI, confirm Start over, and enter a new answer to use instrument 1.2.2.
Existing sessions retain their original snapshots; they are not silently repaired.
