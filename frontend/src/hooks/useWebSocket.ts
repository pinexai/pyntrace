import { useEffect, useRef, useCallback } from 'react'

type WsMessage = { type: string; [key: string]: unknown }

export function useWebSocket(onMessage: (msg: WsMessage) => void) {
  const wsRef  = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()
  const onMsgRef = useRef(onMessage)
  onMsgRef.current = onMessage

  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${location.host}/ws`)
    wsRef.current = ws

    ws.onmessage = (e: MessageEvent) => {
      try { onMsgRef.current(JSON.parse(e.data as string) as WsMessage) } catch (_) {}
    }
    ws.onclose = () => {
      timerRef.current = setTimeout(connect, 5000)
    }
    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
    }, 30_000)
    ws.addEventListener('close', () => clearInterval(ping))
  }, [])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      clearTimeout(timerRef.current)
    }
  }, [connect])

  return wsRef
}
