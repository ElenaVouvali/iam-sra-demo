# Main and legacy separation — 12 October 2026

`legacy/iam-sra-demo-2026-10-08` preserves the original IAM-SRA demo at
`708024817f31b48c7a9009a8ba5103cbf10b93f8`. Its existing local worktree remains
at `~/iam-sra-demo-2026-10-08`, configured separately on port 8502.

Main retains the updated baseline (including current v2 edits and benchmark
fixtures), optional scenario interview, privacy controls, reviewed retrieval,
workbook score screen, current tests and service tools. The old acceptance UI,
scoring/aggregation and follow-up machinery, calibration scripts, manual packs,
old prompts/configuration and superseded implementation documents are removed.
Shared transport, passage provenance, input validation and topic metadata are
trimmed to the updated app. CI runs the retained test suite.

Before cleanup, all tracked and nonignored untracked files were backed up outside
the repository in `~/iam-sra-pre-main-cleanup-20261012T144606Z.tar.gz`.
Existing model weights, virtual environments, private sources and runtime files
were retained. No shared services were stopped or restarted.

The branch separation is prepared locally. Publishing requires GitHub write
access; the current connector returned 403 and shell Git could not resolve
GitHub. See README for running both local versions.

Offline cleanup verification: **254 passed, 9 skipped**. The skipped checks
require real Presidio resources. Local Markdown links, Python compilation, shell
syntax and whitespace checks also passed. No live model accuracy or UI service
restart is claimed.
