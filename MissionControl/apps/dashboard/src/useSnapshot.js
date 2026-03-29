import { useCallback, useEffect, useState } from 'react'
import { mockSnapshot } from './mockData'
import { useRuntimeFeed } from './useRuntimeFeed'

const REFRESH_INTERVAL_MS = 4000

export function useSnapshot() {
  const [data, setData] = useState(mockSnapshot)
  const [status, setStatus] = useState({
    source: 'mock',
    lastUpdated: mockSnapshot.generatedAt || null,
    error: null,
  })

  const applySnapshot = useCallback((snapshot, source = 'runtime') => {
    setData(snapshot)
    setStatus({
      source,
      lastUpdated: snapshot.generatedAt || new Date().toISOString(),
      error: null,
    })
  }, [])

  const onSnapshot = useCallback((snapshot) => applySnapshot(snapshot, 'runtime'), [applySnapshot])
  const connection = useRuntimeFeed(onSnapshot)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch(`/snapshot.json?t=${Date.now()}`, { cache: 'no-store' })
        if (!res.ok) {
          throw new Error(`snapshot fetch failed (${res.status})`)
        }

        const json = await res.json()
        const hasRuntimeData = Boolean(json?.activeMission || (json?.tasks && json.tasks.length) || (json?.agents && json.agents.length) || json?.missionSummary)
        if (!hasRuntimeData) {
          throw new Error('snapshot loaded but contains no runtime data yet')
        }
        if (!cancelled && connection.state !== 'connected') {
          applySnapshot(json, 'runtime')
        }
      } catch (error) {
        if (!cancelled) {
          setData((current) => current || mockSnapshot)
          setStatus((current) => ({
            source: current?.source === 'runtime' ? current.source : 'mock',
            lastUpdated: current?.lastUpdated || mockSnapshot.generatedAt || null,
            error: error instanceof Error ? error.message : 'snapshot unavailable',
          }))
        }
      }
    }

    load()
    const timer = setInterval(load, REFRESH_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [applySnapshot, connection.state])

  return { snapshot: data, status, connection }
}
