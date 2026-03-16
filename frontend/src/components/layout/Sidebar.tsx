import type { TabName } from '../../types'

interface SidebarProps {
  tab: TabName
  onNavigate: (t: TabName) => void
  counts: Partial<Record<TabName, number | string>>
}

const SECTIONS = [
  {
    label: 'Security',
    items: [
      { id: 'security' as TabName, icon: '🔍', label: 'Security' },
      { id: 'mcp'      as TabName, icon: '🔌', label: 'MCP Scans' },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { id: 'eval'    as TabName, icon: '📊', label: 'Eval' },
      { id: 'monitor' as TabName, icon: '📡', label: 'Monitor' },
      { id: 'latency' as TabName, icon: '⚡', label: 'Latency' },
      { id: 'costs'   as TabName, icon: '💰', label: 'Costs' },
      { id: 'git'     as TabName, icon: '🔀', label: 'Git' },
    ],
  },
  {
    label: 'Governance',
    items: [
      { id: 'review'     as TabName, icon: '✅', label: 'Review' },
      { id: 'compliance' as TabName, icon: '📋', label: 'Compliance' },
    ],
  },
]

export default function Sidebar({ tab, onNavigate, counts }: SidebarProps) {
  return (
    <aside
      aria-label="Navigation"
      style={{ gridArea: 'sidebar', background: '#111120', borderRight: '1px solid #25254a', overflowY: 'auto' }}
      className="py-3"
    >
      <nav role="tablist" aria-orientation="vertical" aria-label="Dashboard sections">
        {SECTIONS.map((sec, si) => (
          <div key={sec.label}>
            {si > 0 && <div className="mx-3 my-2 border-t border-border" />}
            <div className="px-4 pt-3 pb-1 text-xs font-semibold uppercase tracking-widest text-t3">{sec.label}</div>
            {sec.items.map(item => {
              const active = item.id === tab
              return (
                <button
                  key={item.id}
                  role="tab"
                  aria-selected={active}
                  aria-current={active ? 'page' : undefined}
                  data-tab={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={[
                    'w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-all rounded-none',
                    active
                      ? 'bg-accent/10 text-t1 border-r-2 border-accent font-medium'
                      : 'text-t2 hover:bg-white/5 hover:text-t1',
                  ].join(' ')}
                >
                  <span aria-hidden="true" className="text-base">{item.icon}</span>
                  <span className="flex-1 text-left">{item.label}</span>
                  <span className="text-xs text-t3 tabular-nums min-w-[1.5rem] text-right">
                    {counts[item.id] ?? '—'}
                  </span>
                </button>
              )
            })}
          </div>
        ))}
      </nav>
    </aside>
  )
}
