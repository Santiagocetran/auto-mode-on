import { cn } from "@/lib/utils"
import type { ProjectLoadRow } from "@/lib/types"

export function ProjectLoadChart({ rows }: { rows: ProjectLoadRow[] }) {
  const top = rows.slice(0, 8)
  const max = Math.max(...top.map((r) => r.open + r.completed), 1)

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-semibold">Carga por proyecto</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">Tareas abiertas y completadas por proyecto</p>

      {top.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">Sin proyectos con tareas en este alcance.</p>
      ) : (
        <>
          <ul className="mt-4 flex flex-col gap-4">
            {top.map((row) => (
              <li key={row.projectId ?? row.projectName}>
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="truncate font-medium">{row.projectName}</span>
                  <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                    {row.open} abiertas
                    {row.overdue > 0 ? ` · ${row.overdue} venc.` : ""}
                  </span>
                </div>
                <div className="mt-1.5 flex h-2 w-full gap-0.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-l-full bg-chart-1"
                    style={{ width: `${(row.open / max) * 100}%` }}
                  />
                  <div
                    className="h-full bg-chart-2"
                    style={{ width: `${(row.completed / max) * 100}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>

          <div className="mt-4 flex items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className={cn("h-2 w-2 rounded-full bg-chart-1")} /> Abiertas
            </span>
            <span className="flex items-center gap-1.5">
              <span className={cn("h-2 w-2 rounded-full bg-chart-2")} /> Completadas
            </span>
          </div>
        </>
      )}
    </div>
  )
}
