# A30 live generalisation session artifacts — 26 November 2026

These are complete exports from fictional, Qwen-generated respondents interacting with the real IAM-SRA2 interviewer, interpreter, controller and scorer. They are synthetic development evidence, not real-participant data, expert review, or independent score validation.

The JSON and JSONL files contain the screened interview records, Markdown files contain readable transcripts, `*-trace.json` files contain authenticated structured decision traces, `*-view.json` files contain participant-view exports, and metrics/summary files record run outcomes. The trace contains validated action/state decisions and structured model proposals; raw hidden chain-of-thought is not present.

Configuration: Qwen3-8B FP16, thinking enabled, 8,192-token context, revision `b968826d9c46dd6066d109eabc6255188de91218`; application checkpoint `ffd91addd469370465f71d500c52abdcc86df155`. The synthetic respondent used the same checkpoint with thinking softly disabled.

`G2-citizen-short/` preserves the initial failed network attempt (summary and metrics only); `G2-citizen-short-retry-network/` is its completed retry. The complete G5, G7 and G10 runs are also included. Review artifacts together with [`../../docs/a30-generalisation-live-examples.md`](../../docs/a30-generalisation-live-examples.md), which summarizes observed scoring strengths and failures.

These exports include FN interview text and the official source identifiers used by the prototype. They are included for debugging at the repository maintainer’s request.
