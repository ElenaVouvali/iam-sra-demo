# IAM-CC UI notes: guidelines PDF and live hub

Two sources in one file: the IAM-CC UI guidelines PDF (page by page, with Nick's corrections and the binding IAM-IQ standard), then the live hub.iamcc.eu site, then the open questions from both.

Source: `IAM-CC_UI_guidelines_for_tools.pdf` (19 pages, 16:9 slides)
Version 1.0 · September 2026 · WP2, Task 2.1
Notes taken 2026-10-11. Things marked ⚠️ are my observations (inconsistencies, ambiguities, things to check). They are not in the source.

## Corrections log (from Nick, 2026-10-11): these override the PDF

| # | Correction | Where applied |
|---|---|---|
| C1 | **The Download button has no arrow icon.** Plain text label "Download" only. | p11 (sizes), p13 (list row) |
| C2 | **Chart palette sits between the PDF and Nick's pastel set** (revised 2026-10-11). Final: `#3579B0`, `#EC6A5C`, `#2FA886`, `#DFA23A`, `#9070C6`. This is the OKLab midpoint, nudged so it passes the colour-blind checks. | p15, token sheet |
| C3 | **New status palette** with 100% and 40%-on-white variants: Success `#2B7A5C` / `#AAC7BD`, Warning **`#8F5117`** (the PDF value is kept; Nick's `#CD7C00` was dropped) / `#EBCA99`, Danger `#C22F2F` / `#E7ACAC`. | p7, p14, token sheet |
| C4 | **All sizes in `rem`** (radius, spacing, type, component sizes, borders, shadows…) so the whole UI scales from the root font size. | new "rem spec" section + token sheet |

---

## IAM-IQ internal tool UI standard (Nick, 2026-10-11): binding for the custom IAM-IQ frontend

IAM-IQ replaces the partner frontends (RefMap, ImAFUSA) with its own UI. The UI talks straight to the partner backends, with no iframes and no partner UI code. These sources define that UI, highest priority first:

1. **The playground [iamcc-ui-playground-standalone.html](iamcc-ui-playground-standalone.html), preset "PDF spec + corrections", is the all-inclusive standard.**
   - It covers every token (colours, status, chart series, radii, spacing, type sizes, shadows, focus ring, rem scale) and every component (buttons, forms, cards, tags/chips, alerts, empty states, modals, toasts, charts, maps, catalogue).
   - Use its "Copy CSS" / "Download tokens JSON" output verbatim. Where the live hub `@theme` differs (ink `#12354F`, coral `#F0776B`, 12px cards, `outline-none` …), **the playground wins**.
2. **Page layout comes from the playground as well.**
   - **Mode B tool header:**
     - 3.75rem tall, white, with a hairline Azure 100 bottom border.
     - Left: IAM-CC logo, then a vertical divider, then "IAM-IQ" (card-title size, 600).
     - Right: a "Back to hub" text link with a coral underline.
     - Below a 30rem container width, the divider and the name are hidden.
   - **Tool footer:** Azure 50 background with the EU statement.
   - **Grid:**

     | Container width | Columns | Margin | Gutter |
     |---|---|---|---|
     | ≥ 75rem | 12 | 4rem | 1.5rem |
     | 48rem to < 75rem | 8 | 2.5rem | 1.25rem |
     | < 48rem | 4 | 1.25rem | 1rem |

   - Content works from 360px to 1440px with **no horizontal page scroll**.
3. **The hub pages are the structural templates for the inner tool pages** (structure only; restyle with the playground tokens):
   - **Tool detail page = [`/tools/iam-compass`](https://hub.iamcc.eu/tools/iam-compass)** (see [live hub notes §7](#live-hub-site-notes-hubiamcceu) below).
     - Top: breadcrumb, then the H1 (tool name), a one-sentence lead and audience/domain tags.
     - Below that, a two-column layout: a main column and a **22.5rem (360px) sidebar**, with a 2.5rem gap. On narrow screens the sidebar stacks under the main column.
     - Main column: a 2:1 screenshot, then "What it does" (3 bullets), then "Who it's for" (one sentence).
     - Sidebar card 1, **Access**: a primary "Open tool" pill, and a definition list with lead partner, suite (RefMap / ImAFUSA), status, and data location (`s3://iam-…`).
     - Sidebar card 2, **Related**: related tools.
     - Sidebar card 3, **Learn it**: only if there is material.
   - **Tool working page = [`/tools/iam-compass-demo`](https://hub.iamcc.eu/tools/iam-compass-demo)** (see [live hub notes §8](#live-hub-site-notes-hubiamcceu) below).
     - Top: breadcrumb, then one large card with an Azure 50 header strip (tool icon + tool name).
     - The card body is a stack of sections. Each section has an icon tile, a section heading and body text. The sections, in order:
       1. Definition
       2. Rationale
       3. Methodology
       4. Data sources
       5. How to use (numbered steps)
       6. **Inputs**: the tool's filters and parameters, built from its backend endpoints
       7. **Run**: one primary button
       8. **Results**: result cards; numbers formatted for people, not `toFixed(6)`
       9. **Visualisation**: a map (Leaflet) or chart, full card width
       10. References
     - Sections that a tool has no content for are left out. They are never filled with placeholders.
     - Wide tables scroll inside their own box (`overflow-x:auto`), never the page.

### Rules that answer the current console's problems
- **No text overflow.**
  - Boxes never have a fixed height around text.
  - Flex and grid children get `min-width:0`.
  - Long strings (S3 paths, URLs, schema JSON) use `overflow-wrap:anywhere`.
  - Every page is checked at 360, 768, 1200 and 1440px.
- **No mini screen.**
  - Internal tools are full pages at their own routes (e.g. `/refmap/noise`, `/imafusa/safety`).
  - No `<iframe>` anywhere.
  - "Open tool" navigates in the same tab. Only links that leave IAM-IQ open in a new tab (PDF p17).
- **Back navigation:**
  - The breadcrumb and the browser Back button always work, because every view is a real URL.
  - Filter state lives in the query string, so Back restores it.
  - The header's "Back to hub" goes to hub.iamcc.eu.
  - No partner back buttons.

### Do not copy from the hub demo (breaches listed in [live hub notes §8](#live-hub-site-notes-hubiamcceu))
- No vertical table dividers.
- No `outline-none`: a visible focus ring every time.
- Every input has a label, including table cells (visually hidden if needed).
- Coral is never used as text or for decoration (coral 700 is for coral-coloured text).
- Sentence-case headings.
- Validate on blur.
- Use a real empty state instead of instruction text.

### Still open
- ⚠️ **Page title format:**
  - The PDF says "Tool name | IAM-CC".
  - Proposal for inner pages: "Noise assessment · IAM-IQ | IAM-CC". Confirm.
- ⚠️ **Hub demo label:** the demo page is labelled "IAM-Compass details" but is a noise indicator (IAM-IQ territory). This is still unconfirmed. It doesn't block the template.

---

## Recurring layout (applies to all pages)

- **Header:** IAM-CC logo top-left (full logo with tagline "INNOVATIVE AIR MOBILITY COMPETENCE CENTRE"), with a full-width horizontal rule under it.
- **Footer:** horizontal rule; left: "IAM-CC UI Guidelines for Tool Partners"; right: page number (no number on the cover).
- **Three slide styles:**
  1. **Dark section slides** (pages 1, 4, 10, 16, 19): Dark Azure background, white logo, large oversized logo-mark watermark on the right in a slightly lighter azure, large title in Light Azure / off-white, bold Google Sans. Rules are light/translucent.
  2. **Light Azure slides** (pages 2, 3): Light Azure (#D0D7DB-ish) background, dark logo, white rules; white logo-mark fragment cropped at the bottom-left corner.
  3. **White content slides** (pages 5–9, 11–15, 17, 18): white background, Dark Azure rules. Left column holds the title, an intro paragraph and bold sub-headings with notes. The right ~2/3 holds the examples, tables and swatches. Each block on the right has a small bold label above a Dark Azure rule.

---

## Page 1 — Cover

- Title: **"UI Guidelines for Tool Partners"** (two lines, very large bold, light colour on Dark Azure).
- Subtitle: "Version 1.0 · September 2026 · WP2, Task 2.1".
- White IAM-CC logo top-left.
- EU block at the bottom: EU emblem (circle of stars in an outlined box) + "Funded by the European Union".
- Disclaimer text next to it: "Funded by the European Union under Grant Agreement No **101271620**. Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them."
- Footer: "IAM-CC UI Guidelines for Tool Partners" (no page number).
- Background: oversized logo-mark watermark on the right half.

## Page 2 — Introduction

- Label (left): **Introduction**
- Text: "This guide helps partners design their IAM-CC tools so they look and work as one product, whether **embedded in the hub** or **opened as an external link**."
- Introduces the two integration modes (detailed on p17).
- Light Azure background; a white logo-mark fragment at the bottom-left.

## Page 3 — Table of Contents

| # | Section | Covers |
|---|---|---|
| 01 | Foundations | Principles, logo, colour, typography, layout |
| 02 | Components | Buttons, forms, content, feedback, charts |
| 03 | Hub integration | Embedded and external tools, handover checklist |

- Mapping to pages: Foundations p4–9, Components p10–15, Hub integration p16–18, closing p19.

## Page 4 — Section divider: "Foundations"

- Dark slide, title only.

## Page 5 — Core principles

Intro: "Five rules that keep **nine tools**, built by different partners, feeling like one product. If you only read one page, read this one."

| Rule | Detail |
|---|---|
| **Coral is the dot** | Use Pastel Coral for **one key action per screen**. Never for text, alerts or decoration. |
| **Azure carries the interface** | Dark Azure for headings, body text, primary buttons and icons. Blue Slate for secondary text. |
| **One typeface** | Google Sans everywhere. Load it inside your tool; fonts do not pass into an embedded frame. |
| **Pills and rounded cards** | Buttons and chips are fully rounded. Cards and panels use **20px** corners. |
| **Accessible by default** | WCAG 2.1 AA contrast, visible focus states, and everything reachable by keyboard. |

- Key fact: there are **9 tools** in the ecosystem, built by different partners.
- "Coral is the dot" refers to the coral dot at the centre of the logo mark.
- Shown as a table with light row dividers: bold rule name on the left, description on the right.

## Page 6 — Logo

Intro: "IAM-CC leads in your tool's header. The tool name sits after a divider. Partner logos go in the footer as a credit, never in the header."

**Do not:**
- Stretch, rotate, outline or add effects.
- Recolour. Use the supplied dark or white files.
- Place it on photos or busy maps without a solid panel.
- Place it on a coral background inside a tool.
- Crowd it: keep clear space of at least the height of the coral dot.

**Logo versions (3 tiles):**
1. **Full logo** (mark with coral dot + "IAM·CC" wordmark + tagline "INNOVATIVE AIR MOBILITY COMPETENCE CENTRE"), dark version: on white or Azure 50. **Min width 140px.**
2. **White wordmark**: on Dark Azure only. ⚠️ The tile shows the wordmark + tagline only, with no mark. The section slides use a white version that does include the mark.
3. **Mark alone** (four-lobed / propeller-like mark with coral centre dot): for favicon and app icon. **Min 24px.**

**Co-branding in your tool (mockup):**
- Header: IAM-CC full logo | vertical divider | tool name ("IAM-Compass", Dark Azure, medium/semibold) … right-aligned **"Back to hub"** link (Dark Azure text with a **coral underline**).
- Body: "TOOL AREA" placeholder.
- Footer (Azure 50 strip): EU emblem + "Funded by the European Union" on the left; "Developed by" + partner logo placeholder (grey box) on the right.
- Example tool name: **IAM-Compass**.

⚠️ The coral underline on "Back to hub" sits uneasily with "coral never for decoration" (p5). It may be an intentional exception for the link affordance.

## Page 7 — Colour palette

Intro: "The brand palette, extended with a few steps for interface states. Dark Azure does the work; Pastel Coral is rare and deliberate."

**Primary and secondary colours (big swatches):**

| Name | Hex | Role |
|---|---|---|
| Dark Azure | `#16364D` | Text, primary UI |
| Blue Slate | `#55788E` | Secondary text |
| Light Azure | `#D0D7DB` | Borders |
| Charcoal | `#0A1217` | Deep surfaces |
| Pastel Coral | `#FF8174` | One key action |
| Pastel Orange | `#FFAA74` | Illustration |

**Extended UI steps (small swatches):**

| Name | Hex | Role |
|---|---|---|
| Azure 900 | `#0F2438` | Hover |
| Azure 300 | `#A9BAC6` | Placeholder |
| Azure 100 | `#E7ECEF` | Dividers |
| Azure 50 | `#F3F6F8` | Surfaces |
| Coral 700 | `#B23F33` | Coral text |
| Coral 100 | `#FFE5E1` | Coral tint |

**Contrast (WCAG AA) table, as stated in the deck:**

| Pair | Ratio | Use |
|---|---|---|
| Dark Azure on white | 12.6:1 | All text |
| Blue Slate on white | 4.7:1 | Secondary text |
| Dark Azure on Pastel Coral | 5.2:1 | Accent button |
| Pastel Coral on white | 2.6:1 (in red) | **Never for text** |

**Status colours** (side note): "Success, warning and danger are for UI states only. Always pair them with an icon and a text label, and never use them as chart series."

| Status | Hex (PDF, superseded) |
|---|---|
| Success | ~~`#2E7D5B`~~ |
| Warning | ~~`#8F5117`~~ |
| Danger | ~~`#B3261E`~~ |

**✅ Correction C3: status palette replaced** ("Balanced Pastel Semantic Palette", shown as 100% and 40%-opacity-on-white variants):

| Status | 100% | 40% on white | Intended use (from the image) |
|---|---|---|---|
| Success | `#2B7A5C` | `#AAC7BD` | Contrast-ready semantic success / Soft, visible backdrop |
| Warning | **`#8F5117`** (kept from the PDF; `#CD7C00` from the image dropped) | `#EBCA99` | Legible warning accent / Warm background fill |
| Danger | `#C22F2F` | `#E7ACAC` | High-contrast critical indication / Muted coral highlight |

Contrast check of the new values (my calculations):
- On white: Success 5.20 ✓, Warning `#8F5117` 6.26 ✓, Danger 5.61 ✓. (The dropped `#CD7C00` was only 3.24.)
- **Status colour on its own 40% tint:** Success 2.87, Warning `#8F5117` on `#EBCA99` 4.00, Danger 2.91, all below 4.5:1. So **alert text on the tints should be Dark Azure** (6.5–8.0:1 on the tints ✓). Use the status colour only for the icon/border and pair it with an icon + label, per the p7 rule.
- The 40% values check out as a 40% blend over white of the image's colours: Warning `#EBCB99` ≈ `#EBCA99` (blended from `#CD7C00`, kept as is) and Danger `#E7ACAC` are exact. Success comes out as `#AACABE` vs the stated `#AAC7BD` (small difference; use the stated value).

⚠️ **I recomputed the contrast ratios (WCAG formula):**
- Dark Azure / white 12.58 ✓ · Blue Slate / white 4.70 ✓ · Dark Azure / Pastel Coral 5.18 ✓
- **Pastel Coral / white is 2.43:1, not 2.6:1.** The conclusion ("never for text") still holds.
- Coral 700 / white 5.75 ✓ · Coral 700 / Coral 100 4.81 ✓ (so "Coral text" on the coral tint passes AA)
- Success / white 5.00 ✓ · Warning 6.26 ✓ · Danger 6.54 ✓
- **Blue Slate on Azure 50 is 4.33:1, which fails AA for normal text.** Blue Slate on the hub background `#F8FAFC` is exactly 4.50 (borderline pass). This matters because secondary text often sits on Azure 50 surfaces (e.g. the footer, the typography panel).
- Azure 300 placeholder / white is 2.00:1. Placeholder text is low contrast. WCAG doesn't strictly require placeholders to pass, but this is worth knowing.
- ⚠️ The Pastel Orange role ("Illustration") isn't explained anywhere else in the deck.
- ⚠️ Coral 700 is labelled "Coral text", but p5 says coral is never for text. Presumably Coral 700 is the allowed dark coral for text where needed (it is not Pastel Coral). Clarify where it's allowed.

## Page 8 — Typography

- **Google Sans**, SIL Open Font License. Weights **400, 500, 600 and 700** are in the partner kit.
- **Fallback stack:** `system-ui, -apple-system, Segoe UI, sans-serif`.

**Rules:**
- Minimum text size **12px**.
- **Sentence case** for headings, buttons and labels.
- Left align. **Tabular figures, right aligned, in tables.**

**Icons:**
- Outline icons, **2px stroke, round caps, 24px grid** (**Tabler Icons** or **Lucide**).
- **16px inline, 20px in buttons.**
- Colour: Dark Azure or Blue Slate.

**Type scale** (shown on an Azure 50 panel; sample text "Plan air mobility with your city"):

| Style | Weight | Size / line-height |
|---|---|---|
| Page title | Bold (700) | 32 / 1.15 |
| Section heading | SemiBold (600) | 24 / 1.25 |
| Card title | SemiBold (600) | 18 / 1.3 |
| Body | Regular (400) | 15 / 1.6 |
| UI label | Medium (500) | 14 / 1.4 |
| Small, meta | Regular (400) | 13 / 1.5 |
| Caption, axis | Regular (400) | 12 / 1.4 |

- Specimen labels are in Blue Slate, small. Samples are in Dark Azure.
- ⚠️ Licence check: historically "Google Sans" was not openly licensed. The OFL-licensed releases are "Google Sans Flex" / "Google Sans Code". Confirm which family the partner kit actually ships.
- ⚠️ Body is 15px, an unusual choice versus the common 16px. Worth noting for implementers.

## Page 9 — Layout

Intro: "A **4px spacing base**, generous rounding that echoes the logotype, and soft azure-tinted shadows."

**Designing for the hub:**
- Design at **1440 desktop** and **390 mobile**.
- Hub content area is **1312px** wide, so embedded tools must work from **360 to 1312px with no horizontal scroll**.

**Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64. (Shown as coral-tint bars with coral outlines.)

**Corner radius:**

| Radius | Use |
|---|---|
| 8px | Small tags, tooltips |
| 12px | Inputs, alerts, thumbnails |
| 20px | Cards, panels, modals |
| Pill | Buttons, chips, pagination |

(Shown as 4 outlined example shapes, increasing radius, with a Blue Slate outline.)

**Elevation** (shadows are tinted Dark Azure, rgb 22,54,77):

| Token | Use | CSS |
|---|---|---|
| sm | Cards at rest | `0 1px 2px rgba(22,54,77,.06)` |
| md | Hover, menus | `0 4px 14px rgba(22,54,77,.08)` |
| lg | Modals | `0 14px 36px rgba(22,54,77,.14)` |

**Grid and breakpoints:**

| Width | Columns | Margin / gutter |
|---|---|---|
| 1312px max | 12 | 64 / 24 |
| 768 to 1199px | 8 | 40 / 20 |
| 360 to 767px | 4 | 20 / 16 |

- ⚠️ The top row is labelled "1312px max" rather than "1200px+". It is implied to cover ≥1200px.
- ⚠️ A 64px margin inside a 1312px content area conflicts with Mode A's "outer margins 24px max" (p17). The grid margins presumably apply to standalone (Mode B) pages only. Clarify.
- ⚠️ Badges/tags: p9 says small tags use 8px radius, but the badges on p13 look pill-shaped. Clarify whether badges are "tags" (8px) or "chips" (pill).

## Page 10 — Section divider: "Components"

- Dark slide, title only.

## Page 11 — Buttons

**Variants:**
- **Accent (coral):** the single most important action on a screen, e.g. "Run assessment". **One per view at most.**
- **Primary:** standard confirming actions.
- **Secondary:** alternatives, and repeated row actions like Download.
- **Ghost:** low-emphasis toolbar actions.
- **Destructive:** delete or reset, with confirmation.

**Labels:** verb first, **1 to 3 words**, sentence case: "Open tool", "Export results". Avoid "OK", "Submit", "Click here".

**Variants × states matrix** (Default / Hover / Focus / Disabled). My visual reading of the swatches:

| Variant | Default | Hover | Focus | Disabled |
|---|---|---|---|---|
| Primary | Dark Azure fill | darker (Azure 900) | Dark Azure + **coral ring** | Azure 100-ish fill, Azure 300 text |
| Accent | Pastel Coral fill | deeper coral (≈ series-2 red-coral) | coral + **slate ring** | same disabled style |
| Secondary | white, Dark Azure 1.5px outline | Azure 50 fill | outline + **coral ring** | same disabled style |
| Ghost | text only | Azure 50 fill | **coral ring** | same disabled style |
| Destructive | Danger red fill | darker red | red + **slate ring** | same disabled style |

- All disabled states look identical: a light grey-azure pill with pale text.
- ⚠️ In the matrix, the "Label" text on filled buttons renders grey/low-contrast in the PDF. This is probably a rendering artifact, as real buttons should have white text on Dark Azure / Danger and Dark Azure text on coral (per the p7 5.2:1 pair).
- ⚠️ Hover colour for the accent and destructive variants is not given as a token.

**Sizes:** Large **48**, Medium **40**, Small **34** (heights in px; rem values in the rem spec section). The PDF's size example shows "Download ↓", a secondary/outline button with a trailing arrow.

**✅ Correction C1:** the Download button has **no arrow icon**. Label "Download" only, secondary style. (The p13 list-row example already shows it without an icon.)

**Spec line:** Medium weight, pill radius, **1.5px border on secondary**. Icons **16 to 20px** with a **6 to 8px gap**. **Focus ring 3px: coral on azure buttons, slate on coral buttons.**

- ⚠️ The focus ring colour for destructive (red) buttons isn't stated in the text. Visually it's slate.

## Page 12 — Forms

- Every field has a **visible label above it**. Placeholders show an example, **never the label**.
- Input height **40px**, **46px on public, form-heavy pages**. Radius **12px**.
- Errors: **red border plus a message saying what to fix. Validate on blur.**
- Mark optional fields with **"(optional)"**.
- Selected and checked states use **Dark Azure, never coral**.

**Text input states (examples):**
- **Default:** label "City", placeholder "Porto" (Azure 300), Light Azure border.
- **Focus:** "City" = "Porto" (typed, Dark Azure), **Dark Azure border + soft coral outer ring/halo**.
- **Error:** label "Work email", value "name@city", red border, message below in red: "Enter a valid email address."
- **Disabled:** label "Country", value "Portugal" (pale text), Azure 50 fill.
- Captions under each: Default / Focus / Disabled (small, Blue Slate). The error example has the message instead.

**Selection controls:** Checkbox (empty, rounded square), **Checked** (Dark Azure fill, white ✓), **Radio** (Dark Azure ring with dot), **Toggle** (Dark Azure track, white knob, on).

**Search and select:** search field with a ⌕ icon and placeholder "Search the library" (wide); dropdown "All types ▾" (narrow). Both 12px radius.

- ⚠️ The focus ring on inputs is coral, consistent with the "coral ring on azure" rule for buttons. Coral therefore does appear as a focus indicator (not only on the one key action), so the focus ring is an implicit exception to "Coral is the dot".

## Page 13 — Content components

Intro: "Audience badges share one neutral style. Colour is reserved for status: **New in coral**, **Most downloaded in Dark Azure**."

**Badges (examples):**
- Audience (neutral, Azure 100 fill, Dark Azure text): **Cities**, **Regulators**, **Citizens**.
- Status: **New** (Pastel Coral fill, dark text), **Most downloaded** (Dark Azure fill, white text).
- **Guide** (content type): an even lighter neutral (Azure 50 fill, Blue Slate text), visually distinct from the audience badges.

**Filter chips:** **All** (selected: Dark Azure fill, white text), **For cities**, **For regulators** (unselected: white with Light Azure outline, Blue Slate/Dark Azure text). Pill shape.

**Cards and lists:**
- Cards: **20px radius, 1px Azure 100 border, 16 to 24px padding**.
- A featured item gets a **2px coral border, never a coral fill**.
- Use **list rows, not cards**, for long sets of records.

**Card example:** image placeholder ("IMAGE", Azure 50 block, rounded), title "IAM-Compass", description "Track policy progress." (Blue Slate), secondary button "Open tool".
**Featured card example:** 2px coral border, "New" badge, title "Featured", caption "2px coral border."

**Tables:** no vertical lines, 1px row dividers, numbers right aligned.

Data table example:

| Scenario | Flights / day | Noise Lden (dB) |
|---|---|---|
| Baseline 2026 | 120 | 42.1 |
| Medical logistics | 340 | 47.8 |
| Full deployment | 1,150 | 53.4 |

- Header row is bold with a darker (Dark Azure) bottom rule; body rows have light dividers.
- ⚠️ In the example, the "Flights / day" column is **left-aligned** while "Noise Lden (dB)" is right-aligned. This contradicts the "numbers right aligned" rule on the same page.

**List row example:** thumbnail (Azure 50 square), title "Micro-vertiport roadmap", meta "Guide · PDF · For cities" (Blue Slate), secondary button "Download" on the right (no icon, per C1).

- ⚠️ The "New" badge is coral, so coral is used for a status/badge. This conflicts with p5 "Coral is the dot … never for … decoration" and with p14 "coral means action, not status". It's an explicit exception, but contradictory wording. Also, a featured card plus an accent button would put two coral elements on one screen.

## Page 14 — Feedback and states

Intro: "Say **what happened**, then **what to do**. Alerts **never use coral**: coral means action, not status."

**Empty states:** "An invitation to act, with one clear button. Not an apology."
**Loading:** "Skeleton blocks in **Azure 100 and 50** for content. For long computations, show **progress and an estimated time**."

**Alert examples** (12px-radius boxes, tinted background, thin tinted border, icon + bold title + body):

| Type | Icon | Title | Body | Look |
|---|---|---|---|---|
| Info | ⓘ | Heads up | Results use the 2025 city dataset. | Azure 50 bg, Light Azure border, Dark Azure text |
| Success | ✓ | Scenario saved | Compare it with others from the results page. | green tint bg, green text |
| Warning | ! | Partial data | 3 districts have no noise measurements yet. | orange/peach tint bg, warning-brown text |
| Error | ✕ | Upload failed | The file is over 20 MB. Compress it and try again. | red/pink tint bg, danger-red text |

**Empty state example:** dashed Light Azure border panel; faded IAM-CC mark (grey with a pale coral dot); title "No scenarios yet"; text "Create one to see its impact on your city."; **primary (Dark Azure) button** "Create scenario".

**Loading example:** a card with 3 skeleton bars (a shorter top bar, two longer bars) in Azure 100/50.

- ~~⚠️ The tint background hexes for alerts are not specified.~~ **Resolved by C3:** use the 40% variants (`#AAC7BD` / `#EBCA99` / `#E7ACAC`) as alert backgrounds, with Dark Azure text (see the p7 contrast note). The info alert stays Azure 50.
- ⚠️ Alert text is in status colours, but the p18 brand check says "All text in Dark Azure or Blue Slate". These contradict each other.
- ⚠️ The warning tint looks peach/orange, close to Pastel Orange / Coral 100. It's easy to confuse with coral.

## Page 15 — Charts and maps

Intro: "For tools with charts, maps and simulations. The categorical palette is checked for colour-blind readers."

**Rules:**
- Use series colours **in order**. Never cycle or invent new ones.
- **One y-axis per chart.** Two measures means two charts.
- **2px lines**, thin bars with **2px gaps**, **Azure 100 gridlines**, **12px Blue Slate axis text**.
- **Legend for 2+ series**, **direct labels on up to 4**. Label text stays azure.
- **Series 4 is low contrast on white: always label it.**
- No 3D, no rainbow ramps. **Offer a table view.**

**Categorical palette (in this order), PDF values, superseded:** ~~`#2B6CA3`, `#E8604F`, `#16A085`, `#D4901A`, `#8A62C2`~~

**✅ Correction C2 (revised): use colours *between* the PDF set and Nick's pastel set.** Final values, still used in this order:

| Series | PDF | Nick | **Final (in-between)** | Final on white |
|---|---|---|---|---|
| 1 | `#2B6CA3` | `#4E89AE` | **`#3579B0`** | 4.65 |
| 2 | `#E8604F` | `#F27D72` | **`#EC6A5C`** | 3.10 |
| 3 | `#16A085` | `#52B788` | **`#2FA886`** | 2.97 |
| 4 | `#D4901A` | `#F4C15D` | **`#DFA23A`** | 2.24 |
| 5 | `#8A62C2` | `#9D85C5` | **`#9070C6`** | 3.95 |

How I got there: I took the perceptual (OKLab) midpoint of each pair, then nudged it slightly. The plain midpoint failed two checks: series 1 read as greyish, and series 3 and series 2 were too close for red-green colour-blind readers. The final set passes the colour-blind separation checks. Series 3 and 4 are still a bit light against white, so the "always label" rule stays. The playground's chart blend slider lets you move anywhere between the two sets.

Nick's original pastel set, for reference ("5-Color Accessible Pastel Categorical Palette"):

| Series | Name | Hex | Note (from the image) | On white | Dark Azure on it |
|---|---|---|---|---|---|
| 1 | Slate Blue | `#4E89AE` | Deep value | 3.81 | 3.30 |
| 2 | Pastel Coral | `#F27D72` | High contrast / High luminance | 2.64 | 4.76 |
| 3 | Sage Green | `#52B788` | High contrast / High value | 2.47 | 5.09 |
| 4 | Honey Gold | `#F4C15D` | Cool-toned / Mid value | **1.66** | 7.57 |
| 5 | Lavender | `#9D85C5` | Cool-toned / Mid value | 3.18 | 3.95 |

(The image uses white labels on series 1, 2, 3 and 5 and dark text on series 4.)

⚠️ Notes on the new palette:
- **Series 2, 3 and 4 are below 3:1 against white** (the WCAG non-text threshold for lines/bars). Series 4 is very low at 1.66. The existing rules matter even more now: "always label" (not just series 4), direct labels, a table view, and never relying on colour alone. Thicker lines or point markers would help.
- **Series 2 "Pastel Coral" `#F27D72` is nearly identical to the brand Pastel Coral `#FF8174`** (1.09:1 between them, visually the same). A chart can therefore put "coral" on screen next to the one accent button, which clashes with "Coral is the dot". Worth confirming this is intentional.
- The image's labels "cool-toned" for Honey Gold and Lavender read oddly (gold is warm). That's cosmetic, not a spec issue.
- The sequential/intensity/diverging ramps were not corrected, so they still have no hex values (open question 4).

**Ramps** (shown as swatch strips, **no hex values given**):
- **Sequential · magnitude:** 6 steps, light → dark azure. Visually: Azure 50 → Light Azure → Azure 300 → Blue Slate → a mid-dark azure (~#3A5068?) → Dark Azure.
- **Intensity · noise, risk, nuisance:** 6 steps, very pale coral → Coral 100 → Pastel Coral → red-coral (~series 2) → Coral 700 → deep red-brown (~#6E1F1A?).
- **Diverging · change vs baseline:** 5 steps, Dark Azure → Blue Slate → Light Azure (neutral midpoint) → Pastel Coral → Coral 700.

**Example chart:** "Daily drone flights per 10 km²". A line chart from 2026 to 2030 with y-ticks 0 / 40 / 80 and light gridlines. Three series with end-point dots and direct labels: **Porto** (series 1 blue, highest, ~60 → ~95), **Madrid** (series 2, ~40 → ~80), **Athens** (series 3, ~30 → ~50). There is no separate legend because the lines are directly labelled.

- (Contrast for the corrected series is in the C2 table above.)
- ⚠️ "Legend for 2+ series, direct labels on up to 4" is ambiguous. It could mean both a legend and direct labels, or direct labels replacing the legend when ≤4 series. The example uses direct labels only.
- ⚠️ Request hex values for the three ramps.

## Page 16 — Section divider: "Hub Integration"

- Dark slide, title only. (Title case "Hub Integration" here vs. "Hub integration" in the TOC. ⚠️ This is minor, but the deck's own sentence-case rule is inconsistently applied: e.g. "Colour Palette" on p7 and "Table of Contents" on p3 are title case.)

## Page 17 — Connecting to the hub

Intro: every tool connects to the hub in one of two ways:
- **Mode A, embedded:** your tool loads inside a page on **hub.iamcc.eu**.
- **Mode B, external link:** users open your tool on your own domain, from its page on the hub.

"**Agree the mode with the WP2 team before you start building.**"

**EU funding statement** (full text, to be used verbatim):
> Funded by the European Union under Grant Agreement No 101271620. Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them.

### Mode A · Embedded on hub.iamcc.eu

Mockup: hub header (IAM-CC logo + nav "Home · Tools · Skills Lab · Resources") → "Your tool · 360 to 1312px" (dashed coral-tint area) → "Hub footer and EU notice" strip.

Requirements:
- **No own site header, navigation, footer or EU notice.** (The hub provides them.)
- Background **`#F8FAFC`** (the hub page colour) or **transparent**; **outer margins 24px max**.
- **Fluid width, no horizontal scroll.** **Tell us your minimum height.**
- **Load Google Sans inside the tool.**
- **Allow framing:** `frame-ancestors https://hub.iamcc.eu`, **no `X-Frame-Options: DENY`**.
- **HTTPS only.** Outbound links open in a **new tab**.
- **If login relies on third-party cookies, use Mode B.**

### Mode B · External link on your domain

Mockup: header (IAM-CC logo | divider | "Tool name" … "Back to hub" with a coral underline) → "Your tool" (dashed) → footer (EU emblem "Funded by the European Union" … "Developed by [Partner]").

Requirements:
- Users reach your tool from its page on the hub, through the **"Open tool"** button.
- **Tool header, 56 to 64px tall:** IAM-CC logo **linking to hub.iamcc.eu**, divider, tool name, **"Back to hub" link to your tool page**, e.g. `hub.iamcc.eu/tools/iam-compass`.
- **Footer, mandatory:** EU emblem with the funding statement, a **"Developed by" credit with your logo**, and a **privacy link**.
- **Page title:** `Tool name | IAM-CC`. **Favicon:** the IAM-CC mark.
- Everything else in this guide applies in full.

Notes:
- ⚠️ **`#F8FAFC` is not in the p7 palette.** Azure 50 is `#F3F6F8`. So the hub page colour is an undocumented extra token (it happens to be Tailwind's slate-50).
- ⚠️ The URL example: the PDF text layer reads "iamcompass" (because of the line-break hyphen); the rendered slide shows `hub.iamcc.eu/tools/iam-compass`. Confirm the actual slug format.
- ⚠️ The Mode A height handling is unspecified. "Tell us your minimum height" implies a fixed-height iframe. There's no mention of postMessage auto-resize.
- ⚠️ The Mode B footer mockup doesn't show the privacy link, even though it's listed as mandatory.
- ⚠️ The Mode B header mockup shows no favicon/tab info. Mode A doesn't say whether the tool needs a `<title>`.
- Contacts named: **WP2 team** (p17), "WP2 team (Future Needs)" (p18).

## Page 18 — Handover

Intro: "Before launch, send **screenshots of your main screens at 1440px and 390px** to the **WP2 team (Future Needs)** for a design check."

### Checklist 1 — Send us for your hub page
- [ ] Tool name, and former name if any
- [ ] One-line description, **up to 90 characters**, **starting with a verb**
- [ ] Audience tags: **Cities, Regulators, Researchers, Citizens, Operators, Policy makers, Planners, Vertiport developers** (8 tags)
- [ ] **Three bullets** for *What it does*, **one sentence** for *Who it's for*
- [ ] Related guides, and a Skills Lab module if there is one
- [ ] Card image **1200 × 480 px** and screenshot **1600 × 800 px (2:1)**, **UI only**
- [ ] Mode A or B, tool URL, lead partner, current version

### Checklist 2 — Brand check
- [ ] At most one coral button per screen
- [ ] No coral text, alerts or backgrounds
- [ ] All text in Dark Azure or Blue Slate
- [ ] Google Sans loaded, 12px minimum
- [ ] Pill buttons and chips, 20px card corners
- [ ] Logo from the kit, right version for the background
- [ ] Mode B: tool header and EU footer present

### Checklist 3 — Accessibility check (WCAG 2.1 AA)
- [ ] Text contrast **4.5:1**, large text and UI **3:1**
- [ ] Visible focus on every interactive element
- [ ] Everything works with a keyboard
- [ ] Labelled fields; errors described in text
- [ ] Colour is never the only signal
- [ ] Text alternatives for images and charts
- [ ] Works at **200% zoom** and at **360px wide**

Notes:
- ⚠️ The card image ratio is 1200 × 480 = **2.5:1** (not 2:1). Only the screenshot is 2:1.
- ⚠️ "All text in Dark Azure or Blue Slate" conflicts with: white text on primary/destructive buttons, Coral 700 "coral text" (p7), coloured alert text (p14), and red error messages (p12). These probably mean "body/UI text", but it should be worded that way.
- ⚠️ The audience tag list (8) is longer than the badges shown on p13 (3). The p13 filter chips use "For cities" phrasing vs the tag "Cities".
- ⚠️ "Researchers" appears as a tag here but nowhere else.

## Page 19 — Closing: "Thank you!"

- Dark slide, title only, page number 19.

---

## rem spec (Correction C4)

**Rule:** every UI dimension is written in `rem`, so the whole interface scales from one value: the root font size. Base: **1rem = 16px** (browser default).
- **Do not** set `html { font-size: 62.5% }` or any px value on `html`. Leave it at `100%` so user browser settings are respected. To scale the page, change `html { font-size }` as a percentage (e.g. `112.5%` → 1rem = 18px).
- Conversion: **rem = px ÷ 16**.
- Media queries: write breakpoints in `em`. In media queries both rem and em resolve against the *initial* font size, so `em` is the convention that behaves the same in all browsers. The numbers are identical (px ÷ 16).
- **Exceptions, kept in px:** raster asset dimensions (card image 1200 × 480, screenshot 1600 × 800, screenshots at 1440/390). These are file sizes, not CSS. Everything else is rem.
- ⚠️ Hairlines in rem (`0.0625rem` = 1px) can render as fractional pixels at non-integer scales. That's acceptable and is the trade-off of "everything in rem".

| Group | Item | px (PDF) | rem |
|---|---|---|---|
| **Radius** | small tags, tooltips | 8 | `0.5rem` |
| | inputs, alerts, thumbnails | 12 | `0.75rem` |
| | cards, panels, modals | 20 | `1.25rem` |
| | **pill: buttons, chips, pagination** | full | `999rem` (any value ≥ half the height; stays a pill at every scale) |
| **Spacing** | scale | 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 | `0.25` · `0.5` · `0.75` · `1` · `1.5` · `2` · `3` · `4rem` |
| **Type** | page title (Bold, lh 1.15) | 32 | `2rem` |
| | section heading (SemiBold, lh 1.25) | 24 | `1.5rem` |
| | card title (SemiBold, lh 1.3) | 18 | `1.125rem` |
| | body (Regular, lh 1.6) | 15 | `0.9375rem` |
| | UI label (Medium, lh 1.4) | 14 | `0.875rem` |
| | small, meta (Regular, lh 1.5) | 13 | `0.8125rem` |
| | caption, axis (Regular, lh 1.4) | 12 | `0.75rem` |
| | minimum text size | 12 | `0.75rem` |
| | line-heights | — | unitless (as given), so they scale automatically |
| **Buttons** | large / medium / small height | 48 / 40 / 34 | `3` / `2.5` / `2.125rem` |
| | secondary border | 1.5 | `0.09375rem` |
| | focus ring | 3 | `0.1875rem` |
| | icon size | 16–20 | `1`–`1.25rem` |
| | icon–label gap | 6–8 | `0.375`–`0.5rem` |
| **Forms** | input height | 40 (46 public) | `2.5rem` (`2.875rem`) |
| | input radius | 12 | `0.75rem` |
| **Cards** | border (Azure 100) | 1 | `0.0625rem` |
| | featured border (coral) | 2 | `0.125rem` |
| | padding | 16–24 | `1`–`1.5rem` |
| **Icons** | inline / in buttons / grid | 16 / 20 / 24 | `1` / `1.25` / `1.5rem` |
| | stroke | 2 (on 24 grid) | keep SVG `stroke-width="2"` in viewBox units: it scales with the icon |
| **Charts** | line width | 2 | `0.125rem` |
| | bar gap | 2 | `0.125rem` |
| | axis text | 12 | `0.75rem` |
| **Logo** | full logo min width | 140 | `8.75rem` |
| | mark min size | 24 | `1.5rem` |
| **Hub** | Mode B tool header height | 56–64 | `3.5`–`4rem` |
| | Mode A max outer margin | 24 | `1.5rem` |
| | hub content max width | 1312 | `82rem` |
| **Grid** | ≥1200: 12 col, margin / gutter | 64 / 24 | `4` / `1.5rem` |
| | 768–1199: 8 col | 40 / 20 | `2.5` / `1.25rem` |
| | 360–767: 4 col | 20 / 16 | `1.25` / `1rem` |
| **Breakpoints** | 360 · 768 · 1200 · 1312 | px | `22.5em` · `48em` · `75em` · `82em` |
| **Elevation** | sm | `0 1px 2px` | `0 0.0625rem 0.125rem` |
| | md | `0 4px 14px` | `0 0.25rem 0.875rem` |
| | lg | `0 14px 36px` | `0 0.875rem 2.25rem` |

## Quick-reference token sheet (consolidated, corrections C2–C4 applied)

```css
:root {
  /* brand */
  --dark-azure:   #16364D; /* text, primary UI */
  --blue-slate:   #55788E; /* secondary text */
  --light-azure:  #D0D7DB; /* borders */
  --charcoal:     #0A1217; /* deep surfaces */
  --pastel-coral: #FF8174; /* ONE key action */
  --pastel-orange:#FFAA74; /* illustration */
  /* extended */
  --azure-900: #0F2438; /* hover */
  --azure-300: #A9BAC6; /* placeholder */
  --azure-100: #E7ECEF; /* dividers */
  --azure-50:  #F3F6F8; /* surfaces */
  --coral-700: #B23F33; /* coral text */
  --coral-100: #FFE5E1; /* coral tint */
  --hub-bg:    #F8FAFC; /* Mode A background (p17, not in palette) */

  /* status (C3): 100% and 40%-on-white */
  --success: #2B7A5C; --success-tint: #AAC7BD;
  --warning: #8F5117; --warning-tint: #EBCA99;
  --danger:  #C22F2F; --danger-tint:  #E7ACAC;

  /* charts (C2, in-between PDF and Nick), use in order */
  --series-1: #3579B0;
  --series-2: #EC6A5C;
  --series-3: #2FA886;
  --series-4: #DFA23A;
  --series-5: #9070C6;

  /* radius (C4) */
  --radius-sm:   0.5rem;   /* 8px  tags, tooltips */
  --radius-md:   0.75rem;  /* 12px inputs, alerts, thumbnails */
  --radius-lg:   1.25rem;  /* 20px cards, panels, modals */
  --radius-pill: 999rem;   /* buttons, chips, pagination */

  /* spacing (C4) */
  --space-1: 0.25rem;  --space-2: 0.5rem;  --space-3: 0.75rem; --space-4: 1rem;
  --space-6: 1.5rem;   --space-8: 2rem;    --space-12: 3rem;   --space-16: 4rem;

  /* type (C4) */
  --font: "Google Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --text-page-title: 2rem;      /* 700, lh 1.15 */
  --text-section:    1.5rem;    /* 600, lh 1.25 */
  --text-card-title: 1.125rem;  /* 600, lh 1.3  */
  --text-body:       0.9375rem; /* 400, lh 1.6  */
  --text-label:      0.875rem;  /* 500, lh 1.4  */
  --text-small:      0.8125rem; /* 400, lh 1.5  */
  --text-caption:    0.75rem;   /* 400, lh 1.4  (also the minimum) */

  /* components (C4) */
  --btn-h-lg: 3rem; --btn-h-md: 2.5rem; --btn-h-sm: 2.125rem;
  --btn-border: 0.09375rem;   /* secondary */
  --focus-ring: 0.1875rem;    /* coral on azure buttons, slate on coral buttons */
  --input-h: 2.5rem; --input-h-public: 2.875rem;
  --border: 0.0625rem; --border-featured: 0.125rem;
  --icon-inline: 1rem; --icon-button: 1.25rem; --icon-grid: 1.5rem;

  /* elevation (C4) */
  --shadow-sm: 0 0.0625rem 0.125rem rgba(22,54,77,.06);
  --shadow-md: 0 0.25rem 0.875rem  rgba(22,54,77,.08);
  --shadow-lg: 0 0.875rem 2.25rem  rgba(22,54,77,.14);

  /* layout (C4) */
  --content-max: 82rem; /* 1312px */
}
/* breakpoints (em, see rem spec): 22.5em · 48em · 75em · 82em */
/* Download button: secondary, label only, no icon (C1) */
```

---

## Live hub site notes (hub.iamcc.eu)

Captured 2026-10-11 from the live site (raw HTML via curl, not screenshots).

⚠️ = my observation: a mismatch with the PDF guidelines, or something to confirm.

---

### 1. Site map

| Path | Status | What it is |
|---|---|---|
| `/` | 200 | Homepage |
| `/tools` | 200 | Tools catalogue (9 tool cards, filters, search) |
| `/tools/iam-compass` | 200 | Tool detail page (the only one that exists) |
| `/tools/iam-compass-demo` | 200 | A working tool page inside the hub: the **noise indicator calculator** |
| `/tools/iam-iq`, `/tools/iamiq` | **404** | No IAM-IQ detail page yet |
| `/future-skills-lab`, `/resources`, `/virtual-think-tank`, `/about`, `/for-cities` | linked from nav | not inspected |
| `/sitemap.xml` | 404 | — |
| `/robots.txt` | 200 | `User-agent: * / Disallow:` (everything allowed) |

- This settles open question 12 from the PDF notes: the slug format is **hyphenated** (`/tools/iam-compass`).
- Most buttons and footer links are still `href="#"` placeholders. The site is a prototype.

### 2. Tech under the hood

- **Backend: Laravel** (`laravel-session` + `XSRF-TOKEN` cookies), served by **Caddy** (`via: 0.0 Caddy`), HTTP/2 + h3.
- **CSS: Tailwind v4 via the in-browser CDN build** (`cdn.jsdelivr.net/npm/@tailwindcss/browser@4`, unpinned major). Theme tokens live in an inline `<style type="text/tailwindcss">@theme{…}</style>`, which is **copy-pasted into every page**.
- **Font:** Google Sans from Google Fonts, `wght@400..700`.
- **Icons:** inline SVG, Lucide-style (2px stroke, round caps), consistent with the PDF.
- **No `X-Frame-Options` / CSP headers** on the responses I checked.
- **Language switcher (EN/PT/ES/IT):** UI only, no translation (says so in a code comment).
- The demo page carries a code comment: `INDICATOR CALCULATOR (converted from Bootstrap)`. An existing Bootstrap tool page was hand-ported into hub Tailwind markup.

### 3. Live design tokens (identical `@theme` on every page)

| Hub token | Hex | Closest PDF token | PDF hex | Match? |
|---|---|---|---|---|
| `ink` | `#12354F` | Dark Azure | `#16364D` | ⚠️ close, not equal |
| `muted` | `#5C7A93` | Blue Slate | `#55788E` | ⚠️ close, not equal |
| `coral` | `#F0776B` | Pastel Coral | `#FF8174` | ⚠️ noticeably darker/redder |
| `mist` (page bg) | `#F7FAFC` | hub bg in PDF p17 | `#F8FAFC` | ⚠️ off by one |
| `fog` | `#EDF1F5` | (Azure 100 `#E7ECEF`?) | — | not in PDF |
| `line` (borders) | `#E2E8EF` | Light Azure (borders) | `#D0D7DB` | ⚠️ much lighter |
| `card` | `#FCFDFE` | white | — | not in PDF |
| `chip` | `#E7ECF1` | Azure 100 | `#E7ECEF` | near |

Font stack: `"Google Sans", ui-sans-serif, system-ui, sans-serif`.

**Contrast check of the live tokens:**
- ink on mist 12.16 ✓
- **muted on mist 4.30 ✗** (body page background, used for most secondary text across the site)
- **muted on fog 3.97 ✗** (footer, recommendation band)
- muted on white 4.51 (borderline ✓) · muted on card 4.42 ✗
- **coral on white 2.78**: used as text for the "Indicator Value" result (see §7)
- ink on coral 4.59 ✓ (the "For cities" button)

⚠️ Which set is canonical, the PDF palette or the live `@theme`? IAM-IQ has to pick one. My guess: the PDF is the spec and the site is a drifted prototype. Confirm with WP2.

### 4. Shared chrome (header and footer, on every page)

**Header** (sticky, `h-20` = 80px, `bg-mist/95` + backdrop blur, bottom border `line`):
- Logo `/img/logo.svg` (h-8 → sm:h-10), alt "IAM-CC, Innovative Air Mobility Competence Centre".
- Desktop nav (≥lg): **Home · Tools · Skills Lab · Resources · Think Tank · About**. Inactive links are 15px medium `muted`. The active link is semibold `ink` with a **6px coral dot centred under it**.
- Right side: search icon button (opens a 288px dropdown panel, placeholder "Search iamcc.eu"), **"For cities" coral pill CTA** (h-11, ink text, the page's one accent), and the language pill (globe + "EN" + chevron).
- Mobile (<lg): hamburger in a 40px rounded-lg bordered box. The menu drops down below the header. The active item gets a `fog` background.
- ⚠️ The PDF p17 Mode A mock showed only "Home · Tools · Skills Lab · Resources". The live nav has 6 items + CTA.

**Container:** `max-w-7xl` = **1280px**, padding `px-6` / `lg:px-10` → usable content width ≈ **1200px** on desktop.
⚠️ The PDF says the hub content area is **1312px**. The live site is narrower.

**Footer** (`bg-fog`, top border):
- Logo + tagline "Innovative Air Mobility Competence Centre - tools, training and guidance for cities."
- Columns: **Explore** (Tools, Skills Lab, Resources, Think Tank) · **Project** (About, For cities, Living Labs, News) · **Contact** (info[at]iamcc[dot]eu, www.iamcc.eu, LinkedIn, X). All except mailto are `#`.
- EU block: `/img/eu-logo.svg` (h-10) + 12px muted statement: "Funded by the European Union under Grant Agreement **number** 101271620. …" (the PDF says "No").

### 5. Homepage `/` — tool-related parts

- `<title>`: "IAM-CC | Innovative Air Mobility Competence Centre"
- Hero: "Helping cities bring drones into their skies, with people on board." Buttons: "Explore the tools", "I represent a city".
- "Start with who you are": 3 audience cards. **Cities & planners**, **Drone logistics operators**, **Citizens**, each with "See your path".
- **"Tools for every stage"**: shows **3 of 9** tools + "All 9 tools" button:
  - IAM-Compass (Cities, Regulators): image `/img/compass.png`
  - **IAM-IQ platform**: "Quantifies environmental, socio-economic and operational impacts of drone services." Tags **Authorities, Researchers**. Image **`/img/iq.png`** (a real asset already exists)
  - IAM VR tool (Cities, Citizens): image `/img/vr.png`
- Then Future Skills Lab, Guides & reports (3 downloads), "Is your city next?" (Declare interest).

### 6. Tools catalogue `/tools`

- `<title>`: "IAM-CC | Tools"
- H1 "Tools" (text-5xl = 48px bold). Sub: "Nine tools for planning, assessing and experiencing innovative air mobility." (18px muted)
- **Search** input "Search tools" (h-12 = 48px, **rounded-lg = 8px**, white, border `line`, focus = border darkens, `outline-none`).
- **Filter chips** (pills, 14px semibold): **All** (active: ink fill, white text) · For cities · For regulators · For researchers · For citizens · For operators (inactive: white, `line` border, muted text). Client-side JS filters on `data-tags` + full-text search.
- **Grid:** 1 col → md 2 → lg 3, gap 24px.

**Tool card anatomy** (`article.tool-card`, `rounded-xl` = **12px**, 1px `line` border, `card` bg, p-6 = 24px):
1. Image slot: h-40 (160px), rounded-lg, `fog` bg. Currently a placeholder (faint 4-dot mark + "IMAGE").
2. Name: 20px bold ink.
3. Subtitle: 14px muted. Either the long name or "formerly X".
4. Description: 15px muted, relaxed leading.
5. Audience tags: `rounded-md` (6px), `chip` bg, 12px semibold, ink/80.
6. **"Open tool"** secondary pill (1px ink/30 border, 14px semibold) with an external-link icon.

**All 9 tools as listed:**

| # | Name | Subtitle | Description | Tags (shown) | `data-tags` (filter) | Open tool → |
|---|---|---|---|---|---|---|
| 1 | IAM-SRA2 | Societal Readiness Assessment | Evaluate and visualise how ready your ecosystem is to adopt air mobility. | Cities, Policy makers | cities regulators | `#` |
| 2 | Drone nuisance app | formerly RHE Noise app | Report noise, visual pollution, safety and privacy concerns where you live. | Citizens, Cities | citizens cities | `#` |
| 3 | IAM-Compass | formerly SUAMI | Track policy progress and air mobility integration into your SUMP. | Cities, Regulators | cities regulators | `/tools/iam-compass` |
| 4 | **IAM-IQ platform** | **Impact Quantification** | **Quantify environmental, socio-economic, business and operational impacts.** | **Authorities, Researchers** | **regulators researchers** | **`#`** |
| 5 | IAM 3D | Safety maps & digital twins | Assess wind and downwash safety risks and run visual impact assessments. | Planners, Vertiport developers | cities operators | `#` |
| 6 | SAMWISE v2.5 | SAIL assessment | Determine SAIL level and safety requirements for drone operations. | Regulators, Operators | regulators operators | `#` |
| 7 | IAM VR tool | Vertiport environment simulation | Experience drone types, traffic volumes and routes in a virtual replica of your city. | Cities, Citizens | cities citizens | `#` |
| 8 | IAM AR tool | Acoustic soundscape studies | Hear and give feedback on real IAM noise levels in augmented reality. | Citizens, Researchers | citizens researchers | `#` |
| 9 | Agent-based simulator | Large-scale scenarios | Evaluate airspace capacity and societal impact of large drone deployments. | Researchers, Regulators | researchers regulators | `#` |

⚠️ The visible tags don't always match the filter tags. For IAM-IQ, "Authorities" displays but filters as "regulators". "Authorities" isn't in the PDF's 8 audience tags either (p18 list: Cities, Regulators, Researchers, Citizens, Operators, Policy makers, Planners, Vertiport developers).
⚠️ The IAM-IQ description differs between the homepage ("…of drone services") and /tools ("…business and operational impacts"). The /tools one is 73 chars and verb-first, which fits the p18 "≤90 chars, starting with a verb" rule.

**"Not sure where to start?" band** (below grid, `fog` section, white rounded-2xl box):
> "The recommendation system compares your neighbourhoods with cities already using these tools and suggests what fits - **powered by IAM-IQ data**."
Primary ink button "Get a recommendation" (`#`).
→ **IAM-IQ is also positioned as the data source behind the hub's recommender**, not only as a tool card.

### 7. Tool detail page `/tools/iam-compass` (the template IAM-IQ's hub page will follow)

- `<title>`: "IAM-CC | Tools > IAM-Compass"
- Breadcrumb: Tools / **IAM-Compass**
- H1 48px → lg 54px bold. Lead: "Track policy progress and air mobility integration into Sustainable Urban Mobility Plans." (18px muted, max-w-xl)
- Tags as **pills** here (`rounded-full`, 14px): Cities · Urban planners · Regulators. ⚠️ These are pills here and 6px-radius tags on the catalogue card. "Urban planners" is not in the PDF tag list.
- **Layout:** `grid lg:grid-cols-[1fr_360px]`, gap 40px (main column + 360px sidebar).

**Main column:**
1. **Screenshot** slot, `aspect-[2/1]` (matches the p18 1600×800 spec), rounded-xl, `fog`, placeholder "SCREENSHOT".
2. **"What it does"** (34px bold h2): 3 bullets (15px, small ink/60 dots):
   - Tracks policy milestones for drone integration in your city
   - Maps air mobility measures into your existing SUMP
   - Compares your progress with peer cities across Europe
3. **"Who it's for"**: one sentence, 18px muted: "City mobility departments, urban planners and regulators who need a shared, up-to-date view of where drone policy stands."

**Sidebar (3 cards, rounded-xl, `line` border, `card` bg, p-6):**
1. **Access**: full-width **primary ink pill "Open tool"** (→ `/tools/iam-compass-demo`) + note "Opens on a partner platform - free for registered users." + definition list:
   - Lead partner: **FN** (Future Needs)
   - Status: **v1 at M12**
   - Formerly: **SUAMI**
2. **Related guides**: list rows with a 44px `fog` file-icon tile + bold title + 12px meta:
   - SUMP integration guide · Guide · PDF
   - Policy tracking manual · Manual · PDF
3. **Learn it**: "'Planning with IAM-Compass' - a 45-minute module in the Future Skills Lab." + text link "Go to the Skills Lab →" (hover turns coral).

This maps one-to-one onto the PDF p18 "Send us for your hub page" checklist: name/former name, one-liner, audience tags, 3 bullets + who-it's-for, related guides + Skills Lab module, card image + 2:1 screenshot, mode/URL/lead partner/version.

⚠️ The "Open tool" sidebar note says "Opens on a partner platform", but the target is a hub-hosted page (§8).

### 8. Working tool page `/tools/iam-compass-demo` — "Noise indicator" calculator

This is the most relevant page for IAM-IQ. It shows what a tool looks like when it lives **natively inside the hub chrome**: full hub header (Tools active), hub footer, no iframe. That makes it neither Mode A (iframe) nor Mode B (own domain) from the PDF.

- `<title>`: "Indicator Details - Tools - IAM-CC" (⚠️ a third title format; the PDF wants "Tool name | IAM-CC")
- Breadcrumb: Tools / **IAM-Compass details**
- One big card (rounded-xl, `line` border, `card` bg) with a `fog` card-header strip: calculator icon + **"Noise indicator"** (18px bold).
- Body sections, each with a 36px `fog` icon tile + 18px bold heading + 15px muted text:
  1. **Definition**: "The percentage of the urban population exposed to transport noise levels exceeding the recommended thresholds (typically Lden > 55 dB)…"
  2. **Rationale**: health and liveability argument for monitoring noise exposure.
  3. **Methodology**: strategic noise mapping per END 2002/49/EC; road, rail, air; Lden.
  4. **Data Sources**: EEA noise data; national/local environmental agencies; urban noise mapping studies; transport infrastructure databases (bullets are **coral dots**).
  5. **How to Calculate:** 5-step ordered list (enter exposure data → HA weight factors → hindrance factors via polynomial regression → normalised hindrance index and scaled indicator → click Calculate).
  6. **Population Exposure Data**: editable table, rows = noise bands **55-59, 60-64, 65-69, 70-74, >75 dB**, columns = **Road, Rail, Air, Drone**. Numeric inputs prefilled (e.g. 55-59: 36900 / 2600 / 12300 / 2000). The Drone inputs have the tooltip "Add zero if you don't have drone data".
  7. **High Annoyance Weight Factors**: same 5×4 table of decimals (0.08 … 0.80).
  8. **Calculate**: centred primary ink pill.
  9. **Results**: two small cards: "Normalized Hindrance Index" (ink) and **"Indicator Value" (coral text)**. Initial text "Push the calculation button to see the results...".
  10. **Visualization**: placeholder panel ("Noise exposure levels visualization...").
  11. **References**: EEA 2020; WHO 2018 Environmental noise guidelines; Directive 2002/49/EC.
- **Calculation (client-side JS):** band mid-points Lden = [57.5, 62.5, 67.5, 72.5, 77.5]. x = Lden − 37. HF = 0.0001795x³ + 0.0211x² + 0.5353x. Highly annoyed per band = Σ_mode P·W. NI = Σ(HA_band · HF_band). Result = NI / ΣHA / 100. Indicator = 10·(0.7 − result)/0.7. Both are printed with `toFixed(6)`.
- Table cells use `overflow-x-auto` with `min-w-[620px]`, so the table scrolls sideways on mobile while the page itself does not.

⚠️ **The content is an impact indicator (noise exposure / annoyance), which is IAM-IQ / ImAFUSA territory, but it's labelled "IAM-Compass details".** It's either a placeholder borrowing IAM-IQ content or a sign that indicator calculators are meant to live under Compass. Worth confirming. Either way it's the reference pattern for "an indicator page in hub style".

**Guideline breaches on this page** (useful as a don't-copy list):
- Tables have **vertical dividers** (`divide-x`). PDF p13 says no vertical lines.
- Inputs use `focus:outline-none` with only a faint border change, so there is **no visible focus ring** (PDF p11/12/18).
- Table inputs have **no labels** (a11y). They're identified only by row/column position.
- **Coral used as text** (Indicator Value, 2.78:1) and as **decorative bullets**, against PDF p5/p7.
- **Title Case** headings ("Data Sources", "How to Calculate:", "Population Exposure Data", "High Annoyance Weight Factors"), against the sentence-case rule. There's also a stray colon.
- The results placeholder text is an instruction, not an empty state. Raw `toFixed(6)` output is not user-friendly.
- Number inputs use inline `oninput` hacks (`maxlength` on number inputs doesn't work natively). "Validate on blur" (PDF p12) isn't followed.

### 9. Where the live hub differs from the PDF guidelines (summary)

| Topic | PDF says | Live hub does |
|---|---|---|
| Colours | Dark Azure `#16364D`, Blue Slate `#55788E`, Coral `#FF8174` | `#12354F`, `#5C7A93`, `#F0776B` |
| Hub bg | `#F8FAFC` | `#F7FAFC` |
| Borders | Light Azure `#D0D7DB` / Azure 100 | `#E2E8EF` |
| Card radius | 20px | 12px (`rounded-xl`); 16px on the recommendation box |
| Input radius / height | 12px / 40px | 8px / 48px (search), 8px / 40px (table inputs) |
| Badges | one style | 6px tags on cards, pills on the detail page |
| Content width | 1312px | 1280px container, ~1200px usable |
| Coral | one key action only | CTA button + nav dot + hover colour on icons/links + bullets + result text |
| Focus | visible 3px ring | `outline-none`, border tint only |
| Tables | no vertical lines | vertical lines on the demo |
| Title format | `Tool name \| IAM-CC` | "IAM-CC \| Tools > IAM-Compass", "Indicator Details - Tools - IAM-CC" |
| Integration modes | A (iframe) or B (own domain) | the demo is a third way: native hub page |
| Secondary text contrast | AA | muted on mist 4.30, on fog 3.97 (fail) |

What does match: Google Sans, pill buttons/chips, ink primary buttons, secondary outline buttons, the Lucide-style 2px icons, sentence case in most UI labels, the EU statement, the 2:1 screenshot slot, and the hub-page content model (p18).

### 10. What this means for IAM-IQ "for now"

**Decided (Nick, 2026-10-11):**
- **Spec:** the PDF (with corrections C1–C4) is the spec. The UI should also look like the live hub.
- **First step:** the hub's tools section is the first step of the IAM-IQ platform.
- **Integration mode:** for now IAM-IQ stays an **independent app**, as it is today. That's effectively Mode B: own domain, IAM-CC tool header with "Back to hub", and the EU footer.
- **Custom frontend:** see [IAM-IQ internal tool UI standard](#iam-iq-internal-tool-ui-standard-nick-2026-10-11-binding-for-the-custom-iam-iq-frontend) above for the source order (playground first, then `/tools/iam-compass` (§7) and `/tools/iam-compass-demo` (§8) as structure templates). Re-checked live 2026-10-11: both pages return 200, and the tokens and layout classes are unchanged from these notes.

My earlier reading, kept for reference:

1. **The hub listing already exists:** a card on `/tools` and the homepage ("IAM-IQ platform", "Impact Quantification", Authorities/Researchers, `/img/iq.png`). Its "Open tool" goes to `#`.
2. **Missing: `/tools/iam-iq` detail page**, built on the IAM-Compass template. To fill it we need the p18 handover items:
   - one-liner (≤90 chars, verb-first)
   - 3 "What it does" bullets and 1 "Who it's for" sentence
   - audience tags
   - 2:1 screenshot and 1200×480 card image
   - Access card: Open-tool target, access note, lead partner, status/version, former name (if any)
   - related guides
   - Skills Lab module
3. **The tool itself, if it follows the demo-page pattern:** each IAM-IQ indicator is a hub-styled page. It needs the definition / rationale / methodology / data sources / how-to / inputs / calculate / results / visualisation / references structure, inside hub chrome, using the hub `@theme` tokens. The noise indicator page is effectively the first IAM-IQ-style page already ported (from Bootstrap).
4. **Stack gap:** IAM-IQ's frontend plan is Vue 3 + Vuetify (Material) + Leaflet/Plotly (see [presentations/techstack.md](presentations/techstack.md)). The hub is Laravel + Tailwind. Matching the hub means either:
   - re-theming Vuetify heavily: Google Sans, pill buttons, ink/coral tokens, 12–20px radii, no Material elevation/ripple look; or
   - shipping IAM-IQ pages as Tailwind/HTML like the demo.
   This decision depends on whether IAM-IQ is embedded (Mode A), external (Mode B) or native (like the demo).
5. **Recommender feed:** the hub's "Get a recommendation" feature is "powered by IAM-IQ data". There is presumably an API/data contract to define there too.

---

## Open questions

### From the PDF guidelines (collected ⚠️)

1. Pastel Coral on white is 2.43:1 by calculation, not 2.6:1 as stated.
2. Blue Slate on Azure 50 is 4.33:1, which fails AA for normal text.
3. `#F8FAFC` hub background is not part of the documented palette.
4. Hex values for the sequential, intensity and diverging ramps are missing (C2 only replaced the categorical palette).
5. ~~Alert tint backgrounds are not specified.~~ Resolved by C3 (40% variants).
6. Coral exceptions are not stated as exceptions: "New" badge, featured border, focus rings, "Back to hub" underline. These sit against "coral never for decoration/status".
7. "All text in Dark Azure or Blue Slate" vs coloured alert/error/button text.
8. Table example has a left-aligned numeric column, contradicting "numbers right aligned".
9. Grid margin 64px vs Mode A "outer margins 24px max".
10. Badges: 8px "tag" radius vs pill "chip" radius.
11. Card image ratio is 2.5:1; only the screenshot is 2:1.
12. Tool slug format: `iam-compass` vs `iamcompass`.
13. Google Sans licensing: which family/files are in the partner kit (OFL claim).
14. Mode A iframe height mechanism (fixed min height vs auto-resize).
15. The Mode B footer mockup omits the mandatory privacy link.
16. Chart contrast with the final in-between palette: S3 2.97 and S4 2.24 are below 3:1 on white, so they always need labels. S2 is still close to brand coral.
17. Sentence-case rule not followed by the deck's own titles ("Colour Palette", "Table of Contents", "Hub Integration").
18. ~~Warning `#CD7C00` too light for text~~ → resolved: warning stays `#8F5117`. Status colours on their own tints are still below 4.5:1, so alert text should be Dark Azure.

### From the live hub (for you / WP2)
- Is the native-hub-page pattern (demo) the target for IAM-IQ, or Mode A or B?
- Canonical tokens: PDF palette or the live `@theme`?
- Is the "Noise indicator" under IAM-Compass actually IAM-IQ content?
- Audience tags for IAM-IQ: keep "Authorities" (not in the PDF list) or switch to Regulators / Policy makers?
- Lead partner, status/version and former name for the IAM-IQ Access card.
