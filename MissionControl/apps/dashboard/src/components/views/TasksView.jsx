import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleDashed,
  CircleDot,
  Clock,
  Search,
  X,
} from 'lucide-react'

const STATUS_CONFIG = {
  done: { color: '#00d4a0', bg: 'rgba(0,212,160,0.1)', border: 'rgba(0,212,160,0.2)', label: 'Completada', Icon: CheckCircle2 },
  completed: { color: '#00d4a0', bg: 'rgba(0,212,160,0.1)', border: 'rgba(0,212,160,0.2)', label: 'Completada', Icon: CheckCircle2 },
  running: { color: '#8875ff', bg: 'rgba(136,117,255,0.1)', border: 'rgba(136,117,255,0.2)', label: 'Corriendo', Icon: CircleDashed },
  in_progress: { color: '#8875ff', bg: 'rgba(136,117,255,0.1)', border: 'rgba(136,117,255,0.2)', label: 'En progreso', Icon: CircleDashed },
  blocked: { color: '#ff4d6d', bg: 'rgba(255,77,109,0.1)', border: 'rgba(255,77,109,0.2)', label: 'Bloqueada', Icon: AlertCircle },
  failed: { color: '#ff4d6d', bg: 'rgba(255,77,109,0.1)', border: 'rgba(255,77,109,0.2)', label: 'Fallida', Icon: AlertCircle },
  pending: { color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.08)', label: 'Pendiente', Icon: Clock },
}

const PRIORITY_CONFIG = {
  critical: { color: '#ff4d6d', label: 'Critica' },
  high: { color: '#ffa940', label: 'Alta' },
  medium: { color: '#8875ff', label: 'Media' },
  low: { color: 'rgba(255,255,255,0.3)', label: 'Baja' },
}

const TABS = [
  { id: 'all', label: 'Todas' },
  { id: 'in_progress', label: 'En progreso' },
  { id: 'pending', label: 'Pendientes' },
  { id: 'done', label: 'Completadas' },
  { id: 'blocked', label: 'Bloqueadas' },
]

function getStatus(status) {
  return STATUS_CONFIG[status?.toLowerCase()] ?? STATUS_CONFIG.pending
}

