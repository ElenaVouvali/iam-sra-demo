# Manual UI checks — current dynamic IAM-SRA

Instrument: `baseline-2.2.0`. Benchmark: `baseline-adaptive-3.0.0`.
Source bank SHA-256: `ebb36e716e8dd9bc852fa073bd992126402edc6e482c74a4a891dcf3fff253a2`.

Generated from the current versioned bank; answers below are synthetic. Regenerate this guide if the bank changes.

## Prepare

Run the model and UI on davinci, open http://localhost:8501, and select Start over for every case. Use the current app on 8501; 8502 is the historical app. If connected remotely, forward 8501. Restart the UI after code changes and use a new session to load baseline-2.2.0. Ensure there is no MOCK MODE banner; mock mode cannot measure real model response time. The first screen should not ask for sector; the interview should show the current question number without a fixed total.

```bash
cd ~/iam-sra-demo
scripts/health-check.sh
# If the model is unavailable:
scripts/recover-model.sh
# After model loading finishes, restart the UI:
scripts/stop-ui.sh
IAM_MOCK=0 IAM_ASSESSMENT_MODE=general_baseline scripts/start-ui.sh
```

## How to run a case

1. Enter only the listed context values that the UI asks for. Sector is retained in historical benchmark metadata but is no longer a UI field; do not add it to an answer.
2. Read the actual question. Copy only its matching answer from this case. Core questions can be omitted or reordered; do not paste the next numbered answer mechanically. Use a probe response only for its matching question. If a question/variant has no binding, record unsupported benchmark branch and stop rather than inventing an answer.
3. Start a stopwatch when you press Continue; stop when the interpretation or error finishes rendering. Record this separately for every model turn. Pauses spent reading, typing, reviewing and confirming are user time, not model response time. Record correction and retry latency separately.
4. Check the question, original answer and proposed interpretation. Confirm only faithful meaning. Record missing/invented claims before choosing Correct this interpretation. That action must preserve the original answer. Use Back only when intentionally changing the answer.
5. Follow only the case’s explicit early-finish/definition/correction actions. Finish at the natural endpoint otherwise. Inspect the summary and download the JSON record.
6. Record semantic results as pass/partial/fail/not_exercised, with a short reason and source turn. An unasked answer is not_exercised; an unjustified omitted question is a separate routing failure. Keep initial errors separate from successful corrections.

## Timing and UX record

Use `manual-checks/response-times-template.csv` as a blank spreadsheet template. Add a row per request, not one total per respondent. `run_id` and `turn_number` group rows into sessions. Include failures/timeouts in the record. A separate `session_total_seconds` includes the complete user journey. Note browser, device, connection/port forwarding, date, model version, instrument version and any simultaneous model usage.

For each case, repeat a fresh session at least three times if comparing response time. Mark the first run as cold/first-after-start and later runs as warm. Report median response time and the observed range separately for initial interpretation, correction and retry requests. With a few runs, avoid treating a tail percentile as reliable. Keep all original failures; do not drop a slow or incorrect run after retry succeeds.

## Useful order

Start with novice_enthusiastic_personal, reasoned_opponent_transferable and authority_seminar_no_contribution. Then test personal_possible_benefit_without_reason and organisation_discussion_without_deployment. Finish with novice_early_stop, novice_definition_exposure, novice_skip_and_decline and opponent_corrected_to_listener, before expanding to other roles. The original authority case can trigger a known detector false positive on “van trips”; record it as a privacy/UX failure rather than silently changing the fixture.

For a deliberate interpretation correction, first log the incorrect interpretation and its latency, then describe the misunderstanding without adding new factual testimony. Verify that Your answer and the exported event text remain unchanged. For a deliberate answer edit, use Back and record the new answer; dependent results should be recomputed and superseded records retained.

## Additional UX checks

- **Interpretation correction:** describe a genuine misunderstanding; original answer text must remain unchanged and the revised interpretation must need confirmation.
- **Answer change:** use Back; the original wording should be restored for editing, and later dependent results should be recomputed.
- **Skip / Unsure / Finish now:** these must remain distinct from lack of capability. The summary should say what was not asked or not established.
- **Synthetic privacy check:** in a separate fresh session try a synthetic email such as tester@example.org. Review the cleaned preview before confirming; check that the original detail is absent from the export. A synthetic contextual PIN should be blocked without consuming a question. Never use actual personal details or credentials.
- **Errors:** record the error, elapsed time and whether your answer remains in the box. A successful retry does not erase the original failed turn. Do not stop the shared model deliberately merely to time failures.
- **Screen usability:** try keyboard navigation, a narrow browser window and enlarged text. Check that controls remain readable and that confirmation/correction/Back are easy to distinguish.

