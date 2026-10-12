# IAM-SRA2 interface review — 12 October 2026

## Source and scope

Read all 19 PDF pages and visually inspected rendered examples on every page of
`IAM-CC_UI_guidelines_for_tools-2.pdf`, version 1.0, September 2026, WP2/T2.1.
SHA-256: `c062b1ff1c38a40848cd0a34dc600ca46f121add7d0e876db056083697618cc3`.
Original and a local reference copy remain outside Git/in ignored references/private.

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
| 15 | Charts/maps palette and chart accessibility (conditional) | Default demo has no readiness charts/maps, numbers or progress gauges | Not applicable; no readiness charts/maps |
| 16 | Hub-integration divider | Reviewed; no extra rules inferred | No deployment performed |
| 17 | Choose embedded A or external B with WP2 | Local standalone preview; **Mode B-like**, not a claimed approved integration | WP2 must choose mode. Mode A header/footer suppression, frame-ancestors and HTTPS are hosting work, not changed here |
| 17 | Mode B header 56–64px, logo/hub/tool-page links; title Tool name | IAM-CC; official favicon | 64px wrapping temporary text header, IAM-SRA2 | IAM-CC title; hub-home HTTPS link opens new tab safely | Logo/mark and exact tool-page URL pending. Mobile header may wrap; no guessed tool slug |
| 17 | Mandatory Mode B EU funding footer, partner credit/logo, privacy link | Exact supplied funding wording visible in footer; accessible Privacy and project information expander | EU emblem/lead partner credit/logo and approved public privacy URL **pending**; expander is local disclosure, not a substitute for final policy URL |
| 18 | Screenshots 1440/390, 360 width, 200% zoom, keyboard, contrast and FN handover | Deterministic AppTest screens and regressions; scoped focus CSS and native controls | No browser installed: no actual app screenshots, mobile pixel checks, keyboard/focus/200% zoom audit or WCAG certification claimed |
| 18 | Hub metadata/card image/related guides/Skills Lab/lead partner | See handover decisions below; illustrative medical subtitle retained | No invented lead partner, module, card image or public endpoint |
| 19 | Closing page | Visually inspected | No additional requirements |

Main cleanup retains the current styling and this source checklist. Earlier
change logs and historical interaction notes live in Git history. Live browser
layout, keyboard and accessibility checks remain a host verification task.
