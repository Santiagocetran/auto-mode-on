/** Colores alineados con --chart-* en globals.css (tema claro). */
export const CHART_COLORS = {
  1: "oklch(0.55 0.11 200)",
  2: "oklch(0.65 0.13 150)",
  3: "oklch(0.7 0.13 75)",
  4: "oklch(0.6 0.15 25)",
  5: "oklch(0.5 0.08 260)",
  muted: "oklch(0.55 0.02 250)",
  grid: "oklch(0.91 0.01 240)",
  destructive: "oklch(0.58 0.2 25)",
} as const

export const CHART_TICK = { fill: CHART_COLORS.muted, fontSize: 11 }
export const CHART_AXIS = { stroke: CHART_COLORS.grid, fontSize: 11 }

export function truncateLabel(label: string, max = 14): string {
  if (label.length <= max) return label
  return `${label.slice(0, max - 1)}…`
}