During the session, use the actual displayed question text. Fill question ID and variant from the downloaded JSON (`events[].question.id` and `events[].question.variant_id`) afterwards; these internal fields are not normally shown in the UI. Keep benchmark timing runs free of other inference requests where possible, or record simultaneous use of the legacy app/model.

## Cases

### novice_enthusiastic_personal

Separate support, familiarity, uncertainty and barriers; optionally test information exposure.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Prefer not to say.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
term
```

**concept** (personal)

In your own words, what is a drone?

```text
I have heard the word, but I do not know what a drone is.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have not heard about drones carrying goods before today.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I like the idea of deliveries by drone, but I cannot explain what difference they would make.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Before this session, I had not attended a drone event or taken part in any activity about delivery drones.
```

**needs** (personal)

What would you like to know more about?

```text
I would like to know how they carry goods and what happens if a delivery cannot be completed.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I would be interested in a discussion, but I have never been invited and do not know where to find one.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I am describing my own lack of drone experience before this session. I have not taken part in a drone activity.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
I am unsure. I cannot explain an effect yet.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
I have not taken part in an activity about drones.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
I am not reporting an earlier activity.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I have not made a contribution, so I cannot report an outcome.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### reasoned_opponent_transferable

Capture causal reasoning and transferable contribution without inventing drone attendance or influence.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Coimbra region.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
little
```

**concept** (personal)

In your own words, what is a drone?

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I am cautious about deliveries near homes. Repeated flights could disturb sleep because the sound may interrupt people who rest during the day. Faster transport might help urgent deliveries, but I do not know whether that would happen locally.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs** (personal)

What would you like to know more about?

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I personally suggested moving a stop during last year’s bus consultation. I have not attended a drone consultation; these are different transport domains.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
The sound could interrupt sleep when flights happen during resting hours; actual disturbance would need measurements.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
The consultation was about buses, not drones.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I do not know whether my suggestion changed the bus-route decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### authority_seminar_no_contribution

Distinguish organisational activity, personal learning, attendance and influence; do not infer organisational capability.

Context: perspective: Representing an organisation; stakeholder_category: National, regional or local authority; city: Milan.
Optional function: Transport planning.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace van trips. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_authority, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_authority`: Has your authority considered delivery drones in its planning? If so, what actions have been taken, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our planning team attended an online seminar about delivery drones earlier this year. I attended as part of that team and listened. Neither I nor the team submitted comments, questions or proposals. I am not reporting an operational drone project.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace and what responsibilities a local authority would have.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### sceptical_academic_personal

Capture causal reasoning and transferable contribution without inventing drone attendance or influence.

Context: perspective: Personal view; stakeholder_category: Research or academia; city: Coimbra region.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
little
```

**concept** (personal)

In your own words, what is a drone?

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I am cautious about deliveries near homes. Repeated flights could disturb sleep because the sound may interrupt people who rest during the day. Faster transport might help urgent deliveries, but I do not know whether that would happen locally.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs** (personal)

What would you like to know more about?

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I personally suggested moving a stop during last year’s bus consultation. I have not attended a drone consultation; these are different transport domains.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
The sound could interrupt sleep when flights happen during resting hours; actual disturbance would need measurements.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
The consultation was about buses, not drones.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I do not know whether my suggestion changed the bus-route decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### authority_actual_contribution

Organisational planning contribution and unknown influence; no ORL inference.

Context: perspective: Representing an organisation; stakeholder_category: National, regional or local authority; city: Milan.
Optional function: Transport planning.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_authority, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_authority`: Has your authority considered delivery drones in its planning? If so, what actions have been taken, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our planning team reviewed delivery-drone options this year and submitted comments requesting evidence about which road journeys could be replaced. I drafted the comments as part of the team. We do not know whether any decision changed because of our comments.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace and what responsibilities a local authority would have.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I drafted the comments this year as part of our planning team. The review and submission were organisational activities.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing road vehicle journeys could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
I drafted our team comments requesting evidence about replaced road journeys.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
Our review and comments concerned delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
We do not know whether our comments changed any decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_planning

