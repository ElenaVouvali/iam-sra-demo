# Scenario interview and provisional workbook score

The optional medical-drone scenario collects proposal views separately from
understanding, information needs, participation, reported influence and ways to
participate. Opposition can demonstrate understanding. Support alone does not.

`Session()` starts the general baseline; explicit
`acceptance_and_readiness_evidence` starts the scenario. The historical acceptance
mode is available only on `legacy`.

The model extracts source-linked claims and a second request reviews their
classification. The application retrieves original quotations, validates IDs and
requires confirmation before retaining interpretations. Actual activities,
hypothetical intentions, unknown outcomes and barriers remain distinct. Editing
invalidates dependent records and final results. Optional information exposures
are logged; reading alone awards no readiness gains. Retrieval is bounded to the
reviewed local corpus and never indexes citizen answers.

After finishing, choose **View readiness score → Calculate readiness score**.
The model returns a provisional CRL from 1 to 9, or insufficient evidence, a short
explanation and supporting answer IDs. `configs/readiness_levels.json`
transcribes `IAM-CC_Topic_experts.xlsx`, Read me K5:L13 and B5:C13, and records the
workbook hash. SRL remains unassessed because it requires synthesis of TRL, ORL
and CRL. The estimate is separate from approved numerical fields and included as
`provisional_workbook_score` in exports. Changes to answers, profile or rubric
invalidate it. Failed requests leave answers intact and allow retry.

The model transport uses a 4096-token budget, full-request tokenization, structured
JSON, disabled thinking and bounded retries. Input is never silently truncated.
Privacy gates screen inputs, outputs and downloads. Tests exercise application
boundaries with synthetic responses; live model judgement requires host review.

Exports include original evidence, confirmations, corrections, initial/final
profiles, source provenance and information exposures. Researcher reports are
available in developer mode. This draft instrument does not independently verify
reported events or establish a city-wide societal readiness level.
