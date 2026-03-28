import { useEffect, useState } from 'react'
import { mockSnapshot } from './mockData'

const REFRESH_INTERVAL_MS = 4000

export function useSnapshot() {
  const [data, setData] = useState(mockSnapshot)
  const [status, setStatus] = useState({
    source: 'mock',
    lastUpdated: mockSnapshot.generatedAt || null,
    error: null,
  })

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch(`/snapshot.json?t=${Date.now()}`, { cache: 'no-store' })
        if (!res.ok) {
          throw new Error(`snapshot fetch failed (${res.status})`)
        }

        const json = await res.json()
        if (!cancelled) {
          setData(json)
          setStatus({
            source: 'runtime',
            lastUpdated: json.generatedAt || new Date().toISOString(),
            error: null,
          })
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
  }, [])

  return { snapshot: data, status }
}
