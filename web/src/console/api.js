/**
 * Thin fetch wrapper around the compiler's API.
 *
 * Every call here hits a real Python run. When the server is not up the console says so
 * plainly rather than falling back to canned data — a demo that silently shows fixtures
 * is worse than one that admits it is offline.
 */
const BASE = ''

async function req(path, options) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  health: () => req('/api/health'),
  metrics: () => req('/api/metrics'),
  schema: () => req('/api/schema'),
  vocabulary: () => req('/api/vocabulary'),
  records: ({ q = '', status = '', page = 1, size = 25 } = {}) =>
    req(
      `/api/records?${new URLSearchParams({ q, status, page, size })}`
    ),
  record: (id) => req(`/api/record/${id}`),
  delivery: (id) => req(`/api/record/${id}/delivery`),
  locator: (ref) => req(`/api/locator?ref=${encodeURIComponent(ref)}`),
  document: (id) => req(`/api/document/${encodeURIComponent(id)}`),
  sourcing: () => req('/api/sourcing'),
  gateTest: (url, manufacturer = '') =>
    req(`/api/gate/test?${new URLSearchParams({ url, manufacturer })}`),
  discovery: () => req('/api/discovery'),
  family: (id) => req(`/api/family/${encodeURIComponent(id)}`),
  contradictions: () => req('/api/contradictions'),
  review: () => req('/api/review'),
  decide: (payload) =>
    req('/api/review/decide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  resetReview: () => req('/api/review/reset', { method: 'POST' }),
  search: (q, k = 10) =>
    req(`/api/search?${new URLSearchParams({ q, k })}`),
  upload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('/api/upload', { method: 'POST', body: fd })
  },
  resetInput: () => req('/api/reset-input', { method: 'POST' }),
  downloadUrl: (fmt) => `/api/download/${fmt}`,
}

export function num(v, digits = 0) {
  if (v == null || Number.isNaN(v)) return '—'
  return Number(v).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function pct(v, digits = 1) {
  if (v == null) return '—'
  return `${Number(v).toFixed(digits)}%`
}
