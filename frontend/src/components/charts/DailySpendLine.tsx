import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import type { DailyCost } from '../../types'

interface Props { data: DailyCost[] }

export default function DailySpendLine({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#25254a" />
        <XAxis dataKey="date" stroke="#859ab5" tick={{ fontSize: 10 }} />
        <YAxis stroke="#859ab5" tick={{ fontSize: 10 }} tickFormatter={v => `$${v.toFixed(3)}`} />
        <Tooltip
          contentStyle={{ background: '#18182e', border: '1px solid #25254a', borderRadius: 8 }}
          formatter={(v: number) => [`$${v.toFixed(6)}`, 'Daily Cost']}
        />
        <Area type="monotone" dataKey="cost" stroke="#c084fc" fill="rgba(192,132,252,0.12)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
