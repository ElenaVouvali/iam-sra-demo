#!/usr/bin/env node
/**
 * Layout + behaviour checks in a real browser (spec §10.3–10.4), driving the system Firefox via puppeteer-core.
 *
 *   npm run check                       # against http://127.0.0.1:5001
 *   BASE=http://127.0.0.1:5099 SHOTS=/tmp/shots npm run check
 *
 * For every page × width (360, 768, 1200, 1440): waits for the network to settle, then fails on
 *   - sideways page scroll (documentElement.scrollWidth > innerWidth)
 *   - clipped text (overflow hidden/clip with scrollWidth > clientWidth on a text element)
 *   - any <iframe>
 *   - an uncaught error or console.error
 * Then runs each tool's flows (click through a tool, Back restores the view). Pages and flows live in tests/pages/<id>.mjs.
 *   ONLY=sra-assessment BASE=http://127.0.0.1:5001 npm run check   # just those tools
 */
import puppeteer from 'puppeteer-core'
import { mkdirSync, readdirSync, writeFileSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:5001').replace(/\/$/, '')
const SHOTS = process.env.SHOTS || ''
const WIDTHS = (process.env.WIDTHS || '360,768,1200,1440').split(',').map(Number)
const FIREFOX = process.env.FIREFOX || '/usr/bin/firefox'

// Shared pages; each tool adds its own in tests/pages/<id>.mjs (export `pages` and `flows`), so parallel work never
// edits this file. ONLY=<id>[,<id>] checks just those tools (and skips the shared pages).
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean)
const PAGES = ONLY.length ? [] : ['/', '/?audience=cities', '/does-not-exist', '/privacy']
const FLOWS = {}
const pageDir = new URL('./pages/', import.meta.url)
for (const f of readdirSync(pageDir).filter((f) => f.endsWith('.mjs')).sort()) {
  if (ONLY.length && !ONLY.includes(f.slice(0, -4))) continue
  const m = await import(new URL(f, pageDir))
  PAGES.push(...(m.pages || []))
  Object.assign(FLOWS, m.flows || {})
}

// ---------------------------------------------------------------- helpers
const failures = []
function expect(ok, msg) { if (!ok) throw new Error(msg) }
async function go(page, path) { await page.goto(BASE + path, { waitUntil: 'networkidle0', timeout: 45000 }) }
// Browser Back. Not page.goBack(): in production Firefox restores the page from the back/forward cache, which fires
// pageshow but no load event, so goBack() waits for a load that never comes. Wait for the URL to change instead.
async function back(page) {
  const from = page.url()
  await page.evaluate(() => history.back())
  await page.waitForFunction((u) => location.href !== u, { timeout: 15000 }, from)
}
async function clickText(page, sel, text) {
  const ok = await page.$$eval(sel, (els, t) => { const el = els.find((e) => e.textContent.trim() === t); el?.click(); return !!el }, text)
  expect(ok, `no ${sel} with text "${text}"`)
}

async function layoutProblems(page) {
  return page.evaluate(() => {
    const out = []
    const de = document.documentElement
    if (de.scrollWidth > innerWidth + 1) out.push(`page scrolls sideways (${de.scrollWidth}px > ${innerWidth}px)`)
    if (document.querySelector('iframe')) out.push('contains an <iframe>')
    for (const el of document.querySelectorAll('h1,h2,h3,p,span,label,b,a,button,dd,dt,li,td,th,legend,figcaption')) {
      const cs = getComputedStyle(el)
      if (!el.textContent.trim() || cs.display === 'none' || cs.visibility === 'hidden') continue
      if (el.closest('.leaflet-container,.js-plotly-plot,.sr-only,select')) continue
      const clips = /(hidden|clip)/.test(cs.overflowX) || /(hidden|clip)/.test(cs.overflow)
      if (clips && el.scrollWidth > el.clientWidth + 1) out.push(`clipped text: <${el.tagName.toLowerCase()}> "${el.textContent.trim().slice(0, 40)}"`)
    }
    return out
  })
}

const browser = await puppeteer.launch({ browser: 'firefox', executablePath: FIREFOX, headless: true })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(`page error: ${e.message}${e.stack ? '\n' + e.stack : ''}`))
  // Firefox reports an Error argument as "JSHandle@error"; read its message so failures say what went wrong.
  page.on('console', async (m) => {
    if (m.type() !== 'error') return
    const args = await Promise.all(m.args().map((a) => a.evaluate((x) => (x instanceof Error ? `${x.name}: ${x.message}` : String(x))).catch(() => null)))
    errors.push(`console.error: ${args.filter(Boolean).join(' ') || m.text()}`)
  })
  if (SHOTS) mkdirSync(SHOTS, { recursive: true })

  for (const path of PAGES) {
    for (const w of WIDTHS) {
      errors.length = 0
      await page.setViewport({ width: w, height: 900 })
      try {
        await go(page, path)
        await new Promise((r) => setTimeout(r, 300))           // let watchers settle after network idle
        const probs = [...(await layoutProblems(page)), ...errors]
        if (SHOTS) await page.screenshot({ path: `${SHOTS}/${path.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home'}-${w}.png`, fullPage: true })
        if (probs.length) failures.push(`${path} @${w}: ${probs.join('; ')}`)
        console.log(`${probs.length ? 'FAIL' : 'ok  '} ${path} @${w}${probs.length ? `  ${probs.join('; ')}` : ''}`)
      } catch (e) {
        failures.push(`${path} @${w}: ${e.message}`)
        console.log(`FAIL ${path} @${w}  ${e.message}`)
      }
    }
  }

  for (const [name, fn] of Object.entries(FLOWS)) {
    if (process.env.FLOW && !name.includes(process.env.FLOW)) continue
    errors.length = 0
    await page.setViewport({ width: 1200, height: 900 })
    try {
      await fn(page, errors, { go, back, expect, clickText })
      if (errors.length) throw new Error(errors.join('; '))
      console.log(`ok   flow: ${name}`)
    } catch (e) {
      if (SHOTS) {
        const nameSafe = name.replace(/[^a-z0-9]+/gi, '_')
        await page.screenshot({ path: `${SHOTS}/failed-${nameSafe}.png`, fullPage: true })
        writeFileSync(`${SHOTS}/failed-${nameSafe}.html`, await page.content())
        writeFileSync(`${SHOTS}/failed-${nameSafe}.json`, JSON.stringify(await page.evaluate(() => ({
          location: location.pathname,
          resources: performance.getEntriesByType('resource').map((r) => ({name:r.name, duration:r.duration, size:r.transferSize})),
        })), null, 2))
      }
      failures.push(`flow "${name}": ${e.message}`)
      console.log(`FAIL flow: ${name}  ${e.message}`)
    }
  }
} finally {
  await browser.close()
}

console.log(failures.length ? `\n${failures.length} problem(s)` : '\nall checks passed')
process.exit(failures.length ? 1 : 0)
