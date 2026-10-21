// Numbers for people (spec §7): Intl.NumberFormat with sensible precision and a unit. Never toFixed(6).
const LOCALE = 'en-GB'
const cache = new Map()
const nf = (opts) => {
  const key = JSON.stringify(opts)
  if (!cache.has(key)) cache.set(key, new Intl.NumberFormat(LOCALE, opts))
  return cache.get(key)
}

/** Pick 0–2 decimals from the magnitude: 1,234 · 56.7 · 0.42 · 0.0031 → 0.0031 (2 significant). */
export function num(value, { digits, unit } = {}) {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return '–'
  const v = Number(value)
  const a = Math.abs(v)
  const opts = digits !== undefined
    ? { minimumFractionDigits: digits, maximumFractionDigits: digits }
    : a >= 100 ? { maximumFractionDigits: 0 } : a >= 1 ? { maximumFractionDigits: 1 } : a === 0 ? {} : { maximumSignificantDigits: 2 }
  const s = nf(opts).format(v)
  return unit ? `${s} ${unit}` : s
}

/** 0.124 → "12.4 %" when ratio=true; 12.4 → "12.4 %" otherwise. */
export const pct = (value, { ratio = false, digits = 1 } = {}) =>
  value == null || Number.isNaN(Number(value)) ? '–' : `${nf({ maximumFractionDigits: digits }).format(ratio ? value * 100 : value)} %`

/** Labels from backend keys: "flights_per_hour" → "Flights per hour" (sentence case). */
export const label = (key) => {
  const s = String(key).replace(/[_-]+/g, ' ').trim()
  return s.charAt(0).toUpperCase() + s.slice(1)
}
