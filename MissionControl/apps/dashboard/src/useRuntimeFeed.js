import { useEffect, useState } from 'react'

function buildWebSocketUrl() {
  const override = import.meta.env.VITE_MISSION_CONTROL_WS_URL
  if (override) return override

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.hostname || '127.0.0.1'
  return `${protocol}//${host}:8765`
}

export function useRuntimeFeed(onSnapshot) {
  const [connection, setConnection] = useState({
    transport: 'snapshot',
    state: 'idle',
    error: null,
  })

  useEffect(() => {
    let socket
    let reconnectTimer
    let stopped = false

    const connect = () => {
      try {
        socket = new WebSocket(buildWebSocketUrl())
        setConnection({ transport: 'websocket', state: 'connecting', error: null })

        socket.onopen = () => {
          if (!stopped) {
            setConnection({ transport: 'websocket', state: 'connected', error: null })
          }
        }

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data?.type === 'snapshot' && data.payload) {
              onSnapshot(data.payload)
            }
          } catch (error) {
            if (!stopped) {
              setConnection({ transport: 'websocket', state: 'degraded', error: error instanceof Error ? error.message : 'invalid websocket payload' })
            }
          }
        }

        socket.onerror = () => {
          if (!stopped) {
            setConnection({ transport: 'snapshot', state: 'degraded', error: 'websocket unavailable' })
          }
        }

        socket.onclose = () => {
          if (!stopped) {
            setConnection({ transport: 'snapshot', state: 'disconnected', error: 'websocket closed; using snapshot polling' })
            reconnectTimer = window.setTimeout(connect, 5000)
          }
        }
      } catch (error) {
        setConnection({ transport: 'snapshot', state: 'degraded', error: error instanceof Error ? error.message : 'websocket setup failed' })
      }
    }

    connect()

    return () => {
      stopped = true
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
      }
      if (socket && socket.readyState < 2) {
        socket.close()
      }
    }
  }, [onSnapshot])

  return connection
}
