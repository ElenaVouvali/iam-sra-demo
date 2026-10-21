---
name: iamcc-ui
description: 'The IAM-CC / IAM-IQ UI standard as ready-to-use tokens, component CSS, icons, page templates and rules, generated from the project''s UI playground ("PDF spec + corrections" preset). Use it for ANY user-facing UI work in the IAM-IQ repo: building or restyling a page, Vue component, tool working page, tool detail page, catalogue, header/footer, form, chart, map, alert or empty state; choosing colours, fonts, spacing or radii; porting a RefMap/ImAFUSA/metaCCAZE partner UI into IAM-IQ; or reviewing a screen against the IAM-CC hub guidelines. Use it even when the user only says "make it look right", "match the hub", "fix the styling" or "build the page for tool X". Not for slide decks or presentations.'
---

# IAM-CC UI for IAM-IQ

IAM-IQ replaces the partner frontends (RefMap, ImAFUSA, metaCCAZE) with its own UI, and that UI must look and
behave like the IAM-CC hub. The design was settled in the playground (`docs/iamcc-ui-playground-standalone.html`,
preset **"PDF spec + corrections"**), which applies Nick's corrections C1–C4 to the WP2 guidelines PDF. This skill
packages that playground so you build with the exact same tokens and components instead of approximating them.

**Source order when anything disagrees** (highest first):
1. The playground, "PDF spec + corrections" preset. It beats the live hub's own `@theme` (ink `#12354F`,
   coral `#F0776B`, 12px cards, `outline-none` …), because the live hub breaks several guidelines.
2. `docs/iamcc-ui-notes.md` → "IAM-IQ internal tool UI standard" (binding rules) and the corrections log.
3. The hub pages `/tools/iam-compass` and `/tools/iam-compass-demo`, for page **structure only**.

If a request would break one of these rules, say so and suggest the compliant version rather than silently
complying. Open questions (audience tags …) are listed at the end of `docs/iamcc-ui-notes.md`;
don't settle them yourself.

## What's in the skill

| File | What | Edit? |
|---|---|---|
| `assets/tokens.css` | every token as a CSS variable on `:root` (colour, status, chart series, radii, spacing, type, shadows, font) | generated |
| `assets/tokens.json` | the same tokens as JSON (for Plotly/Leaflet theming in JS) | generated |
| `assets/components.css` | all playground components, scoped under `.iq` | generated |
| `assets/fonts.css` | Google Sans (Greek, Latin, Latin-ext) inlined as woff2, SIL OFL; offline alternative to Google Fonts | generated |
| `assets/icons.svg` | sprite: `iamcc-logo`, `iamcc-mark`, 12 UI icons | generated |
| `assets/eu-emblem.svg` | "Funded by the European Union" emblem for the footer | generated |
| `assets/layout.css` | page layouts the playground doesn't cover: breadcrumb, detail grid + sidebar, working-page card, sections, result stats, links | hand-written, tokens only |
| `assets/starter.html` | a complete, rendered tool working page: start every new page from it | hand-written |
| `references/components.md` | copy-ready markup for every component, with its usage rules | read when building UI |
| `references/page-templates.md` | routes, the working-page and detail-page structures, responsive rules | read when building a page |
| `scripts/sync_from_playground.mjs` | regenerates the generated files from the playground | run after the playground changes |

Never hand-edit a generated file: change the playground, then run
`node .claude/skills/iamcc-ui/scripts/sync_from_playground.mjs` (node is under `~/.nvm/versions/node/*/bin/` if not on PATH).
New page-level patterns go in `layout.css`, built only from existing tokens.

## How to use it

1. **Read** `references/page-templates.md` for a page, `references/components.md` for components. Open
   `assets/starter.html` when building a tool page; it is the reference rendering.
