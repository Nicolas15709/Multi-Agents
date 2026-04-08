import { useState, useMemo, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Activity, Zap, AlertCircle, CheckCircle2, Info, ArrowRight,
  Bot, Target, Cpu, Bell, RefreshCw, Search, Filter, ChevronDown,
} from 'lucide-react'

const EVENT_CONFIG = {
  mission_start:    { color: '#00d4a0', Icon: Target,       label: 'Misión iniciada' },
  mission_complete: { color: '#38bdf8', Icon: CheckCircle2, label: 'Misión completada' },
  mission_failed:   { color: '#ff4d6d', Icon: AlertCircle,  label: 'Misión fallida' },
  task_start:       { color: '#8875ff', Icon: Zap,          label: 'Tarea iniciada' },
  task_done:        { color: '#00d4a0', Icon: CheckCircle2, label: 'Tarea completada' },
  task_failed:      { color: '#ff4d6d', Icon: AlertCircle,  label: 'Tarea fallida' },
  task_blocked:     { color: '#ffa940', Icon: AlertCircle,  label: 'Tarea bloqueada' },
  agent_action:     { color: '#a899ff', Icon: Bot,          label: 'Acción de agente' },
  heartbeat:        { color: 'rgba(255,255,255,0.25)', Icon: RefreshCw, label: 'Heartbeat' },
  notification:     { color: '#ffa940', Icon: Bell,         label: 'Notificación' },
  error:            { color: '#ff4d6d', Icon: AlertCircle,  label: 'Error' },
  info:             { color: '#38bdf8', Icon: Info,         label: 'Info' },
  default:          { color: 'rgba(255,255,255,0.35)', Icon: Activity, label: 'Evento' },
}

function getEventCfg(type) {
  return EVENT_CONFIG[type] ?? EVENT_CONFIG.default
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d)) return ts
  return d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d)) return ''
  return d.toLocaleDateString('es', { month: 'short', day: 'numeric' })
}

function EventRow({ event, isLast }) {
  const cfg = getEventCfg(event.type)
  const [expanded, setExpanded] = useState(false)
  const hasDetail = event.data && Object.keys(event.data).length > 0

  return (
    <div style={{ display: 'flex', gap: '12px', paddingBottom: isLast ? '0' : '4px' }}>
      {/* Timeline line + dot */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, width: '32px' }}>
        <div style={{
          width: '28px', height: '28px', borderRadius: '8px', flexShrink: 0,
          background: `${cfg.color}14`, border: `1px solid ${cfg.color}28`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <cfg.Icon size={13} style={{ color: cfg.color }} />
        </div>
        {!isLast && (
          <div style={{ width: '1px', flex: 1, minHeight: '16px', background: 'rgba(255,255,255,0.06)', marginTop: '4px' }} />
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '2px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: cfg.color, flexShrink: 0 }}>
            {cfg.label}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--muted)', marginLeft: 'auto', flexShrink: 0 }}>
            {formatTime(event.timestamp)}
          </span>
        </div>

        {event.message && (
          <p style={{ fontSize: '12px', color: 'var(--text)', lineHeight: 1.5, margin: '0 0 6px 0' }}>
            {event.message}
          </p>
        )}

        {event.agent && (
          <span style={{ fontSize: '10px', color: 'var(--muted)', background: 'rgba(255,255,255,0.05)', padding: '1px 6px', borderRadius: '4px' }}>
            <Bot size={9} style={{ display: 'inline', marginRight: '3px', verticalAlign: 'middle' }} />
            {event.agent}
          </span>
        )}

        {hasDetail && (
          <button
            onClick={() => setExpanded(v => !v)}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: '11px', padding: 0, fontFamily: 'Inter, system-ui, sans-serif' }}
          >
            <ChevronDown size={11} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
            {expanded ? 'Ocultar detalles' : 'Ver detalles'}
          </button>
        )}

        {expanded && hasDetail && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginTop: '8px', padding: '8px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', fontFamily: 'monospace', fontSize: '10px', color: 'var(--muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}
          >
            {JSON.stringify(event.data, null, 2)}
          </motion.div>
        )}
      </div>
    </div>
  )
}

function DateDivider({ date }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '8px 0 12px' }}>
      <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.06)' }} />
      <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{date}</span>
      <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.06)' }} />
    </div>
  )
}

