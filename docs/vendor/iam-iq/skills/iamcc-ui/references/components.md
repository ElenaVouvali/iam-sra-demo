# Component markup

Copy-ready markup for every playground component. Class names come from `assets/components.css`
(generated); page-level classes (`crumbs`, `detail`, `tool-card`, `tsec`, `stat`, `facts`…) come from
`assets/layout.css`. Everything must sit inside `<div class="iq">`. Icons: `<svg class="ico"><use href="icons.svg#ID"/></svg>`,
IDs: `i-info i-check i-warn i-err i-x i-search i-ext i-file i-plus i-share i-settings i-play`, plus `iamcc-logo` and `iamcc-mark`.

## Contents
- Chrome: tool header, top nav, tool footer
- Typography and text
- Buttons
- Forms (text, select, textarea, checkbox, radio, switch, search, validation)
- Content: badges, filter chips, cards, data table, list rows, pagination
- Feedback: alerts, empty state, skeleton, progress, modal, tooltip
- Charts and maps

---

## Chrome (Mode B: IAM-IQ on its own domain)

```html
<header class="tool-header">
  <svg class="logo" viewBox="0 0 1781.34 333.04" role="img" aria-label="IAM-CC"><use href="icons.svg#iamcc-logo"/></svg>
  <span class="divider" aria-hidden="true"></span>
  <span class="name">IAM-IQ</span>
  <a class="back" href="https://hub.iamcc.eu/tools" target="_blank" rel="noopener">Back to hub</a>
</header>
```
3.75rem tall, hairline Azure 100 bottom border. Below a 30rem container the divider and "IAM-IQ" hide on their own.

```html
<footer class="tool-footer">
  <div class="eu"><img src="eu-emblem.svg" alt="Funded by the European Union"><p>Funded by the European Union under Grant Agreement No 101271620. Views and opinions expressed are those of the author(s) only and do not necessarily reflect those of the European Union or the granting authority. Neither the European Union nor the granting authority can be held responsible for them.</p></div>
  <div class="credit">Developed by ICCS · <a href="/privacy">Privacy</a></div>
</footer>
```
The EU statement is mandatory and verbatim. Keep the privacy link (the PDF mockup forgot it).

Top nav (hub style), not in the app header yet:
```html
<nav class="topnav" aria-label="Main"><ul>
  <li><a href="/">Home</a></li>
  <li><a href="/tools" aria-current="page">Tools</a></li>
  <li><a href="/resources">Resources</a></li>
</ul></nav>
```
Links are Blue Slate, `fs-card` 500. The current page (`aria-current="page"`) is Dark Azure 600 with a coral dot
centred under it; that dot is the only coral in the nav. Classes are in `layout.css`. On narrow screens it scrolls sideways inside itself.

## Typography

| Class | Use | Size / weight |
|---|---|---|
| `t-title` | page H1 | 2rem · 700 |
| `t-section` | section heading | 1.5rem · 600 |
| `t-card` | card title, tool-section heading | 1.125rem · 600 |
| `t-body` | body | 0.9375rem · 400 |
| `t-label` | UI labels | 0.875rem · 500 |
| `t-small` | meta | 0.8125rem |
| `t-caption` | captions, axes (minimum size) | 0.75rem |
| `muted` | secondary text (Blue Slate) | |

Sentence case everywhere: headings, buttons, labels, tabs.

## Buttons

```html
<button class="btn primary">Save scenario</button>          <!-- Dark Azure: the default action -->
<button class="btn accent lg">Run assessment</button>       <!-- coral: at most ONE per screen -->
<button class="btn secondary">Download</button>             <!-- outline; Download has no icon (C1) -->
<button class="btn ghost">Reset filters</button>
<button class="btn danger">Delete scenario</button>
<button class="btn primary" disabled>Export results</button>
<button class="btn secondary"><svg class="ico ico-btn"><use href="icons.svg#i-share"/></svg>Share results</button>
<span class="tip-wrap"><button class="btn ghost icon-only" aria-label="Settings"><svg class="ico ico-btn"><use href="icons.svg#i-settings"/></svg></button><span class="tip" role="tooltip">Settings</span></span>
```
Sizes: add `lg` (3rem) or `sm` (2.125rem); default is 2.5rem. Labels are verb-first, one to three words.
Focus rings are built in (coral ring on azure buttons, slate ring on coral/red ones). Never remove them.

## Forms

```html
<div class="field">
  <label for="city">City</label>
  <input id="city" class="input" placeholder="Porto">           <!-- placeholder = an example, never the label -->
  <span class="help">The municipality the scenario applies to.</span>
</div>

<div class="field">
  <label for="flights">Flights per day</label>
  <input id="flights" class="input" inputmode="numeric" aria-describedby="flights-err" aria-invalid="true">
  <span class="err" id="flights-err"><svg class="ico"><use href="icons.svg#i-err"/></svg>Enter a whole number, for example 120.</span>
</div>

<div class="field"><label for="scn">Scenario <span class="opt">(optional)</span></label>
  <select id="scn" class="input"><option>Baseline 2026</option></select></div>
<div class="field"><label for="notes">Notes <span class="opt">(optional)</span></label>
  <textarea id="notes" class="input"></textarea></div>

<label class="check"><input type="checkbox" checked>Show buildings</label>
<label class="check"><input type="radio" name="layer" checked>Noise</label>
<label class="switch"><input type="checkbox" role="switch">Night mode</label>
<label class="search"><svg class="ico"><use href="icons.svg#i-search"/></svg><input class="input" type="search" placeholder="Search tools" aria-label="Search tools"></label>
```
- Group fields with `<div class="fields4">` (1 → 2 → 4 columns by container width).
- Validate on **blur**: set `aria-invalid="true"` and un-hide the `.err` (`hidden` class) when the value is wrong; clear it on input once it's valid.
- Error text says what to do ("Enter a whole number, for example 120"), never just "Invalid".
- Selected states use Dark Azure, never coral.
- Table-cell inputs still get a label: `<label class="sr-only" for="…">Road, 55–59 dB</label>`.

