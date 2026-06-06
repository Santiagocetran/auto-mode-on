import { cn } from "@/lib/utils"

function formatSeries(tasks: Array<{ day: string; count: number }>, inbound: Array<{ day: string; count: number }>) {
  const map = new Map<string, { day: string; tasks: number; inbound: number }>()

  for (const point of tasks) {
    map.set(point.day, { day: point.day, tasks: point.count, inbound: map.get(point.day)?.inbound ?? 0 })
  }
  for (const point of inbound) {
    const current = map.get(point.day)
    map.set(point.day, {
      day: point.day,
      tasks: current?.tasks ?? 0,
      inbound: point.count,
    })
  }

  return [...map.values()].sort((a, b) => a.day.localeCompare(b.day))
}

export function ActivityComparisonChart({
  tasks,
  inbound,
}: {
  tasks: Array<{ day: string; count: number }>
  inbound: Array<{ day: string; count: number }>
}) {
  const rows = formatSeries(tasks, inbound)
  const max = Math.max(...rows.map((row) => Math.max(row.tasks, row.inbound)), 1)

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Entrada operativa</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Compara creación de tareas con capturas entrantes a lo largo del periodo.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-chart-1" />
            Tareas
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-chart-3" />
            Capturas
          </span>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">Sin actividad en este periodo.</p>
      ) : (
        <div className="mt-5">
          <div className="flex h-40 items-end gap-2 overflow-x-auto pb-2">
            {rows.map((row) => (
              <div key={row.day} className="flex min-w-9 flex-1 items-end justify-center gap-1">
                <div
                  className={cn("w-3 rounded-t bg-chart-1")}
                  style={{ height: `${(row.tasks / max) * 100}%`, minHeight: row.tasks > 0 ? "6px" : "0" }}
                  title={`${row.day}: ${row.tasks} tareas`}
                />
                <div
                  className={cn("w-3 rounded-t bg-chart-3")}
                  style={{ height: `${(row.inbound / max) * 100}%`, minHeight: row.inbound > 0 ? "6px" : "0" }}
                  title={`${row.day}: ${row.inbound} capturas`}
                />
              </div>
            ))}
          </div>

          <div className="mt-2 flex gap-2 overflow-x-auto">
            {rows.map((row) => (
              <span key={row.day} className="min-w-9 flex-1 text-center text-[10px] text-muted-foreground">
                {row.day.slice(5)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
