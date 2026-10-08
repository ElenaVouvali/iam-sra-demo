# Data handling

Citizen testimony, interpretations, confirmed meanings, scores and raw structured inference audits live in the individual Streamlit session. There is no application database or routine raw-citizen-text log. Model requests go to the configured HTTP endpoint, localhost by default. Reset discards application session state; it cannot erase an export already downloaded by the citizen. No stronger process-memory erasure guarantee is claimed.

Explicit JSON and JSONL exports include citizen evidence, corrections, follow-up answers, proposal contexts, score decisions, confirmations, model settings and aggregation traces. Visible thinking is rejected and is not retained in raw output traces. Current schema 5.4.0 also contains the final-assessment review and bounded-progression decisions.

Service logs and generated evaluation reports are under ignored `.runtime/`. vLLM request-content logging is disabled by the project launcher. Synthetic diagnostic scripts can save raw structured outputs explicitly; manual/live reports can contain full testimony and should be handled accordingly. Git ignores session exports, environment secrets and runtime data.

Historical diagnostics moved to the [external cleanup archive](repository-cleanup.md) still contain their original synthetic evidence. Archiving keeps them out of the active repository; it does not anonymize or erase them.
