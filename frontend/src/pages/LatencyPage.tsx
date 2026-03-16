import { useLatencyEndpoints } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import LatencyBoxPlot from '../components/charts/LatencyBoxPlot'

export default function LatencyPage() {
  const { data, isLoading } = useLatencyEndpoints()

  if (isLoading) return <SkeletonLoader />

  const rows = data ?? []

  if (!rows.length) return (
    <EmptyState
      icon="⚡"
      title="No latency data yet"
      desc="Instrument your LLM endpoints to capture p50/p95/p99 latency profiles."
      cmd="import pyntrace; pyntrace.init()"
    />
  )

  const p50avg = rows.reduce((s, r) => s + (r.p50_ms || 0), 0) / rows.length
  const p95avg = rows.reduce((s, r) => s + (r.p95_ms || 0), 0) / rows.length
  const slow   = rows.filter(r => (r.p95_ms || 0) > 2000).length

  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Endpoints"  value={rows.length}          variant="accent" />
        <MetricCard label="Avg p50"    value={`${Math.round(p50avg)}ms`} variant="info" />
        <MetricCard label="Avg p95"    value={`${Math.round(p95avg)}ms`} variant={p95avg > 2000 ? 'danger' : p95avg > 1000 ? 'warn' : 'success'} />
        <MetricCard label="Slow (p95>2s)" value={slow}              variant={slow > 0 ? 'danger' : 'success'} />
      </div>

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Latency Distribution (Box Plot)</div>
        <LatencyBoxPlot endpoints={rows} />
      </div>

      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Endpoint Breakdown</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'endpoint',   label: 'Endpoint' },
            { key: 'calls',      label: 'Calls' },
            { key: 'p50_ms',     label: 'p50',  render: (v) => `${Math.round(v as number)}ms` },
            { key: 'p95_ms',     label: 'p95',  render: (v) => {
              const ms = v as number
              return <span style={{ color: ms > 2000 ? '#f87171' : ms > 1000 ? '#fbbf24' : '#4ade80' }}>{Math.round(ms)}ms</span>
            }},
            { key: 'p99_ms',     label: 'p99',  render: (v) => `${Math.round(v as number)}ms` },
            { key: 'error_rate', label: 'Error Rate',
              render: (v) => v != null ? `${((v as number) * 100).toFixed(1)}%` : '—' },
          ]}
        />
      </div>
    </div>
  )
}
