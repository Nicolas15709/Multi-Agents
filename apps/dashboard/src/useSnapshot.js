import { useEffect, useState } from 'react'
import { mockSnapshot } from './mockData'

export function useSnapshot() {
  const [data, setData] = useState(mockSnapshot)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch('/snapshot.json', { cache: 'no-store' })
        if (!res.ok) return
        const json = await res.json()
        if (!cancelled) {
          setData(json)
        }
      } catch {
        // fallback to mock data until runtime export exists
      }
    }

    load()
    const timer = setInterval(load, 4000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return data
}
