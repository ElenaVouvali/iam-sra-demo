import { reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

/**
 * Mirror a page's inputs into the query string, so reload and Back restore the same view (spec §4, §10.4).
 *
 *   const q = useQueryState({ city: '', time: '', modes: [] })   // defaults define keys and types
 *   q.city = 'Denhaag'   → URL becomes ?city=Denhaag (router.replace: input changes don't flood history)
 *
 * Arrays are stored as repeated keys. Values equal to their default are left out of the URL.
 * Navigating between pages (catalogue → detail → working page) still uses normal links (history push).
 */
export function useQueryState(defaults) {
  const route = useRoute()
  const router = useRouter()

  const read = (key, raw) => {
    const d = defaults[key]
    if (Array.isArray(d)) return raw == null ? [...d] : [].concat(raw).map(String)
    if (raw == null || Array.isArray(raw)) return d
    if (typeof d === 'number') { const n = Number(raw); return Number.isFinite(n) ? n : d }
    if (typeof d === 'boolean') return raw === '1' || raw === 'true'
    return String(raw)
  }

  const state = reactive(Object.fromEntries(Object.keys(defaults).map((k) => [k, read(k, route.query[k])])))

  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)
  const toQuery = () => {
    const q = { ...route.query }
    for (const k of Object.keys(defaults)) {
      const v = state[k]
      if (same(v, defaults[k]) || v === '' || v == null) delete q[k]
      else q[k] = Array.isArray(v) ? v.map(String) : typeof v === 'boolean' ? (v ? '1' : '0') : String(v)
    }
    return q
  }

  watch(() => ({ ...state }), () => {
    const q = toQuery()
    if (!same(q, route.query)) router.replace({ query: q })
  }, { deep: true })

  // Back/Forward between two query states of the same page: pull the URL back into the inputs.
  watch(() => route.query, (q) => {
    for (const k of Object.keys(defaults)) {
      const v = read(k, q[k])
      if (!same(v, state[k])) state[k] = v
    }
  })

  return state
}
