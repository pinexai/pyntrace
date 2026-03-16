import { useTraces } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import type { Trace } from '../types'

interface Props { onTraceClick: (trace: Trace) => void }

export default function MonitorPage({ onTraceClick }: Props) {
  const { data, isLoading } = useTraces()
  if (isLoading) return <SkeletonLoader />
  const rows = data ?? []
  if (!rows.length) return <EmptyState icon="📡" title="No traces recorded" desc="Initialize pyntrace in your app to start recording production traces." cmd="import pyntrace; pyntrace.init()" />
  const errorCount = rows.filter(r => r.error).length
  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Traces" value={rows.length}  variant="accent" />
        <MetricCard label="Errors" value={errorCount}   variant={errorCount > 0 ? 'danger' : 'success'} />
      </div>
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Trace Timeline</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'name',       label: 'Name' },
            { key: 'start_time', label: 'Time', render: (v) => new Date((v as number) * 1000).toLocaleString() },
            { key: 'error',      label: 'Status',
              render: (v) => v
                ? <span className="text-xs text-red-300 bg-red-500/20 px-1.5 py-0.5 rounded">Error</span>
                : <span className="text-xs text-green-300 bg-green-500/20 px-1.5 py-0.5 rounded">OK</span>
            },
          ]}
          onRowClick={(row) => onTraceClick(row as unknown as Trace)}
        />
      </div>
    </div>
  )
}
