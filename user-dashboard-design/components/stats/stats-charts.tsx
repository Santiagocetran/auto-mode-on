"use client"

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { DashboardSummary, OrgFeatures, OrgOverview, ProjectLoadRow } from "@/lib/types"
import { CHART_COLORS, CHART_TICK, truncateLabel } from "@/lib/chart-theme"
import { ChartCard } from "@/components/stats/chart-card"
import { statusMeta } from "@/lib/ui-helpers"

type LiveStats = {
  open: number
  inProgress: number
  blocked: number
  overdue: number
  pending: number
}

type Props = {
  workload: DashboardSummary["charts"]["workloadByOwner"]
  statusBreakdown: OrgOverview["statusBreakdown"]
  projectLoad: ProjectLoadRow[]
  teamLoad: OrgOverview["teamLoad"]
  liveStats: LiveStats
  activeTasksByDay: DashboardSummary["charts"]["activeTasksByDay"]
  features: OrgFeatures
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number; color?: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      {label ? <p className="mb-1.5 font-medium text-foreground">{label}</p> : null}
      <ul className="space-y-1">
        {payload.map((entry) => (
          <li key={entry.name} className="flex items-center gap-2 text-muted-foreground">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
            <span>{entry.name}</span>
            <span className="ml-auto font-medium tabular-nums text-foreground">{entry.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function PieTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number; payload?: { fill?: string; pct?: number } }>
}) {
  if (!active || !payload?.length) return null
  const item = payload[0]
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{item.name}</p>
      <p className="mt-0.5 text-muted-foreground">
        {item.value} tareas{item.payload?.pct != null ? ` · ${item.payload.pct}%` : ""}
      </p>
    </div>
  )
}

function EmptyChart({ message }: { message: string }) {
  return <p className="flex h-64 items-center justify-center text-sm text-muted-foreground">{message}</p>
}

export function StatsCharts({
  workload,
  statusBreakdown,
  projectLoad,
  teamLoad,
  liveStats,
  activeTasksByDay,
  features,
}: Props) {
  const liveSlices = [
    { name: "Pendiente", value: liveStats.pending, fill: CHART_COLORS.muted },
    { name: "En progreso", value: liveStats.inProgress, fill: CHART_COLORS[1] },
    { name: "Bloqueada", value: liveStats.blocked, fill: CHART_COLORS.destructive },
  ].filter((s) => s.value > 0)

  const liveTotal = liveSlices.reduce((s, r) => s + r.value, 0)
  const liveWithPct = liveSlices.map((s) => ({
    ...s,
    pct: liveTotal > 0 ? Math.round((s.value / liveTotal) * 100) : 0,
  }))

  const workloadRows = workload.slice(0, 8).map((row) => ({
    name: truncateLabel(row.ownerLabel, 12),
    fullName: row.ownerLabel,
    estables: Math.max(0, row.openTasks - row.overdueTasks - row.blockedTasks),
    vencidas: row.overdueTasks,
    bloqueadas: row.blockedTasks,
    total: row.openTasks,
  }))

  const statusSlices = statusBreakdown
    .filter((s) => s.count > 0)
    .map((s, i) => ({
      name: statusMeta[s.status].label,
      value: s.count,
      fill: [CHART_COLORS[1], CHART_COLORS[2], CHART_COLORS.destructive, CHART_COLORS.muted, CHART_COLORS[5]][i % 5],
    }))
  const statusTotal = statusSlices.reduce((s, r) => s + r.value, 0)

  const projectRows = projectLoad.slice(0, 8).map((row) => ({
    name: truncateLabel(row.projectName, 16),
    fullName: row.projectName,
    abiertas: row.open,
    completadas: row.completed,
    vencidas: row.overdue,
  }))

  const teamRows = teamLoad.map(({ team, open, completed }) => ({
    name: truncateLabel(team.name, 12),
    fullName: team.name,
    abiertas: open,
    completadas: completed,
    color: team.color ?? CHART_COLORS[1],
  }))

  return (
    <>
      <section>
        <ChartCard
          title="Evolución de tareas activas"
          subtitle="Backlog abierto reconstruido día a día según creación y cierre (completed_at)."
          footer={
            activeTasksByDay.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                Hoy:{" "}
                <span className="font-medium text-foreground">
                  {activeTasksByDay[activeTasksByDay.length - 1]?.active ?? liveStats.open}
                </span>{" "}
                tareas activas
                {activeTasksByDay.length > 1 ? (
                  <>
                    {" "}
                    · pico del periodo:{" "}
                    <span className="font-medium text-foreground">
                      {Math.max(...activeTasksByDay.map((d) => d.active))}
                    </span>
                  </>
                ) : null}
              </p>
            ) : null
          }
        >
          {activeTasksByDay.length === 0 ? (
            <EmptyChart message="Sin datos temporales en este periodo." />
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={activeTasksByDay} margin={{ top: 8, right: 12, left: -4, bottom: 8 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={CHART_TICK}
                  axisLine={{ stroke: CHART_COLORS.grid }}
                  tickLine={false}
                  interval={activeTasksByDay.length > 45 ? Math.floor(activeTasksByDay.length / 8) : "preserveStartEnd"}
                  minTickGap={24}
                />
                <YAxis
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                  label={{
                    value: "Tareas activas",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: CHART_COLORS.muted, fontSize: 11 },
                  }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    const point = activeTasksByDay.find((d) => d.label === label)
                    return (
                      <ChartTooltip
                        active={active}
                        label={point?.day ?? label}
                        payload={[{ name: "Activas", value: payload?.[0]?.value as number, color: CHART_COLORS[1] }]}
                      />
                    )
                  }}
                />
                <Legend iconType="line" wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                <Line
                  type="monotone"
                  dataKey="active"
                  name="Tareas activas"
                  stroke={CHART_COLORS[1]}
                  strokeWidth={2}
                  dot={activeTasksByDay.length <= 31 ? { r: 3, fill: CHART_COLORS[1] } : false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="Composición de tareas activas"
          subtitle="Distribución proporcional del trabajo en curso (pendiente, progreso, bloqueo)."
          footer={
            liveStats.overdue > 0 ? (
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-destructive">{liveStats.overdue}</span> de{" "}
                {liveStats.open} activas están vencidas.
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Ninguna tarea activa vencida en este alcance.</p>
            )
          }
        >
          {liveWithPct.length === 0 ? (
            <EmptyChart message="No hay tareas activas." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={liveWithPct}
                  cx="50%"
                  cy="50%"
                  innerRadius={62}
                  outerRadius={98}
                  paddingAngle={2}
                  dataKey="value"
                  nameKey="name"
                  label={({ name, pct }) => `${name} (${pct}%)`}
                  labelLine={{ stroke: CHART_COLORS.muted, strokeWidth: 1 }}
                >
                  {liveWithPct.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  iconType="circle"
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title="Estado general del backlog"
          subtitle="Proporción de tareas por estado en el periodo filtrado."
        >
          {statusSlices.length === 0 ? (
            <EmptyChart message="Sin datos de estado." />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={statusSlices}
                  cx="50%"
                  cy="50%"
                  outerRadius={98}
                  dataKey="value"
                  nameKey="name"
                  label={({ value }) =>
                    statusTotal > 0 ? `${Math.round((value / statusTotal) * 100)}%` : ""
                  }
                >
                  {statusSlices.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip content={<PieTooltip />} />
                <Legend
                  verticalAlign="bottom"
                  iconType="circle"
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard
          title="Carga por responsable"
          subtitle="Barras apiladas: abiertas estables, vencidas y bloqueadas por persona."
        >
          {workloadRows.length === 0 ? (
            <EmptyChart message="Sin responsables con carga en este alcance." />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={workloadRows} margin={{ top: 8, right: 8, left: -8, bottom: 48 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={CHART_TICK}
                  axisLine={{ stroke: CHART_COLORS.grid }}
                  tickLine={false}
                  interval={0}
                  angle={-28}
                  textAnchor="end"
                  height={56}
                />
                <YAxis
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                  label={{
                    value: "Tareas",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: CHART_COLORS.muted, fontSize: 11 },
                  }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    const row = workloadRows.find((r) => r.name === label)
                    return (
                      <ChartTooltip
                        active={active}
                        label={row?.fullName ?? label}
                        payload={payload?.map((p) => ({
                          name: p.name,
                          value: p.value as number,
                          color: p.color,
                        }))}
                      />
                    )
                  }}
                />
                <Legend iconType="square" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Bar dataKey="estables" name="Abiertas estables" stackId="a" fill={CHART_COLORS[1]} />
                <Bar dataKey="vencidas" name="Vencidas" stackId="a" fill={CHART_COLORS[3]} />
                <Bar
                  dataKey="bloqueadas"
                  name="Bloqueadas"
                  stackId="a"
                  fill={CHART_COLORS.destructive}
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {features.projects && projectRows.length > 0 ? (
          <ChartCard
            title="Distribución por proyecto"
            subtitle="Comparación de tareas abiertas vs. completadas por proyecto."
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                layout="vertical"
                data={projectRows}
                margin={{ top: 4, right: 16, left: 4, bottom: 4 }}
              >
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tick={CHART_TICK}
                  axisLine={{ stroke: CHART_COLORS.grid }}
                  tickLine={false}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                  width={88}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    const row = projectRows.find((r) => r.name === label)
                    return (
                      <ChartTooltip
                        active={active}
                        label={row?.fullName ?? label}
                        payload={payload?.map((p) => ({
                          name: p.name,
                          value: p.value as number,
                          color: p.color,
                        }))}
                      />
                    )
                  }}
                />
                <Legend iconType="square" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Bar dataKey="abiertas" name="Abiertas" fill={CHART_COLORS[1]} radius={[0, 0, 0, 0]} />
                <Bar dataKey="completadas" name="Completadas" fill={CHART_COLORS[2]} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        ) : (
          <ChartCard title="Distribución por proyecto" subtitle="Proyectos no habilitados o sin datos.">
            <EmptyChart message="No hay proyectos con tareas visibles." />
          </ChartCard>
        )}
      </section>

      {features.team_load_view && teamRows.length > 0 ? (
        <section>
          <ChartCard
            title="Carga por equipo"
            subtitle="Barras agrupadas de tareas abiertas y completadas por equipo."
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={teamRows} margin={{ top: 8, right: 8, left: -8, bottom: 48 }}>
                <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={CHART_TICK}
                  axisLine={{ stroke: CHART_COLORS.grid }}
                  tickLine={false}
                  interval={0}
                  angle={-28}
                  textAnchor="end"
                  height={56}
                />
                <YAxis
                  tick={CHART_TICK}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                  label={{
                    value: "Tareas",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: CHART_COLORS.muted, fontSize: 11 },
                  }}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    const row = teamRows.find((r) => r.name === label)
                    return (
                      <ChartTooltip
                        active={active}
                        label={row?.fullName ?? label}
                        payload={payload?.map((p) => ({
                          name: p.name,
                          value: p.value as number,
                          color: p.color,
                        }))}
                      />
                    )
                  }}
                />
                <Legend iconType="square" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                <Bar dataKey="abiertas" name="Abiertas" fill={CHART_COLORS[1]} radius={[4, 4, 0, 0]} />
                <Bar dataKey="completadas" name="Completadas" fill={CHART_COLORS[2]} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </section>
      ) : null}
    </>
  )
}
