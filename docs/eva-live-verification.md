# Eva interview repair: verification record

**Run date:** 2026-11-04
**Branch / base:** `fix/eva-sra2-live-reliability` / `eb67254585a89d1f9771f9c1b781530e36f40d43`
**Status:** implementation and deterministic checks in progress; FN semantic review pending.

All rehearsal inputs below are authored synthetic examples. They are not Living Lab evidence or participant responses. Each run has a unique directory under `.runtime/eva-live-review-20261104/`; failures and superseded runs are preserved. No source PDFs, source hashes, model weights, GPU allocation, production API, or real participant data were changed.

## Source alignment

The four PDFs and the rubric register were read in full using `pdftotext -layout`. Their identities match `references/chat-source-register.json` and `references/private/chat-rubrics-v1.json`:

| Interview path | Source SHA-256 | Applied behaviour |
| --- | --- | --- |
| Citizen short, 20 min | `61c0ad0db1b17ed4199ce426c84e450b7b9790dccca4826ddcaf29aee2df7ddf` | Gentle onboarding, open concerns, selective priorities, capability/opportunity/activity probes, separate opinion, short scale and review (pp. 1–16). |
| Citizen extended, 35 min | `75953ae14e76566238cd1914b17a147bd51d9c5dfba24db3ec9fb46da224f091` | Conditional deeper probes for affected groups, evidence quality, options/trade-offs, influence, accountability, changed conditions and continued involvement; its own scale/review (pp. 1–21). |
| Organisation | `093351fdd56a3931e603fb451b907d2790af0a6c0ed653436a4dd9e38c35ef6` | Unit remit and gaps, plans/resources, tested arrangements and lessons, routine integration and sustained adaptation (pp. 1–20). |
| Technology | `7d7ac7865fe846ca36b8c281444acc14edc06cca6ff367ac1492a81d131aa071` | Object/version/environment scope, staged evidence and integration/qualification boundaries, scale and respondent review (pp. 1–23). |

These are authored interview examples pending FN approval. The new generic profile judgment uses the registered profile-specific example scale; it does not average the fifteen indicator scores. The v4 indicator bank remains distinct. A citizen result is CRL, an organisation result ORL, and a technical-object result TRL. There is no individual or city-level SRL. Lack of participation opportunity is not treated as inability or influence. The policy and rubric are prototypes, not an FN-approved scoring algorithm.

## Live runs

Live tests used the actual API adapter, API on `127.0.0.1:8015`, and Qwen3-8B on `127.0.0.1:18000`. The API advertised `chat.synthetic_rehearsal=true`; the existing API at 8006 was not used or restarted. Generation-call and latency values are those observable in the screened synthetic exports.

| Path | Run(s) | Outcome |
| --- | --- | --- |
| Citizen short | `citizen-short` through `citizen-short-8` | Earlier attempts include API/privacy failures and scoring failures. Latest pre-final-score-schema run, `citizen-short-8`: 14 submitted turns, 12 generation calls, 4 reported attempts (3 retries), 3 authored fallbacks, 53.301 s model generation, 75.402 s elapsed; reached `review_addition` and screened JSON export. Generic CRL judgment was unavailable (`generic_profile_match`, schema field `explanation`); one objective remained unexplored. |
| Citizen extended | `citizen-extended-1` | Partial; 17 submitted turns, 13 calls, 45.666 s generation, 71.932 s elapsed. Conversation reached summary but did not reach the scale/result review. This is not a completed interview. |
| Organisation | `organisation-pilot-1` | Failed during summary/result processing with a privacy failure from the assessor path; 11 submitted turns, 8 calls, 25.682 s generation, 42.994 s elapsed. Partial screened export retained. No ORL judgment. |
| Technology | `technical-lab-1` through `technical-lab-4` | Runs 1–3 reached `review_addition` and exported screened JSON, but no TRL judgment was accepted. Run 3: 15 submitted turns, 11 calls, 2 reported attempts, 48.529 s generation, 72.358 s elapsed; the model returned a selected anchor while marking evidence incomplete/conflicted. After the fix, run 4 reached `review_addition`, exported screened JSON and produced an explicit abstention: 15 submitted turns, 10 calls, 0 retries/fallbacks, 40.063 s generation, 72.358 s elapsed. One objective remained unexplored. |

The score contract was changed so empty/long optional prose cannot invalidate anchor IDs and citations. A contradictory “selected anchor + incomplete/conflicted evidence” is normalized to an explicit abstention, with the selected level and citations discarded. Run 4 live-verified this conservative abstention path. It does **not** show that Qwen can produce a defensible non-null score.

The short and technical journeys reached respondent review, but the generic profile judgment was unavailable or rejected; therefore they are not successful scored journeys. “Completed journey” in the runner refers to having reached a review stage, not semantic success. The fixed synthetic scripts sometimes drift from Qwen’s adaptive follow-up and can reach summary earlier than intended. No score was tuned to match the PDFs’ illustrative levels.

## Deterministic checks and limitations

Affected broad test run: **97 passed, 1 warning**. The one spaCy/Click deprecation warning is informational. An earlier run had exposed a real-detector privacy failure: Presidio tagged the server-generated 48-character `preview_id` as a person in a confirm-cleaned request. A narrow `root.preview_id` plus 48-hex exemption was added, with a structural-only test; the affected API integration test then passed. Identical-looking values in respondent answer fields remain screened. After the score-abstention and near-duplicate-question changes, focused tests passed: **70 passed in 2.65 s**. `git diff --check`, Python byte compilation, and the Vue production build passed; build output reported 58 modules and 608 ms.

The full browser flow suite was not run. A focused Firefox smoke test opened `/chat` against the synthetic API and verified the title “Let's talk about drones”, a visible free-text composer, the direct route, and no legacy indicator form. The smoke test passed. Keyboard/mobile interaction flows remain unverified. Human semantic review remains pending; passing JSON validation does not establish assessment correctness.

## Rehearsal command

With the isolated synthetic API already running and Qwen available:

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv-api/bin/python scripts/rehearse-chat.py \
  --api-url http://127.0.0.1:8015 --allow-live \
  --case technical_lab \
  --output .runtime/eva-live-review-20261104/technical-lab-next
```

Use a new output directory each time. Never set `--allow-live` against a production participant API.
