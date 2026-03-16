import { useComplianceReports } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'

export default function CompliancePage() {
  const { data, isLoading } = useComplianceReports()
  if (isLoading) return <SkeletonLoader />
  const items = data ?? []
  if (!items.length) return <EmptyState icon="📋" title="No compliance reports" desc="Generate a compliance report for your security framework." cmd="pyntrace compliance --framework owasp_llm_top10" />
  const passed = items.filter(r => r.overall_status === 'pass' || r.overall_status === 'compliant').length
  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-2 gap-4">
        <MetricCard label="Reports" value={items.length} variant="accent" />
        <MetricCard label="Passing"  value={`${passed}/${items.length}`} variant={passed === items.length ? 'success' : 'warn'} />
      </div>
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Compliance Reports</div>
        <DataTable
          rows={items as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'framework',      label: 'Framework' },
            { key: 'overall_status', label: 'Status',
              render: (v) => {
                const ok = v === 'pass' || v === 'compliant'
                return <span className={`text-xs px-1.5 py-0.5 rounded ${ok ? 'text-green-300 bg-green-500/20' : 'text-red-300 bg-red-500/20'}`}>{String(v)}</span>
              }
            },
            { key: 'created_at', label: 'Date', render: (v) => new Date((v as number) * 1000).toLocaleDateString() },
          ]}
        />
      </div>
    </div>
  )
}
