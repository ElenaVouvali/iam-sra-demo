# Synthetic A2 live retest: S8

This bundle records a fictional, scripted citizen interview processed by the real Qwen3-8B AWQ interviewer, interpretation/routing and scorer on Liono A2. It is synthetic engineering evidence, not human-participant evidence, FN approval, or independent CRL validation.

Configuration: thinking enabled, 8,192-token context, `model_led_fn`; see `metrics.json` for run measurements. The transcript preserves repeated questions and unsolicited explanations. The structured trace is developer diagnostic data; it does not contain raw hidden chain-of-thought. Private FN source files and model weights are not included.

Files:

- `S8_uninformed_project_sceptic_short.md`: complete participant-facing transcript and result.
- `S8_uninformed_project_sceptic_short.json`: exported session.
- `S8_uninformed_project_sceptic_short.jsonl`: event export.
- `S8_uninformed_project_sceptic_short-trace.json`: authenticated developer trace captured for this synthetic run.
- `metrics.json`: model and run metrics.
