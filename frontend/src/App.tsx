import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import Header from './components/layout/Header'
import Sidebar from './components/layout/Sidebar'
import SecurityPage from './pages/SecurityPage'
import McpPage from './pages/McpPage'
import EvalPage from './pages/EvalPage'
import MonitorPage from './pages/MonitorPage'
import LatencyPage from './pages/LatencyPage'
import CostsPage from './pages/CostsPage'
import ReviewPage from './pages/ReviewPage'
import CompliancePage from './pages/CompliancePage'
import GitPage from './pages/GitPage'
import { useTabState } from './hooks/useTabState'
import { useWebSocket } from './hooks/useWebSocket'
import type { TabName, SecurityReport, Trace } from './types'

const TAB_META: Record<TabName, { label: string; icon: string }> = {
  security:   { label: 'Security',   icon: '🔍' },
  mcp:        { label: 'MCP Scans',  icon: '🔌' },
  eval:       { label: 'Eval',       icon: '📊' },
  monitor:    { label: 'Monitor',    icon: '📡' },
  latency:    { label: 'Latency',    icon: '⚡' },
  costs:      { label: 'Costs',      icon: '💰' },
  review:     { label: 'Review',     icon: '✅' },
  compliance: { label: 'Compliance', icon: '📋' },
  git:        { label: 'Git',        icon: '🔀' },
}

export default function App() {
  const { tab, navigate } = useTabState('security')
  const [searchOpen, setSearchOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailTitle, setDetailTitle] = useState('')
  const [detailContent, setDetailContent] = useState<React.ReactNode>(null)
  const qc = useQueryClient()

  useWebSocket(useCallback((msg) => {
    if (msg.type === 'scan_completed' || msg.type === 'refresh') {
      void qc.invalidateQueries()
    }
  }, [qc]))

  const openDetail = useCallback((title: string, content: React.ReactNode) => {
    setDetailTitle(title)
    setDetailContent(content)
    setDetailOpen(true)
  }, [])

  const handleSecurityRowClick = useCallback((row: SecurityReport) => {
    openDetail(row.target_fn || 'Scan Detail', (
      <div className="space-y-4 p-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          {(['id', 'model', 'model_provider', 'total_attacks', 'vulnerable_count',
             'vulnerability_rate', 'total_cost_usd', 'avg_latency_ms', 'status', 'git_commit'] as (keyof SecurityReport)[]).map(k => (
            row[k] != null && (
              <div key={k} className="flex flex-col gap-0.5">
                <span className="text-xs text-t3 uppercase tracking-wide">{k.replace(/_/g, ' ')}</span>
                <span className="text-t1 font-medium">{String(row[k])}</span>
              </div>
            )
          ))}
        </div>
      </div>
    ))
  }, [openDetail])

  const handleTraceClick = useCallback((trace: Trace) => {
    const dur = trace.end_time && trace.start_time
      ? `${((trace.end_time - trace.start_time) * 1000).toFixed(0)}ms`
      : '—'
    openDetail(trace.name || 'Trace', (
      <div className="p-4 space-y-3 text-sm">
        <div className="text-t3"><span className="uppercase tracking-wide text-xs">ID</span> <span className="font-mono text-t1">{trace.id}</span></div>
        <div className="text-t3"><span className="uppercase tracking-wide text-xs">Duration</span> <span className="text-t1">{dur}</span></div>
        <div className="text-t3"><span className="uppercase tracking-wide text-xs">Status</span> {trace.error
          ? <span className="text-red-300 bg-red-500/20 text-xs px-1.5 py-0.5 rounded ml-1">Error</span>
          : <span className="text-green-300 bg-green-500/20 text-xs px-1.5 py-0.5 rounded ml-1">OK</span>
        }</div>
      </div>
    ))
  }, [openDetail])

  const metaCurrent = TAB_META[tab]

  return (
    <div className="app-grid">
      <Header onSearch={() => setSearchOpen(true)} />
      <Sidebar tab={tab} onNavigate={navigate} counts={{}} />

      <main
        style={{ gridArea: 'main', overflowY: 'auto', background: '#09090f' }}
        role="tabpanel"
        aria-live="polite"
        aria-label={`${metaCurrent.label} content`}
      >
        {/* Breadcrumb */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-6 py-3 border-b border-border" style={{ background: 'rgba(9,9,15,0.9)', backdropFilter: 'blur(8px)' }}>
          <div className="text-sm text-t3">
            pyntrace <span className="mx-1">›</span>
            <span className="text-t1 font-medium">{metaCurrent.icon} {metaCurrent.label}</span>
          </div>
        </div>

        {tab === 'security'   && <SecurityPage onRowClick={handleSecurityRowClick} />}
        {tab === 'mcp'        && <McpPage />}
        {tab === 'eval'       && <EvalPage />}
        {tab === 'monitor'    && <MonitorPage onTraceClick={handleTraceClick} />}
        {tab === 'latency'    && <LatencyPage />}
        {tab === 'costs'      && <CostsPage />}
        {tab === 'review'     && <ReviewPage />}
        {tab === 'compliance' && <CompliancePage />}
        {tab === 'git'        && <GitPage />}
      </main>

      {/* Detail slide-over */}
      {detailOpen && (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          onClick={() => setDetailOpen(false)}
        >
          <div
            className="w-full max-w-lg h-full overflow-y-auto shadow-2xl"
            style={{ background: '#111120', borderLeft: '1px solid #25254a' }}
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Item detail"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border sticky top-0 bg-surface">
              <span className="font-semibold text-t1 text-sm">{detailTitle}</span>
              <button
                className="w-8 h-8 flex items-center justify-center rounded-lg border border-border text-t3 hover:text-t1 hover:bg-card"
                onClick={() => setDetailOpen(false)}
                aria-label="Close detail panel"
              >✕</button>
            </div>
            <div className="text-sm text-t1">{detailContent}</div>
          </div>
        </div>
      )}

      {/* Search modal */}
      {searchOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/70 backdrop-blur-sm"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="w-full max-w-xl rounded-2xl shadow-2xl border border-border overflow-hidden"
            style={{ background: '#111120' }}
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-label="Global search"
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
              <span className="text-t3">⌕</span>
              <input
                autoFocus
                className="flex-1 bg-transparent text-t1 text-sm outline-none placeholder:text-t3"
                placeholder="Search across all tabs… (Cmd+K)"
                onKeyDown={e => { if (e.key === 'Escape') setSearchOpen(false) }}
                aria-label="Global search input"
              />
              <kbd className="text-xs text-t3">ESC</kbd>
            </div>
            <div className="p-4 text-sm text-t3 text-center">
              Start typing to search across all tabs…
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
