const EMPTY = '—'

export function formatNumber(value: unknown, digits = 0): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatInteger(value: unknown): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  return Math.round(Number(value)).toLocaleString('zh-CN')
}

export function formatCurrency(value: unknown, currency = '¥'): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  return `${currency}${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

export function formatPercent(value: unknown, digits = 1, isRatio = true): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  const raw = Number(value)
  const pct = isRatio ? raw * 100 : raw
  return `${pct.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`
}

export function formatRate(value: unknown, digits = 2): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

export function formatDays(value: unknown): string {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return EMPTY
  return `${Math.round(Number(value))} 天`
}

export function displayOrDash(value: unknown): string {
  if (value === null || value === undefined || value === '') return EMPTY
  return String(value)
}
