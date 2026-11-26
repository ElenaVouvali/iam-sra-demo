# A30 live generalisation examples — 26 November 2026

These excerpts are from fictional Qwen-generated respondents interacting with
the live IAM-SRA2 interviewer, interpreter, controller and scorer. They are
development examples, not participant evidence, expert review or independent
score validation. The synthetic respondent and interviewer used the same model
checkpoint, so persona consistency needs human review.

The complete screened JSON, JSONL and Markdown transcripts remain in the local
ignored `.runtime/fn-v42-final-live-a30-20261126/` campaign directory. They are
not copied here because they include the source-defined interview text and
scales. No raw model reasoning or authenticated developer trace is published.
The excerpts below retain only selected synthetic respondent evidence and
final scoring fields needed to inspect the observed result.

## Configuration and interpretation

- Interviewer, interpretation and scoring: Qwen3-8B FP16, thinking enabled,
  8,192-token context; revision
  `b968826d9c46dd6066d109eabc6255188de91218`.
- Synthetic respondent: same Qwen checkpoint, thinking softly disabled.
- Application code used by these runs: `ffd91addd469370465f71d500c52abdcc86df155`.
- A score marked `validated_score` passed the application’s structural and
  evidence-citation checks. That status does **not** establish that the model
  interpreted every relevant answer correctly.
- The simulated reviewer selected “not sure” in each case. This is automated
  synthetic behaviour; review remains pending and is not agreement.

## Cases completed so far

| Case | Result | Respondent turns | Interviewer generations | Respondent generations | Scoring calls | Total elapsed | Technical issues |
|---|---:|---:|---:|---:|---:|---:|---|
| G2 citizen, short | CRL 5, suggested | 35 | 29 | 30 | 1 | 860 s | None; 0 fallbacks |
| G5 organisation, narrow remit | ORL 3, suggested | 26 | 23 | 22 | 1 | 670 s | None; 0 fallbacks |
| G10 technology, integrated representative demo | TRL 6, suggested | 39 | 36 | 36 | 1 | 1,079 s | No transport error; boundary rationale is semantically defective |
| G7 organisation, approved pilot | ORL 3, suggested | 43 | 40 | 39 | 1 | 1,175 s | No transport error; result contradicts pilot evidence |

All four interviews reached a non-partial terminal state and exported JSON,
JSONL and Markdown. The synthetic review was uncertain in every case. These are
not four successful semantic assessments: G7 and G10 exposed important scoring
problems described below.

## G2 — informed citizen with proposed safeguards

The respondent supported exploring urgent delivery conditionally and had no
reported consultation or influence experience. The provisional result was
**CRL 5 — Co-design**, with four exact respondent-answer citations. Examples:

> “Thinking about drones transporting healthcare items in my city, I consider
> the potential for urgent deliveries but also need clear safeguards, like
> night flight restrictions and data rules, before accepting them near homes.”

> “Night noise, camera/data rules, and fair distribution matter most. I want
> safeguards to ensure no group is unfairly affected.”

The model’s rationale was that these answers propose conditions and changes;
its boundary was that the evidence did not show comparing alternatives or
trade-offs. This is a plausible provisional interpretation of the selected
answers. It must not be read as evidence of actual co-design or influence.
There were no fallbacks or technical failures. The automated reviewer selected
“not sure” and the result remains pending review.

## G5 — organisation with a narrow advisory remit

The respondent described an advisory unit without approval, allocated budget,
pilot or authority to operate/regulate. The provisional result was **ORL 3 —
Assessment**, with four exact respondent-answer citations. One cited answer:

> “Our unit evaluates route efficiency for potential drone services but does
> not operate or regulate them. No institutional commitment or allocated
> resources exist yet. We await confirmation of responsible operators and
> approving authorities before advancing further.”

The rationale focused on identifying requirements and preparedness gaps. The
adjacent boundary was that preliminary roles, resources and procedures were
not yet demonstrated. This is broadly consistent with the fictional evidence,
although the participant-facing boundary contained a malformed fragment
(`(: Planning)`) in the transcript. It passed the validator, showing that
readability still needs stronger review. No fallbacks or technical failures
were recorded; synthetic review remains pending.

## G7 — organisation with a completed, approved pilot

The respondent explicitly reported an approved supervised pilot completed at
two hospitals, tested roles/procedures, and a lessons log; routine procedures
and sustained monitoring remained absent. For example:

> “A supervised pilot was completed with two hospitals. Roles and procedures
> were tested, but no sustained monitoring or routine authorization exists.”

The scorer nevertheless proposed **ORL 3 — Assessment** and said the next
level’s preliminary plans and procedures were “not explicitly shown.” This
does not reconcile the explicit pilot and tested-procedure evidence in the
same transcript. The selected level may be conservative, but the explanation
and boundary are not defensible as written. Treat this as a semantic scoring
failure, not a success. No technical transport failure or fallback occurred;
the synthetic review was uncertain.

## G10 — integrated technology shown in a representative setting

The respondent described an integrated prototype demonstrated on a
hospital-campus route, with measured route accuracy and payload temperature;
long-duration reliability, adverse weather and formal qualification remained
unresolved. The model proposed **TRL 6 — Technology demonstrated in a relevant
environment**. The cited evidence supports a representative demonstration,
but the adjacent boundary is not sound:

> “The current evidence only describes a demonstration, not a fully developed
> prototype, and lacks formal operational qualification.”

That explanation does not cleanly distinguish the relevant-environment
demonstration from an operational-environment prototype, and treats formal
qualification as part of the adjacent boundary without grounding that
distinction in the demonstrated environment. It also contained malformed
punctuation (“next level,,”). The level itself is plausible, but the result
does not meet the required defensible-boundary standard. No transport error
occurred; synthetic review remains pending.

## Current engineering finding

The live runs show that the real controller and model can complete all three
profile paths and return cited numerical suggestions. They also show that
structural validation alone does not reliably catch explanations that ignore
important evidence or misstate adjacent-level distinctions. In particular,
the scorer must reconcile pilot/testing evidence and operational-environment
evidence against its selected boundary before the result is presented as
defensible. The remaining G4, G8 and G12 interviews and expert review are still
required; no readiness accuracy claim is made here.
