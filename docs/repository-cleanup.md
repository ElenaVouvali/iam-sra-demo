# Repository cleanup — 6 October 2026

The active repository now contains the current application, policies/prompts, model-serving tools, diagnostic runners, automated checks and the complete manual experiment pack. Historical report data has been moved outside the repository rather than mixed with current performance documentation.

## What was retired

- The pre-confirmation `legacy_session.py` implementation. Its inference-audit helper moved to `inference.py`, which the current session uses.
- The one-shot `LLMClient` assessment/scoring interface and its separate score schemas and prompt. `LLMTransport` retains the bounded request/retry logic used by `ConversationClient`.
- The unused fixed-key facet extractor and its prompt, the bypassed registry-batch mapping path, and unused position-description helpers. Current expressed-issue evidence extraction and independent facet assembly remain.
- Old FN question selection and qualitative final-report helpers. Current reference-question choice outcomes, independent gates, macro-policy questions and final reporting remain.
- Five obsolete smoke scripts (`smoke.py`, `smoke-confirmed.py`, `smoke-ui.py`, `smoke-discovery-ui.py`, `smoke-updates.py`) that exercised old workflows, controls or export versions. Current UI regression tests and end-to-end manual scripts cover the current flow.
- Historical documentation reports and `docs/history/`, saved `eval/results/`, an unused development-heldout fixture, and 32 generated runtime reports.
- Tests exclusively for retired interfaces. Transport checks now exercise the current conversation client; active facet assembly, evidence, export and update checks remain.

`eval/run.py` now uses the application's interpretation, explicit scripted confirmation and initial scoring sequence. It no longer compares an obsolete one-shot implementation. README and current documentation have been rewritten to remove contradictory historical scoring descriptions and broken report links.

## Preserved application material

All 32 initial cases, 155 baseline end-to-end runs, nine extension experiments and their authored score targets remain. Model identity, scoring/update policy values, environment pins, service launch settings, weights, service logs and PID records were preserved. The current 4.1 audit record embedded in schema 5.4 exports and the archived-ordinal audit checker remain because active reporting/replay tools use them; neither is an alternative live scoring engine.

Python bytecode and pytest caches are generated material and can be rebuilt. The large `.venv` and `.runtime/huggingface` directories are required local runtime dependencies, not obsolete reports.

## Recoverable archive

Archive: [iam-sra-demo-cleanup-archive-20261006T161654Z](/home/evouvali/iam-sra-demo-cleanup-archive-20261006T161654Z). It contains:

- `removed/`: historical reports and retired files at their original relative paths.
- `before/`: original copies of edited files.
- [manifest.json](/home/evouvali/iam-sra-demo-cleanup-archive-20261006T161654Z/manifest.json): moved paths, byte counts, before-copies and renamed files.

There are 53 moved entries (some are directories), totaling approximately 10.4 MiB. Restore specific files from this archive when reviewing past experiments; restoring old implementation files can reintroduce obsolete behavior. The archive is outside the app's repository and is not imported or used at runtime.

For current verification, see [verification status](verification.md). Historical success counts and model errors are retained in the archive, not presented as measurements of today's application.
