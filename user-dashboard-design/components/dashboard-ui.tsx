import { cn } from "@/lib/utils"
import { ArrowUpRight } from "lucide-react"

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: React.ReactNode
}) {
  return (
    <header className="flex flex-col gap-3 border-b border-border bg-card/40 px-4 py-5 sm:px-6 md:flex-row md:items-center md:justify-between md:py-6">
      <div className="min-w-0">
        <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground text-pretty">{description}</p>
        ) : null}
      </div>
      {children ? <div className="flex shrink-0 items-center gap-2">{children}</div> : null}
    </header>
  )
}

export function StatCard({
  label,
  value,
  hint,
  accent,
  icon,
}: {
  label: string
  value: string | number
  hint?: string
  accent?: "default" | "success" | "warning" | "danger"
  icon?: React.ReactNode
}) {
  const accentColor = {
    default: "text-foreground",
    success: "text-chart-2",
    warning: "text-chart-3",
    danger: "text-destructive",
  }[accent ?? "default"]
  const accentSurface = {
    default: "bg-card",
    success: "bg-chart-2/[0.06]",
    warning: "bg-chart-3/[0.07]",
    danger: "bg-destructive/[0.06]",
  }[accent ?? "default"]
  const iconSurface = {
    default: "bg-primary/10 text-primary",
    success: "bg-chart-2/15 text-chart-2",
    warning: "bg-chart-3/15 text-chart-3",
    danger: "bg-destructive/10 text-destructive",
  }[accent ?? "default"]

  return (
    <div
      className={cn(
        "group relative h-full overflow-hidden rounded-xl border border-border px-4 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-sm",
        accentSurface,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className={cn("mt-2 text-2xl font-semibold tracking-tight tabular-nums", accentColor)}>
            {value}
          </p>
        </div>
        {icon ? (
          <span className={cn("flex h-9 w-9 items-center justify-center rounded-lg", iconSurface)}>
            {icon}
          </span>
        ) : null}
      </div>
      <div className="mt-2 flex min-h-4 items-center justify-between gap-2">
        {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : <span />}
        <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground/50 transition-colors group-hover:text-primary" />
      </div>
    </div>
  )
}

export function SectionHeader({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: React.ReactNode
}) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <div>
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {description ? <p className="mt-0.5 text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card/40 px-4 py-10 text-center">
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  )
}
