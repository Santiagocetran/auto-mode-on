"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { statusMeta } from "@/lib/ui-helpers"
import { shiftMonthKey } from "@/lib/date-ranges"
import type { CalendarView, TaskWithRefs } from "@/lib/types"
import { referenceNow } from "@/lib/data-source"

const WEEKDAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

function mergeMonthParams(current: URLSearchParams, monthKey: string) {
  const next = new URLSearchParams(current.toString())
  next.set("mes", monthKey)
  return next
}

function TaskPill({ task }: { task: TaskWithRefs }) {
  return (
    <span
      className={cn(
        "block truncate rounded px-1.5 py-0.5 text-[11px] leading-tight",
        statusMeta[task.status].badge,
      )}
      title={task.task_title}
    >
      {task.task_title}
    </span>
  )
}

function DayPanel({ tasks }: { tasks: TaskWithRefs[]; date: string }) {
  if (tasks.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin tareas para este día.</p>
  }

  return (
    <ul className="divide-y divide-border rounded-xl border border-border bg-card">
      {tasks.map((task) => (
        <li key={task.id} className="px-4 py-3">
          <div className="flex items-start gap-2">
            <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", statusMeta[task.status].dot)} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{task.task_title}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {[task.ownerName, task.projectName ?? (task.is_global ? "Global" : null), task.teamName]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <span className="shrink-0 text-xs text-muted-foreground">{statusMeta[task.status].label}</span>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function TaskCalendar({ view }: { view: CalendarView }) {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const todayKey = referenceNow().toISOString().slice(0, 10)

  const [selectedDate, setSelectedDate] = useState<string | null>(() => {
    const inMonth = view.days.find((d) => d.inMonth && d.date === todayKey)
    return inMonth?.date ?? view.days.find((d) => d.inMonth)?.date ?? null
  })

  const selectedTasks = useMemo(() => {
    if (!selectedDate) return []
    return view.days.find((d) => d.date === selectedDate)?.tasks ?? []
  }, [selectedDate, view.days])

  const navigateMonth = (delta: number) => {
    const nextMonth = shiftMonthKey(view.monthKey, delta)
    const qs = mergeMonthParams(searchParams, nextMonth).toString()
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const dateModeLabel =
    view.dateMode === "created_at" ? "fecha de creación" : "fecha de vencimiento"

  return (
    <div className="flex flex-col gap-5 xl:flex-row xl:items-start">
      <div className="min-w-0 flex-1">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold capitalize">{view.monthLabel}</h2>
            <p className="text-xs text-muted-foreground">Agrupado por {dateModeLabel}</p>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="icon-sm" onClick={() => navigateMonth(-1)} aria-label="Mes anterior">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const qs = mergeMonthParams(searchParams, referenceNow().toISOString().slice(0, 7)).toString()
                router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
              }}
            >
              Hoy
            </Button>
            <Button variant="outline" size="icon-sm" onClick={() => navigateMonth(1)} aria-label="Mes siguiente">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
          <div className="grid grid-cols-7 border-b border-border bg-muted/40">
            {WEEKDAY_LABELS.map((label) => (
              <div
                key={label}
                className="px-2 py-2 text-center text-xs font-medium text-muted-foreground"
              >
                {label}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7">
            {view.days.map((day) => {
              const isToday = day.date === todayKey
              const isSelected = day.date === selectedDate
              const visibleTasks = day.tasks.slice(0, 3)
              const overflow = day.tasks.length - visibleTasks.length

              return (
                <button
                  key={day.date}
                  type="button"
                  onClick={() => setSelectedDate(day.date)}
                  className={cn(
                    "min-h-[7.5rem] border-b border-r border-border p-1.5 text-left transition-colors last:border-r-0",
                    !day.inMonth && "bg-muted/20 text-muted-foreground",
                    day.inMonth && "hover:bg-muted/30",
                    isSelected && "bg-primary/5 ring-1 ring-inset ring-primary/30",
                  )}
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span
                      className={cn(
                        "inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium tabular-nums",
                        isToday && "bg-primary text-primary-foreground",
                      )}
                    >
                      {Number(day.date.slice(8, 10))}
                    </span>
                    {day.tasks.length > 0 ? (
                      <span className="text-[10px] tabular-nums text-muted-foreground">{day.tasks.length}</span>
                    ) : null}
                  </div>
                  <div className="flex flex-col gap-0.5">
                    {visibleTasks.map((task) => (
                      <TaskPill key={task.id} task={task} />
                    ))}
                    {overflow > 0 ? (
                      <span className="px-1 text-[10px] text-muted-foreground">+{overflow} más</span>
                    ) : null}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <aside className="w-full shrink-0 xl:w-80">
        <div className="sticky top-4 flex flex-col gap-4">
          <section>
            <h3 className="mb-2 text-sm font-medium capitalize">
              {selectedDate
                ? new Date(selectedDate + "T12:00:00Z").toLocaleDateString("es-ES", {
                    weekday: "long",
                    day: "numeric",
                    month: "long",
                  })
                : "Selecciona un día"}
            </h3>
            {selectedDate ? <DayPanel tasks={selectedTasks} date={selectedDate} /> : null}
          </section>

          {view.undatedTasks.length > 0 ? (
            <section className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-sm font-medium">Sin {dateModeLabel}</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {view.undatedTasks.length} tareas visibles sin fecha asignada
              </p>
              <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto">
                {view.undatedTasks.slice(0, 8).map((task) => (
                  <li key={task.id} className="text-sm">
                    <span className="font-medium">{task.task_title}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {statusMeta[task.status].label}
                    </span>
                  </li>
                ))}
              </ul>
              {view.undatedTasks.length > 8 ? (
                <Link href="/tasks/list" className="mt-2 inline-block text-xs text-primary hover:underline">
                  Ver listado completo
                </Link>
              ) : null}
            </section>
          ) : null}
        </div>
      </aside>
    </div>
  )
}
