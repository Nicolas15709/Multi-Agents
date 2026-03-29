import { useCallback, useEffect, useState } from 'react'
import { mockSnapshot } from './mockData'
import { useRuntimeFeed } from './useRuntimeFeed'

const REFRESH_INTERVAL_MS = 4000

function isRuntimeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== 'object') return false

  const hasCoreEnvelope = Object.prototype.hasOwnProperty.call(snapshot, 'generatedAt')
    && Object.prototype.hasOwnProperty.call(snapshot, 'meta')
    && Object.prototype.hasOwnProperty.call(snapshot, 'stream')

  if (!hasCoreEnvelope) return false

  return [
    snapshot.activeMission,
    snapshot.missionSummary,
    snapshot.progress?.mission,
    Array.isArray(snapshot.missions) ? snapshot.missions : null,
    Array.isArray(snapshot.tasks) ? snapshot.tasks : null,
    Array.isArray(snapshot.agents) ? snapshot.agents : null,
  ].some((value) => (Array.isArray(value) ? true : Boolean(value)))
}

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
        if (!isRuntimeSnapshot(json)) {
          throw new Error('snapshot loaded but does not match runtime snapshot shape yet')
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
