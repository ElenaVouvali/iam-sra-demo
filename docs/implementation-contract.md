# Implementation contract
Source: Future Needs, SRA_LLM concept feasibility.pdf, 10 PDF pages, read locally; PDF remains outside Git.

Requirements: English corridor scenario (p.5), register 15 concerns in three phases (pp.1–2), structured interpretation (pp.3–4), preserve four-score reference and bottleneck example (pp.6–7), targeted hypothetical validation questions (pp.8–9), no coaching.

Executable provisional choices: concern-specific acceptance anchors 1–9; null for missing or ambiguous evidence; at least three assessed concerns for scenario summary; phase means over assessed concerns; phase-1 scores ≤3 eligible for lowest score +2 cap, applied with min so it cannot raise a mean; half-up rounding. All choices are experimental. Qwen extracts evidence, application controls flow and arithmetic. Original interpretation is immutable in session history; corrections are separate snapshots. Validation is qualitative.

Unresolved: score anchors, bottleneck definition, arithmetic discrepancy, numeric updates, overlapping outcomes, leading/bundled validation wording, and limited scenario coverage. See methodology.md. No personality or ignorance diagnoses, official EU instrument claims, or psychometric validity claims.

Additional executable safeguards: score/concern-position consistency and a conservative, versioned English evidence-eligibility screen. These are provisional rejection rules requiring FN feedback; they never manufacture or replace a score.
