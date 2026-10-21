> Privacy screening is mandatory for every case, including demo fixtures. There is no runtime bypass. Missing local detector resources block processing. Run `scripts/setup-privacy.sh` and `.venv-privacy/bin/python scripts/check-privacy.py`. Screening can miss private information; use synthetic examples.

# Internal synthetic demonstration: privacy and data handling

The API integration preserves these screening gates. A real-detector HTTP export
check found that spaCy misclassified the current Git commit as a person. The
generated `provenance.code_commit` field now recognises only a full lowercase
40-character hexadecimal Git identifier as integrity metadata, alongside the
existing narrowly located SHA-256 metadata. The same text in an answer remains
screened. Names, credentials and arbitrary strings in that metadata field remain
screened too; this does not exempt respondent or model prose.

A final real-resource API export check also reproduced a spaCy PERSON finding on
a substring of a randomly generated public session UUID. The exact UUID4 encoding
is now recognised only in known controller/export and presentation ID locations,
including baseline/scenario records and archived scenarios. IDs provide references,
not ownership: the signed HttpOnly cookie is still required. UUIDs in answers,
respondent context and nested respondent JSON remain screened, as do names,
credentials and arbitrary strings in the ID fields. Synthetic and real-detector
regressions exercise the reproduced identifier and these boundaries.

The v1.2 synthetic respondent evaluator writes only to ignored `.runtime/`
paths, marks each generated session `SYNTHETIC_TEST_ONLY`, and passes the full
record through the same privacy screening. If screening withholds an artifact,
the run report retains a minimal screened status record; screening is never
disabled for synthetic tests.

IAM-SRA2 starts with a scenario-free general interview and offers a separate optional citizen proposal example. Neither the general interview nor a role selection assigns readiness. This is **an internal demo for synthetic examples**, not a production service, an anonymisation guarantee or a GDPR certification. Do not enter names, private addresses, contact details, credentials, bank details or identifiable medical information. Use general descriptions.

## Implemented flow — privacy-1.0.0

The selectable `retrieval_grounded_conversation` mode exports schema
`iam-conversation-1.0.0`: separately contextualised general/scenario components,
confirmed snapshots, original screened answers, corrections, retrieved question
plans, exact information exposures, unresolved attempts and source/code/model
provenance. It uses the same mandatory local boundary and final download checks.
The corpus and source-comparison sidecars remain private; neither citizen answers
nor identifiable session records are indexed. The role/city picker, optional RAG
question, interpretation feedback and edits all use the existing screening flow.

The new mode's exact version strings and fixed workbook locators are registered
application metadata after real Presidio PERSON false positives. No arbitrary
strings or respondent answers are exempted. An address-only cleaned fragment is
not sent for assessment. A safe answer remains available for retry after a
withheld generated interpretation; an unsafe original is cleared from
application-owned text widgets. This does not promise forensic memory erasure.

`meeting_notes` is a single private file. Workbook original draft/feedback text
is retained in a private comparison sidecar, outside retrieval, rather than fed
wholesale into the planner. Only screened, curated question variants and
allowlisted explanations enter the new mode. Historical numerical examples are
researcher references and excluded from citizen explanation retrieval.

```mermaid
flowchart LR
  B[Browser text widget] --> S[Local Streamlit server]
  S --> P[Local Presidio and contextual screening]
  P -->|Clean or explicitly confirmed masked text| M[Local model or bounded retrieval]
  M --> O[Output screening and evidence validation]
  O --> R[Screened session record]
  R --> E[Final privacy check]
  E --> D[Optional download]
```

The browser and transient Streamlit widget memory necessarily receive the submitted text before screening. Screening runs before application draft/evidence retention, content caches, tokenization and generation. `/tokenize` receives text too and uses the same outbound gate. Local detection sends no text to a cloud PII service.

Credentials, contextual PINs, financial details and identifiable medical identifiers are blocked with a message that does not repeat them. Detected unnecessary names, contact information and private addresses produce a masked preview for explicit confirmation. Only confirmed cleaned text is processed, and edits are screened again. The application does not retain raw-to-masked mappings, rejected originals or secret hashes. Rejection consumes no interview question and changes no assessment. Rejected widget references are cleared on the next safe Streamlit rerun; this is not forensic memory erasure.

All model responses are screened before validation traces, history or display. Routine inference traces retain structural metadata, not raw model output. Unsafe output is withheld. Curated retrieval passages are screened before use; exact source-register bibliographic titles, local source filenames and hashes are separately allowlisted metadata, not a general exemption for draft or approved content. Citizen sessions and stakeholder lists are never indexed. Evidence and citation checks remain required after privacy screening.

