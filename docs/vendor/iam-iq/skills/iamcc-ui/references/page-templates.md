# Page templates

IAM-IQ pages copy the **structure** of two live hub pages and restyle them with the playground tokens.
Background: `docs/iamcc-ui-notes.md`, "IAM-IQ internal tool UI standard" and live hub notes §7–§8.
Every page: `<div class="iq">` → `tool-header` → `<main><div class="wrap">…</div></main>` → `tool-footer`.

## Routes

Every view is a real URL, so the breadcrumb and the browser Back button always work. Routes are fixed by
`docs/frontend-spec.md` §4 (`<id>` is the tool id, e.g. `refmap-noise`, `imafusa-safety`):
- `/` tool catalogue (hub `/tools` + playground "Tools catalogue": search + filter chips + `grid3` of cards)
- `/tools/<id>` tool detail page (hub `/tools/iam-compass` template), breadcrumb "Tools / <name>"
- `/tools/<id>/app` tool working page (hub `/tools/iam-compass-demo` template), breadcrumb "Tools / <name> / Tool"
- anything else: not found = an `empty` state with a link home

Page titles (decision D3): `<Page> · IAM-IQ | IAM-CC`; the home page is `IAM-IQ | IAM-CC`.
"Back to hub" goes to `https://hub.iamcc.eu/tools` in a new tab (there is no IAM-IQ hub page yet).

Filter and input state lives in the query string (`?altitude=50&op=cruise`) so Back restores it.
"Open tool" navigates in the same tab; only links that leave IAM-IQ open a new tab (`target="_blank" rel="noopener"`).
No `<iframe>` anywhere, and no partner UI code or partner back buttons: IAM-IQ talks straight to the partner backends.

## Tool working page (hub `/tools/iam-compass-demo`)

`assets/starter.html` is a complete, rendered example of this page. Start from it.

```
crumbs: Tools / <Suite> / <Tool>
tool-card
├── strip: icon + <h1 class="t-card">Tool name</h1>
└── body: stack of tsec sections, in this order
    1 Definition   2 Rationale   3 Methodology   4 Data sources   5 How to use (numbered)
    6 Inputs: the tool's filters/parameters, built from its backend endpoints
    7 Run: one primary button (div.run)
    8 Results: div.results of div.stat cards; numbers formatted for people
    9 Visualisation: tsec.full (no icon tile), chart-card or .map at full card width
   10 References
```
- Leave out any section the tool has no content for. Never fill one with placeholder text.
- Cascading filters (e.g. altitude → operation → payload → run): later selects stay `disabled` with
  "Choose <previous> first" until the previous one is set.
- Results before the first run: an `empty` state, not instruction text. After the run: `Intl.NumberFormat`
  with sensible precision plus units, never `toFixed(6)`.
- Result images that partner UIs let you drag around become a fixed, sortable grid (keyboard-usable).

## Tool detail page (hub `/tools/iam-compass`)

```html
<nav class="crumbs" aria-label="Breadcrumb"><a href="/">Tools</a><span class="sep" aria-hidden="true">/</span><span aria-current="page">Noise assessment</span></nav>
<div class="detail-head">
  <h1 class="t-title">Noise assessment</h1>
  <p class="lead">Measure drone noise at ground level from recorded test flights.</p>   <!-- ≤ 90 chars, verb-first -->
  <div class="tags"><span class="badge">Cities</span><span class="badge">Regulators</span></div>
</div>
<div class="detail">
  <div>                                                         <!-- main column -->
    <div class="shot"><img src="…" alt="Noise assessment results screen"></div>   <!-- 2:1 -->
    <h2 class="t-section">What it does</h2>
    <ul class="bullets"><li>…</li><li>…</li><li>…</li></ul>  <!-- exactly 3 -->
    <h2 class="t-section">Who it's for</h2>
    <p class="t-body muted">One sentence.</p>
  </div>
  <aside class="sidebar">                                       <!-- 22.5rem; stacks below 62rem -->
    <section class="card"><h2 class="t-card">Access</h2>
      <a class="btn primary block" href="/tools/imafusa-noise/app">Open tool<svg class="ico ico-btn" aria-hidden="true"><use href="icons.svg#i-ext"/></svg></a>   <!-- label, then the external-link icon -->
      <dl class="facts"><dt>Lead partner</dt><dd>USAL</dd><dt>Suite</dt><dd>ImAFUSA</dd><dt>Status</dt><dd>K8s active</dd>
        <dt>Data</dt><dd><code>s3://iam-eu/environmental/imafusa/</code></dd></dl></section>
    <section class="card"><h2 class="t-card">Related</h2> …lrow list… </section>
    <section class="card"><h2 class="t-card">Learn it</h2> …only if there is material… </section>
  </aside>
</div>
```

## Responsive rules

- Works from 360px to 1440px with **no horizontal page scroll**. Check every page at 360, 768, 1200 and 1440px.
- Grid: ≥ 75rem → 12 columns, 4rem margin, 1.5rem gutter; 48–75rem → 8 / 2.5rem / 1.25rem; < 48rem → 4 / 1.25rem / 1rem
  (handled by `.wrap` and the `iq` container queries).
- Boxes never have a fixed height around text; flex/grid children get `min-width:0`; long strings
  (S3 paths, URLs, JSON) use `overflow-wrap:anywhere`; wide tables scroll inside `.table-scroll`.
