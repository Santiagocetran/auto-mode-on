import Link from "next/link"
import type { DashboardSummary } from "@/lib/types"
import { StatCard } from "@/components/dashboard-ui"
import { buildTaskListHref } from "@/lib/task-list-href"
import { AlertTriangle, Ban, CalendarClock, ListTodo } from "lucide-react"

export function KpiRail({
  kpis,
  searchParams = {},
}: {
  kpis: DashboardSummary["kpis"]
  searchParams?: Record<string, string | undefined>
}) {
  const href = (extra: Record<string, string | undefined>) => buildTaskListHref(searchParams, extra)

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Link href={href({ estado: "abiertas", filtro: "vencidas" })} className="block transition-opacity hover:opacity-90">
        <StatCard
          label="Vencidas"
          value={kpis.overdueTasks}
          hint={kpis.overdueTasks > 0 ? "Necesitan seguimiento" : "Todo al día"}
          accent={kpis.overdueTasks > 0 ? "danger" : "default"}
          icon={<AlertTriangle className="h-4.5 w-4.5" />}
        />
      </Link>
      <Link href={href({ estado: "abiertas", filtro: "proximas" })} className="block transition-opacity hover:opacity-90">
        <StatCard
          label="Vencen esta semana"
          value={kpis.dueThisWeekTasks}
          hint="Próximos 7 días"
          icon={<CalendarClock className="h-4.5 w-4.5" />}
        />
      </Link>
      <Link href={href({ estado: "abiertas" })} className="block transition-opacity hover:opacity-90">
        <StatCard
          label="Abiertas"
          value={kpis.openTasks}
          hint="Trabajo activo"
          icon={<ListTodo className="h-4.5 w-4.5" />}
        />
      </Link>
      <Link href={href({ estado: "blocked" })} className="block transition-opacity hover:opacity-90">
        <StatCard
          label="Bloqueadas"
          value={kpis.blockedTasks}
          hint={kpis.blockedTasks > 0 ? "Requieren intervención" : "Sin bloqueos"}
          accent={kpis.blockedTasks > 0 ? "warning" : "default"}
          icon={<Ban className="h-4.5 w-4.5" />}
        />
      </Link>
    </div>
  )
}
