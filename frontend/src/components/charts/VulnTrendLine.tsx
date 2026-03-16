import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { SecurityReport } from '../../types'

interface Props { reports: SecurityReport[] }

export default function VulnTrendLine({ reports }: Props) {
  const data = [...reports].reverse().map((r, i) => ({
    name: `#${i + 1}`,
    vuln: +((r.vulnerability_rate || 0) * 100).toFixed(1),
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25254a" />
        <XAxis dataKey="name" stroke="#859ab5" tick={{ fontSize: 10 }} />
        <YAxis stroke="#859ab5" tick={{ fontSize: 10 }} tickFormatter={v => `${v}%`} />
        <Tooltip
          contentStyle={{ background: '#18182e', border: '1px solid #25254a', borderRadius: 8 }}
          formatter={(v: number) => [`${v}%`, 'Vuln Rate']}
        />
        <Line type="monotone" dataKey="vuln" stroke="#c084fc" strokeWidth={2} dot={{ r: 3, fill: '#c084fc' }} fill="rgba(192,132,252,0.1)" />
      </LineChart>
    </ResponsiveContainer>
  )
}
