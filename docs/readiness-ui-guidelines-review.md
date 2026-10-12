# IAM-SRA2 interface review — 12 October 2026

## Source and scope

Read all 19 PDF pages and visually inspected rendered examples on every page of
`IAM-CC_UI_guidelines_for_tools-2.pdf`, version 1.0, September 2026, WP2/T2.1.
SHA-256: `c062b1ff1c38a40848cd0a34dc600ca46f121add7d0e876db056083697618cc3`.
Original and a local reference copy remain outside Git/in ignored references/private.
No AGENTS.md was found in the checkout or its parent source directory.
Baseline: 6de0ff9 with existing uncommitted citation-reliability changes preserved.

No separate partner kit, Google Sans files, approved IAM-CC logo/mark, EU emblem,
or lead-partner logo was supplied. No logo was redrawn, cropped from the confidential
PDF, downloaded or falsely presented as approved. This is **partial guide alignment**,
not full brand/accessibility compliance or FN approval. The plain IAM-CC text identity
is temporary text, not an approved logo. The guide permits a system-font fallback on
p.8; it also requires loading Google Sans for handover, so that requirement stays open.

## PDF-to-implementation checklist

Requirement rows below are normative guidance unless marked example, own choice,
conditional, or pending. Page numbers are PDF pages, matching the printed numbers.

| Page | Guidance / distinction | Component and implementation | Verification / remaining limit |
|---|---|---|---|
| 1–4 | Title/introduction/contents, foundations divider | Reviewed for context; no additional UI rules inferred | Full text and rendered pages read |
| 5,7 | Dark Azure #16364D carries text/UI; Blue Slate #55788E secondary; Azure 50 #F3F6F8 surfaces | .streamlit/config.toml and assets/ui/iam-cc.css centralise palette | Theme/CSS consistency and text-pair contrast checked; computed browser styles pending |
| 5,7,11 | Pastel Coral #FF8174 only for one key action, never body text, alerts or decoration | One application-owned iam_accent container per screen; Continue, confirmation, correction or JSON download | AppTest verifies primary actions on answer/review/interview; no readiness colour/reward styling |
| 6 | Official logo leads header, divider then tool name; partner marks footer only; supplied files only | ui_presentation.header has temporary text IAM-CC, divider, IAM-SRA2 and hub-home link | **Blocked:** approved kit missing; no fake logo/favicon or partner claim; clear space/min logo width awaits real asset |
| 7,14 | Status colours #2E7D5B / #8F5117 / #B3261E, with icon and label; no coral alerts | Neutral native alerts, danger/warning border hooks and explicit icon+text on error/reset | Error/reset text and retained drafts tested; browser icon/style inspection pending |
| 8 | Google Sans; documented system-ui/-apple-system/Segoe UI fallback; hierarchy 32/24/18/15/14/13/12 | CSS uses fallback, 32px title, 24px sections, 15px body, 14px labels/buttons, 13px captions | Google Sans **pending kit**. No external font request. 18px temporary header identity. No chart/table labels required |
| 8 | Sentence case, left alignment, outline icons if used | Sentence-case native controls; no decorative icon set imported | Native status icons have text equivalents; icon-kit styling awaits browser/kit review |
| 9 | 4px spacing, 12px inputs, 20px panels, pill buttons; width 360–1312 | CSS: 16/24px form padding, 20/40/64px responsive margins, 20px forms/expanders, 12px fields, pill buttons | Static CSS reviewed; viewport screenshots and overflow tests pending |
| 9 | 12/8/4-column grid and elevation tokens | **Partial / own usability choice:** linear reading/form flow, no multi-column grid or extra hover animation | Avoids unnecessary columns on mobile; not claiming a pixel-identical slide reproduction |
| 11 | Accent/primary/secondary/ghost/destructive variants; 1–3-word verb-first labels; 40px medium controls, focus ring 3px | One accent primary; alternatives/download JSONL secondary; reset is confirmed, danger-outline inside native modal | Reset cancel/dismiss leaves underlying form mounted; confirmed reset tested; some existing long edit-answer labels intentionally retain question context |
| 12 | Visible labels, optional fields marked, 12px radii, checked states Azure | Native labels/checkbox/radio; optional explanation labelled; primaryColor Azure avoids coral selection | Label and interaction tests. **Partial:** native Streamlit form validation is on submit, not blur; cannot promise field-specific red borders without component work |
| 13 | 20px cards, 16–24px padding; lists for long records | Native form panels and expanders; concise findings with additional records in expanders | Long interpretations/words remain available, exact text remains in audit; no invented badges/table metrics |
| 14 | Say what happened and next action; neutral empty states; loading progress/estimate | Friendly failures preserve text; unknown evidence described neutrally; existing reading spinner retained | Failure/retry and empty findings tested. No latency estimate invented; meaningful inference ETA/progress not implemented in this UI-only change |
| 15 | Charts/maps palette and chart accessibility (conditional) | Default demo has no readiness charts/maps, numbers or progress gauges | Not applicable; historical arithmetic unchanged; no new chart series |
| 16 | Hub-integration divider | Reviewed; no extra rules inferred | No deployment performed |
| 17 | Choose embedded A or external B with WP2 | Local standalone preview; **Mode B-like**, not a claimed approved integration | WP2 must choose mode. Mode A header/footer suppression, frame-ancestors and HTTPS are hosting work, not changed here |
| 17 | Mode B header 56–64px, logo/hub/tool-page links; title Tool name | IAM-CC; official favicon | 64px wrapping temporary text header, IAM-SRA2 | IAM-CC title; hub-home HTTPS link opens new tab safely | Logo/mark and exact tool-page URL pending. Mobile header may wrap; no guessed tool slug |
| 17 | Mandatory Mode B EU funding footer, partner credit/logo, privacy link | Exact supplied funding wording visible in footer; accessible Privacy and project information expander | EU emblem/lead partner credit/logo and approved public privacy URL **pending**; expander is local disclosure, not a substitute for final policy URL |
| 18 | Screenshots 1440/390, 360 width, 200% zoom, keyboard, contrast and FN handover | Deterministic AppTest screens and regressions; scoped focus CSS and native controls | No browser installed: no actual app screenshots, mobile pixel checks, keyboard/focus/200% zoom audit or WCAG certification claimed |
| 18 | Hub metadata/card image/related guides/Skills Lab/lead partner | See handover decisions below; illustrative medical subtitle retained | No invented lead partner, module, card image or public endpoint |
| 19 | Closing page | Visually inspected | No additional requirements |