## Content

```html
<span class="badge">Cities</span>            <!-- audience tags: one neutral style -->
<span class="badge new">New</span>  <span class="badge top">Most used</span>  <span class="badge type">Guide</span>

<div class="row" data-chipgroup>              <!-- single-select filter; toggle aria-pressed in JS -->
  <button class="chipf" aria-pressed="true">All</button>
  <button class="chipf" aria-pressed="false">RefMap</button>
</div>

<article class="card">
  <div class="img"><svg viewBox="0 0 333 333"><use href="icons.svg#iamcc-mark"/></svg></div>   <!-- 2.5:1 card image slot -->
  <h3 class="t-card">Noise assessment</h3>
  <p class="t-small muted">Drone noise at ground level from recorded flights.</p>
  <div class="tags"><span class="badge">ImAFUSA</span></div>
  <div class="actions"><a class="btn secondary sm" href="/tools/imafusa-noise/app">Open tool</a></div>
</article>
<article class="card featured">…</article>    <!-- featured = 2px coral border, never a coral fill -->

<div class="table-scroll"><table class="data">
  <thead><tr><th>Scenario</th><th class="num">Flights / day</th><th class="num">Lden (dB)</th></tr></thead>
  <tbody><tr><td>Baseline 2026</td><td class="num">120</td><td class="num">42.1</td></tr></tbody>
</table></div>
```
Tables: no vertical lines, numbers right-aligned with `num` (tabular figures), wide tables scroll inside `.table-scroll`.

```html
<div class="lrow"><span class="th"><svg class="ico ico-btn"><use href="icons.svg#i-file"/></svg></span>
  <div class="tx"><b>SUMP integration guide</b><span class="t-small muted">Guide · PDF</span></div>
  <button class="btn secondary sm">Download</button></div>
<nav class="pager" aria-label="Pagination"><button aria-current="page">1</button><button>2</button></nav>
```

## Feedback and states

```html
<div class="alert info" role="status"><svg class="ico"><use href="icons.svg#i-info"/></svg>
  <div><b>Heads up</b><p>Results use the 2025 city dataset.</p></div>
  <button class="x" aria-label="Dismiss"><svg class="ico"><use href="icons.svg#i-x"/></svg></button></div>
<!-- success → i-check · warning → i-warn · danger → i-err with role="alert" -->

<div class="empty"><svg class="m" viewBox="0 0 333 333" aria-hidden="true"><use href="icons.svg#iamcc-mark"/></svg>
  <h3 class="t-card">No scenarios yet</h3><p class="t-small muted">Create one to see its impact on your city.</p>
  <button class="btn primary"><svg class="ico ico-btn"><use href="icons.svg#i-plus"/></svg>New scenario</button></div>

<div class="skel" aria-busy="true" aria-label="Loading"><i style="width:55%"></i><i style="width:85%"></i><i style="width:70%"></i></div>

<div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="40"><i style="width:40%"></i></div>

<dialog class="modal" aria-labelledby="m-title">
  <h3 class="t-card" id="m-title">Delete this scenario?</h3>
  <p class="t-body muted">"Medical logistics" and its results will be removed. This can't be undone.</p>
  <div class="row"><button class="btn secondary" data-close>Keep scenario</button><button class="btn danger" data-close>Delete scenario</button></div>
</dialog>
```
- Say what happened, then what to do. Alerts never use coral. Status colour always comes with an icon and a text label; alert text stays Dark Azure.
- Every async area has four states: loading (`skel`), empty (`empty`), error (`alert danger` + a retry button), ready.

## Charts and maps

```html
<div class="chart-card">
  <div class="ctitle">Daily drone flights per 10 km²</div><div class="csub">2026 to 2030, by city</div>
  <div class="legend"><span><i style="background:var(--s1)"></i>Porto</span><span><i style="background:var(--s2)"></i>Madrid</span></div>
  <div class="chart"><!-- Plotly / SVG --></div>
</div>
```
- Categorical series use `--s1` … `--s5` **in that order**, never cycled. S3 and S4 are below 3:1 on white, so always label them (legend or direct labels).
- One y-axis per chart. Legend for 2+ series; direct labels on up to four. Offer a table view.
- Axis text: `--fs-caption`, Blue Slate; gridlines Azure 100.
- Ramps (build with OKLab mixing, as the playground does): sequential `--c-a50 → --c-azure`; intensity (noise, risk) `coral100 → coral → coral700`; diverging `azure · slate · light · coral · coral700`.
- Maps (Leaflet) sit in `.map` inside the visualisation section, full card width.
