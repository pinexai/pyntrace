import { useCostSummary, useDailyCosts } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import SpendBarChart from '../components/charts/SpendBarChart'
import DailySpendLine from '../components/charts/DailySpendLine'
import CostScatterChart from '../components/charts/CostScatterChart'

export default function CostsPage() {
  const { data, isLoading } = useCostSummary()
  const { data: daily } = useDailyCosts()

  if (isLoading) return <SkeletonLoader />

  const rows = data ?? []

  if (!rows.length) return (
    <EmptyState
      icon="💰"
      title="No cost data yet"
      desc="Initialize pyntrace to start tracking LLM API costs in real time."
      cmd="import pyntrace; pyntrace.init()"
    />
  )

  const total = rows.reduce((s, r) => s + (r.total_cost || 0), 0)
  const calls = rows.reduce((s, r) => s + (r.calls || 0), 0)

  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Models"     value={rows.length}          variant="accent" />
        <MetricCard label="Total Calls" value={calls}               variant="info" />
        <MetricCard label="Total Cost" value={`$${total.toFixed(4)}`} variant="warn" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="text-sm font-semibold text-t2 mb-3">Cost per Model</div>
          <SpendBarChart data={rows} />
        </div>
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="text-sm font-semibold text-t2 mb-3">Cost vs Latency</div>
          <CostScatterChart data={rows} />
        </div>
      </div>

      {daily && daily.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="text-sm font-semibold text-t2 mb-3">Daily Spend (30d)</div>
          <DailySpendLine data={daily} />
        </div>
      )}

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Breakdown</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'model',      label: 'Model' },
            { key: 'calls',      label: 'Calls' },
            { key: 'total_cost', label: 'Total Cost', render: (v) => `$${(v as number).toFixed(4)}` },
            { key: 'avg_ms',     label: 'Avg Latency', render: (v) => v != null ? `${Math.round(v as number)}ms` : '—' },
          ]}
        />
      </div>
    </div>
  )
}
