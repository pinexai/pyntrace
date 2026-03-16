import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts'
import type { CostSummary } from '../../types'

interface Props { data: CostSummary[] }

export default function SpendBarChart({ data }: Props) {
  const chartData = data.map(r => ({ name: (r.model || '?').slice(0, 12), cost: r.total_cost || 0 }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25254a" />
        <XAxis dataKey="name" stroke="#859ab5" tick={{ fontSize: 10 }} />
        <YAxis stroke="#859ab5" tick={{ fontSize: 10 }} tickFormatter={v => `$${v.toFixed(2)}`} />
        <Tooltip
          contentStyle={{ background: '#18182e', border: '1px solid #25254a', borderRadius: 8 }}
          formatter={(v: number) => [`$${v.toFixed(4)}`, 'Cost']}
        />
        <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={`rgba(192,132,252,${0.6 + i / chartData.length * 0.3})`} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
