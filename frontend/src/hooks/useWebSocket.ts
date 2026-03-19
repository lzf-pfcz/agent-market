import { useState, useEffect, useRef, useCallback } from 'react'
import type { PlatformEvent } from '../types'

interface UseMonitorWebSocketOptions {
  onEvent?: (event: PlatformEvent) => void
}

export function useMonitorWebSocket(options: UseMonitorWebSocketOptions = {}) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<(PlatformEvent & { ts: string })[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<NodeJS.Timeout>()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket('ws://localhost:8000/ws/monitor')
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // 开始心跳
      const heartbeat = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 30000)
      ws.onclose = () => {
        clearInterval(heartbeat)
        setConnected(false)
        // 5秒后重连
        reconnectTimer.current = setTimeout(connect, 5000)
      }
    }

    ws.onmessage = (e) => {
      if (e.data === 'pong') return
      try {
        const event: PlatformEvent = JSON.parse(e.data)
        const entry = { ...event, ts: new Date().toLocaleTimeString() }
        setEvents(prev => [entry, ...prev].slice(0, 100))
        options.onEvent?.(event)
      } catch {}
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected, events }
}
