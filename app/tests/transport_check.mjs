// Run against a running frontend proxy. All content is explicitly synthetic.
import assert from 'node:assert/strict'
const base = process.env.BASE || 'http://127.0.0.1:5001'
const prefix = base + '/api/sra-assessment/v1'
const bootstrap = await fetch(prefix + '/capabilities')
assert.equal(bootstrap.status, 200)
const cap = await bootstrap.json()
const cookie = bootstrap.headers.get('set-cookie').split(';')[0]
assert.match(bootstrap.headers.get('set-cookie'), /HttpOnly/)
assert.match(bootstrap.headers.get('set-cookie'), /SameSite=Strict/)
const headers = { Cookie: cookie, 'X-CSRF-Token': cap.csrf_token, 'Content-Type': 'application/json', Origin: base }
assert.equal((await fetch(prefix + '/sessions', { method: 'POST', headers: { Cookie: cookie, 'Content-Type': 'application/json' }, body: '{}' })).status, 403)
let response = await fetch(prefix + '/sessions', { method: 'POST', headers, body: '{}' })
assert.equal(response.status, 201)
let view = (await response.json()).session
const path = prefix + '/sessions/' + view.id
async function act(action, data = {}) {
  const body = JSON.stringify({ action, data, expected_version: view.version, request_id: crypto.randomUUID() })
  const response = await fetch(path + '/actions', { method: 'POST', headers, body })
  assert.equal(response.status, 202)
  const result = await response.json()
  // Same receipt, same job; no double advancement through a proxy retry.
  const duplicate = await fetch(path + '/actions', { method: 'POST', headers, body })
  assert.equal((await duplicate.json()).job_id, result.job_id)
  const end = Date.now() + 15000
  while (Date.now() < end) {
    const r = await fetch(prefix + '/jobs/' + result.job_id, { headers: { Cookie: cookie } })
    const job = (await r.json()).job
    if (job.status === 'completed') break
    assert.notEqual(job.status, 'failed')
    await new Promise((resolve) => setTimeout(resolve, 80))
  }
  view = (await (await fetch(path, { headers: { Cookie: cookie } })).json()).session
  assert.equal(view.busy_job, null)
}
await act('set_context', { perspective: 'personal', role: 'citizen', city: 'madrid' })
await act('finish'); await act('confirm_general'); await act('decline_scenario'); await act('confirm_final')
assert.equal((await fetch(path, { headers: { Cookie: '' } })).status, 403)
for (const format of ['json', 'jsonl']) {
  const r = await fetch(path + '/export?format=' + format, { headers: { Cookie: cookie } })
  assert.equal(r.status, 200); assert.equal(r.headers.get('cache-control'), 'no-store')
  assert.match(r.headers.get('content-disposition'), /attachment/)
  const text = await r.text()
  assert.equal(JSON.parse(text).export_profile, 'browser_evidence')
  if (format === 'jsonl') assert.equal(text.trim().split('\n').length, 1)
}
assert.equal((await fetch(path, { method: 'DELETE', headers: { ...headers, 'X-Session-Version': String(view.version) } })).status, 204)
assert.equal((await fetch(path, { headers: { Cookie: cookie } })).status, 410)
assert.equal((await fetch(base + '/api/unknown/v1/health')).status, 404)
assert.equal((await fetch(base + '/api/sra-assessment-other/v1/health')).status, 404)
assert.equal((await fetch(base + '/tools/sra-assessment/app')).status, 200)
assert.equal((await fetch(base + '/assets/missing.js')).status, 404)
console.log('PASS: proxy prefix, cookies/CSRF, duplicate jobs, ownership, JSON/JSONL, DELETE, status forwarding and deep links')