function formatTag(value) {
  return String(value || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function joinList(values, fallback = 'N/A') {
  if (!Array.isArray(values) || values.length === 0) {
    return fallback
  }
  return values.map(formatTag).join(', ')
}

function countBy(tasks, selector) {
  const values = new Set()
  tasks.forEach((task) => {
    const value = selector(task)
    if (Array.isArray(value)) {
      value.forEach((item) => item && values.add(String(item)))
      return
    }
    if (value) {
      values.add(String(value))
    }
  })
  return values.size
}

function TaskRow({ task, agents, depth = 0, selected, onSelect }) {
  const [expanded, setExpanded] = useState(false)
  const status = getStatus(task.status)
  const agent = agents.find((item) => item.agent_id === task.agent_id || item.agent_id === task.assigned_to)
  const hasChildren = task.subtasks?.length > 0
  const isSelected = selected?.id === task.id
  const phaseLabel = task.details?.phase_label
  const workstream = task.details?.workstream

  return (
    <>
      <motion.div
        onClick={() => onSelect(isSelected ? null : task)}
        whileHover={{ background: 'rgba(255,255,255,0.04)' }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '9px 14px',
          paddingLeft: `${14 + depth * 20}px`,
          cursor: 'pointer',
          borderRadius: '6px',
          background: isSelected ? 'rgba(136,117,255,0.08)' : 'transparent',
          borderLeft: isSelected ? '2px solid #8875ff' : '2px solid transparent',
          transition: 'all 0.1s',
        }}
      >
        {hasChildren ? (
          <button
            onClick={(event) => {
              event.stopPropagation()
              setExpanded((value) => !value)
            }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 0, display: 'flex', flexShrink: 0 }}
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <div style={{ width: '12px', flexShrink: 0 }} />
        )}

        <status.Icon size={13} style={{ color: status.color, flexShrink: 0 }} />

        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span
            style={{
              fontSize: '12px',
              color: isSelected ? 'var(--text-bright)' : 'var(--text)',
              fontWeight: isSelected ? 600 : 400,
              overflow: 'hidden',
              whiteSpace: 'nowrap',
              textOverflow: 'ellipsis',
            }}
          >
            {task.title}
          </span>
          {(phaseLabel || workstream) && (
            <span style={{ fontSize: '10px', color: 'var(--muted)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
              {[phaseLabel, workstream && formatTag(workstream)].filter(Boolean).join(' • ')}
            </span>
          )}
        </div>

        {agent && (
          <span style={{ fontSize: '10px', color: 'var(--muted)', background: 'rgba(255,255,255,0.06)', padding: '1px 6px', borderRadius: '4px', flexShrink: 0 }}>
            {agent.display_name}
          </span>
        )}

        {task.priority && PRIORITY_CONFIG[task.priority] && (
          <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: PRIORITY_CONFIG[task.priority].color, flexShrink: 0 }} />
        )}

        <span style={{ fontSize: '10px', fontWeight: 600, padding: '1px 6px', borderRadius: '20px', background: status.bg, color: status.color, border: `1px solid ${status.border}`, flexShrink: 0 }}>
          {status.label}
        </span>
      </motion.div>

      <AnimatePresence>
        {expanded && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden' }}
          >
            {task.subtasks.map((subtask) => (
              <TaskRow key={subtask.id} task={subtask} agents={agents} depth={depth + 1} selected={selected} onSelect={onSelect} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

function MetaRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', fontSize: '11px' }}>
      <span style={{ color: 'var(--muted)', flexShrink: 0 }}>{label}</span>
      <span style={{ color: 'var(--text)', fontWeight: 500, textAlign: 'right' }}>{value}</span>
    </div>
  )
}

function TagList({ values, tone = 'neutral' }) {
  if (!Array.isArray(values) || values.length === 0) {
    return null
  }

  const palette =
    tone === 'danger'
      ? { bg: 'rgba(255,77,109,0.08)', border: 'rgba(255,77,109,0.18)', color: '#ff9aae' }
      : tone === 'accent'
        ? { bg: 'rgba(136,117,255,0.1)', border: 'rgba(136,117,255,0.22)', color: '#b8afff' }
        : { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.08)', color: 'var(--text)' }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
      {values.map((value) => (
        <span
          key={value}
          style={{
            fontSize: '10px',
            padding: '4px 8px',
            borderRadius: '999px',
            background: palette.bg,
            border: `1px solid ${palette.border}`,
            color: palette.color,
          }}
        >
          {formatTag(value)}
        </span>
      ))}
    </div>
  )
}

function TaskDetail({ task, agents, onClose }) {
  const status = getStatus(task.status)
  const agent = agents.find((item) => item.agent_id === task.agent_id || item.agent_id === task.assigned_to)
  const details = task.details || {}
  const missionProfile = details.mission_profile || {}
  const retryCount = details.retry_count ?? 0
  const maxRetries = details.guardrails?.max_retries

  const summaryTags = [
    details.phase_label,
    details.workstream && formatTag(details.workstream),
    missionProfile.primary_domain && `Dominio ${formatTag(missionProfile.primary_domain)}`,
  ].filter(Boolean)

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
      style={{
        width: '320px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
        <status.Icon size={16} style={{ color: status.color, marginTop: '1px', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)', lineHeight: 1.3 }}>{task.title}</div>
          {summaryTags.length > 0 && (
            <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {summaryTags.map((tag) => (
                <span key={tag} style={{ fontSize: '10px', color: 'var(--muted)', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', padding: '3px 7px', borderRadius: '999px' }}>
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: '2px', flexShrink: 0 }}>
          <X size={13} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div>
          <div style={sectionLabel}>Estado</div>
          <span style={{ fontSize: '11px', fontWeight: 600, padding: '3px 8px', borderRadius: '20px', background: status.bg, color: status.color, border: `1px solid ${status.border}` }}>
            {status.label}
          </span>
        </div>

        {task.description && (
          <div>
            <div style={sectionLabel}>Descripcion</div>
            <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.6, margin: 0 }}>{task.description}</p>
          </div>
        )}

        <div>
          <div style={sectionLabel}>Detalles</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {agent && <MetaRow label="Agente" value={agent.display_name} />}
            {task.priority && <MetaRow label="Prioridad" value={PRIORITY_CONFIG[task.priority]?.label ?? task.priority} />}
            {details.phase_label && <MetaRow label="Fase" value={details.phase_label} />}
            {details.team_role && <MetaRow label="Rol de equipo" value={details.team_role} />}
            {details.workstream && <MetaRow label="Workstream" value={formatTag(details.workstream)} />}
            {details.workflow_version && <MetaRow label="Planner" value={details.workflow_version} />}
            {missionProfile.risk_level && <MetaRow label="Riesgo" value={formatTag(missionProfile.risk_level)} />}
            {details.approval_policy && <MetaRow label="Approval policy" value={formatTag(details.approval_policy)} />}
            {details.external_action_kind && <MetaRow label="Action kind" value={formatTag(details.external_action_kind)} />}
            {typeof maxRetries === 'number' && <MetaRow label="Retry guard" value={`${retryCount}/${maxRetries}`} />}
            {Array.isArray(task.depends_on) && task.depends_on.length > 0 && <MetaRow label="Dependencias" value={String(task.depends_on.length)} />}
            {task.id && <MetaRow label="ID" value={task.id} />}
          </div>
        </div>

        {details.required_capabilities?.length > 0 && (
          <div>
            <div style={sectionLabel}>Capacidades requeridas</div>
            <TagList values={details.required_capabilities} tone="accent" />
          </div>
        )}

        {details.tool_primitives?.length > 0 && (
          <div>
            <div style={sectionLabel}>Tools</div>
            <TagList values={details.tool_primitives} />
          </div>
        )}

        {details.specialist_template_hints?.length > 0 && (
          <div>
            <div style={sectionLabel}>Plantillas sugeridas</div>
            <TagList values={details.specialist_template_hints} />
          </div>
        )}

        {missionProfile.domains?.length > 0 && (
          <div>
            <div style={sectionLabel}>Contexto de mision</div>
            <TagList values={missionProfile.domains} tone="accent" />
          </div>
        )}

        {missionProfile.risk_flags?.length > 0 && (
          <div>
            <div style={sectionLabel}>Guardrails</div>
            <TagList values={missionProfile.risk_flags} tone="danger" />
            {missionProfile.requires_human_approval && (
              <div style={{ marginTop: '8px', fontSize: '11px', color: '#ffb86b' }}>
                Esta tarea cae en una mision con aprobacion humana recomendada.
              </div>
            )}
          </div>
        )}

        {task.error && (
          <div>
            <div style={sectionLabel}>Error</div>
            <div style={{ fontSize: '11px', color: '#ff4d6d', background: 'rgba(255,77,109,0.05)', border: '1px solid rgba(255,77,109,0.15)', borderRadius: '6px', padding: '8px', fontFamily: 'monospace' }}>
              {task.error}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

function EmptyTasks() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '12px', padding: '60px 0' }}>
      <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(136,117,255,0.08)', border: '1px solid rgba(136,117,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircleDot size={24} style={{ color: '#8875ff', opacity: 0.6 }} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '4px' }}>Sin tareas activas</div>
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>Las tareas apareceran cuando haya una mision en curso.</div>
      </div>
    </div>
  )
}

function InsightsStrip({ tasks }) {
  const workstreamCount = countBy(tasks, (task) => task.details?.workstream)
  const capabilityCount = countBy(tasks, (task) => task.details?.required_capabilities)
  const riskyTaskCount = tasks.filter((task) => (task.details?.mission_profile?.risk_flags || []).length > 0).length

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
      <InsightCard label="Workstreams activos" value={String(workstreamCount)} hint="Tracks abiertos por el planner" />
      <InsightCard label="Capacidades detectadas" value={String(capabilityCount)} hint="Skills requeridas por tareas actuales" />
      <InsightCard label="Tareas con riesgo" value={String(riskyTaskCount)} hint="Requieren guardrails o approval" />
    </div>
  )
}

function InsightCard({ label, value, hint }) {
  return (
    <div style={{ padding: '14px', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '2px' }}>{value}</div>
      <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{hint}</div>
    </div>
  )
}

export function TasksView({ tasks, agents }) {
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [agentFilter, setAgentFilter] = useState('all')

  const filtered = useMemo(() => {
    return tasks.filter((task) => {
      if (tab === 'in_progress' && task.status !== 'running' && task.status !== 'in_progress') {
        return false
      }
      if (tab === 'pending' && task.status !== 'pending' && !(!task.status)) {
        return false
      }
      if (tab === 'done' && task.status !== 'done' && task.status !== 'completed') {
        return false
      }
      if (tab === 'blocked' && task.status !== 'blocked') {
        return false
      }
      if (agentFilter !== 'all' && task.agent_id !== agentFilter && task.assigned_to !== agentFilter) {
        return false
      }

      const haystack = [
        task.title,
        task.details?.phase_label,
        task.details?.workstream,
        ...(task.details?.required_capabilities || []),
        ...(task.details?.tool_primitives || []),
        ...(task.details?.specialist_template_hints || []),
        ...(task.details?.mission_profile?.domains || []),
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()

      if (search && !haystack.includes(search.toLowerCase())) {
        return false
      }

      return true
    })
  }, [tasks, tab, search, agentFilter])

  const tabCounts = useMemo(() => ({
    all: tasks.length,
    in_progress: tasks.filter((task) => task.status === 'running' || task.status === 'in_progress').length,
    pending: tasks.filter((task) => task.status === 'pending' || !task.status).length,
    done: tasks.filter((task) => task.status === 'done' || task.status === 'completed').length,
    blocked: tasks.filter((task) => task.status === 'blocked').length,
  }), [tasks])

  const completedPct = tasks.length > 0 ? Math.round((tabCounts.done / tasks.length) * 100) : 0

  return (
    <div className="view-shell">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="view-title">Tareas</h1>
          <p className="view-subtitle">{tasks.length} tareas en total - {completedPct}% completadas.</p>
        </div>
        {tasks.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '120px', height: '4px', borderRadius: '2px', background: 'rgba(255,255,255,0.08)' }}>
              <div style={{ width: `${completedPct}%`, height: '100%', borderRadius: '2px', background: '#00d4a0', transition: 'width 0.5s' }} />
            </div>
            <span style={{ fontSize: '11px', color: '#00d4a0', fontWeight: 600 }}>{completedPct}%</span>
          </div>
        )}
      </div>

      {tasks.length > 0 && <InsightsStrip tasks={tasks} />}

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px' }}>
          {TABS.map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              style={{
                ...tabBtn,
                background: tab === item.id ? 'rgba(136,117,255,0.2)' : 'transparent',
                color: tab === item.id ? '#a899ff' : 'var(--muted)',
              }}
            >
              {item.label}
              {tabCounts[item.id] > 0 && (
                <span style={{ ...countBadge, background: tab === item.id ? 'rgba(136,117,255,0.3)' : 'rgba(255,255,255,0.08)' }}>
                  {tabCounts[item.id]}
                </span>
              )}
            </button>
          ))}
        </div>

        {agents.length > 0 && (
          <select value={agentFilter} onChange={(event) => setAgentFilter(event.target.value)} style={{ ...searchInput, paddingLeft: '10px', width: '160px' }}>
            <option value="all">Todos los agentes</option>
            {agents.map((agent) => (
              <option key={agent.agent_id} value={agent.agent_id}>
                {agent.display_name}
              </option>
            ))}
          </select>
        )}

        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por tarea, workstream o capability..." style={searchInput} />
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ flex: 1, overflowY: 'auto', background: 'rgba(255,255,255,0.01)', padding: filtered.length === 0 ? '0' : '8px' }}>
          {filtered.length === 0 ? (
            <EmptyTasks />
          ) : (
            filtered.map((task) => <TaskRow key={task.id} task={task} agents={agents} selected={selected} onSelect={setSelected} />)
          )}
        </div>

        <AnimatePresence>
          {selected && <TaskDetail task={selected} agents={agents} onClose={() => setSelected(null)} />}
        </AnimatePresence>
      </div>
    </div>
  )
}

const sectionLabel = {
  fontSize: '10px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: 'var(--muted)',
  marginBottom: '8px',
}

const tabBtn = {
  padding: '4px 10px',
  borderRadius: '5px',
  border: 'none',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
  gap: '5px',
  fontFamily: 'Inter, system-ui, sans-serif',
  transition: 'all 0.12s',
}

const countBadge = {
  fontSize: '10px',
  minWidth: '18px',
  height: '18px',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: '999px',
  color: 'var(--text-bright)',
}

const searchInput = {
  width: '220px',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '8px',
  color: 'var(--text)',
  padding: '8px 10px 8px 30px',
  fontSize: '12px',
  outline: 'none',
}
