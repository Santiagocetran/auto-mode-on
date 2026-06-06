import { Suspense } from "react"
import { getOrgOverview } from "@/lib/data"
import { PageHeader, EmptyState, SectionHeader, StatCard } from "@/components/dashboard-ui"
import { DateRangeFilter } from "@/components/date-range-filter"
import { DashboardFilters } from "@/components/dashboard-filters"
import { StatsCharts } from "@/components/stats/stats-charts"
import { formatRangeLabel, resolveRange, type RangePreset } from "@/lib/date-ranges"
import { Activity } from "lucide-react"

const VALID_PRESETS: RangePreset[] = [
  "todo",
  "esta_semana",
  "proxima_semana",
  "semana_pasada",
  "ultimo_mes",
  "ultimos_3_meses",
  "personalizado",
]

async function StatsContent({
  preset,
  from,
  to,
  searchParams,
}: {
  preset: RangePreset
  from?: string
  to?: string
  searchParams: Record<string, string | undefined>
}) {
  const overview = await getOrgOverview({ preset, from, to, searchParams })
  const { organization, stats, summary, features } = overview
  const range = resolveRange(preset, from, to)
  const rangeLabel = range ? formatRangeLabel(range) : "Todo el tiempo"

  const liveKpis = [
    {
      label: "Tareas activas",
      value: summary.kpis.openTasks,
      hint: "Pendientes, en progreso o bloqueadas",
      accent: "default" as const,
      icon: <Activity className="h-4.5 w-4.5" />,
    },
    {
      label: "En progreso",
      value: stats.inProgressTasks,
      hint: "Trabajo en curso ahora",
      accent: "default" as const,
      icon: <Activity className="h-4.5 w-4.5" />,
    },
    {
      label: "Bloqueadas",
      value: stats.blockedTasks,
      hint: "Requieren desbloqueo",
      accent: stats.blockedTasks > 0 ? ("warning" as const) : ("default" as const),
      icon: <Activity className="h-4.5 w-4.5" />,
    },
    {
      label: "Vencidas",
      value: summary.kpis.overdueTasks,
      hint: "Abiertas fuera de plazo",
      accent: summary.kpis.overdueTasks > 0 ? ("danger" as const) : ("default" as const),
      icon: <Activity className="h-4.5 w-4.5" />,
    },
  ]

  return (
    <>
      <PageHeader
        title="Estadísticas"
        description={`${organization.name} · Carga operativa y distribución del trabajo.`}
      />

      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-7 p-4 sm:p-6 lg:gap-8 lg:p-8">
        <section className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Periodo</p>
              <p className="text-sm font-medium">{rangeLabel}</p>
            </div>
            <DateRangeFilter preset={preset} from={from} to={to} />
          </div>

          <div className="mt-4 border-t border-border pt-4">
            <Suspense fallback={null}>
              <DashboardFilters
                teams={overview.teams}
                categories={overview.categories}
                projects={overview.projects}
                people={overview.people}
                features={features}
                showTeamCategory={features.team_category_filters}
                showProject={features.project_filters}
              />
            </Suspense>
          </div>
        </section>

        {stats.totalTasks === 0 ? (
          <EmptyState message="No hay datos para mostrar con los filtros actuales." />
        ) : (
          <>
            <section>
              <SectionHeader
                title="Tareas en vivo"
                description="Resumen numérico del trabajo activo con los filtros aplicados."
              />
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {liveKpis.map((item) => (
                  <StatCard
                    key={item.label}
                    label={item.label}
                    value={item.value}
                    hint={item.hint}
                    accent={item.accent}
                    icon={item.icon}
                  />
                ))}
              </div>
            </section>

            <section className="flex flex-col gap-4">
              <SectionHeader
                title="Gráficos de carga"
                description="Visualización con ejes, leyenda y tooltips — distribución por persona, proyecto y equipo."
              />
              <StatsCharts
                workload={summary.charts.workloadByOwner}
                statusBreakdown={overview.statusBreakdown}
                projectLoad={overview.projectLoad}
                teamLoad={overview.teamLoad}
                activeTasksByDay={summary.charts.activeTasksByDay}
                liveStats={{
                  open: summary.kpis.openTasks,
                  inProgress: stats.inProgressTasks,
                  blocked: stats.blockedTasks,
                  overdue: summary.kpis.overdueTasks,
                  pending: stats.pendingTasks,
                }}
                features={features}
              />
            </section>
          </>
        )}
      </div>
    </>
  )
}

export default async function StatsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>
}) {
  const sp = await searchParams
  const preset: RangePreset = VALID_PRESETS.includes(sp.rango as RangePreset)
    ? (sp.rango as RangePreset)
    : "todo"

  return (
    <div className="flex flex-col">
      <Suspense fallback={<div className="p-8 text-sm text-muted-foreground">Cargando estadísticas…</div>}>
        <StatsContent preset={preset} from={sp.desde} to={sp.hasta} searchParams={sp} />
      </Suspense>
    </div>
  )
}
