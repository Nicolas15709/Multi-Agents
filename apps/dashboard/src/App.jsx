import { useState } from 'react'
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

function AgentNode({ agent }) {
  return (
    <div className="agent-node">
      <div className="agent-name">{agent.display_name}</div>
      <div className="agent-role">{agent.role}</div>
      <div className="state-pill">{agent.state}</div>
    </div>
  )
}

export default function App() {
  const [entered, setEntered] = useState(true)
  const snapshot = useSnapshot()
  const { activeMission, agents = [], tasks = [], stream = { events: [], notifications: [] } } = snapshot

  if (!entered) {
    return <LoginGate />
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">MISSION CONTROL</div>
        <div className="badge">Login-first / Dashboard scaffold</div>
      </header>

      <main className="layout">
        <section className="panel left-stack">
          <h2 className="section-title">Agents</h2>
          {agents.map((agent) => <AgentCard key={agent.agent_id} agent={agent} />)}
        </section>

        <section className="panel room">
          <div className="room-grid" />
          <div className="stage">
            {agents.map((agent) => <AgentNode key={agent.agent_id} agent={agent} />)}
          </div>
        </section>

        <aside className="panel right-stack">
          <div className="mission-box">
            <h2 className="section-title">Active Mission</h2>
            <div className="agent-name">{activeMission?.title || 'Sin misión activa'}</div>
            <p className="muted">{activeMission?.goal || 'Esperando datos del runtime...'}</p>
            <div className="state-pill">{activeMission?.status || 'idle'}</div>
          </div>

          <TaskPanel tasks={tasks} />

          <div className="panel-section">
            <h2 className="section-title">Event Feed</h2>
            {stream.events.map((event) => (
              <div key={event.id} className="event-item">{event.summary}</div>
            ))}
          </div>

          <SystemPanel stream={stream} />
        </aside>
      </main>
    </div>
  )
}