## Additional citizen-journey choices (user request, not invented PDF rules)

- Current-step navigation explains recurring confirmation; no numeric readiness
  progress indicator. The proposed sequence is described without locking the controller.
- Review shows at most three findings in each category immediately, with all additional
  findings and supporting words on demand. This is presentation, never evidence deletion.
- Results distinguish “Your views of this proposal” from “What you told us about
  understanding and participation”. No opportunity/experience/uncertainty deficit inferred.
- Raw coverage/change JSON and failure diagnostics are developer-only. Complete
  JSON/JSONL downloads remain prominent and preserve their schema and meaning.
- Optional explanation/reflection stays optional, exact exposure logging unchanged.
- Editing calls the existing invalidation machinery; no stale dependent final downloads.
- Reset uses a native modal so the underlying form stays mounted, including drafts.
- Model-produced findings use plain text rather than rendering their content as markdown.

## Versioning and methodological boundary

Instrument 1.2.2 records the neutral initial invitation and its preceding wording in
presentation_revision. Earlier sessions retain their frozen instrument and previous
invitation. This initial wording can affect elicited answers; it is not claimed to be
measurement-invariant. Follow-up definitions retain their 1.2.1 versions and exact
question texts; extraction, eligibility, five-question budget, information-module
content/version, evidence validation, scoring/nulls, snapshots and export schema are
unchanged by this UI task. This change does not amend the separate pre-existing,
uncommitted citation patch or historical arithmetic.

## Verification and limitations

See tests/test_readiness_evidence_ui.py for deterministic initial, review, interview,
correction, reset, final, model-error, developer and optional-reflection screens.
These do not establish live Qwen semantics. No live inference is needed for this
presentation-only change. Runtime-only screen descriptions are saved under
.runtime/ui-review-screens.json; they are **not screenshots**. Browser automation,
Chromium/Chrome, Playwright and Selenium are unavailable here. Therefore desktop/mobile
layout, actual keyboard/focus, visual contrast, 200% zoom, assistive technology and
rendered CSS effects remain manual checks, not passed tests. No public service restarted.

Known Streamlit limits: theme CSS hooks are pinned to Streamlit 1.45.1 data-testid and
application-owned container keys; they avoid generated Emotion classes but still need
browser recheck after upgrades. Native field validation is submit-based. Native modal
focus trapping and return focus are delegated to Streamlit, not verified in AppTest.
The optional explanation remains reading acknowledgement on click, not proof of reading.

## FN/WP2 handover decisions

