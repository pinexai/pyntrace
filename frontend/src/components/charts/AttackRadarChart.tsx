import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts'
import type { SecurityReport } from '../../types'

interface Props { reports: SecurityReport[] }

const AXES = ['Injection', 'Jailbreak', 'PII/Leakage', 'MultiAgent', 'Toolchain', 'Other']
const KWS  = [['inject','prompt'], ['jailbreak','refuse','escape'], ['pii','leak','privacy'], ['agent','multi','swarm'], ['tool','chain','function'], []]

export default function AttackRadarChart({ reports }: Props) {
  const counts: Record<string, number> = {}
  reports.forEach(r => {
    if (!r.results_json) return
    try {
      const res = typeof r.results_json === 'string' ? JSON.parse(r.results_json) : r.results_json
      if (Array.isArray(res)) res.forEach((item: { plugin?: string; vulnerable?: boolean }) => {
        if (item.plugin && item.vulnerable) counts[item.plugin.toLowerCase()] = (counts[item.plugin.toLowerCase()] || 0) + 1
      })
    } catch (_) {}
  })

  const vals = AXES.map((_, ai) => {
    const kws = KWS[ai]
    if (!kws.length) {
      const known = KWS.slice(0, 5).flat()
      return Object.entries(counts).filter(([k]) => !known.some(w => k.includes(w))).reduce((s, [, v]) => s + v, 0)
    }
    return Object.entries(counts).filter(([k]) => kws.some(w => k.includes(w))).reduce((s, [, v]) => s + v, 0)
  })
  const max = Math.max(...vals) || 1

  const data = AXES.map((name, i) => ({ subject: name, value: +(vals[i] / max * 10).toFixed(1) }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="#25254a" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#b8c5d6', fontSize: 11 }} />
        <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#859ab5', fontSize: 9 }} />
        <Radar dataKey="value" stroke="#c084fc" fill="#c084fc" fillOpacity={0.15} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
