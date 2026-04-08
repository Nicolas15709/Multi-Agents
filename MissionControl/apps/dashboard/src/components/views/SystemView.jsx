import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Cpu, Wifi, WifiOff, Database, Server, Activity,
  CheckCircle2, AlertCircle, Clock, RefreshCw,
  MessageCircle, GitBranch, Globe, Bell, Bot,
  BarChart3, Zap, HardDrive, Terminal,
} from 'lucide-react'

function StatusDot({ ok, pulse }) {
  const color = ok ? '#00d4a0' : '#ff4d6d'
  return (
    <div style={{
      width: '8px', height: '8px', borderRadius: '50%',
      background: color, flexShrink: 0,
      ...(pulse ? { animation: 'pulse 2s infinite', boxShadow: `0 0 6px ${color}` } : {}),
    }} />
  )
}

function StatusCard({ icon: Icon, title, value, subtitle, ok, color = '#8875ff', action }) {
  return (
    <motion.div
      whileHover={{ y: -1 }}
      style={{
        padding: '16px', borderRadius: '12px',
        background: ok ? 'rgba(0,212,160,0.04)' : 'rgba(255,77,109,0.04)',
        border: `1px solid ${ok ? 'rgba(0,212,160,0.15)' : 'rgba(255,77,109,0.15)'}`,
        display: 'flex', flexDirection: 'column', gap: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${color}15`, border: `1px solid ${color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon size={15} style={{ color }} />
          </div>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)' }}>{title}</span>
        </div>
        <StatusDot ok={ok} pulse={ok} />
      </div>
      <div>
        <div style={{ fontSize: '18px', fontWeight: 700, color: ok ? '#00d4a0' : '#ff4d6d', lineHeight: 1 }}>{value}</div>
        {subtitle && <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '3px' }}>{subtitle}</div>}
      </div>
      {action && (
        <button onClick={action.fn} style={{ fontSize: '11px', color: color, background: `${color}12`, border: `1px solid ${color}20`, borderRadius: '6px', padding: '5px 10px', cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif', textAlign: 'left' }}>
          {action.label}
        </button>
      )}
    </motion.div>
  )
}

function IntegrationRow({ icon: Icon, name, status, color, detail }) {
  const isOk = status === 'connected' || status === 'configured'
  const isPending = status === 'not_configured'
  const statusColor = isOk ? '#00d4a0' : isPending ? '#ffa940' : '#ff4d6d'
  const statusLabel = isOk ? 'Conectado' : isPending ? 'Sin configurar' : 'Error'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px', borderRadius: '9px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ width: '34px', height: '34px', borderRadius: '9px', background: `${color}12`, border: `1px solid ${color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon size={16} style={{ color }} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)' }}>{name}</div>
        {detail && <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{detail}</div>}
      </div>
      <span style={{ fontSize: '10px', fontWeight: 600, padding: '2px 8px', borderRadius: '20px', background: `${statusColor}15`, color: statusColor, border: `1px solid ${statusColor}25`, flexShrink: 0 }}>
        {statusLabel}
      </span>
    </div>
  )
}

function LogEntry({ level, message, time }) {
  const colors = { error: '#ff4d6d', warn: '#ffa940', info: '#38bdf8', debug: 'var(--muted)' }
  return (
    <div style={{ display: 'flex', gap: '10px', fontSize: '11px', padding: '3px 0', fontFamily: 'monospace' }}>
      <span style={{ color: colors[level] ?? 'var(--muted)', flexShrink: 0, width: '40px' }}>{level.toUpperCase()}</span>
      <span style={{ color: 'var(--muted)', flexShrink: 0 }}>{time}</span>
      <span style={{ color: 'var(--text)' }}>{message}</span>
    </div>
  )
}

function formatUptime(secs) {
  if (!secs) return '—'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function SystemView({ stream, connection }) {
  const [uptime, setUptime] = useState(0)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  useEffect(() => {
    const interval = setInterval(() => setUptime(v => v + 1), 1000)
    return () => clearInterval(interval)
  }, [])

  const events = stream?.events ?? []
  const notifications = stream?.notifications ?? []
  const isConnected = connection?.state === 'connected'
  const transport = connection?.transport ?? 'snapshot'
  const wsSubtitle = transport === 'websocket'
    ? `WebSocket · ${connection?.state ?? '—'}`
    : `Polling snapshot · ${connection?.state ?? '—'}`

  // Derive basic stats from events
  const recentErrors = events.filter(e => e.type === 'error').slice(-5)
  const lastEvent = events[events.length - 1]

  const statusCards = [
    {
      icon: Wifi, title: 'WebSocket',
      value: isConnected ? 'Online' : 'Offline',
      subtitle: wsSubtitle,
      ok: isConnected, color: '#38bdf8',
    },
    {
      icon: Server, title: 'Runtime',
      value: events.length > 0 ? 'Activo' : 'Sin datos',
      subtitle: lastEvent ? `Último evento: ${new Date(lastEvent.timestamp).toLocaleTimeString('es')}` : 'Sin eventos',
      ok: events.length > 0, color: '#00d4a0',
    },
    {
      icon: Database, title: 'Snapshot',
      value: stream ? 'OK' : 'Sin datos',
      subtitle: `${events.length} eventos en stream`,
      ok: !!stream, color: '#8b5cf6',
    },
    {
      icon: Activity, title: 'Uptime',
      value: formatUptime(uptime),
      subtitle: 'Tiempo en sesión',
      ok: true, color: '#ffa940',
    },
  ]

  const integrations = [
    { icon: MessageCircle, name: 'Telegram',   color: '#2BA5E1', status: 'not_configured', detail: 'Alertas y aprobaciones por chat' },
    { icon: GitBranch,     name: 'GitHub',      color: '#e2e8f0',  status: 'not_configured', detail: 'Pull requests y commits' },
    { icon: Globe,         name: 'Slack',       color: '#E01E5A',  status: 'not_configured', detail: 'Notificaciones de equipo' },
    { icon: Globe,         name: 'Web Search',  color: '#8875ff',  status: 'not_configured', detail: 'Investigación online' },
    { icon: Bot,           name: 'OpenClaw',    color: '#00d4a0',  status: isConnected ? 'connected' : 'not_configured', detail: 'Adapter principal de agentes' },
  ]

  const SECTIONS = ['status', 'integrations', 'logs']
  const [activeSection, setActiveSection] = useState('status')

  return (
    <div className="view-shell">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="view-title">Sistema</h1>
          <p className="view-subtitle">Estado operacional y configuración de integraciones.</p>
        </div>
        <button
          onClick={() => setLastRefresh(new Date())}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '7px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.04)', color: 'var(--muted)', fontSize: '11px', fontWeight: 600, cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif' }}
        >
          <RefreshCw size={11} />
          Actualizar
        </button>
      </div>

      {/* Section tabs */}
      <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px', width: 'fit-content' }}>
        {[
          { id: 'status',       label: 'Estado' },
          { id: 'integrations', label: 'Integraciones' },
          { id: 'logs',         label: 'Logs' },
        ].map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)} style={{
            padding: '5px 14px', borderRadius: '5px', border: 'none', cursor: 'pointer',
            fontSize: '12px', fontWeight: 500, fontFamily: 'Inter, system-ui, sans-serif', transition: 'all 0.12s',
            background: activeSection === s.id ? 'rgba(136,117,255,0.2)' : 'transparent',
            color: activeSection === s.id ? '#a899ff' : 'var(--muted)',
          }}>
            {s.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeSection === 'status' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
              {statusCards.map(c => <StatusCard key={c.title} {...c} />)}
            </div>

            {/* Event stream stats */}
            <div style={{ padding: '16px', borderRadius: '10px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div style={sectionLabel}>Stream de eventos</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '12px' }}>
                {[
                  { label: 'Total eventos', value: events.length, color: '#8875ff' },
                  { label: 'Notificaciones', value: notifications.length, color: '#ffa940' },
                  { label: 'Errores', value: events.filter(e => e.type === 'error').length, color: '#ff4d6d' },
                  { label: 'Agente activo', value: events.filter(e => e.type === 'agent_action').length, color: '#00d4a0' },
                ].map(s => (
                  <div key={s.label} style={{ textAlign: 'center', padding: '10px', borderRadius: '8px', background: `${s.color}08`, border: `1px solid ${s.color}15` }}>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.value}</div>
                    <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeSection === 'integrations' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '4px', lineHeight: 1.5 }}>
              Las integraciones se configuran mediante variables de entorno en <code style={{ background: 'rgba(255,255,255,0.06)', padding: '1px 4px', borderRadius: '3px', fontSize: '11px' }}>.env.vps</code>.
            </div>
            {integrations.map(i => <IntegrationRow key={i.name} {...i} />)}
          </div>
        )}

        {activeSection === 'logs' && (
          <div style={{ padding: '14px', borderRadius: '10px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.06)', fontFamily: 'monospace' }}>
            <div style={sectionLabel}>Log reciente del sistema</div>
            {events.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--muted)', fontStyle: 'italic' }}>Sin eventos registrados.</div>
            ) : (
              events.slice(-30).reverse().map((e, i) => (
                <LogEntry
                  key={i}
                  level={e.type === 'error' ? 'error' : e.type === 'heartbeat' ? 'debug' : 'info'}
                  message={e.message ?? e.type ?? 'event'}
                  time={e.timestamp ? new Date(e.timestamp).toLocaleTimeString('es') : '—'}
                />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Shared styles ───────────────────────────────────────────────────
const sectionLabel = { fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: '10px' }
