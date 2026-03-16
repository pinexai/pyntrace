import { useState, useEffect } from 'react'

interface HeaderProps {
  onSearch: () => void
}

export default function Header({ onSearch }: HeaderProps) {
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'error'>('connecting')
  const [version, setVersion] = useState('')

  useEffect(() => {
    fetch('/api/security/reports?limit=1')
      .then(r => setVersion(r.headers.get('x-pyntrace-version') || ''))
      .catch(() => {})
  }, [])

  return (
    <header
      className="app-header col-span-2 flex items-center px-5 gap-4 z-50"
      style={{ gridArea: 'header', background: 'rgba(17,17,32,0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #25254a' }}
    >
      <div className="flex items-center gap-2 flex-1">
        <span className="text-accent font-bold tracking-tight text-base">pyntrace</span>
        {version && <span className="text-xs text-t3 bg-surface px-2 py-0.5 rounded-full border border-border">{version}</span>}
      </div>

      <button
        onClick={onSearch}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-t3 text-sm hover:border-accent hover:text-t1 transition-colors"
        aria-label="Open global search"
      >
        <span>⌕</span>
        <span>Search…</span>
        <kbd className="text-xs opacity-60 ml-2">⌘K</kbd>
      </button>

      <div
        role="img"
        aria-label={`WebSocket: ${wsStatus}`}
        className="w-2 h-2 rounded-full"
        style={{ background: wsStatus === 'connected' ? '#4ade80' : wsStatus === 'error' ? '#f87171' : '#fbbf24' }}
        title={`WebSocket: ${wsStatus}`}
        id="wsStatusReact"
      />
    </header>
  )
}
