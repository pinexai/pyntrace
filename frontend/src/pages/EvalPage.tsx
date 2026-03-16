import { useEvalExperiments } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'

export default function EvalPage() {
  const { data, isLoading } = useEvalExperiments()
  if (isLoading) return <SkeletonLoader />
  const rows = data ?? []
  if (!rows.length) return <EmptyState icon="📊" title="No experiments yet" desc="Run an evaluation experiment to compare model outputs across prompts." cmd="pyntrace eval run experiment.py" est="~5 min" />
  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Experiments" value={rows.length} variant="accent" />
        <MetricCard label="Avg Pass Rate" value={`${(rows.filter(r => r.pass_rate != null).reduce((s, r) => s + (r.pass_rate || 0), 0) / Math.max(rows.length, 1) * 100).toFixed(1)}%`} variant="info" />
      </div>
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Experiments</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'name',          label: 'Name' },
            { key: 'function_name', label: 'Function' },
            { key: 'git_commit',    label: 'Git Commit', render: (v) => v ? String(v).slice(0, 7) : '—' },
            { key: 'pass_rate',     label: 'Pass Rate', render: (v) => v != null ? `${((v as number) * 100).toFixed(1)}%` : '—' },
            { key: 'created_at',    label: 'Date', render: (v) => new Date((v as number) * 1000).toLocaleDateString() },
          ]}
        />
      </div>
    </div>
  )
}