2. **Wire the assets in.** In the custom frontend (`app/`, see `docs/frontend-spec.md`):
   - `assets/tokens.css`, `components.css`, `layout.css` → `app/src/styles/`, imported in that order in `src/main.js`.
   - `assets/icons.svg`, `eu-emblem.svg` → `app/public/brand/`; reference as `/brand/icons.svg#i-search`.
   - Font: the spec loads Google Sans from Google Fonts in `app/index.html`; use `fonts.css` instead when the page must work offline.
   - Wrap the app root in `<div class="iq">`. It is the size container for the 12/8/4-column breakpoints, so every component
     class only works inside it.
   For a standalone HTML page, link the four CSS files and keep `icons.svg` next to it (served over http, not `file://`).
3. **Use variables, never literals.** Colours are `var(--c-azure)`, `var(--s1)` …; sizes are rem tokens
   (`var(--sp4)`, `var(--r-lg)`, `var(--fs-label)`). If something seems to need a new value, it probably maps to an
   existing token: check `tokens.css` first. All sizes stay in rem (correction C4) so the UI scales from the root size.
4. **Check it** with the list at the bottom before calling the work done.

## Rules that matter most

These come from the guidelines and from problems the old console and the partner UIs actually had.

- **Colour roles.** Dark Azure `--c-azure` carries text and primary UI; Blue Slate `--c-slate` is secondary text.
  Pastel Coral `--c-coral` marks the **one** key action on a screen (an `accent` button, a featured card's border, a focus ring),
  and is never text, decoration, a selected state or an alert. Coral-coloured text uses `--c-coral700`.
- **Status** colours (`--c-success|warning|danger` and their `-t` 40% tints) always come with an icon and a text label;
  alert text stays Dark Azure, because status colour on its tint is below 4.5:1.
- **Charts:** series `--s1`…`--s5` in order, never cycled; label S3/S4 (below 3:1); one y-axis; legend for 2+ series;
  offer a table view. Theme Plotly from `tokens.json` (font `--font`, axis text `--fs-caption` Blue Slate, gridlines Azure 100).
- **Focus is always visible.** Never `outline:none` without the built-in ring replacement.
- **Every input has a visible label** above it (table-cell inputs get an `sr-only` label). Placeholders are examples.
  Validate on blur with an error that says what to do.
- **Sentence case** for every heading, button, label and tab. Button labels are verb-first, 1–3 words. "Download" has no icon (C1).
- **Real states.** Loading = skeleton, empty = `empty` component, error = `alert danger` plus retry. Never instruction text as an
  empty state, never `toFixed(6)`: format numbers for people with units.
- **No overflow, no mini screens.** Pages work from 360 to 1440px with no horizontal page scroll; no fixed heights around text;
  `min-width:0` on flex/grid children; long strings wrap (`overflow-wrap:anywhere`); wide tables scroll in their own box.
  Each tool is a full page at its own route: no `<iframe>`, no partner UI code, no partner back buttons.
- **Navigation.** Every view is a real URL; filter state in the query string; breadcrumb on every inner page;
  "Back to hub" goes to `https://hub.iamcc.eu/tools` (new tab); only links leaving IAM-IQ open a new tab. Routes are `/`, `/tools/<id>`, `/tools/<id>/app` (`docs/frontend-spec.md` §4).
- **Footer** carries the EU emblem and the Grant Agreement 101271620 statement verbatim, plus a privacy link.

## Done checklist

- [ ] Only token variables: `grep -nE '#[0-9a-fA-F]{3,6}\b|[0-9.]+px' <your css/vue>` finds nothing new (SVG viewBoxes excepted).
- [ ] Inside `.iq`, header + breadcrumb + footer present; page `<title>` is "<Page> · IAM-IQ | IAM-CC" (decision D3).
- [ ] At most one coral `accent` button visible; coral never used as text.
- [ ] Tab through the page: every interactive element shows a focus ring, in a logical order.
- [ ] Every input has a label; errors appear on blur and clear when fixed.
- [ ] Loading, empty, error and ready states all exist for each async area.
- [ ] Screenshot at 360, 768, 1200 and 1440px (headless Firefox works:
      `firefox --headless --profile <fresh dir> --no-remote --window-size=W,H --screenshot out.png <url>`) and look at them:
      no sideways scroll, nothing clipped, icons and logo visible.
