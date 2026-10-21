# Patterns

Each pattern names the template file (under `assets/app-template/`) that implements it. Copy from the file rather
than retyping: the files are the reference.

## Contents
- Project layout
- Calling a backend
- Async states
- Filters in the URL and cascading selects
- Maps
- Charts
- Routing and titles
- Numbers and text
- Production server
- Backend gotchas

## Project layout

Matches spec §3. `src/main.js` imports the iamcc-ui CSS (tokens → components → layout) and mounts `App.vue`, which
wraps every route in `components/AppChrome.vue` (the `.iq` container, Mode B header, EU footer, skip link).
Pages: `pages/Home.vue`, `pages/ToolDetail.vue`, `pages/ToolApp.vue` (breadcrumb + the tool's own page),
`pages/NotFound.vue`. Tool pages: `tools/<id>.vue`, found by `toolPages.js` with `import.meta.glob` so each is its own
lazy chunk (Leaflet and Plotly only download on pages that use them).

## Calling a backend (`src/api.js`)

```js
import { api, apiUrl } from '@/api'
const data = await api('imafusa-safety', '/plot-data', { query: { variable }, signal })        // GET
const res  = await api('imafusa-affordability', '/calculate', { method: 'POST', body, signal })  // POST JSON
const img  = apiUrl('refmap-noise', '/scale-argb.png')                                          // <img :src>
```
- The route is the backend's own route from `endpoints.md` (RefMap routes often start with `/api/`, so the browser
  path becomes `/api/refmap-noise/api/noise_cities`; that's correct).
- Arrays in `query` become repeated keys, which Flask reads with `request.args.getlist`.
- Throws `ApiError` (with `status`, `tool`, `userMessage`) for network errors, 30 s timeouts, non-2xx answers and
  `{"error": "..."}` bodies, which several partner backends return, sometimes with a 200.
- `raw: true` returns the `Response` for non-JSON payloads.

## Async states (`composables/useAsync.js`, `components/AsyncState.vue`)

```js
const result = useAsync((signal) => api(TOOL, '/calculate', { method: 'POST', body: …, signal }),
                        { isEmpty: (d) => !Object.keys(d?.user_affordability || {}).length })
// template
<AsyncState :state="result.state.value" :error="result.error.value" @retry="result.run()">…ready content…</AsyncState>
```
States: `idle` (nothing asked yet: shows the idle empty state), `loading` (skeleton), `ready`, `empty`, `error`
(alert + "Try again"). `run()` aborts the previous request; `immediate: true` runs on mount (metadata calls).

## Filters in the URL and cascading selects

- `composables/useQueryState.js`: `const q = useQueryState({ city: '', modes: [], trips: 20 })`. Defaults define keys and
  types; arrays are repeated keys; default values stay out of the URL; Back/Forward write back into `q`.
- `components/SelectField.vue`: labelled select; one option → pre-selected; no options → disabled with a
  "Choose X first" hint; drops a value that no longer exists. Mount it only once its options have loaded (inside the
  ready slot of `AsyncState`), or it drops URL-restored values.
- Cascades (`tools/refmap-noise.vue`): load all combinations once, derive each level's options with `computed`, and
  reset the later levels from the select's `@update:model-value` handler (a user change), **not** from a watcher.
  A complete selection that arrives from the URL runs straight away; one the user is editing waits for the run button.

## Maps (`components/MapView.vue`)

Leaflet directly, OpenStreetMap standard tiles as the basemap. Not CARTO: its tiles now need an API key and are
watermarked without one. OSM's tile server is keyless but meant for light use; the long-term solution is self-hosted
Protomaps (one `.pmtiles` file on our own storage, e.g. MinIO). `overlay = { url, bounds: [[south, west], [north, east]], opacity }` → image
overlay with the view fitted to it. Scroll-zoom turns on after a click or focus, so the page scroll isn't trapped.
32rem tall (22rem in narrow containers). Backend heatmaps keep their own colour scale: show its legend (the noise
page draws `/scale-argb.png` as a bar with the range for the chosen metric).

## Charts (`components/PlotlyChart.vue`)

Lazy-loads `plotly.js-dist-min`, themes it from the iamcc-ui CSS variables at runtime (font, `--s1…--s5` in order,
Blue Slate axes, Azure 100 grid), and resizes with its container. Pass traces without colours. At most 5 series;
always give a `label` and a table view or result cards as the text alternative.

## Routing and titles (`src/router.js`)

`/` · `/tools/:id` · `/tools/:id/app` · catch-all Not found (spec §4). Guards send unknown ids, detail-only tools and
tools without a page file to Not found. Titles: `<Page> · IAM-IQ | IAM-CC`, home `IAM-IQ | IAM-CC` (D3). Back restores
the scroll position.

## Numbers and text (`src/format.js`)

`num(v, { unit, digits })`, `pct(v, { ratio })` with `Intl.NumberFormat`; never `toFixed(6)`. `label('flights_per_hour')`
→ "Flights per hour" for backend keys. Tool text comes from the partner docs (RefMap `src/data/documentation.json`,
ImAFUSA `docs/tools.md`), edited only for sentence case and length (spec §4).

## Production server (`serve_app.py`)

Standard library only, port 5000. Serves `dist/` with an SPA fallback for page paths; missing files (`/assets/…`, any
path with an extension) are a JSON 404. Forwards `/api/<tool>/…` with GET/POST/HEAD, query and body unchanged, 30 s
timeout, backend status and content type kept; 502 JSON `{error, tool}` when a backend is unreachable, 404 JSON for
unknown tools, 405 for other methods. Env: `PORT`, `HOST`, `K8S_HOST`, `IAMIQ_IN_CLUSTER=1`.

## Backend gotchas

Found while building the template (2026-10-12). Add to this list when you find more.

| Tool | Gotcha |
|---|---|
| `refmap-noise` | `bounds` is `{'lat-min','lat-max','lon-min','lon-max'}`; Leaflet wants `[[lat-min, lon-min], [lat-max, lon-max]]`. `image_data` is base64 PNG (or `null` when the folder is missing): use `data:image/png;base64,…`. |
| `imafusa-affordability` | `income_level` is `low` / `middle` / `high`. `income_range` is only `[min, max]`; the distributions use 200 € steps from `max(200, floor(min/200)*200)` to `max`. Rebuild that axis exactly. `POST /calculate` returns **500 `TypeError: Object of type int64 is not JSON serializable`** (`Price_Affordability/app.py:117`: `[min_income, max_income]` contains pandas `int64`). Backend bug, not ours: show the error state and tell Nick. |
| `imafusa-travel-time`, `imafusa-pjr` | One backend (Accessibility, NodePort 30017) behind two tool ids; PJR routes start with `/pjr/`. |
| `imafusa-social` | `/averages`, `/question_data`, `/individual_scores` return **500 `KeyError: 'paticipant_name'`** (the code expects a misspelled column). Backend bug, not ours: show the error state and tell Nick. |
| `refmap-pollution` | `/api/metadata` → 500 `ZARR store not found at None` (spec §8, D9: no-data placeholder). |
| `refmap-climate` | `/api/get-dates` → `{"dates": []}` (spec §8, D9: no-data placeholder). |
| several | Errors come back as `{"error": "..."}`, sometimes with 200; Flask crashes come back as an HTML 500 page. `api()` turns both into `ApiError`. |
