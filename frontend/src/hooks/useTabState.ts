import { useState, useCallback } from 'react'
import type { TabName } from '../types'

export function useTabState(initial: TabName = 'security') {
  const [tab, setTab] = useState<TabName>(initial)
  const navigate = useCallback((t: TabName) => setTab(t), [])
  return { tab, navigate }
}
