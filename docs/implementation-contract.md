# Current implementation contract

`app.py` uses `Session` and `ConversationClient`. The model transport is `LLMTransport`; it has no one-shot assessment interface. Synthetic evaluation uses the same confirmed initial-stage path. Mock mode is explicit and never an error fallback.

## Evidence and confirmation

- Original, hypothetical and combined-proposal evidence retain explicit contexts and stable IDs. Question text is not citizen testimony.
- Quotation validation accepts whitespace-only formatting differences from PDF copying and restores the untouched source span for auditing. It never repairs spelling, punctuation, case or invented wording, and never matches across passage boundaries.
- Prompt policy 7.0.0 uses one model generation request over all original citizen passages to interpret the whole route and independently evidenced facets, positions, willingness and conditions. Source IDs retrieve unchanged citizen text. Python validates schema, canonical facets, reference provenance and compatibility with the existing ledger; it does not reinterpret or semantically veto the model output. Initial nomination, omission, relevance, subject and polarity-review chains are disabled. An invalid response receives at most one retry.
- The model remains responsible for semantic accuracy. One accepted response replaces the baseline's 23 generation calls, but measured latency and generalization still require live evaluation. Correction, hypothetical interpretation and numerical scoring retain their existing contracts. The previous mappers remain available for explicitly configured replay experiments.
- Policy 7.1.0 makes the wire format compact: an expressed-facet array, fixed position/willingness labels and passage IDs, with no generated rationales. The application supplies neutral audit labels and retains the original citizen passages as the explanation. This reduces unnecessary generated text and avoids presenting the full registry as optional output fields. The 1400-token output allowance, one-retry limit and provenance checks remain enforced; incomplete responses are never accepted as finished interpretations. Actual truncation and semantic accuracy rates still require live measurement.
- Interpretation is score-free. Meaning is confirmed before numerical scoring, including the updated review before progression gains.
- Original-proposal corrections can trigger a separate reassessment. Hypothetical clarification does not silently overwrite the original baseline.
- Contradictions require review. Edits invalidate dependent confirmations and results; the initial snapshot remains unchanged.

## Scoring and follow-ups

The LLM assigns confirmed facet scores. Python validates them and applies minimum facet combination, assessed-only mean, all-phase minimum-plus-two cap and half-down rounding. Missing evidence stays unavailable. Automatic metadata inference is disabled by the current prompt configuration; explicit discovery controls remain available.

Independent mitigation questions target objections and conditions. Accepted companion facets are excluded. Unknown facets receive original-context clarification. A policy question follows relevant independent gates, including dynamically added ones. It has no numeric targets. Combined assessment is optional by default and mandatory only once requested or in preserved FN reference mode.

`assessment_review.py` derives the bounded progression profile from confirmed gate evidence and the validated-original profile. It adds at most +2 once per fully resolved assessed concern, capped at 9. Reservations, conflicts, partial outcomes, rejected changes, uncertainty and skips do not produce an automatic gain. All arithmetic and reasons are shared by UI and export.

## Requests and runtime

Each full chat request is tokenized against a 4096-token context before generation. Evidence is rejected when over budget rather than silently truncated. Requests have at most one retry and a stage deadline of 180 seconds; transport timeouts are bounded by remaining time. Structured output uses the pinned XGrammar transport schema, with full Pydantic bounds enforced locally. Stage output limits are centralized in `llm_client.py`.

Session-local request caches include exact evidence, context, prompt, model and policy keys and clear on edits. Requests are serialized. Citizen sessions and raw inference audit data remain in memory until an explicit export. Deployment scripts manage only owned project processes.

Request caches store the validated wire response, not the transformed application result. Cache hits rerun the original validator, so ID-to-source conversions cannot break retries. Token counts have a separate bounded session cache keyed by the exact tokenization payload, endpoint and pinned model revision; edits and session changes clear it. Every request still applies the current output reservation and context limit. These optimizations avoid repeated generation or tokenization work; they change neither prompts nor sampling, numerical policy, validation or model precision. Cold-request latency improvements have not been measured. The live T01 report before these cache changes completed in 27.99 seconds with 23 generation calls, but had mapping errors (extra equity and missing noise condition), so it is not a quality pass.

## Reporting and compatibility

Export schema 5.4.0 contains the initial, final-original and optional conditional snapshots, bounded progression, policy decisions, evidence, versions and arithmetic traces. The final screen presents the initial, validated-original and final values separately. It discloses coverage changes and the selected construct.

The existing 4.1 audit record remains embedded in current exports because current reporting and regression tools consume it. The archived ordinal-description checker remains only for audit compatibility; it does not assign scores in the live application. Retiring the old one-shot client does not remove these active contracts.

See [the update policy](fn-followup-update-policy.md), [methodology](methodology.md) and [end-to-end experiments](../manual-tests/end-to-end-manual-tests.md).
