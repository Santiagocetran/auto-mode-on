import { cn } from "@/lib/utils"
import type { DashboardSummary } from "@/lib/types"

export function WorkloadRiskChart({
  data,
}: {
  data: DashboardSummary["charts"]["workloadByOwner"]
}) {
  const rows = data.slice(0, 6)
  const max = Math.max(...rows.map((row) => row.openTasks), 1)

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-semibold">Presión por responsable</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">
        Qué responsables concentran más carga abierta y cuánto de eso ya está en riesgo.
      </p>

      {rows.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">Sin responsables activos en este alcance.</p>
      ) : (
        <>
          <ul className="mt-5 space-y-4">
            {rows.map((row) => {
              const overduePct = row.openTasks > 0 ? (row.overdueTasks / row.openTasks) * 100 : 0
              const blockedPct = row.openTasks > 0 ? (row.blockedTasks / row.openTasks) * 100 : 0

              return (
                <li key={row.ownerPeopleId ?? row.ownerLabel}>
                  <div className="mb-1.5 flex items-center justify-between gap-3">
                    <span className="truncate text-sm font-medium">{row.ownerLabel}</span>
                    <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                      {row.openTasks} abiertas
                    </span>
                  </div>

                  <div className="h-3 overflow-hidden rounded-full bg-muted">
                    <div
                      className="flex h-full overflow-hidden rounded-full"
                      style={{ width: `${(row.openTasks / max) * 100}%` }}
                    >
                      <div
                        className={cn("h-full bg-chart-1")}
                        style={{ width: `${Math.max(0, 100 - overduePct - blockedPct)}%` }}
                      />
                      <div className={cn("h-full bg-chart-3")} style={{ width: `${overduePct}%` }} />
                      <div className={cn("h-full bg-destructive")} style={{ width: `${blockedPct}%` }} />
                    </div>
                  </div>

                  <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                    <span className="tabular-nums">{row.overdueTasks} vencidas</span>
                    <span className="tabular-nums">{row.blockedTasks} bloqueadas</span>
                  </div>
                </li>
              )
            })}
          </ul>

          <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-chart-1" />
              Abiertas estables
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-chart-3" />
              Vencidas
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-destructive" />
              Bloqueadas
            </span>
          </div>
        </>
      )}
    </div>
  )
}
