import { ref, shallowRef, onBeforeUnmount } from 'vue'
import { ApiError, isAbort } from '@/api'

/**
 * One async area = one useAsync(). It owns the four states every tool page must show:
 *   'idle' (nothing asked yet) · 'loading' · 'ready' · 'empty' · 'error'
 * A new run() aborts the previous one, so fast filter changes never show stale results.
 *
 *   const result = useAsync((signal) => api('sra-assessment', '/v1/capabilities', { query: { variable: v.value }, signal }),
 *                           { isEmpty: (d) => !d?.data?.length })
 *   result.run()            // template: <AsyncState :state="result.state.value" …>
 */
export function useAsync(fn, { isEmpty = (d) => d == null || (Array.isArray(d) && d.length === 0), immediate = false } = {}) {
  const state = ref('idle')
  const data = shallowRef(null)
  const error = shallowRef(null)
  let controller = null

  async function run(...args) {
    controller?.abort()
    const mine = (controller = new AbortController())
    state.value = 'loading'
    error.value = null
    try {
      const value = await fn(mine.signal, ...args)
      if (mine !== controller) return                        // a newer run took over
      data.value = value
      state.value = isEmpty(value) ? 'empty' : 'ready'
      return value
    } catch (e) {
      if (isAbort(e) || mine !== controller) return
      error.value = e instanceof ApiError ? e : new ApiError(e?.message || 'Something went wrong.', { cause: e })
      state.value = 'error'
      console.debug('[IAM-SRA]', { status: e?.status || 0, code: e?.code || 'request_failed' })
    }
  }

  function reset() {
    controller?.abort()
    controller = null
    data.value = null
    error.value = null
    state.value = 'idle'
  }

  onBeforeUnmount(() => controller?.abort())
  if (immediate) run()
  return { state, data, error, run, reset }
}