Every download is screened again. Unsafe or older records without the current privacy contract are withheld rather than silently rewritten. Start a new synthetic session; existing files are not deleted. New general-interview exports use **iam-baseline-2.3.1** (old frozen sessions retain their original **1.0.0–2.3.0** versions); scenario exports use **6.4.0** or **6.5.0** when carrying separate baseline provenance, and researcher evidence reports use **1.1.0**, with `privacy_contract=privacy-1.0.0`. Historical acceptance code and exports are isolated on the legacy branch. Confirmed snapshots remain versioned and unchanged by later answers.

## Dependencies and detector limits

The implementation uses **Presidio Analyzer**, spaCy and local contextual recognisers. **NeMo Guardrails is not integrated**: it would add orchestration without improving this bounded screening boundary. Pins are in `requirements-privacy.txt`: Presidio Analyzer 2.2.360, spaCy 3.8.7 and the English CPU model en_core_web_sm 3.8.0. Install them with `scripts/setup-privacy.sh` into the separate `.venv-privacy` UI environment; this does not alter the vLLM/PyTorch environment. No NLP model is downloaded at request time. Missing or incompatible resources fail closed with an actionable setup message.

The selected versions satisfy the published package constraints ([Presidio package metadata](https://raw.githubusercontent.com/microsoft/presidio/2.2.360/presidio-analyzer/pyproject.toml), [English model metadata](https://raw.githubusercontent.com/explosion/spacy-models/master/meta/en_core_web_sm-3.8.0.json)). Actual installation resolution must still pass `pip check` on the host. Only English screening is configured. Pattern and statistical detection can miss names, addresses, indirect identifiers, unusual secrets and medical descriptions, and can over-mask ordinary words. General caring responsibilities, public place names, altitude and flight counts are not intentionally treated as secrets. Context recognisers supplement Presidio; no universal detection claim is made. Masked text is not necessarily anonymous.

Pinned detector resources are available in `.venv-privacy`. Focused tests run the actual detector separately from synthetic detector doubles. Passing these bounded fixtures does not establish a population-wide detection or false-positive rate. Run `scripts/check-privacy.py` on the intended host before the meeting.

## Retention and infrastructure boundary

There is no application database. Screened testimony, interpretations, confirmations, corrections, exposures and provenance live in the Streamlit session and optional downloads. Reset drops application references, not securely erased process memory, service logs or downloaded files. Downloads remain with their recipients. `.runtime/`, private originals and identifiable session files remain Git-ignored.

Project launchers bind services to localhost and disable vLLM request-content logging. Application transport errors omit response bodies and unsafe exception text. Existing infrastructure, reverse proxies, shell history, crash handling and administrator access are outside this application's guarantees. Old runtime logs or exports predate these controls and are not automatically deleted or retrospectively certified safe.

## Institutional decisions still required

Before real citizen use, establish the responsible controller and contact, purpose and lawful basis, recipients/processors, retention schedule, rights procedures, special-category handling, access controls, and DPIA screening where applicable. A consent checkbox does not resolve these decisions.

The supplied GA describes data-management and ethics work, including D1.2 Data Management Plan and WP13 D13.1 OEI Requirement No.1. The completed DMP and WP13 deliverables were **not supplied**; no institutional policy is inferred from their planned existence. This build remains an internal synthetic demonstration until ownership and deployment decisions are agreed.


### Host detector check update

Pinned Presidio/spaCy resources subsequently became available. Real screening identified false PERSON matches on workbook cell references J8/L13 in the curated citation metadata. Exact reviewed citation-location strings are now registered separately and exempted as bibliographic metadata; unreviewed text remains screened. Real synthetic preflight also exposed a phone-number miss at the configured threshold; a contact-context phone recogniser supplements the statistical detector. This small preflight does not establish universal detector coverage.

A subsequent full-request regression identified false PERSON matches in controlled prompt wording and JSON-schema/topic labels (for example `minLength`, `Topic Ids`, and `Airspace`). The prompt was rephrased without changing its criterion. Standard schema keys are treated as structure; exact generated schema titles and configured topic labels join the reviewed metadata set. Arbitrary caller-provided titles, descriptions, source prose, citizen testimony and generated interpretations remain screened. Real-detector tests now exercise both extraction and grounding request envelopes against synthetic HTTP responses; they do not establish live Qwen semantic accuracy. Restart the project UI after updating Python modules to avoid retaining old imported notice/policy code.

Structured audits now distinguish lowercase machine field keys and generated `R<number>_<number>` evidence/event IDs from free prose. Credential key/value pairs are still explicitly screened. Exact controlled thematic labels (such as Noise) are excluded from PERSON findings; they are not a wildcard for surrounding names, contacts or descriptions. The static draft-information label and reviewed workbook locations are registered metadata. All three meeting cases completed baseline and information/correction/export paths with the real detector and controlled extraction responses; actual model output remains a separate host verification requirement.

### Generated-JSON boundary correction

Model response envelopes contain structured JSON inside `content`. Valid JSON object/list strings are now parsed and recursively screened as fields, rather than treating field names and punctuation as prose. Invalid JSON remains screened as text; parsing never bypasses semantic strings or contextual credential key/value checks. Regression tests assert that JSON-wrapped credentials and contact details are still rejected. Output rejections retain only safe structural stage/entity-type metadata and no rejected response. They tell the user to retry the same answer, rather than incorrectly requiring a new session. The exact trigger in the reported live screenshot was not available; this fixes a reproducible architectural source of false positives, not a claim that the unseen live response was inspected. Five real-detector tests passed, including six controlled meeting paths; 88 focused regression tests passed with five detector-dependent tests skipped in the original environment. Live Qwen outputs remain unverified here.


### General interview 2.0.0 — bounded address and preview hardening

The local street recogniser now uses case-insensitive, word-separated street
markers with a house number. It covers number-first/street-first English forms,
selected Spanish/Italian/Portuguese street prefixes, selected Greek street forms,
and adjacent unit/postcode details. A regression prevents substring matches such
as `most 100` being treated as `St 100`. Explicit address context remains supported.
Unlabelled adjacent postcodes are masked only following a detected street address;
bare years, altitude, flight counts, broad city names and `near my home` are controls.
The NLP resource is still English: these bounded patterns are not comprehensive
multilingual detection. Accents, transliteration, unconventional addresses, indirect
identifiers, and unlabeled medical details can still be missed; names can be
misclassified. No arbitrary user-string exemption or privacy switch was added.

Masked previews are bound to the session/action, step, version, pending answer,
question, information-exposure sequence and controlled context selections.
Navigation, editing, reset, changed context or new typed input invalidates stale
previews; no raw text or secret hash is used for this binding. Only the confirmed
cleaned action reaches a controller. New context free text, answers, corrections,
model/tokenisation envelopes, pending and confirmed exports are screened.
Controlled sector/category metadata is not evidence of capability. Exact reviewed
GA taxonomy wording is bibliographic/configuration metadata, not an exemption
for surrounding citizen text. Existing credential/financial blocking remains.

Optional definition displays record exact content/version/time and a pre-display
profile. They are not answers; later evidence is marked after information and
cannot establish independent prior knowledge by repeating that text. Baseline
answers are never indexed in RAG. Browser/server transient receipt, retention,
rights, lawful basis, controller/contact and access/security obligations remain
as described above and require institutional review before real citizen use.


Actual-detector export tests exposed intermittent PERSON classifications of random
session UUIDs. The existing machine-identifier PERSON filter now recognises the
strict canonical version-4 UUID syntax, alongside generated evidence IDs. This
excludes only the mistaken PERSON finding: contextual credentials and all other
entity checks still run, including a password whose value is such a UUID. It is
not a general user-string exemption or a claim that session identifiers are anonymous.

Privacy notices at baseline free-text entries use information boxes. Cleaned previews explain the replacement marker and require explicit confirmation before assessment. A narrow English UI check rejects answer fragments containing only the privacy marker and address-introduction words (for example, “My [private detail removed]”); it requests a new answer or Skip without a model call or consumed question. This is not a general relevance classifier or multilingual completeness check. Useful remaining answer text and context fields retain the existing screened-preview confirmation workflow.

### Baseline 2.3.1 — input versus generated-output rejection

Generated-output screening can consume the second existing model attempt; it adds
no retry budget and never retries when detector resources are unavailable. The
rejected body is excluded from retry feedback, traces and caches. A baseline
output/derived-record rejection keeps the already screened answer available for
retry without committing an interpretation. Input rejection still clears unsafe
widget text and requires cleaning/resubmission. Exports still withhold unsafe
records. Only screened failure metadata is logged (stage/boundary, entity type,
recognizer, confidence and field path); no rejected content is logged. The exact
trigger in the reported live screenshot was unavailable and is not claimed as an
adjudicated false positive. See `baseline-recovery-2.3.1.md` for verification scope.
