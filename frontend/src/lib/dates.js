const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

// Storage/wire format is plain ISO (yyyy-mm-dd) end to end now — Postgres's
// DateField, DRF's serializer, and the native <input type="date"> all speak
// ISO natively, so v1's toIsoDate/fromIsoDate round-tripping (needed because
// Sheets cells drifted between dd/mm/yyyy and Sheets' own short format) isn't
// needed any more. Only a read-only display formatter remains, matching the
// "28-Jul-26" style staff are used to from Sheets.
export function formatDateDisplay(value) {
  const m = (value || '').match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!m) return value || ''
  const [, yyyy, mm, dd] = m
  const monthName = MONTH_NAMES[parseInt(mm, 10) - 1]
  return `${parseInt(dd, 10)}-${monthName}-${yyyy.slice(-2)}`
}
