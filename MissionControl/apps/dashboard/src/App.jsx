import React, { useMemo, useState, Suspense, lazy, forwardRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Terminal,
  Search,
  Paintbrush,
  Code2,
  ShieldCheck,
  Activity,
  Zap,
  Layers,
  Target,
  Cpu,
  BarChart3,
  Clock,
  ChevronRight,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useSnapshot } from './useSnapshot'
import { TaskPanel } from './components/TaskPanel'
import { SystemPanel } from './components/SystemPanel'
import { LoginGate } from './components/LoginGate'
import { MissionInspector } from './components/MissionInspector'
import { TimelinePanel } from './components/TimelinePanel'
import { MissionLauncher } from './components/MissionLauncher'
import { ThoughtLogPanel } from './components/ThoughtLogPanel'

// Lazy load the 3D scene to prevent import-time crashes
const MissionRoomScene = lazy(() => import('./components/MissionRoomScene').then(module => ({ default: module.MissionRoomScene })))

const AGENT_ICONS = {
  'agent-0': Terminal,
  'agent-1': Search,
  'agent-2': Paintbrush,
  'agent-3': Code2,
  'agent-4': ShieldCheck,
}

const AGENT_COLORS = {
  'agent-0': ['#6366f1', '#4338ca'],
  'agent-1': ['#06b6d4', '#0891b2'],
  'agent-2': ['#f472b6', '#db2777'],
  'agent-3': ['#10b981', '#059669'],
  'agent-4': ['#f59e0b', '#d97706'],
}

const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 }
  }
}

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
}

const AgentCard = forwardRef(({ agent }, ref) => {
  const Icon = AGENT_ICONS[agent.agent_id] || Activity
  const colors = AGENT_COLORS[agent.agent_id] || ['#6366f1', '#4338ca']
  const isActive = agent.state !== 'idle'

  return (
    <motion.div
      ref={ref}
      variants={staggerItem}
      layout
      className="agent-card"
      whileHover={{ scale: 1.01 }}
    >
      <div className="agent-head">
        <div className="avatar-container">
          <div className="avatar" style={{
            background: `linear-gradient(135deg, ${colors[0]} 0%, ${colors[1]} 100%)`,
            boxShadow: `0 4px 12px ${colors[0]}40`,
          }}>
            <Icon size={18} strokeWidth={2.5} />
          </div>
          <div className={`status-dot ${isActive ? 'active' : ''}`} />
        </div>
        <div style={{ marginLeft: '10px', flex: 1 }}>
          <div className="agent-name">{agent.display_name}</div>
          <div className="agent-role">{agent.role}</div>
        </div>
        <ChevronRight size={14} style={{ color: 'var(--muted)', opacity: 0.4 }} />
      </div>
      <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <div className="state-pill" style={isActive ? {
          background: 'rgba(16, 185, 129, 0.1)',
          color: '#10b981',
          border: '1px solid rgba(16, 185, 129, 0.15)',
        } : {}}>
          {agent.state}
        </div>
      </div>
      <p className="muted" style={{ marginTop: '8px', fontSize: '11px', lineHeight: 1.4, position: 'relative', zIndex: 1 }}>
        {agent.personality}
      </p>
    </motion.div>
  )
})

