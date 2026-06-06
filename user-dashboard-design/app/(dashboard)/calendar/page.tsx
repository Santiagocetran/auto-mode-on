import { Suspense } from "react"
import { getCalendarView, getOrgOverview } from "@/lib/data"
import { PageHeader, EmptyState } from "@/components/dashboard-ui"
import { DashboardFilters } from "@/components/dashboard-filters"
import { TaskCalendar } from "@/components/task-calendar"
import { getSessionContext } from "@/lib/data"
import { canAccessSection } from "@/lib/permissions"
import { redirect } from "next/navigation"

async function CalendarContent({
  searchParams,
}: {
  searchParams: Record<string, string | undefined>
}) {
  const session = await getSessionContext()
  if (!session.features.calendar_view || !canAccessSection(session.permissions, "calendar", session.membership)) {
    redirect("/")
  }

  const [view, overview] = await Promise.all([
    getCalendarView({ searchParams }),
    getOrgOverview({ searchParams, preset: "todo" }),
  ])

  return (
    <>
      <PageHeader
        title="Calendario"
        description={`${view.monthLabel} · Tareas según los filtros activos.`}
      />

      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-7 p-4 sm:p-6 lg:gap-8 lg:p-8">
        <section className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-5">
          <Suspense fallback={null}>
            <DashboardFilters
              teams={overview.teams}
              categories={overview.categories}
              projects={overview.projects}
              people={overview.people}
              features={overview.features}
              showTeamCategory={overview.features.team_category_filters}
              showProject={overview.features.project_filters}
            />
          </Suspense>
        </section>

        {view.totalTasks === 0 ? (
          <EmptyState message="No hay tareas visibles en este mes con los filtros actuales." />
        ) : (
          <TaskCalendar view={view} />
        )}
      </div>
    </>
  )
}

export default async function CalendarPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>
}) {
  const sp = await searchParams

  return (
    <div className="flex flex-col">
      <Suspense fallback={<div className="p-8 text-sm text-muted-foreground">Cargando calendario…</div>}>
        <CalendarContent searchParams={sp} />
      </Suspense>
    </div>
  )
}
