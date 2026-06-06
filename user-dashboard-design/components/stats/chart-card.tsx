import type { ReactNode } from "react"

export function ChartCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      <div className="mt-4">{children}</div>
      {footer ? <div className="mt-3 border-t border-border pt-3">{footer}</div> : null}
    </div>
  )
}
