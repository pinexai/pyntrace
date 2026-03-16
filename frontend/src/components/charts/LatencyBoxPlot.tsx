import type { LatencyEndpoint } from '../../types'

interface Props { endpoints: LatencyEndpoint[] }

export default function LatencyBoxPlot({ endpoints }: Props) {
  const data = endpoints.slice(0, 12).map(r => ({
    name: (r.endpoint || '?').split('/').pop()?.slice(0, 16) || r.endpoint.slice(0, 16),
    p50: r.p50_ms || 0,
    p95: r.p95_ms || 0,
    p99: r.p99_ms || 0,
  }))

  const maxVal = Math.max(...data.map(d => d.p99)) || 1

  return (
    <div className="space-y-2">
      {data.map(d => (
        <div key={d.name} className="flex items-center gap-3 text-sm">
          <div className="w-28 text-t3 text-right text-xs truncate" title={d.name}>{d.name}</div>
          <div className="flex-1 relative h-6 flex items-center">
            <div className="absolute inset-0 bg-border/20 rounded" />
            {/* p50 bar */}
            <div
              className="absolute h-4 rounded-sm opacity-80"
              style={{ left: 0, width: `${(d.p50 / maxVal) * 100}%`, background: '#38bdf8' }}
              title={`p50: ${d.p50}ms`}
            />
            {/* p95 marker */}
            <div
              className="absolute w-0.5 h-5 rounded"
              style={{ left: `${(d.p95 / maxVal) * 100}%`, background: '#fbbf24' }}
              title={`p95: ${d.p95}ms`}
            />
            {/* p99 marker */}
            <div
              className="absolute w-0.5 h-5 rounded"
              style={{ left: `${(d.p99 / maxVal) * 100}%`, background: '#f87171' }}
              title={`p99: ${d.p99}ms`}
            />
          </div>
          <div className="w-20 text-xs text-t3 tabular-nums">
            <span style={{ color: '#38bdf8' }}>{d.p50}</span>/<span style={{ color: '#fbbf24' }}>{d.p95}</span>/<span style={{ color: '#f87171' }}>{d.p99}</span>ms
          </div>
        </div>
      ))}
      <div className="flex gap-4 text-xs text-t3 mt-2 ml-32">
        <span><span style={{ color: '#38bdf8' }}>■</span> p50</span>
        <span><span style={{ color: '#fbbf24' }}>|</span> p95</span>
        <span><span style={{ color: '#f87171' }}>|</span> p99</span>
      </div>
    </div>
  )
}