const TYPE_FILTERS = [
  { id: 'all',     label: 'Todo' },
  { id: 'mission', label: 'Misiones' },
  { id: 'task',    label: 'Tareas' },
  { id: 'agent',   label: 'Agentes' },
  { id: 'system',  label: 'Sistema' },
]

function matchesTypeFilter(event, filter) {
  if (filter === 'all') return true
  if (filter === 'mission') return event.type?.startsWith('mission')
  if (filter === 'task') return event.type?.startsWith('task')
  if (filter === 'agent') return event.type?.startsWith('agent') || !!event.agent
  if (filter === 'system') return event.type === 'heartbeat' || event.type === 'error' || event.type === 'info'
  return true
}

function EmptyTimeline() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '12px', padding: '80px 0' }}>
      <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Activity size={24} style={{ color: '#38bdf8', opacity: 0.6 }} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '4px' }}>Sin actividad registrada</div>
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>Los eventos aparecerán aquí en tiempo real.</div>
      </div>
    </div>
  )
}

export function TimelineView({ stream }) {
  const [typeFilter, setTypeFilter] = useState('all')
  const [search, setSearch] = useState('')
  const bottomRef = useRef(null)
  const [autoScroll, setAutoScroll] = useState(true)

  const events = stream?.events ?? []

  const filtered = useMemo(() => {
    return events.filter(e => {
      if (!matchesTypeFilter(e, typeFilter)) return false
      if (search && !e.message?.toLowerCase().includes(search.toLowerCase()) && !e.type?.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [events, typeFilter, search])

  // Group by date
  const grouped = useMemo(() => {
    const groups = []
    let lastDate = null
    for (const e of filtered) {
      const d = formatDate(e.timestamp)
      if (d !== lastDate) {
        groups.push({ type: 'divider', date: d, key: `d-${d}` })
        lastDate = d
      }
      groups.push({ type: 'event', event: e, key: e.id ?? `${e.timestamp}-${e.type}` })
    }
    return groups
  }, [filtered])

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [filtered.length, autoScroll])

  return (
    <div className="view-shell">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="view-title">Timeline</h1>
          <p className="view-subtitle">{events.length} eventos registrados.</p>
        </div>
        <button
          onClick={() => setAutoScroll(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '6px 12px', borderRadius: '7px', border: `1px solid ${autoScroll ? 'rgba(0,212,160,0.3)' : 'rgba(255,255,255,0.08)'}`,
            background: autoScroll ? 'rgba(0,212,160,0.1)' : 'rgba(255,255,255,0.04)',
            color: autoScroll ? '#00d4a0' : 'var(--muted)',
            fontSize: '11px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <RefreshCw size={11} />
          {autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'}
        </button>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px' }}>
          {TYPE_FILTERS.map(f => (
            <button key={f.id} onClick={() => setTypeFilter(f.id)} style={{
              padding: '4px 10px', borderRadius: '5px', border: 'none', cursor: 'pointer',
              fontSize: '12px', fontWeight: 500, fontFamily: 'Inter, system-ui, sans-serif', transition: 'all 0.12s',
              background: typeFilter === f.id ? 'rgba(136,117,255,0.2)' : 'transparent',
              color: typeFilter === f.id ? '#a899ff' : 'var(--muted)',
            }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar evento..." style={searchInput} />
        </div>
      </div>

      {/* Timeline */}
      <div
        onScroll={e => {
          const el = e.currentTarget
          const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
          setAutoScroll(atBottom)
        }}
        style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.01)', padding: filtered.length === 0 ? '0' : '20px 20px 8px' }}
      >
        {filtered.length === 0 ? (
          <EmptyTimeline />
        ) : (
          <>
            {grouped.map((item, i) =>
              item.type === 'divider' ? (
                <DateDivider key={item.key} date={item.date} />
              ) : (
                <EventRow
                  key={item.key}
                  event={item.event}
                  isLast={i === grouped.length - 1}
                />
              )
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  )
}

// ── Shared styles ───────────────────────────────────────────────────
const searchInput = { paddingLeft: '28px', paddingRight: '10px', paddingTop: '6px', paddingBottom: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '7px', color: 'var(--text)', fontSize: '12px', fontFamily: 'Inter, system-ui, sans-serif', outline: 'none', width: '180px' }