Exercise the explicit organisational planning variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Urban planning, architecture or engineering; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_planning, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_planning`: Has your organisation considered delivery drones in planning or design work? If so, what was done, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_researcher

Exercise the explicit organisational researcher variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Research or academia; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_research, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_research`: Has your organisation researched or evaluated delivery drones? If so, what was done, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_logistics

Exercise the explicit organisational logistics variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Logistics or delivery service provider; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_operations, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_operations`: Has your organisation tested, operated, developed or evaluated drone deliveries? If so, what was done, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_regulator

Exercise the explicit organisational regulator variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Aviation regulator or policymaker; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_regulatory, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_regulatory`: Has your organisation reviewed delivery drones or taken part in a related regulatory consultation? If so, what was done, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_citizen

Exercise the explicit organisational citizen variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Citizen / resident or civil-society organisation; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_community, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_community`: Has your organisation discussed delivery drones or contributed community views? If so, what was done, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_other

Exercise the explicit organisational other variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Other; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_neutral, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_neutral`: Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### seminar_organisation_withheld

Exercise the explicit organisational withheld variant without inferring capability from the role.

Context: perspective: Representing an organisation; stakeholder_category: Prefer not to say; city: Milan.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_neutral, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_neutral`: Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team attended an online seminar about delivery drones. I listened as a member of the team. Neither I nor our team submitted comments, questions or proposals. This was learning, not an operational project, planning action, research evaluation or regulatory review.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I attended as a member of our planning team. We listened to the delivery-drone seminar and did not submit comments, questions or proposals.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
We only listened to the seminar. Neither I nor the team contributed comments, questions or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
The seminar was about delivery drones.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
No contribution was reported from that seminar; I do not know of any resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### operator_personal_transferable

Capture causal reasoning and transferable contribution without inventing drone attendance or influence.

Context: perspective: Personal view; stakeholder_category: Aircraft operator, airport or airspace-service provider; city: Coimbra region.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
little
```

**concept** (personal)

In your own words, what is a drone?

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I am cautious about deliveries near homes. Repeated flights could disturb sleep because the sound may interrupt people who rest during the day. Faster transport might help urgent deliveries, but I do not know whether that would happen locally.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs** (personal)

What would you like to know more about?

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I personally suggested moving a stop during last year’s bus consultation. I have not attended a drone consultation; these are different transport domains.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
The sound could interrupt sleep when flights happen during resting hours; actual disturbance would need measurements.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
The consultation was about buses, not drones.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I do not know whether my suggestion changed the bus-route decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### novice_early_stop

Separate support, familiarity, uncertainty and barriers; optionally test information exposure.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Prefer not to say.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
term
```

**concept** (personal)

In your own words, what is a drone?

```text
I have heard the word, but I do not know what a drone is.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have not heard about drones carrying goods before today.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I like the idea of deliveries by drone, but I cannot explain what difference they would make.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Before this session, I had not attended a drone event or taken part in any activity about delivery drones.
```

**needs** (personal)

What would you like to know more about?

```text
I would like to know how they carry goods and what happens if a delivery cannot be completed.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I would be interested in a discussion, but I have never been invited and do not know where to find one.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I am describing my own lack of drone experience before this session. I have not taken part in a drone activity.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
I am unsure. I cannot explain an effect yet.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
I have not taken part in an activity about drones.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
I am not reporting an earlier activity.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I have not made a contribution, so I cannot report an outcome.
```

Action: after 2 submitted/confirmed answers, select **Finish now**, then confirm the summary. Do not continue through the remaining answer options.

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### novice_definition_exposure

Separate support, familiarity, uncertainty and barriers; optionally test information exposure.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Prefer not to say.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
term
```

**concept** (personal)

In your own words, what is a drone?

```text
From the definition you just showed me, a drone is an aircraft with no pilot on board. I did not know that before this interview.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have not heard about drones carrying goods before today.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I like the idea of deliveries by drone, but I cannot explain what difference they would make.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Before this session, I had not attended a drone event or taken part in any activity about delivery drones.
```

**needs** (personal)

What would you like to know more about?

```text
I would like to know how they carry goods and what happens if a delivery cannot be completed.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I would be interested in a discussion, but I have never been invited and do not know where to find one.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I am describing my own lack of drone experience before this session. I have not taken part in a drone activity.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
I am unsure. I cannot explain an effect yet.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
I have not taken part in an activity about drones.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
I am not reporting an earlier activity.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I have not made a contribution, so I cannot report an outcome.
```

