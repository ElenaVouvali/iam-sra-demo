import { ref, shallowRef, computed, onBeforeUnmount } from 'vue'
import { api, ApiError } from '@/api'
import { useAsync } from './useAsync'
const TOOL = 'sra-assessment'
const pause = (signal) => new Promise((resolve, reject) => {
  const abort = () => { clearTimeout(timer); reject(new DOMException('Cancelled', 'AbortError')) }
  const timer = setTimeout(() => { signal.removeEventListener('abort', abort); resolve() }, 600)
  signal.addEventListener('abort', abort, { once: true })
  if (signal.aborted) abort()
})

/** Controller state and CSRF remain in memory; the HttpOnly cookie owns the server session. */
export function useAssessment() {
  const session = shallowRef(null)
  const capabilities = shallowRef(null)
  const expired = ref(false)
  const ended = ref(false)
  const jobStatus = ref('')
  let csrf = ''
  let active = true
  let epoch = 0
  const accept = (value, signal, mine) => {
    if (!active || signal.aborted || mine !== epoch) return
    if (!session.value || value.id !== session.value.id || value.version >= session.value.version) session.value = value
  }
  async function read(signal, mine) {
    if (!session.value) return
    try {
      const result = await api(TOOL, `/v1/sessions/${session.value.id}`, { signal })
      accept(result.session, signal, mine)
      return result.session
    } catch (error) {
      if (error.status === 410 || error.status === 404) {
        if (!signal.aborted && mine === epoch) { session.value = null; expired.value = true }
      }
      throw error
    }
  }
  async function poll(job, signal, mine) {
    while (!signal.aborted && active && mine === epoch) {
      const { job: result } = await api(TOOL, `/v1/jobs/${job}`, { signal })
      if (signal.aborted || mine !== epoch) return
      jobStatus.value = result.status
      if (['completed', 'failed', 'cancelled'].includes(result.status)) {
        await read(signal, mine)
        if (result.error) throw new ApiError(result.error.message, { code: result.error.code, retryable: result.error.retryable, status: 503 })
        return result
      }
      await pause(signal)
    }
  }
  const boot = useAsync(async (signal) => {
    const mine = ++epoch
    const data = await api(TOOL, '/v1/capabilities', { signal })
    if (!active || signal.aborted || mine !== epoch) return
    csrf = data.csrf_token
    capabilities.value = data
    const last = data.sessions.at(-1)
    if (last) {
      const result = await api(TOOL, `/v1/sessions/${last.id}`, { signal })
      accept(result.session, signal, mine)
    }
    return data
  })
  const operation = useAsync(async (signal, kind, data = {}) => {
    const mine = epoch
    const headers = { 'X-CSRF-Token': csrf }
    try {
      if (kind === 'new') {
        const result = await api(TOOL, '/v1/sessions', { method: 'POST', body: {}, headers, signal })
        if (mine === epoch && !signal.aborted) { expired.value = false; ended.value = false }
        accept(result.session, signal, mine)
      } else if (kind === 'refresh') {
        const current = await read(signal, mine)
        if (current?.busy_job) await poll(current.busy_job, signal, mine)
      } else if (kind === 'end') {
        const current = session.value
        await api(TOOL, `/v1/sessions/${current.id}`, { method: 'DELETE', headers: { ...headers, 'X-Session-Version': String(current.version) }, signal })
        if (!signal.aborted && mine === epoch) { session.value = null; ended.value = true }
      } else if (kind === 'export') {
        const response = await api(TOOL, `/v1/sessions/${session.value.id}/export`, { query: { format: data.format }, raw: true, signal })
        const blob = await response.blob()
        if (signal.aborted || mine !== epoch || !active) return
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url; link.download = `iam-sra2.${data.format}`; link.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      } else {
        // A unique request ID and expected revision prevent accidental double advancement.
        // Original input is not retained for retries: recover state, or use the server's screened retry draft.
        const current = session.value
        const body = { action: kind, data, expected_version: current.version, request_id: crypto.randomUUID() }
        const result = await api(TOOL, `/v1/sessions/${current.id}/actions`, { method: 'POST', body, headers, signal })
        accept(result.session, signal, mine)
        if (result.job_id) await poll(result.job_id, signal, mine)
      }
      return true
    } catch (error) {
      if (!signal.aborted && mine === epoch && session.value) {
        try { await read(signal, mine) } catch { /* retain the original safe error */ }
      }
      throw error
    } finally {
      if (mine === epoch && !signal.aborted) jobStatus.value = ''
    }
  }, { isEmpty: () => false })
  const working = computed(() => operation.state.value === 'loading' || Boolean(session.value?.busy_job))
  const allowed = (action) => Boolean(session.value?.allowed_actions.includes(action))
  async function initialize() {
    await boot.run()
    if (session.value?.busy_job) await operation.run('refresh')
  }
  async function act(action, data) {
    if (working.value && action !== 'reset' && action !== 'refresh') return
    return operation.run(action, data)
  }
  async function reset() {
    epoch++
    operation.reset()
    jobStatus.value = ''
    await operation.run('reset')
  }
  function retry() {
    const draft = session.value?.retry_draft
    if (draft && !session.value?.busy_job) return act(draft.action, draft.data)
    return act('refresh')
  }
  onBeforeUnmount(() => { active = false; epoch++; csrf = ''; session.value = null; capabilities.value = null })
  return { session, capabilities, expired, ended, jobStatus, boot, operation, working, allowed, initialize, act, reset, retry }
}
