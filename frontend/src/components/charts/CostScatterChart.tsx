import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { CostSummary } from '../../types'

interface Props { data: CostSummary[] }

export default function CostScatterChart({ data }: Props) {
  const points = data.map(r => ({ x: r.avg_ms || 0, y: r.total_cost || 0, name: r.model }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" stroke="#25254a" />
        <XAxis dataKey="x" type="number" stroke="#859ab5" tick={{ fontSize: 10 }} name="Avg Latency (ms)" unit="ms" />
        <YAxis dataKey="y" type="number" stroke="#859ab5" tick={{ fontSize: 10 }} name="Total Cost" tickFormatter={v => `$${v.toFixed(3)}`} />
        <Tooltip
          contentStyle={{ background: '#18182e', border: '1px solid #25254a', borderRadius: 8 }}
          formatter={(v: number, name: string) => [name === 'x' ? `${v}ms` : `$${v.toFixed(4)}`, name === 'x' ? 'Latency' : 'Cost']}
        />
        <Scatter data={points} fill="#c084fc" opacity={0.8} />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