Action: at **concept**, select **Show definition** before submitting that answer. Record display time separately; it is not a model-turn response. Check that later evidence is marked after_information and no automatic prior-knowledge or readiness gain is awarded.

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### opponent_corrected_to_listener

Capture causal reasoning and transferable contribution without inventing drone attendance or influence.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Coimbra region.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
little
```

**concept** (personal)

In your own words, what is a drone?

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
I am cautious about deliveries near homes. Repeated flights could disturb sleep because the sound may interrupt people who rest during the day. Faster transport might help urgent deliveries, but I do not know whether that would happen locally.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs** (personal)

What would you like to know more about?

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I personally suggested moving a stop during last year’s bus consultation. I have not attended a drone consultation; these are different transport domains.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
The sound could interrupt sleep when flights happen during resting hours; actual disturbance would need measurements.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
The consultation was about buses, not drones.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I do not know whether my suggestion changed the bus-route decision.
```

**Authored answer-change variant (distinct from correcting a model interpretation)**

After completing the initial journey, keep its JSON export. Use **Back** repeatedly until the `experience` answer is reopened. The raw answer-change editor block no longer exists. Replace that answer with:

```text
Last year I listened to a public bus-route consultation. I did not speak or submit a suggestion. I have never attended a drone consultation.
```

Confirm the new interpretation and answer only newly selected questions. For reopened probes use these replacement answers, not the original contributor’s account:

scope (personal):

```text
This corrects my earlier account: I personally listened to the bus consultation but did not contribute. I have never attended a drone consultation.
```

contribution (personal):

```text
I listened to the bus consultation but did not speak or submit a suggestion.
```

influence (personal):

```text
I did not make a contribution at that bus consultation and cannot report an outcome from one.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### novice_skip_and_decline

Separate support, familiarity, uncertainty and barriers; optionally test information exposure.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Prefer not to say.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
term
```

**concept** (personal)

In your own words, what is a drone?

```text
I have heard the word, but I do not know what a drone is.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

Choose **skip** instead of submitting text.

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

Choose **decline** instead of submitting text.

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Before this session, I had not attended a drone event or taken part in any activity about delivery drones.
```

**needs** (personal)

What would you like to know more about?

```text
I would like to know how they carry goods and what happens if a delivery cannot be completed.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I would be interested in a discussion, but I have never been invited and do not know where to find one.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I am describing my own lack of drone experience before this session. I have not taken part in a drone activity.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
I am unsure. I cannot explain an effect yet.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
I have not taken part in an activity about drones.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
I am not reporting an earlier activity.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I have not made a contribution, so I cannot report an outcome.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### personal_possible_benefit_without_reason

An undetailed possible effect must remain impact evidence and invite neutral clarification, not become organisational or technical capability.

Context: perspective: Personal view; stakeholder_category: Citizen / resident or civil-society organisation; city: Coimbra region.

These are matching options, not a fixed question sequence.

**familiarity** (personal)

Before today, how familiar were you with drones?

```text
little
```

**concept** (personal)

In your own words, what is a drone?

```text
A drone is an aircraft without a pilot sitting inside it.
```

**delivery** (personal)

What have you heard about drones carrying goods, if anything?

```text
I have heard of drones carrying parcels and medical samples. I understand that avoiding road traffic is one reason people consider them.
```

**understanding** (personal)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries might arrive sooner in urgent situations.
```

**experience** (personal; equivalent variants: contribution_after_exposure)

Before this session, have you had any direct experience, learning or involvement related to delivery drones? If yes, briefly describe what you did.

Equivalent displayed questions for this case:

- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Last year I attended a public bus-route consultation and suggested moving a stop closer to a clinic. That was about buses, not drones. I have never attended a drone consultation. I would attend one if I could.
```

**needs** (personal)

What would you like to know more about?

```text
I would want measured sound at homes and evidence about delivery times before forming a view about a local service.
```

**opportunity** (personal)

What would help you take part in discussions or decisions about delivery drones?

```text
I do not know where to submit comments about delivery drones. Caring responsibilities make evening meetings difficult; an online option would help.
```

**scope** (personal; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I personally suggested moving a stop during last year’s bus consultation. I have not attended a drone consultation; these are different transport domains.
```

**reasoning** (personal)

Can you explain why that effect might occur?

```text
I have not worked out why. I am describing a possible benefit, not a measured outcome.
```

**contribution** (personal)

What did you do or contribute during that activity, if anything?

```text
At the bus consultation I suggested moving a stop closer to a clinic.
```

**domain** (personal)

Were those experiences about drones or another service?

