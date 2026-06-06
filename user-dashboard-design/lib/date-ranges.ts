import { referenceNow } from "@/lib/data-source"

// Presets de rango de fechas para el filtro del resumen.
export type RangePreset =
  | "todo"
  | "esta_semana"
  | "proxima_semana"
  | "semana_pasada"
  | "ultimo_mes"
  | "ultimos_3_meses"
  | "personalizado"

export const RANGE_PRESETS: { value: RangePreset; label: string }[] = [
  { value: "todo", label: "Todo el tiempo" },
  { value: "esta_semana", label: "Esta semana" },
  { value: "proxima_semana", label: "Semana siguiente" },
  { value: "semana_pasada", label: "Semana pasada" },
  { value: "ultimo_mes", label: "Último mes" },
  { value: "ultimos_3_meses", label: "Últimos 3 meses" },
  { value: "personalizado", label: "Personalizado" },
]

export interface DateRange {
  from: Date
  to: Date
}

function startOfDay(d: Date): Date {
  const x = new Date(d)
  x.setUTCHours(0, 0, 0, 0)
  return x
}

function endOfDay(d: Date): Date {
  const x = new Date(d)
  x.setUTCHours(23, 59, 59, 999)
  return x
}

function addDays(d: Date, n: number): Date {
  const x = new Date(d)
  x.setUTCDate(x.getUTCDate() + n)
  return x
}

// Lunes como inicio de semana.
function startOfWeek(d: Date): Date {
  const x = startOfDay(d)
  const day = (x.getUTCDay() + 6) % 7
  return addDays(x, -day)
}

function parseDate(value?: string): Date | null {
  if (!value) return null
  const d = new Date(value + "T00:00:00Z")
  return Number.isNaN(d.getTime()) ? null : d
}

// Devuelve el rango de fechas para un preset, o null si es "todo el tiempo".
export function resolveRange(preset: RangePreset, from?: string, to?: string): DateRange | null {
  const today = referenceNow()
  const weekStart = startOfWeek(today)

  switch (preset) {
    case "esta_semana":
      return { from: weekStart, to: endOfDay(addDays(weekStart, 6)) }
    case "proxima_semana":
      return { from: addDays(weekStart, 7), to: endOfDay(addDays(weekStart, 13)) }
    case "semana_pasada":
      return { from: addDays(weekStart, -7), to: endOfDay(addDays(weekStart, -1)) }
    case "ultimo_mes":
      return { from: startOfDay(addDays(today, -30)), to: endOfDay(today) }
    case "ultimos_3_meses":
      return { from: startOfDay(addDays(today, -90)), to: endOfDay(today) }
    case "personalizado": {
      const f = parseDate(from)
      const t = parseDate(to)
      if (!f || !t) return null
      return { from: startOfDay(f), to: endOfDay(t) }
    }
    case "todo":
    default:
      return null
  }
}

/** Ventana para gráficos de línea temporal cuando el preset es "todo el tiempo". */
export function resolveTimelineRange(
  range: DateRange | null,
  tasks: Array<{ created_at: string }> = [],
): DateRange {
  if (range) return range

  const today = referenceNow()
  const defaultFrom = startOfDay(addDays(today, -89))
  const defaultTo = endOfDay(today)

  if (tasks.length === 0) return { from: defaultFrom, to: defaultTo }

  let earliest = defaultFrom
  for (const task of tasks) {
    const created = new Date(task.created_at.length === 10 ? `${task.created_at}T00:00:00Z` : task.created_at)
    if (created < earliest) earliest = startOfDay(created)
  }

  const spanDays = Math.ceil((defaultTo.getTime() - earliest.getTime()) / (1000 * 60 * 60 * 24)) + 1
  if (spanDays > 90) return { from: defaultFrom, to: defaultTo }

  return { from: earliest, to: defaultTo }
}

export function eachDayInRange(range: DateRange): Date[] {
  const days: Date[] = []
  let cursor = startOfDay(range.from)
  const end = range.to
  while (cursor <= end) {
    days.push(new Date(cursor))
    cursor = addDays(cursor, 1)
  }
  return days
}

const UTC_DATE_FMT: Intl.DateTimeFormatOptions = { timeZone: "UTC" }

function formatUTCDate(d: Date, options: Intl.DateTimeFormatOptions): string {
  return d.toLocaleDateString("es-ES", { ...options, ...UTC_DATE_FMT })
}

export function formatRangeLabel(range: DateRange): string {
  const fmt = (d: Date) =>
    formatUTCDate(d, { day: "numeric", month: "short", year: "numeric" })
  return `${fmt(range.from)} – ${fmt(range.to)}`
}

const MONTH_KEY_RE = /^(\d{4})-(\d{2})$/

export function currentMonthKey(reference: Date = referenceNow()): string {
  return `${reference.getUTCFullYear()}-${String(reference.getUTCMonth() + 1).padStart(2, "0")}`
}

export function parseMonthKey(value?: string): string | null {
  if (!value || !MONTH_KEY_RE.test(value)) return null
  const match = value.match(MONTH_KEY_RE)
  if (!match) return null
  const year = match[1]
  const month = match[2]
  const mon = Number(month)
  if (mon < 1 || mon > 12) return null
  return `${year}-${month}`
}

export function resolveMonthRange(monthKey: string): DateRange | null {
  const parsed = parseMonthKey(monthKey)
  if (!parsed) return null
  const [, year, month] = parsed.match(MONTH_KEY_RE)!
  const mon = Number(month) - 1
  const from = startOfDay(new Date(Date.UTC(Number(year), mon, 1)))
  const lastDay = new Date(Date.UTC(Number(year), mon + 1, 0))
  return { from, to: endOfDay(lastDay) }
}

export function formatMonthLabel(monthKey: string): string {
  const parsed = parseMonthKey(monthKey)
  if (!parsed) return monthKey
  const match = parsed.match(MONTH_KEY_RE)
  if (!match) return monthKey
  const year = match[1]
  const month = match[2]
  const d = new Date(Date.UTC(Number(year), Number(month) - 1, 1))
  return formatUTCDate(d, { month: "long", year: "numeric" })
}

export function shiftMonthKey(monthKey: string, delta: number): string {
  const parsed = parseMonthKey(monthKey) ?? currentMonthKey()
  const match = parsed.match(MONTH_KEY_RE)
  if (!match) return currentMonthKey()
  const year = match[1]
  const month = match[2]
  const d = new Date(Date.UTC(Number(year), Number(month) - 1 + delta, 1))
  return currentMonthKey(d)
}

export function calendarGridDays(monthKey: string): Array<{ date: string; inMonth: boolean }> {
  const range = resolveMonthRange(monthKey)
  if (!range) return []

  const monthStart = range.from
  const gridStart = startOfWeek(monthStart)
  const monthEnd = range.to
  const days: Array<{ date: string; inMonth: boolean }> = []

  for (let i = 0; i < 42; i++) {
    const d = addDays(gridStart, i)
    const date = d.toISOString().slice(0, 10)
    const inMonth = d >= monthStart && d <= monthEnd
    days.push({ date, inMonth })
  }

  return days
}