Supply approved logo variants/mark, font files and licence, EU emblem and lead-partner
identity/logo; agree Mode A vs B, tool-page URL, public privacy policy and hosting
security. Review the neutral invitation as an instrument revision. Provide numerical
CRL criteria/prerequisites/aggregation/verification rules separately; this UI supplies
none. Decide whether this chat counts as engagement/co-design; currently it does not.
Before launch, visually check every main screen at 1440/390 and 360px plus 200% zoom,
keyboard/focus and screen-reader labels, then submit screenshots to WP2/FN for review.

Suggested hub copy (draft, not approved): “Share your views and experiences of an
illustrative medical drone route.” Audience: Citizens, Researchers. What it does:
collect proposal views; clarify understanding and participation evidence; export a
confirmed descriptive summary. For citizens exploring an illustrative proposal.
Lead partner, production URL, Skills Lab links and approved card image remain unset.

## Run locally

```bash
cd /home/evouvali/iam-sra-demo
scripts/stop-ui.sh
scripts/start-ui.sh
```

Open http://localhost:8501. Restart only this project UI to load changes (watcher is
disabled); no vLLM restart needed. For deterministic plumbing only:
`IAM_MOCK=1 .venv/bin/python -m streamlit run app.py --server.port 8502`.
Developer diagnostics require IAM_DEVELOPER=1 before starting the UI. No push performed.

## Changed files and user benefit

| File | Purpose |
|---|---|
| .streamlit/config.toml | Guide-derived light palette; Azure selected controls, no global coral selection colour |
| assets/ui/iam-cc.css | Central palette, type scale/fallback, spacing, pills, rounded fields/panels, responsive margins, focus and disabled-state rules |
| src/iam_sra/ui_presentation.py | Reusable identity, navigation, funding/privacy footer, safe plain-text findings and reset confirmation |
| app.py | IAM-SRA2 page/header identity; shared styling/reset/footer, historical diagnostics developer-only; no historical arithmetic changes |
| src/iam_sra/readiness_ui.py | Concise citizen review/results, accessible secondary actions, explicit primary action, optional reflection, visible exports, developer-only internals |
| configs/readiness.json | Instrument 1.2.2 neutral invitation with recorded preceding wording; frozen sessions preserved; follow-ups unchanged |
| references/source-register.json | Guide hash and reviewed pages, no claim of implementation approval |
| tests/test_readiness_evidence_ui.py | Reset/cancel, corrections, long text, distinct controls, export/UI agreement, old-instrument wording and developer visibility regressions |
| tests/test_ui_error_messages.py | Historical failure-detail visibility updated to developer-only; evidence failures still retain citizen text and complete diagnostics |
| docs/readiness-ui-guidelines-review.md, docs/readiness-v120-fn-review.md, README.md | Source checklist, limitations, versioning and run instructions |

Readiness session/profile code and information-module configuration were inspected
and left unchanged. The six already uncommitted citation-patch files were preserved;
only the shared readiness config/docs also received the documented UI revision.

### Browser review still required

At 1440×900, 390×844 and 360px widths, verify each main screen and reset modal;
check long unbroken text and all summaries for horizontal overflow. At 200% zoom,
confirm labels/actions stay readable and available. Tab and Shift+Tab through forms,
correction/learning expanders, downloads, hub/privacy links and reset; verify focus
visibility, modal trapping, Escape/dismissal and focus return. Check native checkbox,
radio, disabled button and error computed colours, plus screen-reader announcements.
Record actual screenshots and send them to FN/WP2. No screenshot should be inferred
from the AppTest description artifact.

### Completed checks

- Final full regression run: `.venv/bin/python -m pytest -q` — **1111 passed in 53.66s**.
- Focused UI/error/historical interaction run: **37 passed**; broader readiness/UI
  run before the final added old-instrument regression: **90 passed**. The final full
  suite includes all new tests.
- `git diff --check` and Python compileall passed.
- Seven deterministic screen descriptions captured without exceptions: initial,
  interpretation, interview, optional reflection, summary, initial-answer editing,
  reset confirmation. They contain no live model results.
- Configured text contrast ratios: Azure/white 12.58, Slate/white 4.70,
  Azure/coral 5.18, Azure/Azure50 11.59, danger/white 6.54, warning/white 6.26.
  See ignored .runtime/ui-contrast-review.json. This is not a rendered contrast audit.
- Source PDF and both runtime review artifacts confirmed Git-ignored.
- No browser screenshots, live-model validation, hub deployment or service restart
  performed. Uncommitted work remains uncommitted; no push performed.