```text
The consultation was about buses, not drones.
```

**influence** (personal)

Do you know whether anything changed following your contribution?

```text
I do not know whether my suggestion changed the bus-route decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.

### organisation_discussion_without_deployment

Discussion is reported involvement even when a deployment plan was not produced.

Context: perspective: Representing an organisation; stakeholder_category: National, regional or local authority; city: Milan.
Optional function: Transport planning.

These are matching options, not a fixed question sequence.

**familiarity** (organisation)

Before today, how familiar were you with drones?

```text
lot
```

**concept** (organisation)

In your own words, what is a drone?

```text
A drone is an aircraft with no pilot on board; it can be remotely controlled or use automated systems.
```

**delivery** (organisation)

What have you heard about drones carrying goods, if anything?

```text
I have heard of parcel delivery and transporting medical materials. I do not know which services operate in this region.
```

**understanding** (organisation)

What difference, if any, could these deliveries make to people or local services?

```text
Deliveries could avoid some road journeys if they replace road vehicle journeys. They might also create extra trips instead, so the overall traffic effect would depend on what they replace.
```

**experience** (organisation; equivalent variants: organisation_authority, contribution_after_exposure)

Before this session, what experience or involvement have you had with delivery drones? Describe what you did, or an activity of the organisation you represent, and say which you mean.

Equivalent displayed questions for this case:

- `organisation_authority`: Has your authority considered delivery drones in its planning? If so, what actions have been taken, and what did you do?
- `contribution_after_exposure`: You mentioned an earlier activity. What did you do or contribute during it, if anything?

```text
Our team has discussed delivery aircraft, but we have not planned or operated a service. I joined the discussion but did not submit comments or proposals.
```

**needs** (organisation)

What would you like to know more about?

```text
Our team would like evidence about which road journeys deliveries would replace and what responsibilities a local authority would have.
```

**opportunity** (organisation)

What would help you or the organisation you represent take part in discussions or decisions about delivery drones? Say which you mean.

```text
For our team, a clearly advertised consultation and an accessible way to send written comments would help. I do not know of an existing local channel.
```

**scope** (organisation; equivalent variants: subject, activity, time, meaning, contradiction)

Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

Equivalent displayed questions for this case:

- `subject`: Are you describing something you did, something your organisation did, or someone else’s experience?
- `activity`: Which activity are you referring to, and what did you do?
- `time`: When did this happen? Are you referring to the same period or different experiences?
- `meaning`: Could you clarify what you mean, or say if you are unsure?
- `contradiction`: Are these statements about the same activity and period, or different experiences? You can say if you are unsure.

```text
I joined our team discussion about delivery aircraft; this was not a deployment project.
```

**reasoning** (organisation)

Can you explain why that effect might occur?

```text
Replacing van trips could reduce road journeys, but adding deliveries without replacing trips would not do that.
```

**contribution** (organisation)

What did you do or contribute during that activity, if anything?

```text
I joined the discussion but did not submit comments or proposals.
```

**domain** (organisation)

Were those experiences about drones or another service?

```text
Our discussion concerned delivery aircraft.
```

**influence** (organisation)

Do you know whether anything changed following your contribution?

```text
I did not submit a contribution and cannot report a resulting decision.
```

Expected meanings and routing/invariant criteria: see this case’s `expectations` in the versioned bank. Evaluate only the answers actually supplied.


### Model recovery when GPUs are occupied

Run `.venv/bin/python scripts/diagnose-model.py` on the GPU host. This reads GPU inventory, probes local listening ports for model-list endpoints, and checks project PID visibility; it does not stop processes or print their arguments. Both GPUs being occupied does not establish that either workload belongs to this app.

The launcher selects a unique idle supported GPU when `IAM_GPU_UUID` is unset. If several are idle, explicitly choose an available UUID from the diagnostic inventory. An explicit UUID that is missing from the host is rejected. Recovery checks GPU availability before stopping the project service.

If an existing compatible service is confirmed, supply its address as `IAM_BASE_URL=http://127.0.0.1:PORT` when launching the UI and running the health check. The UI launcher now preserves this setting. A model alias and healthy endpoint alone do not establish the required pinned revision, `/tokenize` support or guided JSON compatibility. Do not terminate other GPU workloads to make room without identifying their ownership.

If an export is withheld by privacy screening, record which button or command triggered it. The generic privacy message alone cannot establish whether the trigger is actual sensitive content or a detector false positive. Do not disable screening to obtain the download.
