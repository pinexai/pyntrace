interface MetricCardProps {
  label: string
  value: string | number
  variant?: 'accent' | 'success' | 'warn' | 'danger' | 'info'
}

const variantColor: Record<string, string> = {
  accent:  '#c084fc',
  success: '#4ade80',
  warn:    '#fbbf24',
  danger:  '#f87171',
  info:    '#38bdf8',
}

export default function MetricCard({ label, value, variant = 'accent' }: MetricCardProps) {
  return (
    <div className="bg-card rounded-xl border border-border p-4 flex flex-col gap-1">
      <div className="text-xs text-t3 font-medium uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color: variantColor[variant] }}>{value}</div>
    </div>
  )
}
