const STORAGE_KEY = 'missioncontrol.custom-agents'

export const AGENT_AVATAR_COLORS = [
  '#6366f1', '#8b5cf6', '#a855f7', '#ec4899',
  '#ef4444', '#f97316', '#f59e0b', '#eab308',
  '#22c55e', '#10b981', '#14b8a6', '#06b6d4',
  '#3b82f6', '#0ea5e9', '#64748b', '#94a3b8',
]

export const DEFAULT_AGENT_ICON = 'bot'
export const PIXEL_AVATAR_PRESETS = [
  { palette: 0, hueShift: 0, label: 'Classic Blue' },
  { palette: 1, hueShift: 0, label: 'Golden Red' },
  { palette: 2, hueShift: 0, label: 'Research Green' },
  { palette: 3, hueShift: 0, label: 'Purple Designer' },
  { palette: 4, hueShift: 0, label: 'Amber Ops' },
  { palette: 5, hueShift: 0, label: 'Orange Night' },
]

export function loadCustomAgents() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveCustomAgents(agents) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(agents))
  } catch {}
}

function slugify(value) {
  return String(value || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function createCustomAgent(input, existingAgents = []) {
  const timestamp = Date.now().toString(36)
  const baseId = slugify(input.display_name) || 'agent'
  const existingIds = new Set(existingAgents.map((agent) => agent.agent_id))
  let agentId = `custom-${baseId}`
  if (existingIds.has(agentId)) {
    agentId = `custom-${baseId}-${timestamp}`
  }

  return {
    agent_id: agentId,
    display_name: input.display_name.trim(),
    name: input.display_name.trim(),
    role: input.role.trim() || 'Agent',
    personality: input.personality?.trim() || '',
    state: 'idle',
    current_task: '',
    avatar_icon: input.avatar_icon || DEFAULT_AGENT_ICON,
    avatar_color: input.avatar_color || AGENT_AVATAR_COLORS[0],
    pixel_palette: Number.isInteger(input.pixel_palette) ? input.pixel_palette : 0,
    pixel_hue_shift: Number.isInteger(input.pixel_hue_shift) ? input.pixel_hue_shift : 0,
    is_custom: true,
  }
}

export function mergeAgents(runtimeAgents = [], customAgents = []) {
  const merged = new Map()

  for (const agent of customAgents) {
    merged.set(agent.agent_id, { ...agent })
  }

  for (const agent of runtimeAgents) {
    const existing = merged.get(agent.agent_id)
    merged.set(agent.agent_id, {
      ...existing,
      ...agent,
      avatar_icon: agent.avatar_icon ?? existing?.avatar_icon ?? DEFAULT_AGENT_ICON,
      avatar_color: agent.avatar_color ?? existing?.avatar_color ?? AGENT_AVATAR_COLORS[0],
      pixel_palette: agent.pixel_palette ?? existing?.pixel_palette ?? 0,
      pixel_hue_shift: agent.pixel_hue_shift ?? existing?.pixel_hue_shift ?? 0,
      is_custom: existing?.is_custom ?? false,
    })
  }

  return Array.from(merged.values())
}
