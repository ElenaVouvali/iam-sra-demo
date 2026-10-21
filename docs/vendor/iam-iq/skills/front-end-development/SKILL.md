---
name: front-end-development
description: 'How to build the IAM-IQ web app: Vite + Vue 3 (script setup) + vue-router + Leaflet + Plotly, connected to the 13 RefMap and ImAFUSA backends through the same-origin /api/{tool} proxy. Ships a ready app template (proxy config, Vite config, serve_app.py, API wrapper, state and query-string composables, map and chart components, pages, two pilot tool pages) and a generated reference of every backend endpoint with its parameters. Use it whenever the task touches the IAM-IQ frontend in any way: scaffolding app/, adding or porting a tool page, calling a partner backend, wiring the proxy, routing, filters in the URL, loading/empty/error states, maps, charts, the production server, or debugging why a tool page shows no data, even if the user only says "add the safety tool", "connect it to the backend" or "build phase 1". Uses the iamcc-ui skill for the look.'
---

# Front-end development for IAM-IQ

IAM-IQ is replacing the partner UIs (RefMap, ImAFUSA) with one Vue app that calls the partner **backends** directly
and renders every tool as a full page. The plan is approved and fixed in `docs/frontend-spec.md`: read the section
you're working on before writing code, and don't change decisions it records (D1–D9). This skill turns that plan
into working code patterns.

**Two skills, two jobs.** This skill = how it works (Vue, data, backend, routing, servers). The **iamcc-ui** skill =
how it looks (tokens, components, page structure, UI rules). Load iamcc-ui too for anything visible.

## What's in the skill

| Path | What |
|---|---|
| `assets/app-template/` | the `app/` folder from spec §3, ready to copy: `package.json` (pinned), `vite.config.js`, `proxy-routes.json`, `serve_app.py`, `index.html`, `src/` (api, composables, router, registry, components, pages, two pilot tools), `tests/browser_check.mjs` |
| `references/endpoints.md` | **generated**: every backend route (60 in 13 backends), method, query params, JSON body keys, response keys, source line, and the partner UI file that shows how it's used |
| `references/patterns.md` | the Vue and backend patterns, which template file shows each, and the backend gotchas found so far |
| `scripts/inventory_endpoints.py` | regenerates `endpoints.md` from the partner sources; `--probe http://localhost:5000` (through the app) or `--probe-nodeports 192.168.49.2` checks the parameter-free GET routes answer |

## Start the app (spec phase 1, step 1.1)

Work on the branch `custom-frontend` (spec §11). Then:

```bash
cp -r .claude/skills/front-end-development/assets/app-template app
mkdir -p app/src/styles app/public/brand
cp .claude/skills/iamcc-ui/assets/{tokens,components,layout}.css app/src/styles/
cp .claude/skills/iamcc-ui/assets/{icons,eu-emblem}.svg app/public/brand/
cd app && npm install && npm run dev        # http://localhost:5000 (stop the old console first: it owns :5000)
npm run build && npm run serve              # production: serve_app.py on :5000
```
Backends must be up (`minikube status`, `kubectl get pods`); `docs/START.md` has the full start order.

## Add a tool page (the job you'll do most)

1. **Registry**: add/complete the entry in `src/tools.js` (fields documented there; text from spec §5 and the
   partner docs, sentence case). `id` is everything: route `/tools/<id>/app`, proxy prefix `/api/<id>`, file `src/tools/<id>.vue`.
2. **Proxy**: check `<id>` is in `proxy-routes.json` (all 14 are). Never add a host, IP or port anywhere else.
3. **Learn the backend**: read the tool's section in `references/endpoints.md`, then the partner UI file it names, for
   the call order, the cascade between filters and how results are drawn. That behaviour is what you reproduce; the
   partner's markup and CSS are not.
4. **Write `src/tools/<id>.vue`** from the closer pilot: `tools/refmap-noise.vue` (cascading filters from one call →
   map overlay) or `tools/imafusa-affordability.vue` (form → POST → result cards + chart). Use `api()`, `useAsync()`,
   `useQueryState()`, `AsyncState`, `SelectField`, `MapView`, `PlotlyChart`; see `references/patterns.md`.
5. **Check it**: the API calls answer through the proxy (`curl localhost:5000/api/<id>/<route>` or the probe script),
   reload and Back restore the view, and the iamcc-ui done checklist passes. Add the page and a flow to
   `tests/browser_check.mjs` so it's covered from then on.

## Rules for connecting to backends

- The browser only talks to its own origin: `api(tool, route, …)` → `/api/<tool><route>`. No CORS, no cluster IPs,
  no partner URLs in components. Images from a backend go through `apiUrl()` too.
- `proxy-routes.json` is the single table for both the Vite dev proxy and `serve_app.py`, so dev and production can't
  drift. Moving the app into the cluster later is `IAMIQ_IN_CLUSTER=1`, not a code change.
- Every async area has the four states (loading, empty, error with "Try again", ready) via `useAsync` + `AsyncState`.
  A down backend shows the error state, never a blank map or a spinner forever. Errors from a new request supersede
  older ones (`useAsync` aborts the previous run).
- Inputs live in the query string (`useQueryState`); input changes use `router.replace`, page changes are links.
  Reset downstream filters only on **user** changes, never in a watcher, or Back wipes restored values.
- Don't change partner backends (spec §1, out of scope). If one is broken, show the state honestly, note it in
  `references/patterns.md` "Backend gotchas", and tell Nick.
- Tools without data (`refmap-climate`, `refmap-pollution`, status `no-data`, decision D9): build the full page with
  inputs disabled, an info alert "Data for this tool is not available yet." and an empty visualisation.

## Template status

`npm run build` passes and `serve_app.py` was tested against the live cluster: SPA deep links, JSON 404 for unknown
tools and missing assets, 405 for other methods, status and body pass-through, and 19 of 23 probed endpoints answering
(the 4 failures are backend bugs, see patterns.md). Not yet confirmed in a browser: the two pilot pages loading their
data and the Back flow; `tests/browser_check.mjs` is written but has not been run. Verify those before relying on them.
