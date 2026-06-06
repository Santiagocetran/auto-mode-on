import { Suspense } from "react"
import { getOrgOverview } from "@/lib/data"
import { PageHeader, EmptyState, SectionHeader, StatCard } from "@/components/dashboard-ui"
import { DateRangeFilter } from "@/components/date-range-filter"
import { DashboardFilters } from "@/components/dashboard-filters"
import { DueDateHistogram } from "@/components/due-date-histogram"
import { DistributionChart } from "@/components/distribution-chart"
import { StatusBreakdown } from "@/components/status-breakdown"
import { TeamLoad } from "@/components/team-load"
import { StackedBreakdownChart } from "@/components/stacked-breakdown-chart"
import { ActivityComparisonChart } from "@/components/activity-comparison-chart"
import { WorkloadRiskChart } from "@/components/workload-risk-chart"
import { toStackedChartRows } from "@/lib/aggregations"
import { formatRangeLabel, resolveRange, type RangePreset } from "@/lib/date-ranges"
import { referenceNow } from "@/lib/data-source"
import { AlertTriangle, ArrowDownUp, BadgeAlert, MessageSquareMore } from "lucide-react"

const VALID_PRESETS: RangePreset[] = [
  "todo",
  "esta_semana",
  "proxima_semana",
  "semana_pasada",
  "ultimo_mes",
  "ultimos_3_meses",
  "personalizado",
]

async function AnalyticsContent({
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
  const { organization, stats, summary, features, categories, projects } = overview
  const range = resolveRange(preset, from, to)
  const rangeLabel = range ? formatRangeLabel(range) : "Todo el tiempo"
  const referenceDate = referenceNow().toISOString()

  const story = [
    {
      label: "Tareas en riesgo",
      value: summary.kpis.overdueTasks + summary.kpis.blockedTasks,
      hint: "Vencidas y bloqueadas",
      accent:
        summary.kpis.overdueTasks + summary.kpis.blockedTasks > 0 ? "danger" : "default",
      icon: <AlertTriangle className="h-4.5 w-4.5" />,
    },
    {
      label: "Alta prioridad abierta",
      value: summary.kpis.highPriorityOpenTasks,
      hint: "Alta o urgente",
      accent: summary.kpis.highPriorityOpenTasks > 0 ? "warning" : "default",
      icon: <BadgeAlert className="h-4.5 w-4.5" />,
    },
    {
      label: "Sin responsable",
      value: summary.kpis.unownedTasks + summary.kpis.unresolvedOwnerTasks,
      hint: "Vacantes o no vinculadas",
      accent:
        summary.kpis.unownedTasks + summary.kpis.unresolvedOwnerTasks > 0 ? "warning" : "default",
      icon: <ArrowDownUp className="h-4.5 w-4.5" />,
    },
    {
      label: "Entrada del periodo",
      value: summary.kpis.inboundMessagesInRange,
      hint: "Capturas recibidas",
      accent: summary.kpis.inboundMessagesInRange > 0 ? "success" : "default",
      icon: <MessageSquareMore className="h-4.5 w-4.5" />,
    },
  ] as const

  return (
    <>
      <PageHeader
        title="Análisis detallado"
        description={`${organization.name} · Tendencias, carga y estructura del trabajo.`}
      />

      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-7 p-4 sm:p-6 lg:gap-8 lg:p-8">
        <section className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Periodo</p>
              <p className="text-sm font-medium">{rangeLabel}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Referencia de cálculo: {new Date(referenceDate).toLocaleDateString("es-ES")}
              </p>
            </div>
            <DateRangeFilter preset={preset} from={from} to={to} />
          </div>

          <div className="mt-4 border-t border-border pt-4">
            <Suspense fallback={null}>
              <DashboardFilters
                teams={overview.teams}
                categories={categories}
                projects={projects}
                people={overview.people}
                features={features}
                showTeamCategory={features.team_category_filters}
                showProject={features.project_filters}
              />
            </Suspense>
          </div>
        </section>

        {stats.totalTasks === 0 ? (
          <EmptyState message="No hay datos para analizar con los filtros actuales." />
        ) : (
          <>
            <section>
              <SectionHeader
                title="Pulso operativo"
                description="Cuatro señales para entender dónde está la tensión hoy."
              />
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {story.map((item) => (
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

            <section>
              <SectionHeader
                title="Narrativa del flujo"
                description="Primero vemos cuánto entra, luego dónde se acumula el riesgo."
              />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
                <ActivityComparisonChart
                  tasks={summary.charts.tasksCreatedByDay}
                  inbound={summary.charts.inboundMessagesByDay}
                />
                <DueDateHistogram data={summary.charts.dueDateBuckets} />
              </div>
            </section>

            <section>
              <SectionHeader
                title="Dónde se siente la presión"
                description="Carga por responsables y equipos, con énfasis en atraso y bloqueo."
              />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <WorkloadRiskChart data={summary.charts.workloadByOwner} />
                {features.team_load_view ? (
                  <TeamLoad teamLoad={overview.teamLoad} />
                ) : (
                  <StatusBreakdown data={overview.statusBreakdown} total={stats.totalTasks} />
                )}
              </div>
            </section>

            <section>
              <SectionHeader
                title="Composición del trabajo"
                description="Cómo se distribuye el backlog por estado, prioridad, origen y estructura."
              />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                <StatusBreakdown data={overview.statusBreakdown} total={stats.totalTasks} />
                <DistributionChart
                  title="Prioridad"
                  subtitle="Qué parte del backlog exige atención mayor."
                  kind="priority"
                  rows={summary.charts.tasksByPriority.map((row) => ({
                    key: row.priority,
                    count: row.count,
                  }))}
                />
                <DistributionChart
                  title="Origen"
                  subtitle="Desde dónde entra el trabajo al sistema."
                  kind="source"
                  rows={summary.charts.tasksBySource.map((row) => ({
                    key: row.sourceType,
                    count: row.count,
                  }))}
                />
              </div>
            </section>

            <section>
              <SectionHeader
                title="Estructura por área"
                description="Comparación del mix de estados por equipo y categoría."
              />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <StackedBreakdownChart
                  title="Equipos"
                  subtitle="Dónde se concentra el volumen operativo"
                  rows={toStackedChartRows(summary.charts.tasksByTeamAndStatus, "teamId", "teamName")}
                />
                {features.team_category_filters ? (
                  <StackedBreakdownChart
                    title="Categorías"
                    subtitle="Qué áreas acumulan más trabajo"
                    rows={toStackedChartRows(
                      summary.charts.tasksByCategoryAndStatus,
                      "categoryId",
                      "categoryName",
                    )}
                  />
                ) : (
                  <DistributionChart
                    title="Estado"
                    subtitle="Balance general del trabajo visible"
                    kind="status"
                    rows={summary.charts.tasksByStatus.map((row) => ({
                      key: row.status,
                      count: row.count,
                    }))}
                  />
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </>
  )
}

export default async function AnalyticsPage({
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
      <Suspense fallback={<div className="p-8 text-sm text-muted-foreground">Cargando análisis…</div>}>
        <AnalyticsContent preset={preset} from={sp.desde} to={sp.hasta} searchParams={sp} />
      </Suspense>
    </div>
  )
}
