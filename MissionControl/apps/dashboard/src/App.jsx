import { useMemo, useState } from 'react'
import { useSnapshot } from './useSnapshot'
import { TaskPanel } from './components/TaskPanel'
import { SystemPanel } from './components/SystemPanel'
import { LoginGate } from './components/LoginGate'

function AgentCard({ agent }) {
  return (
    <div className="agent-card">
      <div className="agent-head">
        <div className="avatar" />
        <div>
          <div className="agent-name">{agent.display_name}</div>
          <div className="agent-role">{agent.role}</div>
        </div>
      </div>
      <div className="state-pill">{agent.state}</div>
      <p className="muted">{agent.personality}</p>
    </div>
  )
}

function AgentNode({ agent, index }) {
  const positions = [
    { top: '10%', left: '8%' },
    { top: '18%', left: '38%' },
    { top: '52%', left: '18%' },
    { top: '20%', right: '10%' },
    { bottom: '10%', right: '14%' }
  ]

  return (
    <div className="agent-node" style={positions[index % positions.length]}>
      <div className="agent-name">{agent.display_name}</div>
      <div className="agent-role">{agent.role}</div>
      <div className="state-pill">{agent.state}</div>
    </div>
  )
}

function StatCard({ label, value, tone = 'neutral', hint }) {
  return (
    <div className={`stat-card stat-${tone}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
  )
}

function formatTimestamp(value) {
  if (!value) return 'Unknown'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function MissionHighlights({ activeMission, agents, tasks, events, meta }) {
  const stats = useMemo(() => {
    const activeAgents = meta?.activeAgentCount ?? agents.filter((agent) => agent.state !== 'idle').length
    const completedTasks = meta?.completedTaskCount ?? tasks.filter((task) => task.status === 'done' || task.status === 'completed').length
    const missionStatus = activeMission?.status || 'idle'

    return {
      activeAgents,
      completedTasks,
      totalTasks: meta?.taskCount ?? tasks.length,
      eventCount: meta?.eventCount ?? events.length,
      missionStatus,
      blockedTasks: meta?.blockedTaskCount ?? tasks.filter((task) => task.status === 'blocked').length,
    }
  }, [activeMission, agents, tasks, events, meta])

  return (
    <section className="hero-panel panel">
      <div className="hero-copy">
        <div className="eyebrow">Mission overview</div>
        <h1 className="hero-title">{activeMission?.title || 'Mission Control standby'}</h1>
        <p className="hero-text">
          {activeMission?.goal || 'Esperando snapshot del runtime para poblar el estado operativo.'}
        </p>
        <div className="hero-meta">
          <span className="state-pill">{stats.missionStatus}</span>
          <span className="meta-chip">Mode: {activeMission?.mode || 'n/a'}</span>
          <span className="meta-chip">Priority: {activeMission?.priority || 'normal'}</span>
          <span className="meta-chip">Blocked tasks: {stats.blockedTasks}</span>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="Agents active" value={stats.activeAgents} tone="accent" hint={`${meta?.agentCount ?? agents.length} total`} />
        <StatCard label="Tasks done" value={stats.completedTasks} tone="success" hint={`${stats.totalTasks} tracked`} />
        <StatCard label="Feed events" value={stats.eventCount} tone="info" hint="Live mission log" />
      </div>
    </section>
  )
}

export default function App() {
  const [entered] = useState(true)
  const { snapshot, status } = useSnapshot()
  const { activeMission, agents = [], tasks = [], meta = {}, stream = { events: [], notifications: [] } } = snapshot

  if (!entered) {
    return <LoginGate />
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand">MISSION CONTROL</div>
          <div className="topbar-subtitle">Real-time coordination view for agents, tasks and system state.</div>
        </div>
        <div className="topbar-actions">
          <div className="badge">Dashboard scaffold</div>
          <div className={`live-pill ${status.source === 'runtime' ? 'is-live' : 'is-fallback'}`}>
            {status.source === 'runtime' ? 'Runtime snapshot' : 'Mock snapshot'}
          </div>
          <div className="meta-chip">Updated: {formatTimestamp(status.lastUpdated)}</div>
        </div>
      </header>

      <main className="dashboard-shell">
        {status.error ? (
          <section className="panel warning-banner">
            <strong>Snapshot fallback:</strong> no se pudo leer `/snapshot.json`. Mostrando el último estado disponible o mock data.
            <div className="muted">{status.error}</div>
          </section>
        ) : null}

        <MissionHighlights
          activeMission={activeMission}
          agents={agents}
          tasks={tasks}
          events={stream.events}
          meta={meta}
        />

        <div className="dashboard-grid">
          <section className="panel left-stack">
            <div className="stack-head">
              <h2 className="section-title">Agents</h2>
              <span className="section-count">{meta?.agentCount ?? agents.length}</span>
            </div>
            {agents.length === 0 ? (
              <p className="muted">No hay agentes activos.</p>
            ) : (
              agents.map((agent) => <AgentCard key={agent.agent_id} agent={agent} />)
            )}
          </section>

          <section className="panel room">
            <div className="room-header">
              <div>
                <h2 className="section-title">Mission room</h2>
                <p className="muted room-copy">Mapa visual del equipo activo y su distribución operativa.</p>
              </div>
              <div className="meta-chip">{meta?.activeAgentCount ?? agents.length} active</div>
            </div>
            <div className="room-grid" />
            <div className="room-glow room-glow-a" />
            <div className="room-glow room-glow-b" />
            <div className="stage">
              {agents.map((agent, index) => <AgentNode key={agent.agent_id} agent={agent} index={index} />)}
            </div>
          </section>

          <aside className="right-stack">
            <section className="panel mission-box">
              <div className="stack-head">
                <h2 className="section-title">Active mission</h2>
                <span className="state-pill">{activeMission?.status || 'idle'}</span>
              </div>
              <div className="agent-name">{activeMission?.title || 'Sin misión activa'}</div>
              <p className="muted">{activeMission?.goal || 'Esperando datos del runtime...'}</p>
              <div className="meta-list">
                <span className="meta-chip">Mode: {activeMission?.mode || 'n/a'}</span>
                <span className="meta-chip">Priority: {activeMission?.priority || 'normal'}</span>
                <span className="meta-chip">Notifications: {meta?.notificationCount ?? stream.notifications.length}</span>
              </div>
            </section>

            <TaskPanel tasks={tasks} />

            <section className="panel panel-section">
              <div className="stack-head">
                <h2 className="section-title">Event feed</h2>
                <span className="section-count">{meta?.eventCount ?? stream.events.length}</span>
              </div>
              {stream.events.length === 0 ? (
                <p className="muted">Sin eventos todavía.</p>
              ) : (
                stream.events.map((event) => (
                  <div key={event.id} className="event-item">{event.summary}</div>
                ))
              )}
            </section>

            <SystemPanel stream={stream} />
          </aside>
        </div>
      </main>
    </div>
  )
}
