import { Suspense } from "react"
import { getOrgOverview } from "@/lib/data"
import { PageHeader, EmptyState, SectionHeader } from "@/components/dashboard-ui"
import { ProjectCard } from "@/components/project-card"
import { DateRangeFilter } from "@/components/date-range-filter"
import { DashboardFilters } from "@/components/dashboard-filters"
import { KpiRail } from "@/components/kpi-rail"
import { OperationalLists } from "@/components/operational-lists"
import { statusMeta } from "@/lib/ui-helpers"
import { resolveRange, formatRangeLabel, type RangePreset } from "@/lib/date-ranges"
import { referenceNow } from "@/lib/data-source"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { ArrowRight, CalendarDays } from "lucide-react"

const VALID_PRESETS: RangePreset[] = [
  "todo",
  "esta_semana",
  "proxima_semana",
  "semana_pasada",
  "ultimo_mes",
  "ultimos_3_meses",
  "personalizado",
]

async function DashboardContent({
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
  const { organization, stats, projects, categories, projectProgress, features, summary, session } =
    overview

  const activeProjects = projects.filter((p) => p.status !== "archived")
  const range = resolveRange(preset, from, to)
  const rangeLabel = range ? formatRangeLabel(range) : "Todo el tiempo"
  const referenceDate = referenceNow().toISOString()

  return (
    <>
      <PageHeader
        title="Resumen"
        description={`${organization.name} · Lo que necesita atención ahora.`}
      >
        {session.isDemo ? (
          <span className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground">Modo demo</span>
        ) : null}
      </PageHeader>

      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-7 p-4 sm:p-6 lg:gap-8 lg:p-8">
        <section className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <CalendarDays className="h-4 w-4" />
              </span>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Periodo</p>
                <p className="text-sm font-medium">{rangeLabel}</p>
              </div>
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

        <section>
          <SectionHeader
            title="Señales clave"
            description="Una lectura rápida del trabajo que requiere seguimiento."
          />
          <KpiRail kpis={summary.kpis} searchParams={searchParams} />
        </section>

        {stats.totalTasks === 0 ? (
          <EmptyState message="No hay tareas visibles con los filtros actuales." />
        ) : (
          <>
            <section>
              <SectionHeader
                title="Requiere atención"
                description="Prioridades operativas ordenadas por urgencia."
              />
              <OperationalLists lists={summary.lists} referenceDate={referenceDate} />
            </section>

            <section>
              <SectionHeader
                title="Trabajo en curso"
                description="Actividad reciente y avance de los proyectos activos."
              />
              <div
                className={cn(
                  "grid gap-5",
                  features.projects &&
                    activeProjects.length > 0 &&
                    "xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]",
                )}
              >
                <div className="min-w-0">
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="text-sm font-medium">Tareas recientes</h3>
                    <Link href="/tasks/list" className="text-xs text-primary hover:underline">
                      Ver todas
                    </Link>
                  </div>
                  {overview.recentTasks.length === 0 ? (
                    <EmptyState message="Sin tareas recientes en este periodo." />
                  ) : (
                    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
                      <ul className="divide-y divide-border">
                        {overview.recentTasks.slice(0, 6).map((task) => (
                          <li
                            key={task.id}
                            className="flex min-h-12 flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2.5 text-sm transition-colors hover:bg-muted/35"
                          >
                            <span
                              className={cn(
                                "h-2 w-2 shrink-0 rounded-full",
                                statusMeta[task.status].dot,
                              )}
                              aria-hidden
                            />
                            <span className="min-w-0 flex-1 truncate font-medium">{task.task_title}</span>
                            {task.projectName ? (
                              <span className="hidden max-w-36 truncate text-xs text-muted-foreground sm:inline">{task.projectName}</span>
                            ) : task.is_global ? (
                              <span className="hidden text-xs text-muted-foreground sm:inline">Global</span>
                            ) : null}
                            <span className="w-24 shrink-0 truncate text-right text-xs text-muted-foreground">
                              {task.ownerName ?? "Sin asignar"}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {features.projects && activeProjects.length > 0 ? (
                  <div className="min-w-0">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-medium">Proyectos activos</h3>
                      <Link
                        href="/tasks/projects"
                        className="flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        Ver todos <ArrowRight className="h-3 w-3" />
                      </Link>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-1">
                      {activeProjects.slice(0, 2).map((project) => {
                        const prog = projectProgress.find((p) => p.projectId === project.id)
                        return (
                          <ProjectCard
                            key={project.id}
                            project={project}
                            categories={categories.filter((c) => project.category_ids.includes(c.id))}
                            taskCount={prog?.total ?? 0}
                            completedCount={prog?.completed ?? 0}
                          />
                        )
                      })}
                    </div>
                  </div>
                ) : null}
              </div>
            </section>

            <section className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold tracking-tight">Profundizar análisis</h2>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    Carga por persona, proyectos y equipos con los mismos filtros.
                  </p>
                </div>
                <Link
                  href={{ pathname: "/stats", query: searchParams }}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  Abrir estadísticas <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </section>
          </>
        )}
      </div>
    </>
  )
}

export default async function OverviewPage({
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
      <Suspense
        fallback={
          <div className="p-8 text-sm text-muted-foreground">Cargando resumen…</div>
        }
      >
        <DashboardContent preset={preset} from={sp.desde} to={sp.hasta} searchParams={sp} />
      </Suspense>
    </div>
  )
}
