import { useMcpScans } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'

export default function McpPage() {
  const { data, isLoading } = useMcpScans()
  if (isLoading) return <SkeletonLoader />
  const rows = data ?? []
  if (!rows.length) return <EmptyState icon="🔌" title="No MCP scans yet" desc="Scan an MCP server endpoint for security vulnerabilities." cmd="pyntrace scan-mcp http://localhost:3000" est="~1 min" />
  const totalTests = rows.reduce((s, r) => s + (r.total_tests || 0), 0)
  const totalVulns = rows.reduce((s, r) => s + (r.vulnerable_count || 0), 0)
  return (
    <div className="p-6 space-y-5">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="MCP Scans"       value={rows.length}  variant="accent" />
        <MetricCard label="Total Tests"     value={totalTests}   variant="info" />
        <MetricCard label="Vulnerabilities" value={totalVulns}   variant={totalVulns > 0 ? 'danger' : 'success'} />
      </div>
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">MCP Security Scans</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'endpoint',        label: 'Endpoint' },
            { key: 'total_tests',     label: 'Tests' },
            { key: 'vulnerable_count', label: 'Vulns' },
            { key: 'created_at',      label: 'Date', render: (v) => new Date((v as number) * 1000).toLocaleDateString() },
          ]}
        />
      </div>
    </div>
  )
}
