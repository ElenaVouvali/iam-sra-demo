// The only way pages talk to backends: same-origin /api/<tool>/<backend route>, forwarded by the proxy
// (proxy-routes.json). Never put a cluster IP, NodePort or partner URL in a component.

export class ApiError extends Error {
  constructor(message, { tool, status = 0, path = '', cause, code, retryable } = {}) {
    super(message)
    this.name = 'ApiError'
    Object.assign(this, { tool, status, path, cause, code, retryable })
  }
  /** Short text for the error alert. The details stay in the console. */
  get userMessage() {
    if (this.code) return this.message
    if (this.status === 0) return 'The request did not complete. Check your connection and try again.'
    if (this.status === 502 || this.status === 504) return 'This tool’s service is not responding right now. Try again in a minute.'
    if (this.status === 404) return 'The tool could not find data for this selection.'
    if (this.status >= 500) return 'The tool’s service hit an error. Try again, or change the selection.'
    return this.message
  }
}

/** Build a same-origin URL. Arrays become repeated keys (?mode=a&mode=b), which Flask reads with getlist(). */
export function apiUrl(tool, path, query) {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(query || {})) {
    if (v === undefined || v === null || v === '') continue
    for (const item of Array.isArray(v) ? v : [v]) qs.append(k, String(item))
  }
  const s = qs.toString()
  return `/api/${tool}${path.startsWith('/') ? path : `/${path}`}${s ? `?${s}` : ''}`
}

/**
 * fetch + timeout + JSON + uniform errors.
 *   await api('sra-assessment', '/v1/capabilities')
 *   await api('sra-assessment', '/v1/sessions', { method: 'POST', body: {...}, signal })
 * Throws ApiError for network errors, timeouts, non-2xx answers and `{"error": "..."}` payloads
 * (several partner backends report failures that way, sometimes with a 200).
 */
export async function api(tool, path, { method = 'GET', query, body, signal, timeoutMs = 30000, raw = false, headers = {} } = {}) {
  const url = apiUrl(tool, path, query)
  const timeout = AbortSignal.timeout(timeoutMs)
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout
  let res
  try {
    res = await fetch(url, {
      method,
      signal: combined,
      credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    if (signal?.aborted) throw e                                  // superseded by a newer request: let the caller ignore it
    const timedOut = timeout.aborted
    throw new ApiError(timedOut ? 'The request timed out.' : 'Network error.', { tool, status: timedOut ? 504 : 0, path, cause: e })
  }
  if (raw && res.ok) return res
  const text = await res.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { /* not JSON */ }
  if (!res.ok) throw new ApiError(data?.error?.message || (typeof data?.error === 'string' ? data.error : `HTTP ${res.status}`),
    { tool, status: res.status, path, code: data?.error?.code, retryable: data?.error?.retryable })
  if (data === null && text) throw new ApiError('The service sent an unexpected response.', { tool, status: res.status, path })
  if (data && typeof data === 'object' && !Array.isArray(data) && typeof data.error === 'string' && data.error)
    throw new ApiError(data.error, { tool, status: 422, path })
  return data
}

/** True when an error is just an aborted, superseded request (do not show it). */
export const isAbort = (e) => e?.name === 'AbortError'
