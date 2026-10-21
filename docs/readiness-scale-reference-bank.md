# FN v4 readiness-scale reference bank

This checkpoint imports the complete FN v4 draft anchor bank for direct source
inspection. It is provisional tool input, permitted by the project owner's
instruction, pending consortium validation. The workbook's `Read me!A2` identifies
it as a Task 3.2 draft. GA Annex 1 T3.2/T3.3 (printed p.9) distinguishes framework
validation from tool implementation; importing definitions does not approve an
operational scoring instrument.

From the repository root, using any Python 3.10+ (standard library only):

```bash
python3 scripts/import-readiness-scales.py build
python3 scripts/import-readiness-scales.py inspect --indicator Noise --profile citizen
```

The build reads
`references/private/IAM-CC_SRA_IAM_indicators_TRL_ORL_CRL_scales_v4.xlsx` and
writes `references/private/readiness-scales-v4.json`. Both remain Git-ignored.
The inspection command reads that JSON directly, without the workbook, model,
GPU, API or UI. Select an indicator by its exact source name (case-insensitive),
source number, or ID such as `indicator-07`. Profiles are `technical`,
`organisational`, and `citizen`. `--help` lists optional input/output paths;
generated source text is restricted to `references/private/`.

The importer resolves actual sheet names through workbook relationships, allowing
whitespace differences, and reads shared, rich and inline strings and numeric
level cells. It preserves wording, punctuation, whitespace and line breaks.
Merged indicator cells resolve to their source anchor; the repeated definitions
in the scales sheet must agree with the definitions in the criteria sheet.
Unexpected headers, formulas, missing cells, identity conflicts, incomplete
levels or duplicate keys fail the build before a bank is written.

The bank stores document identity/SHA256 and schema/bank versions once.
`indicators` retain source numbers, names, definitions and three assessment
criteria with source cells. `statements` carry explicit indicator/profile/scale/
level keys and source cells. Their `review_row_id` points to `review_rows`, where
the shared H/I row status and comment are stored once. These are not independent
approvals for three profiles. `generic_scales` contains the separate generic TRL,
ORL, CRL and SRL descriptions; there are no indicator-specific SRL rubrics.
`read_me` retains all non-empty notice cells. `references/source-register.json`
records source metadata and this checkpoint's scope; the build does not mutate it.

Verified source SHA256:
`809ce70aec6444fd59358ac1d79806d7c47fcfce72460c8430cb1dad64882818`.
The actual import contains 15 indicators, 45 assessment criteria, 405 non-empty
statements (135 per profile, nine distinct levels per indicator/profile), and
36 generic descriptions (nine per scale). All 135 source rows are `To review`;
all comments are blank. Inspection of Noise/citizen reproduces `G56:G64` in
order. Technical/organisational Noise cells `E56/F56/E64/F64` and generic levels
were checked against the source. Synthetic tests contain no private statements.

The supplementary report
`IAM-CC_D3.1_Initial_Societal_Readiness_Report_v0.18_with_LL_workshops.docx`
was found on recheck and reviewed. Its SHA256 is
`c86e4742793f7f30cb18b0abb51ee64110a1f968929627e11764c6e5fbe5aefd`.
All 15 names, 15 definitions, 45 profile criteria (Table 6), 36 generic
descriptions (Tables 2 and 5), and nine example statements (Table 7) match the
workbook exactly. This cross-check is recorded in the source register. Source
text in the bank continues to come exclusively from the v4 workbook.

Two points need partner clarification before the next assessment change. The
filename says `v0.18`, but document identification/history says `0.1` and first
draft; confirm which version to cite. The report discusses capability and
participation opportunities and proposes median aggregation and weakest-link
integration, explicitly to be finalised in T3.3 and tested in T3.4. These are
draft proposals, not approved operational rules. Future quality-control dates
are not treated as completed approvals. No internal definition/mapping conflict
was found.

At the importer checkpoint, no runtime imported this bank. The subsequent
[assisted self-assessment continuation](indicator-assisted-self-assessment.md)
now has explicit project-owner authorisation to use its draft definitions,
under a separate versioned prototype matching policy. The original reference
and review status remains unchanged. At that earlier checkpoint, `configs/readiness_levels.json`,
`ConversationSession.provisional_estimate`, `citizen_score.py`, Flask endpoints,
Vue UI, questions and evidence requirements remained unchanged. V4 descriptions
can differ from the old global anchors; the importer does not migrate the
historical estimate. The authorised continuation uses separate per-indicator
results, not the global score field. Questionnaire design, evidence sufficiency, evidence-to-level
policy, prerequisites, aggregation, weights and SRL synthesis remain separate
methodological decisions. The only corpus-builder change clarifies its missing
approved instrument metadata; the reference bank is not added to conversational
retrieval. The importer does not rebuild conversation corpora; operators can independently rebuild the existing collection from its original sources.

Focused verification:

```bash
.venv/bin/python -m pytest -q tests/test_import_readiness_scales.py
```