function StatCard({ label, value, hint, icon: IconComp }) {
  return (
    <motion.div
      className="stat-card"
      whileHover={{ scale: 1.02, borderColor: 'rgba(99, 102, 241, 0.15)' }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {IconComp && <IconComp size={11} style={{ color: 'var(--accent-2)', opacity: 0.7 }} />}
        <div className="stat-label">{label}</div>
      </div>
      <div className="stat-value">{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </motion.div>
  )
}

function MissionHighlights({ activeMission, agents, tasks, events, meta }) {
  const stats = useMemo(() => {
    const activeAgents = meta?.activeAgentCount ?? agents.filter((a) => a.state !== 'idle').length
    const completedTasks = meta?.completedTaskCount ?? tasks.filter((t) => t.status === 'done' || t.status === 'completed').length
    const missionStatus = activeMission?.status || 'idle'

    return {
      activeAgents,
      completedTasks,
      totalTasks: meta?.taskCount ?? tasks.length,
      eventCount: meta?.eventCount ?? events.length,
      missionStatus,
    }
  }, [activeMission, agents, tasks, events, meta])

  return (
    <motion.section
      className="panel mission-highlights"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.5 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div className="eyebrow" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Target size={12} /> Mission Live Activity
          </div>
          <h1 className="mission-title">
            {activeMission?.title || 'Operational Standby'}
          </h1>
          <p className="muted" style={{ maxWidth: '500px', fontSize: '12px', lineHeight: 1.5, marginTop: '4px' }}>
            {activeMission?.goal || 'Esperando snapshot del sistema para sincronizar objetivos estratégicos.'}
          </p>
          <div style={{ display: 'flex', gap: '6px', marginTop: '12px', flexWrap: 'wrap' }}>
            <span className="state-pill" style={{
              background: stats.missionStatus === 'running' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.04)',
              color: stats.missionStatus === 'running' ? '#10b981' : 'var(--muted)',
              border: stats.missionStatus === 'running' ? '1px solid rgba(16, 185, 129, 0.15)' : '1px solid transparent',
            }}>
              {stats.missionStatus}
            </span>
            <span className="badge">
              Mode: {activeMission?.mode || 'Normal'}
            </span>
          </div>
        </div>

        <div className="stats-grid" style={{ minWidth: '320px' }}>
          <StatCard label="Agents" value={stats.activeAgents} hint={`${agents.length} total`} icon={Cpu} />
          <StatCard label="Tasks" value={stats.completedTasks} hint={`${stats.totalTasks} total`} icon={BarChart3} />
          <StatCard label="Events" value={stats.eventCount} hint="Live stream" icon={Clock} />
        </div>
      </div>
    </motion.section>
  )
}

export default function App() {
  const [entered] = useState(true)
  const { snapshot, status, connection } = useSnapshot()
<<<<<<< HEAD
=======
  const { activeMission, agents = [], tasks = [], meta = {}, stream = { events: [], notifications: [] } } = snapshot
  const progress = snapshot?.progress || null
>>>>>>> d05530c8abb00f53582858def9c6ff2f811a81aa

  if (!entered) {
    return <LoginGate />
  }

  if (!snapshot) {
    return (
      <div className="loading-screen">
        <div className="loading-brand">MISSION CONTROL</div>
        <div style={{ opacity: 0.5, fontSize: '13px' }}>Sincronizando con el sistema...</div>
        {status.error && <div style={{ color: '#ef4444', fontSize: '11px', marginTop: '8px' }}>Error: {status.error}</div>}
      </div>
    )
  }

  const { activeMission, agents = [], tasks = [], meta = {}, stream = { events: [], notifications: [] } } = snapshot || {}

  return (
    <div className="app-shell">
      {/* ═══ TOP BAR ═══ */}
      <motion.header
        className="topbar"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers size={20} color="#6366f1" />
          <div className="brand">MISSION CONTROL</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div className={`live-pill ${status.source === 'runtime' ? 'is-live' : 'is-fallback'}`}>
            <Zap size={10} fill="currentColor" />
            {status.source === 'runtime' ? 'Live Runtime' : 'Mock Mode'}
          </div>
          <div className="badge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {connection.state === 'connected' ? <Wifi size={10} /> : <WifiOff size={10} />}
            WS: {connection.state}
          </div>
        </div>
      </motion.header>

      {/* ═══ MAIN LAYOUT ═══ */}
      <main className="layout">

        {/* ── LEFT: Team Operatives ── */}
        <motion.aside
          className="left-stack panel"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15, duration: 0.5 }}
        >
          <h2 className="section-title">
            <Cpu size={12} /> Team Operatives
          </h2>
          <div className="scroll-area">
            <motion.div variants={staggerContainer} initial="hidden" animate="show">
              <AnimatePresence mode="popLayout">
                {agents.map((agent) => (
                  <AgentCard key={agent.agent_id} agent={agent} />
                ))}
              </AnimatePresence>
            </motion.div>
          </div>
        </motion.aside>

        {/* ── CENTER: Highlights + 3D Office + Timeline ── */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '14px', overflow: 'hidden', minHeight: 0 }}>
          <MissionHighlights
            activeMission={activeMission}
            agents={agents}
            tasks={tasks}
            events={stream.events}
            meta={meta}
          />

          <div style={{ flex: 1, display: 'grid', gridTemplateRows: '1fr 200px', gap: '14px', minHeight: 0 }}>
            <Suspense fallback={
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '28px' }}>
                <div style={{ color: 'var(--muted)', fontSize: '11px' }}>Iniciando Oficina Virtual 3D...</div>
              </div>
            }>
              <MissionRoomScene agents={agents} />
            </Suspense>
            <motion.section
              className="panel"
              style={{ padding: '16px' }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              <h2 className="section-title">
                <Activity size={12} /> Mission Timeline
              </h2>
              <div className="scroll-area">
                <TimelinePanel events={stream.events} />
              </div>
            </motion.section>
          </div>
        </section>

        {/* ── RIGHT: Strategic + Tasks + System + Launcher ── */}
        <motion.aside
          className="right-stack"
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <section className="panel mission-box" style={{ padding: '16px' }}>
            <h2 className="section-title">
              <Target size={12} /> Strategic Intel
            </h2>
            <MissionInspector mission={activeMission} tasks={tasks} agents={agents} meta={meta} />
          </section>

          <TaskPanel tasks={tasks} />
          <SystemPanel stream={stream} />

          <div style={{ marginTop: 'auto' }}>
            <MissionLauncher />
<<<<<<< HEAD
          </div>
        </motion.aside>
=======
            <ThoughtLogPanel events={stream.events} />
            <TaskPanel tasks={tasks} />
            <SystemPanel stream={stream} progress={progress} />
          </aside>
        </div>
>>>>>>> d05530c8abb00f53582858def9c6ff2f811a81aa
      </main>
    </div>
  )
}
