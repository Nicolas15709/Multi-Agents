// ─── URL resolvers ────────────────────────────────────────────────────────────

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '')
}

export function resolveApiBaseUrl() {
  const override = import.meta.env.VITE_MISSION_CONTROL_API_BASE_URL
  if (override) return trimTrailingSlash(override)

  const { protocol, hostname, port } = window.location
  const isLocalVite = ['4173', '5173', '5174'].includes(port)
  if (isLocalVite) {
    return `${protocol}//${hostname}:8787/api`
  }
  return '/api'
}

export function resolveWebSocketUrl() {
  const override = import.meta.env.VITE_MISSION_CONTROL_WS_URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const { hostname, host, port } = window.location
  const isLocalVite = ['4173', '5173', '5174'].includes(port)

  let base
  if (override) {
    base = override
  } else if (isLocalVite) {
    base = `${protocol}//${hostname}:8765`
  } else {
    base = `${protocol}//${host}/ws`
  }

  // Append JWT token as query param so the WebSocket server can verify auth
  const token = getAuthToken()
  return token ? `${base}?token=${encodeURIComponent(token)}` : base
}

// ─── Auth token management ────────────────────────────────────────────────────
// JWT is stored in sessionStorage (survives page refresh, cleared on tab close).
// Never stored in a VITE_ build-time env var to avoid bundle exposure.

const _SESSION_KEY = 'mc_jwt'

export function getAuthToken() {
  try {
    return sessionStorage.getItem(_SESSION_KEY) || ''
  } catch {
    return ''
  }
}

export function setAuthToken(token) {
  try {
    if (token) sessionStorage.setItem(_SESSION_KEY, token)
    else sessionStorage.removeItem(_SESSION_KEY)
  } catch {
    // sessionStorage unavailable (e.g. private mode restrictions) — no-op
  }
}

export function clearAuthToken() {
  try {
    sessionStorage.removeItem(_SESSION_KEY)
  } catch {
    // no-op
  }
}

export function isAuthenticated() {
  const token = getAuthToken()
  if (!token) return false
  // Quick expiry check by peeking at the JWT payload (no crypto verify — just UX guard)
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return false
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      clearAuthToken()
      return false
    }
    return true
  } catch {
    return false
  }
}

function buildAuthHeaders() {
  const token = getAuthToken()
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export async function login(username, password) {
  const res = await fetch(`${resolveApiBaseUrl()}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || !json.token) {
    throw new Error(json.error || 'login_failed')
  }
  setAuthToken(json.token)
  return json.token
}

// ─── Runtime API ──────────────────────────────────────────────────────────────

export async function fetchRuntimeSnapshot() {
  const res = await fetch(`${resolveApiBaseUrl()}/snapshot`, {
    cache: 'no-store',
    headers: buildAuthHeaders(),
  })
  if (res.status === 401) {
    clearAuthToken()
    throw Object.assign(new Error('session_expired'), { code: 401 })
  }
  if (!res.ok) {
    throw new Error(`runtime api snapshot failed (${res.status})`)
  }
  return res.json()
}

export async function createMission(payload) {
  const res = await fetch(`${resolveApiBaseUrl()}/missions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `mission create failed (${res.status})`)
  }
  return json
}

export async function submitProblem(payload) {
  const res = await fetch(`${resolveApiBaseUrl()}/intake/requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `problem submit failed (${res.status})`)
  }
  return json
}

export async function hireSubagent(missionId, payload) {
  const res = await fetch(`${resolveApiBaseUrl()}/missions/${missionId}/hire-subagent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `hire subagent failed (${res.status})`)
  }
  return json
}

export async function fetchAgentTemplates(params = {}) {
  const search = new URLSearchParams()
  if (params.division) search.set('division', params.division)
  if (params.query) search.set('q', params.query)
  if (params.limit) search.set('limit', String(params.limit))
  const suffix = search.toString() ? `?${search.toString()}` : ''
  const res = await fetch(`${resolveApiBaseUrl()}/agent-templates${suffix}`, {
    headers: buildAuthHeaders(),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `agent templates failed (${res.status})`)
  }
  return json.templates || []
}

export async function fetchHireSuggestions(missionId) {
  const res = await fetch(`${resolveApiBaseUrl()}/missions/${missionId}/hire-suggestions`, {
    headers: buildAuthHeaders(),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `hire suggestions failed (${res.status})`)
  }
  return json.suggestions || []
}

export async function approveHireRequest(hireRequestId, payload = {}) {
  const res = await fetch(`${resolveApiBaseUrl()}/hire-requests/${hireRequestId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `approve hire request failed (${res.status})`)
  }
  return json
}

export async function pauseMission(missionId, payload = {}) {
  const res = await fetch(`${resolveApiBaseUrl()}/missions/${missionId}/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `pause mission failed (${res.status})`)
  }
  return json
}

export async function resumeMission(missionId, payload = {}) {
  const res = await fetch(`${resolveApiBaseUrl()}/missions/${missionId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...buildAuthHeaders() },
    body: JSON.stringify(payload),
  })
  const json = await res.json().catch(() => ({}))
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `resume mission failed (${res.status})`)
  }
  return json
}
