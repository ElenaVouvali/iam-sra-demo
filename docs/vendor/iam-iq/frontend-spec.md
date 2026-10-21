# IAM-IQ frontend: implementation spec

Status: **approved plan, not executed** (2026-10-11). Nick answered the open questions (§12) and his answers are worked in below. Nothing in this spec has been installed or built yet.
Design rules: [iamcc-ui-notes.md › "IAM-IQ internal tool UI standard"](iamcc-ui-notes.md#iam-iq-internal-tool-ui-standard-nick-2026-10-11-binding-for-the-custom-iam-iq-frontend). This spec says *what* to build. That section says how it must look.
Rollback point: git tag `snapshot-pre-custom-frontend`.

---

## 1. Goal

**One IAM-IQ web app replaces every partner frontend.**
- It calls the 13 RefMap and ImAFUSA backends directly.
- It renders every tool as a full page in IAM-CC style.

**Fixes for the three current problems:**
- **Overflowing text:** our own CSS, with no partner CSS.
- **Small embedded window:** no iframes.
- **Broken RefMap back buttons:** a real URL for every view, so the browser Back button always works.

**Out of scope:**
- Changing backend APIs. Exception: the two broken RefMap backends in §8, which need data, not code.
- The admin cluster overview (`admin/cluster-overview/`), which stays separate and loopback-only.
- The partner repos, which are not touched.

## 2. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Partner UIs disappear from IAM-IQ completely. They live on in the partner repos. | decided |
| D2 | Design standard: the playground first, then the hub `iam-compass` and `iam-compass-demo` pages as structural templates | decided |
| D3 | Page title format: `<Page> · IAM-IQ \| IAM-CC`. The home page is `IAM-IQ \| IAM-CC`. | decided |
| D4 | Mode B (independent app, own domain, IAM-CC tool header with "Back to hub") | decided earlier |
| D5 | **Stack: Vite + Vue 3 single-file components, using npm.** npm gets installed as the first step of phase 1 (see §3). | decided |
| D6 | **The app runs on port 5000** from the start, in both dev and production. The old console's server is stopped when the new app first starts; the console stays recoverable from the snapshot tag. | decided |
| D7 | Admin links (the MinIO console and the Kubernetes dashboard) are removed from the public UI. They stay in the admin dashboard. | decided |
| D8 | **Images:** we use our own screenshots, plus placeholders where none exist yet. All of them sit behind one image manifest, so the official images can be swapped in all at once (see §4, "Images"). | decided |
| D9 | **Tools without data** (`refmap-pollution`, `refmap-climate`): ignore the missing data for now. Their pages are built with placeholders (see §8). | decided |

## 3. Stack and architecture

**Step 0 of phase 1: install npm. ✅ Done.**
- `sudo pacman -S npm`. Done by Nick on 2026-10-11: npm 12.2.0 with node v26.11.1.

| Piece | Choice |
|---|---|
| Build tool | Vite, with versions pinned in `package.json` / `package-lock.json` |
| UI framework | Vue 3 single-file components (`.vue`) using `<script setup>` |
| Router | `vue-router` 4 in history mode. It gives real paths with no `#`, and filter state is kept in the query string. |
| Maps | Leaflet 1.9, used directly, with no `vue-leaflet` wrapper, so Leaflet stays fully under our control. Basemap: OpenStreetMap's standard tiles (`tile.openstreetmap.org`). The partner UIs' CARTO light basemap now needs an API key and watermarks every tile without one. OSM's tile server needs no key but is meant for light use, so it is a stopgap. **Long-term solution: self-hosted Protomaps** (one `.pmtiles` file served from our own storage, e.g. MinIO), so no third-party tile service or key is needed. |
| Charts | Plotly (`plotly.js-dist-min`), themed with the playground tokens. Plotly is needed for the safety tool's 3D bars and for several scatter and line charts. It is loaded lazily, only on pages that have charts. |
| CSS | One `tokens.css`, generated from the playground's "Download tokens JSON". One `components.css`, ported from the playground's preview CSS. Everything is in rem. **No Vuetify and no other UI kit.** |
| Font | Google Sans from Google Fonts, as in the playground |
| Dev server | `npm run dev` runs Vite on **port 5000**. Its `server.proxy` handles `/api/<tool>/…` (§6). |
| Production server | `npm run build` produces `app/dist/`. `serve_app.py` (Python standard library only) serves it on **port 5000**. Any path that isn't a file returns `index.html`, so deep links work. It forwards `/api/<tool>/…` the same way. |
| Proxy table | One file, `app/proxy-routes.json`. Both `vite.config.js` and `serve_app.py` read it, so dev and production can't drift apart. |

**Layout on disk** (new folder `IAM-IQ/app/`):

```
app/
  package.json, package-lock.json, vite.config.js
  proxy-routes.json     /api/<tool> → backend target (§6), read by Vite and serve_app.py
  serve_app.py          production: serves dist/ + SPA fallback + API proxy
  index.html            shell: <head>, fonts, mounts #app
  src/main.js           createApp, router
  src/router.js         routes (§4), titles "<Page> · IAM-IQ | IAM-CC"
  src/styles/tokens.css       generated from the playground tokens JSON
  src/styles/components.css   ported playground component styles
  src/api.js            fetch wrapper: timeouts, JSON errors → UI error states
  src/tools.js          the tool registry (§5): text, routes, endpoints, inputs, status
  src/images.js         the image manifest (§4 "Images")
  src/components/       AppHeader, AppFooter, Breadcrumb, ToolCard, Section, SelectField, MapView, PlotlyChart, EmptyState, ErrorState, Placeholder…
  src/pages/            Home.vue, ToolDetail.vue, NotFound.vue
  src/tools/<id>.vue    one working page per tool
  src/content/<id>.md   tool text (definition, methodology …) taken from the partner docs
  public/images/tools/  card images and screenshots (§4 "Images")
  public/brand/         IAM-CC logo, EU emblem (from the playground)
  tests/                route + API + layout checks (§10)
```

## 4. Pages and routes

| Route | Page | Template |
|---|---|---|
| `/` | **Home / tool catalogue** | hub `/tools` + playground "Tools catalogue" |
| `/tools/<id>` | **Tool detail** | hub `iam-compass` |
| `/tools/<id>/app` | **Tool working page** | hub `iam-compass-demo` |
| anything else | Not found (an empty state with a link home) | playground "Feedback and states" |

**Shared chrome (every page):**
- **Header:** the playground tool header (Mode B). It holds the IAM-CC logo, a divider, "IAM-IQ", and "Back to hub". "Back to hub" goes to `https://hub.iamcc.eu/tools`, because there is no `/tools/iam-iq` hub page yet. That link opens in a new tab.
- **Footer:** the EU footer, with the emblem and the Grant Agreement statement from the playground.

**Home `/`:**
- Title "Impact quantification", plus a lead sentence. The lead is the hub's catalogue line: "Quantify environmental, socio-economic, business and operational impacts."
- A search field and filter chips: **All · RefMap · ImAFUSA · metaCCAZE**, plus a domain filter (environmental, socio-economic, safety, accessibility).
- A tool card grid with 1, 2 or 3 columns. Each card holds:
  - the image slot
  - the name
  - the suite (as the subtitle)
  - a one-line description
  - tags
  - an **"Open tool"** secondary pill
- "Open tool" goes to `/tools/<id>` in the same tab.
- The search and filters are kept in the query string, so the browser Back button restores them.

**Tool detail `/tools/<id>`:**
- Breadcrumb "Tools / <name>", then the H1, the lead and the tags.
- Main column:
  - a 2:1 screenshot of our own working page, taken after the build
  - "What it does" (3 bullets)
  - "Who it's for"
- Sidebar, 22.5rem wide:
  - **Access card:** a primary "Open tool" button to `/tools/<id>/app`, then:
    - Suite
    - Lead partner
    - Status (Live / No data yet / Pending disclosure)
    - Data location (`s3://iam-eu/…`)
  - **Related tools:** the same suite, or the same domain.

**Images (D8): one manifest, easy to swap.**
- Every image the UI shows is looked up through `src/images.js`. No component hard-codes an image path.
- The manifest lists, for each tool id:
  - `card`: the catalogue card image, 1200×480 (2.5:1)
  - `screenshot`: the detail page image, 1600×800 (2:1)
  - `alt`: the alt text
- The files live in `public/images/tools/<id>-card.<ext>` and `<id>-screenshot.<ext>`. That's one fixed naming scheme.
- **To change one image:** drop a file with the same name into that folder. To use a different name or format, edit one line in `images.js`.
- **To change them all:** replace the folder, then rebuild.
- **Our images:** screenshots of our own working pages, taken at 1600×800 by a script, `npm run screenshots`. The script can be re-run whenever a page changes.
- **Placeholders:** used when there is no image yet, or the file is missing.
  - The `Placeholder` component draws the playground's image placeholder: an Azure 50 block, rounded, with a faint IAM-CC mark and the tool name.
  - The fallback is automatic. A broken or missing file never shows a broken-image icon.
- **Status of each image:** `images.js` marks each one as `official`, `ours` or `placeholder`. One command, `npm run images:report`, lists which images still need official replacements.

**Tool working page `/tools/<id>/app`:**
- Breadcrumb "Tools / <name> / Tool", then one large card.
- Card sections, in order. A section with no content is left out.
  1. Definition
  2. Rationale
  3. Methodology
  4. Data sources
  5. How to use
  6. Inputs
  7. Run
  8. Results
  9. Visualisation
  10. How to read the results
  11. References
- "How to read the results" is the only addition to the template. It holds the RefMap "Analysis guidelines" and the ImAFUSA interpretation notes.
- Every input value is mirrored into the query string (`?city=Denhaag&time=Daytime…`). Reloading the page or pressing Back restores the same view.
- **Text sources.** The text comes from the partner documentation and is not written fresh:
  - RefMap: `src/data/documentation.json`, with its tabs Overview, Input parameters, Visualizations and Analysis guidelines.
  - ImAFUSA: `docs/tools.md`.
  - The text is edited only for sentence case and length.

## 5. Tool registry and per-tool pages

There are 17 entries: 6 RefMap, 9 ImAFUSA and 2 metaCCAZE. "Data in cluster" is what the live backends returned on 2026-10-11.

### RefMap (lead: RefMap consortium)

| id | Page name | Backend endpoints | Inputs | Run → results / visualisation | Data in cluster |
|---|---|---|---|---|---|
| `refmap-noise` | Noise assessment | `noise_available_combinations`, `noise_image_info`, `/scale-argb.png` | city, ambient profile (day/night), flight zone, flights per hour, metric. All cascade from one `available_combinations` call. | "Show map" → a Leaflet image overlay at the returned bounds, plus a horizontal colour bar. The bar's range depends on the metric: dB 0–100, annoyance 0–10, or %HA 0–100%. | ⚠️ **placeholder only**: the PNGs are opaque screenshots with a satellite photo of another city baked in, not map layers (§8) |
| `refmap-wind` | Wind and turbulence risk | `available_combinations`, `image_info` | level of detail, city, parameter, altitude, wind | "Show map" → an image overlay centred on the returned centre and radius, plus a legend | ⚠️ **placeholder only**: the PNGs are slide screenshots (title, two 3D city renders, colour bar), not map layers (§8) |
| `refmap-emissions` | Emissions footprint | `emissions_reductions` → `metrics` → `cases` → `image_file` | reduction, metric, case (cascading) | "Show result" → a full-width figure with a caption | ✅ `10perc_reduction` |
| `refmap-trajectories` | Optimised trajectories | `/cases`, `/gif/<path>` | area, turbulence, take-off, landing (filters on the case list) | Animation (GIF) with a play/pause control, plus a case table. The animation does not autoplay with sound and respects reduced-motion. | ✅ 1 case |
| `refmap-climate` | Climate impact and ATR | `get-dates` → `get-data-types` → `get-scales` → `get-costs` → `get-netcdf-metadata`, `get-heatmap-overlay`, `get-atr-percentage-increase` | date, data type, scale, cost, time, altitude | Heatmap overlay, plus an ATR % increase chart | ⚠️ **no data**: `get-dates` returns `[]` |
| `refmap-pollution` | Atmospheric pollution | `/api/metadata`, POST `timeseries`, `snapshot`, `heatmap`, `point` | variable, time, area or point on the map | Heatmap overlay, a time-series chart, and a value at a clicked point | ⚠️ **backend error**: `"ZARR store not found at None"` |

### ImAFUSA (lead: ImAFUSA consortium)

| id | Page name | Backend endpoints | Inputs | Run → results / visualisation | Data |
|---|---|---|---|---|---|
| `imafusa-air-quality` | Air quality | `/api/emissions` | energy used (kWh, with unit), country, year, emission unit | "Calculate" → a result card per pollutant (CO₂, CO₂eq, NOx, PM2.5 …) plus a bar chart | ✅ |
| `imafusa-noise` | Noise assessment (operations) | `filters`, `calculate`, `images/<path>` | altitude → operation → payload → scenario (cascading) | "Calculate" → result values plus result images. The partner UI let users drag images around to reorder them. We replace that with a fixed grid that can be sorted, which can be used from the keyboard. | ✅ |
| `imafusa-visual` | Visual pollution | `/calculate`, `/scatter` | density, path type | "Calculate" → result cards plus a scatter chart | ✅. The valid `path_type` values are still to be read from the partner UI. |
| `imafusa-safety` | Safety assessment | `/variables`, `/plot-data`, `/3d-bar-data` | variable | a chart for the chosen variable, plus the 3D bar chart (Plotly) | ✅ 4 variables |
| `imafusa-social` | Social acceptance | `/cities`, `/city-stats`, `/city/<name>`, `/averages`, `/question_data`, `/individual_scores` | city (one or several to compare) | city statistics cards, per-question charts, and a comparison against the averages | ✅ Athens, Lisbon, Scilly Islands |
| `imafusa-affordability` | Price affordability | `/metadata`, POST `/calculate` | country, income level (below average / average / above average), transport modes (multi-select), trips per month | "Calculate" → each mode's cost as a % of monthly income, shown against the 10% "affordable" and 15% "moderate" thresholds and labelled by status. Plus a line chart of affordability across the income range. | ✅ 10 countries, 13 modes |
| `imafusa-travel-time` | Accessibility: travel time | `/countries`, `/travel-time-range`, `/calculate`, `/analyze` | distance, country, min/max travel time | "Calculate" → results plus charts | ✅ 8 countries, 1–60 min |
| `imafusa-pjr` | Accessibility: population-to-job ratio | `pjr/countries`, `europe-years`, `europe-data`, `regions-geojson`, `regions-data`, `region-sheet`, `municipality-sheets` | year (Europe view) → country → region | a Leaflet choropleth (Europe, then regions), plus region and municipality tables | ✅ 2018–2024 |
| `imafusa-welfare` | Welfare impact | **no backend** | the inputs from `welfare.vue` | the calculation is moved from `welfare.vue` into `src/tools/imafusa-welfare.vue` and runs in the browser; results plus a chart | ✅ client-side |

### metaCCAZE

| id | Page name | Behaviour |
|---|---|---|
| `metaccaze-equity` | Demographic equity and vulnerability | Detail page only. Status "Pending disclosure". No "Open tool" button, just a status note. |
| `suami-fiches` | SUAMI sustainable mobility fiches | Detail page only. Status "Data lake ready". |

## 6. API proxy (`proxy-routes.json`, used by the Vite dev server and `serve_app.py`)

The browser only ever talks to the app's own origin. That avoids CORS errors and hard-coded IPs and ports in the frontend.

| Browser path | Forwarded to (default `K8S_HOST=192.168.49.2`) |
|---|---|
| `/api/refmap-climate/…` | `:30001/…` |
| `/api/refmap-wind/…` | `:30002/…` |
| `/api/refmap-noise/…` | `:30003/…` |
| `/api/refmap-trajectories/…` | `:30004/…` |
| `/api/refmap-emissions/…` | `:30005/…` |
| `/api/refmap-pollution/…` | `:30006/…` |
| `/api/imafusa-air-quality/…` | `:30011/…` |
| `/api/imafusa-noise/…` | `:30012/…` |
| `/api/imafusa-safety/…` | `:30013/…` |
| `/api/imafusa-visual/…` | `:30014/…` |
| `/api/imafusa-social/…` | `:30015/…` |
| `/api/imafusa-affordability/…` | `:30016/…` |
| `/api/imafusa-travel-time/…`, `/api/imafusa-pjr/…` | `:30017/…` (the same Accessibility backend) |

**How the proxy behaves:**
- **Methods:** it handles GET and POST. Bodies and query strings pass through unchanged.
- **Timeout:** 30 s.
- **Errors:** when a backend is down, it returns `502` with a JSON body `{error, tool}`. The page shows that as an error state with a "Try again" button, never as a blank map.
- **Unknown tools:** a path that isn't in the table returns `404`.
- **Limits:** only these paths are forwarded. There is no open proxy.
- **Later, if the app moves into the cluster:** the targets switch to service DNS names (`refmap-noise:4003`, …) through one env variable. No frontend change is needed.

## 7. Behaviour rules for every tool page

- **States:** each async area has four states: loading (skeleton), empty (playground empty state), error (playground alert plus retry), and ready.
- **Filters:**
  - A filter that has only one option is still shown, but pre-selected.
  - When an earlier filter in a chain changes, the filters after it reset.
- **Numbers:**
  - Formatted with `Intl.NumberFormat`, using sensible precision and units, e.g. "12.4 %" or "96.1 g CO₂eq". Raw `toFixed(6)` output is never shown.
- **Colour:**
  - Charts use the C2 palette in a fixed series order and always carry labels.
  - Map heatmaps keep the backend's own colour scale. It's data, not UI colour, and we show its legend.
- **Maps:**
  - A fixed height of 32rem on desktop and 22rem on mobile, inside the card.
  - Maps scroll-zoom only after a click, so the page scroll isn't trapped.
  - Map controls can be reached with the keyboard.
- **Wide tables** scroll inside their own box. The page never scrolls sideways.
- **No partner chrome:** no partner logos inside working pages. The partner is credited in the detail page's Access card and in "Data sources".

## 8. Blockers found while writing this spec

- **`refmap-pollution`:** the backend answers `/api/metadata` with `{"error":"ZARR store not found at None"}`. Its dataset path isn't configured, or the data isn't in `iam-eu`.
- **`refmap-climate`:** `/api/get-dates` returns an empty list, so the backend has no NetCDF data.
- **`refmap-noise`:** `noise_image_info` returns an opaque RGB screenshot with a satellite photo baked in, and the photo is of another city (it looks like Prague), pinned to Den Haag's bounds. Drawn on the map it covers the basemap like a pasted picture.
- **`refmap-wind`:** `image_info` returns a presentation slide screenshot ("City of Den Haag" title, LoD 1.2 and LoD 2.2 renders side by side, its own colour bar), not a georeferenced layer.
- Noise and wind need transparent, georeferenced rasters (heatmap only, no background) to be usable as map overlays.

**Decision (D9): ignore the missing data for now and use placeholders.** This applies to climate and pollution, and (decided 2026-10-13) to noise and wind until real rasters replace their placeholder screenshots.
- Both pages are built in full: text, inputs, layout and a placeholder visualisation.
- Their inputs are disabled.
- A neutral info alert says "Data for this tool is not available yet."
- The map or chart area shows the playground's empty state with the same message. It is not shown as an error.
- In the registry their status is `no-data`, so the catalogue card and Access card read "Status: data coming soon".
- When data arrives, flipping the status to `live` turns the page on. No other code changes.
- Filling the data is a separate task and is **not part of this plan**.

## 9. What gets removed (phase 3, after every page has replaced its partner page)

- `k8s/imafusa-frontends.yaml`: the 9 `imafusa-ui-*` Deployments and Services (NodePorts 30021–30029) are deleted from the cluster and the repo.
- The RefMap Vite dev server on `:4000` is no longer started.
- `console/` and `serve_console.py` are replaced by `app/` and `serve_app.py`. Any images still in use move to `app/public/`. The old files stay recoverable from the snapshot tag.
- `START.md`, the decks' architecture slides (when you ask), and `partner_tools_interfaces.md` are updated to the new layout.

## 10. Verification (it must pass before I report a phase as done)

1. **Routes:** every route in §4 returns 200 for every tool id, and an unknown path renders the Not found page.
2. **APIs:** every proxied endpoint that a page calls returns 2xx, except the two known blockers in §8.
3. **Layout:** headless Firefox at **360, 768, 1200 and 1440 px** on every page checks that:
   - `document.documentElement.scrollWidth ≤ innerWidth` (no sideways page scroll)
   - no text element is clipped (`scrollWidth > clientWidth` with `overflow:hidden` on text)
   - there is **no `<iframe>`** in the DOM
4. **Navigation:** home with a filter → detail → working page with inputs set → Back, then Back again. Each step restores the previous view and its query state.
5. **Accessibility:**
   - every input has a label
   - focus rings are visible when tabbing through each page
   - text contrast is ≥ 4.5:1, measured from the tokens
6. Screenshots of every page at 1440 and 360 px go into the scratchpad for your review.

## 11. Phases

| Phase | Content | Done when |
|---|---|---|
| **1. Shell + pilots** | npm install (step 0, ✅ done), the Vite project on port 5000 (the old console stops), the proxy, tokens and components, header and footer, home, the detail template, and two working pages: **`refmap-noise`** (map) and **`imafusa-affordability`** (calculator and chart) | §10 checks pass for these pages. **You review the look before phase 2.** |
| 2. Remaining tools | the other 13 working pages and the 2 metaCCAZE detail pages | §10 passes for all pages |
| 3. Switch-over | the removals in §9, `START.md`, and the app on port 5000 | the old console and partner UIs are gone and `START.md`'s check script passes |

Work happens on the git branch `custom-frontend`, with a commit at the end of each phase.

### Phase 1 in steps

Each step ends with its check passing and **one commit**, so any step can be reviewed or reverted on its own. The steps marked 👀 are **checkpoints**: I stop and wait for your OK before continuing.

| Step | What | Done when (checked by me) | You can see |
|---|---|---|---|
| 1.0 | Install npm | `npm --version` works | ✅ done (npm 12.2.0, node v26.11.1) |
| 1.1 | **Scaffold.** Create the branch `custom-frontend` and the `app/` Vite + Vue project with pinned dependencies (vue, vue-router, leaflet, plotly.js-dist-min). Stop the old console. Run the dev server on port 5000. | `npm run dev` → `:5000` returns 200 · `npm run build` succeeds | a blank IAM-IQ page on `:5000` |
| 1.2 | **API proxy.** `proxy-routes.json` with all 14 routes, Vite proxy config, and `serve_app.py` for the production build | One sample endpoint per backend returns 2xx through `:5000/api/<tool>/…`, in both dev and production. The two known no-data tools are exempt. Unknown tools → 404, backend down → 502 JSON. | `curl` output in my report |
| 1.3 | **Tokens and base styles.** Generate `tokens.css` from the playground's "PDF spec + corrections" preset and port `components.css`: type, buttons, forms, cards, tags/chips, alerts, empty state, tables, focus rings. Add a dev-only `/_styleguide` page that shows every component. | The token values match the playground's export exactly, as checked by a script diff. | 👀 **Checkpoint A:** compare `/_styleguide` with the playground side by side |
| 1.4 | **Chrome and routing.** Header (logo, IAM-IQ, "Back to hub"), EU footer, breadcrumb, vue-router with page titles (`<Page> · IAM-IQ \| IAM-CC`), and the Not found page | Routes render, titles are correct, and Back/Forward work | header and footer on every page |
| 1.5 | **Test harness.** Route checks, API checks, and headless Firefox at 360, 768, 1200 and 1440 px. The browser checks cover: no page-wide sideways scroll, no clipped text, no `<iframe>`, and Back restoring query state. Plus the screenshot script. | The harness runs green on the pages built so far. From here on, every step re-runs it. | the test output |
| 1.6 | **Tool registry and images.** `tools.js` with all 17 entries (names, suite, tags, status, endpoints, short text). `images.js` manifest, the `Placeholder` component, and `npm run images:report`. | 17 entries load. Every image resolves to a file or a placeholder. The report lists every image as `placeholder`, because no screenshots exist yet. | the report output |
| 1.7 | **Home catalogue.** Search, suite and domain chips, the card grid, filters kept in the query string | The harness passes at all four widths, and Back restores the filters | 👀 **Checkpoint B:** the home page |
| 1.8 | **Detail page template.** Generic `/tools/<id>` for all 17 tools: breadcrumb, H1, tags, screenshot slot, "What it does", "Who it's for", Access card, related tools | All 17 detail pages pass the harness. metaCCAZE has no "Open tool" button, and the no-data tools show "data coming soon". | any `/tools/<id>` |
| 1.9 | **Working page template.** `Section`, `SelectField`, the result card, and the loading, empty and error states. The markdown content loader for `src/content/<id>.md`. | A demo tool page shows all four states correctly (the states are forced in a dev-only test route) | – |
| 1.10 | **Pilot 1: `refmap-noise`.** Text from `documentation.json`, cascading inputs, the Leaflet map with an image overlay and colour bar, inputs mirrored into the URL | It shows the Denhaag LAmax and SEL heatmaps. Reload and Back restore the same view. The harness passes. | `/tools/refmap-noise/app` |
| 1.11 | **Pilot 2: `imafusa-affordability`.** Text from `docs/tools.md`, the form (country, income level, modes, trips), Calculate, result cards with 10%/15% status, and the Plotly chart | The results match the backend's `/calculate` output for the same inputs. The harness passes. | `/tools/imafusa-affordability/app` |
| 1.12 | **Wrap-up.** Run the full harness, take screenshots of every phase 1 page at 1440 and 360 px, regenerate the "ours" images for both pilots, and commit | Everything is green, and the screenshots are in the scratchpad | 👀 **Checkpoint C:** the full phase 1 review before phase 2 |

## 12. Answers (Nick, 2026-10-11)

1. **Stack:** install npm and use Vite with Vue single-file components. → D5, §3
2. **Port:** port 5000 is free for the app. → D6
3. **Admin links:** yes, remove the MinIO and Kubernetes links from the public UI. → D7
4. **Images:** use ours plus placeholders, and make them easy to change so all of them can be swapped when the official ones arrive. → D8, §4 "Images"
5. **Missing data:** ignore it for now and add placeholders where needed. → D9, §8

No open questions remain. Execution starts only when you say so.
