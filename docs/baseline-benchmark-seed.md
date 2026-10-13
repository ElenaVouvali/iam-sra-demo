> Historical bank: `baseline_seed_v1.json` remains unchanged. For the adaptive successor and executable runner, see [adaptive benchmark](baseline-adaptive-benchmark.md).

# Benchmark use cases

## (1) novice_enthusiastic_personal

Separate support, familiarity, uncertainty and barriers; optionally test information exposure.

### Choose these details

- `perspective`: `personal`
- `stakeholder_category`: `citizen`
- `city`: `withheld`
- `sector`: `none`

### Answers — paste only if asked

**familiarity**

```text
term
```

**concept**

```text
I have heard the word, but I do not know what a drone is.
```

**delivery**

```text
I have not heard about drones carrying goods before today.
```

**understanding**

```text
I like the idea of deliveries by drone, but I cannot explain what difference they would make.
```

**experience**

```text
Before this session, I had not attended a drone event or taken part in any activity about delivery drones.
```

**needs**

```text
I would like to know how they carry goods and what happens if a delivery cannot be completed.
```

**opportunity**

```text
I would be interested in a discussion, but I have never been invited and do not know where to find one.
```

### Adaptive answers — only for the matching question

**scope**

```text
These statements concern different activities. Please keep the experiences separate; I am not reporting independent verification.
```

**reasoning**

```text
I am unsure. I cannot explain an effect yet.
```

**contribution**

```text
I have not taken part in an activity about drones.
```

**domain**

```text
I am not reporting an earlier activity.
```

**influence**

```text
I have not made a contribution, so I cannot report an outcome.
```

### Expected evidence

- Familiarity is self-reported recognition of a term, not demonstrated understanding.
- Concept and delivery knowledge are explicitly unknown/absent before optional information.
- Understanding remains unestablished despite enthusiasm.
- Explicit absence of prior drone activity.
- Information needs: carrying goods and unsuccessful deliveries.
- Willingness to discuss; never invited and unknown access are participation barriers.

### Errors to flag

- Actual contribution or influence.
- Inability from never being invited.
- A readiness level or numerical score from support.

### Optional variant

At the concept question explicitly select Show definition, then answer concept with the following text. Run separately from the no-information baseline.

```text
From the definition you just showed me, a drone is an aircraft with no pilot on board. I did not know that before this interview.
```

- Preserve the earlier familiarity answer and pre-information snapshot.
- Record exact definition/version/time; later evidence is after_information.
- The repeated definition must not establish independent prior knowledge or an automatic learning/readiness gain.

## (2) reasoned_opponent_transferable

Capture causal reasoning and transferable contribution without inventing drone attendance or influence.

### Choose these details

- `perspective`: `personal`
- `stakeholder_category`: `citizen`
- `city`: `coimbra`
- `sector`: `healthcare`

### Answers — paste only if asked

**familiarity**

```text
little
```

**concept**

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery**

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding**

```text
I am cautious about deliveries near homes. Repeated flights could disturb sleep because the sound may interrupt people who rest during the day. Faster transport might help urgent deliveries, but I do not know whether that would happen locally.
```

**experience**

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs**

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity**

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

### Adaptive answers — only for the matching question

**scope**

```text
These statements concern different activities. Please keep the experiences separate; I am not reporting independent verification.
```

**reasoning**

```text
The sound could interrupt sleep when flights happen during resting hours; actual disturbance would need measurements.
```

**contribution**

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain**

```text
The consultation was about buses, not drones.
```

**influence**

```text
I do not know whether my suggestion changed the bus-route decision.
```

### Expected evidence

- Everyday drone concept and delivery-use knowledge, separately from impact reasoning.
- Causal sleep/noise reasoning and conditional possible delivery benefit, not verified local facts.
- Actual self-reported bus consultation contribution in a transferable domain.
- Explicit absence of drone consultation; willingness to attend remains intention.
- Unknown influence after the outcome answer.
- Both evidence needs: sound and delivery times.
- Unknown feedback route, caring barrier, and requested online opportunity.
- Healthcare sector does not change the personal claim subject.

### Errors to flag

- Actual drone consultation or verified influence.
- A contradiction between bus participation and no drone consultation.
- Equity, infrastructure, airspace expertise or organisation capability from clinic references.
- A medical-corridor acceptance assessment or readiness penalty for caution.

### Correction variant

After completing the baseline, edit the experience answer using Edit your details or an earlier answer.

```text
Last year I listened to a public bus-route consultation. I did not speak or submit a suggestion. I have never attended a drone consultation.
```

- Original confirmed records/snapshots remain in history but superseded dependent events become inactive.
- Current profile retains listening exposure, not the superseded contribution.
- Recompute selection and handoff; do not retain dependent influence answers as current evidence.
- Confirm the correction and any newly asked answers, then confirm the summary again.

## (3) authority_seminar_no_contribution

Distinguish organisational activity, personal learning, attendance and influence; do not infer organisational capability.

### Choose these details

- `perspective`: `organisation`
- `stakeholder_category`: `authority`
- `city`: `milan`
- `sector`: `none`
- `function`: `Transport planning`

### Answers — paste only if asked

**familiarity**

```text
lot
```

**concept**

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery**

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding**

```text
Deliveries could avoid some road journeys if they replace van trips. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience**

```text
Our planning team attended an online seminar about delivery drones earlier this year. I attended as part of that team and listened. Neither I nor the team submitted comments, questions or proposals. I am not reporting an operational drone project.
```

**needs**

```text
Our team would like evidence about which road journeys deliveries would replace and what responsibilities a local authority would have.
```

**opportunity**

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

### Adaptive answers — only for the matching question

**scope**

```text
These statements concern different activities. Please keep the experiences separate; I am not reporting independent verification.
```

**reasoning**

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution**

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain**

```text
The seminar was about delivery drones.
```

**influence**

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

### Expected evidence

- Familiarity remains self-report, even with substantial familiarity selected.
- Concept/use knowledge and conditional substitution reasoning.
- Team seminar attendance and respondent attendance are distinguishable subjects.
- Actual IAM learning exposure, explicit absence of contribution in that seminar.
- Both organisational information needs: replaced journeys and authority responsibilities.
- Unknown local channel and requested written/accessible consultation opportunity.

### Errors to flag

- Contribution or influence merely from attendance.
- A completed organisational audit, operational experience or ORL/CRL estimate.
- Verified congestion reduction or an actual local consultation opportunity.
- No interest or inability from an unknown channel.

## Review each run

For every expectation record `pass`, `partial`, `fail` or `not_exercised`, a quotation/evidence ID, the actual interpretation, and a short reason. Count missed substantive facts separately from invented claims. Include question repetition/incorrect omissions, attribution, temporal/domain errors, privacy errors and transport/schema failures. Report denominators and keep baseline and corrected performance separate. Three cases are a regression seed, not evidence of general validity; add paraphrases, genuinely unseen answers, role contrasts, refusals and privacy fixtures before treating this as a benchmark.

No live outputs have been populated. `evaluation_protocol.actual_runs` is deliberately empty.
