import { useGitHistory } from '../api/queries'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'

export default function GitPage() {
  const { data, isLoading } = useGitHistory()
  if (isLoading) return <SkeletonLoader />
  const rows = data ?? []
  if (!rows.length) return <EmptyState icon="🔀" title="No regression history" desc="Run scans across multiple git commits to detect regressions." />
  const last = rows[0]?.avg_vuln_rate || 0
  const prev = rows[1]?.avg_vuln_rate || 0
  const regression = rows.length >= 2 && last > prev * 1.05
  return (
    <div className="p-6 space-y-5">
      {regression && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          ⚠ Regression detected: latest commit vuln rate {(last * 100).toFixed(1)}% vs previous {(prev * 100).toFixed(1)}%
        </div>
      )}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Git Regression History</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'git_commit',    label: 'Commit', render: (v) => <span className="font-mono text-xs">{String(v).slice(0, 7)}</span> },
            { key: 'scans',         label: 'Scans' },
            { key: 'avg_vuln_rate', label: 'Avg Vuln Rate',
              render: (v) => {
                const r = v as number
                return <span style={{ color: r > 0.15 ? '#f87171' : r > 0.05 ? '#fbbf24' : '#4ade80' }}>{(r * 100).toFixed(1)}%</span>
              }
            },
            { key: 'total_cost', label: 'Total Cost', render: (v) => `$${(v as number).toFixed(4)}` },
          ]}
        />
      </div>
    </div>
  )
}
