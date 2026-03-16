import { useSecurityReports } from '../api/queries'
import MetricCard from '../components/shared/MetricCard'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'
import VulnTrendLine from '../components/charts/VulnTrendLine'
import AttackRadarChart from '../components/charts/AttackRadarChart'
import type { SecurityReport } from '../types'

interface SecurityPageProps {
  onRowClick: (row: SecurityReport) => void
}

export default function SecurityPage({ onRowClick }: SecurityPageProps) {
  const { data, isLoading } = useSecurityReports()

  if (isLoading) return <SkeletonLoader />

  const rows = data ?? []

  if (!rows.length) return (
    <EmptyState
      icon="🔍"
      title="No security scans yet"
      desc="Run your first red-team scan to see vulnerability results here."
      cmd="pyntrace scan myapp:chatbot"
      est="~2 min"
    />
  )

  const avgVuln   = rows.reduce((s, r) => s + (r.vulnerability_rate || 0), 0) / rows.length
  const totalCost = rows.reduce((s, r) => s + (r.total_cost_usd || 0), 0)
  const critical  = rows.filter(r => (r.vulnerability_rate || 0) > 0.15).length
  const score     = Math.round((1 - avgVuln) * 100)

  const gradeLabel = score >= 85 ? 'Excellent' : score >= 65 ? 'Good' : score >= 40 ? 'Fair' : 'At Risk'
  const gradeColor = score >= 85 ? '#4ade80' : score >= 65 ? '#38bdf8' : score >= 40 ? '#fbbf24' : '#f87171'

  return (
    <div className="p-6 space-y-5">
      {/* Health score */}
      <div className="bg-card rounded-xl border border-border p-5 flex items-center gap-6">
        <div
          role="img"
          aria-label={`Security health score: ${score}/100`}
          className="relative w-20 h-20 flex-shrink-0"
        >
          <svg width="80" height="80" viewBox="0 0 80 80">
            <circle cx="40" cy="40" r="32" fill="none" stroke="#25254a" strokeWidth="6" />
            <circle
              cx="40" cy="40" r="32" fill="none"
              stroke={gradeColor} strokeWidth="6"
              strokeDasharray={`${2 * Math.PI * 32}`}
              strokeDashoffset={`${(2 * Math.PI * 32) * (1 - score / 100)}`}
              strokeLinecap="round"
              transform="rotate(-90 40 40)"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold text-t1">{score}</span>
            <span className="text-xs text-t3">/100</span>
          </div>
        </div>
        <div>
          <div className="text-sm text-t3 mb-1">Security Health Score</div>
          <div className="text-xl font-bold" style={{ color: gradeColor }}>{gradeLabel}</div>
          <div className="text-xs text-t3 mt-1">
            {rows.length} scans · avg {(avgVuln * 100).toFixed(1)}% vuln rate · ${totalCost.toFixed(4)} spent
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total Scans"  value={rows.length} variant="accent" />
        <MetricCard label="Avg Vuln Rate" value={`${(avgVuln * 100).toFixed(1)}%`} variant={avgVuln > 0.15 ? 'danger' : avgVuln > 0.05 ? 'warn' : 'success'} />
        <MetricCard label="Critical Scans" value={critical} variant={critical > 0 ? 'danger' : 'success'} />
        <MetricCard label="Total Cost" value={`$${totalCost.toFixed(4)}`} variant="info" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="text-sm font-semibold text-t2 mb-3">Vulnerability Trend</div>
          <VulnTrendLine reports={rows} />
        </div>
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="text-sm font-semibold text-t2 mb-3">Attack Exposure Radar</div>
          <AttackRadarChart reports={rows} />
        </div>
      </div>

      {/* Table */}
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Red Team Reports</div>
        <DataTable
          rows={rows as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'target_fn',         label: 'Target' },
            { key: 'model',             label: 'Model' },
            { key: 'total_attacks',     label: 'Attacks' },
            { key: 'vulnerable_count',  label: 'Vulns' },
            { key: 'vulnerability_rate', label: 'Vuln Rate',
              render: (v) => {
                const rate = v as number
                const cls = rate > 0.15 ? '#f87171' : rate > 0.05 ? '#fbbf24' : '#4ade80'
                return <span style={{ color: cls }}>{(rate * 100).toFixed(1)}%</span>
              }
            },
            { key: 'total_cost_usd',    label: 'Cost',
              render: (v) => `$${(v as number).toFixed(4)}` },
            { key: 'created_at',        label: 'Date',
              render: (v) => new Date((v as number) * 1000).toLocaleDateString() },
          ]}
          onRowClick={(row) => onRowClick(row as unknown as SecurityReport)}
        />
      </div>
    </div>
  )
}
