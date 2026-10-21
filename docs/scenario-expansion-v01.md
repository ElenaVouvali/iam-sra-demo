# Six optional scenario adaptations v0.1

This supplements [questionnaire v0.2](questionnaire-v02-prototype.md). The
private ZIP was extracted to `references/private/scenarios-v0.1/` without
changing originals. It is configuration and authored reflection wording, not
an approved FN instrument, training data or a scoring policy.

Identity: `iam-sra-scenario-expansion-0.1.0` / `2026-10-21-v0.1`, compatible
with questionnaire `2026-10-21-v0.2`. JSON SHA256:
`022ed7e33d3ffb3f9c3774f137107ce04527f019ea7c15025c16afdd210c5e0d`.
ZIP SHA256:
`76dd496f8fd624631bc2a737e7bd9712382a71728c603c6aeb38f9422a677705`.

| Case | Supplied source status | Local source resolution |
| --- | --- | --- |
| expansion-01: disrupted road access | Planned demonstration context | GA local technical-annex PDF p.59 checked; D3.1 §12.2.1 hash/text checked |
| expansion-02: underserved emergency need | Reported need, not confirmed demonstration route | D3.1 §12.2.1 hash/text checked; not attached to an existing hospital route |
| expansion-03: whole delivery journey | Reported logistics requirements | Madrid workshop PDF and WP8 slides missing; **unverified draft adaptation** |
| expansion-04: noise reporting and response | Illustrative story in source | GA local PDF pp.52–53 and D3.1 §12.5 checked; no demonstrated mitigation outcome |
| expansion-05: comparing possible sites | Source-supported exercise without supplied options | Topic I3 and Use case(s) per LL A2/B2:D2, D3.1 §12.5 checked; WP8 missing; **partly verified draft adaptation** |
| expansion-06: service expansion/network | Illustrative story in source | GA local PDF p.53 and D3.1 §12.4 checked; no current local network conditions inferred |

“Verified” here concerns source identity/text, not verified service performance
or instrument validity. Package GA and Topic binary hashes differ from the
registered local originals. Package-claimed and actual local hashes remain
separate. Prefix differences are resolved by registered identity and checked
locators. D3.1 and v4 hashes match. Missing originals are precisely
`IAM-CC LL Madrid Workshop 11-09-2026 Results.pdf` and
`IAM-CC WP8 20260929.pptx`. No missing source was labelled verified.
GA page conventions were checked: local technical-annex pp.52–53/59 correspond
to the package's full signed pp.112–113/119, Part B pp.15–16/22.

## Implementation

`scenario_expansion.py` explicitly maps the six records into existing cards;
there is no generic registry or new retrieval service. It validates all routing
IDs against the 45 questionnaire modules and checks available originals against
the existing source register. `build-conversation-corpus.py` generates
`conversation-corpus-1.2.0`: the unchanged nine original cards plus six additions,
65 existing questions and 24 explanatory passages. `load_corpus()` supports the
legacy nine-card 1.1 collection and strictly validates the combined 1.2 collection,
source membership, source hashes and expansion/configuration identity.

The expansion JSON is itself the primary source of each authored adaptation;
references separately state original availability/hash status. No paraphrase
is mislabelled verbatim extraction. Case text, significant unknowns, illustrative
assumptions, source status, references and presented version survive screened
exports. Supplied source-basis summaries remain in the researcher inspection
view, outside respondent/model context. The privacy detector flagged fictional
names in one such summary; the runtime researcher summary is explicitly marked
privacy-redacted. Original package wording is preserved. Only fixed bibliographic
locators were added to the existing reviewed-citation list; respondent prose
screening was not relaxed.

New API/UI sessions copy the collection, and presented cards are frozen in the
indicator scope/exposure record. The expansion file participates in provenance
and API staleness checks. Changing configuration blocks stale actions until a
reviewed rebuild/restart; it does not silently replace a presented case.

## Administration and scope

A confirmed local actual/proposed use case stays primary. The optional-case
control in both Vue and Streamlit lets the participant select or decline a
source-status-labelled illustration. There is no compulsory second interview.
Selection uses existing retrieval: area, active indicator, previously presented
IDs and deterministic ordering; duplicate route families follow distinct
situations. The unexplained corridor bonus is removed. Related route IDs do
not transfer facts or authorisations.

For citizens, at most one authored case opening and one unresolved probe can
enter the existing bounded question candidates, only for a relevant tagged
module. The normal module opening remains, and all questions share the default
three-open-question budget. A model nomination must address a missing relevant
purpose and cite the actual answer. Tags are routing hints, never proof of
criterion sufficiency. Org/technical respondents use their profile module
questions, confirm the unit/responsibility or object/version/environment, and
receive no citizen reflection prompts. A card alone provides no respondent
evidence and yields no tool level. Outside-role/no-object states survive case
changes and continue to block fabricated levels.

The selected card and its unknowns/status/references enter the model context
with one module and its nine statements. Duplicate bookkeeping is omitted;
respondent evidence is never silently shortened. Explanatory retrieval filters
to the selected case plus generic workbook material; historical FN corridor
facts and other cases cannot leak into it. Read more and case presentation are
recorded information exposures. Scenario reasoning is neither historical
participation/influence, a VR/AR evaluation, nor real organisational/technical
validation.

Selecting the same case/version again does not restart a completed indicator.
A deliberate change invalidates that indicator and linked dependent evidence,
leaving unrelated completed results intact. Returning to a previously presented
case makes its text available collapsed, without requiring it to be reread.
Partial finish and decline remain available. Tool and participant judgments stay
separate, with no overall number or change to the v4 anchors.

## Build and review without replacing the deployed corpus

```bash
cd /home/elvouvali/IAM_CC/iam-sra-demo
PYTHONPATH=src .venv-api/bin/python scripts/build-conversation-corpus.py --output references/private/conversation-corpus-scenarios-v01.json
PYTHONPATH=src .venv-api/bin/python scripts/build-conversation-corpus.py --inspect-case expansion-04
```

The alternate output leaves `conversation-corpus.json` and its source-notes/
coverage sidecars unchanged. The inspection command starts no model/GPU/UI.
To use the expanded corpus with the isolated API command in the questionnaire
note, add:

```bash
IAM_CONVERSATION_CORPUS=references/private/conversation-corpus-scenarios-v01.json IAM_BASE_URL=http://127.0.0.1:18000 IAM_SRA_API_PORT=8004 IAM_SRA_UI_PORT=5004 scripts/start-api.sh
```

Set the same `IAM_CONVERSATION_CORPUS` environment variable for the alternative
Streamlit command. Build/serve Vue on review port 5004 as documented there.
No running service was restarted for this integration.

Small live check, using only the existing service:

```bash
IAM_CONVERSATION_CORPUS=references/private/conversation-corpus-scenarios-v01.json PYTHONPATH=src .venv-api/bin/python scripts/smoke-questionnaire.py --base-url http://127.0.0.1:18000 --case disagreement --scenario expansion-04 --output .runtime/scenario-citizen-smoke
```

Demonstrate citizen Noise with expansion-04, organisational Noise with the same
case and explicit responsibility, and technical safety with expansion-03 plus an
actual named test object. The latter case must display its unverified-source
status. A textual case never proves completed technical tests. Request a draft
suggestion, review the nine statements, disagree or remain unsure, finish a
partial profile, reload and download. See [observed verification](questionnaire-v02-verification.md)
for successes and model failures; successful UI operation is not scoring validity.
