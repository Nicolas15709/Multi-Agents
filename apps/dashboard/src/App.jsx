import { useState } from 'react'
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
  Target
} from 'lucide-react'
import { useSnapshot } from './useSnapshot'
import { TaskPanel } from './components/TaskPanel'
import { SystemPanel } from './components/SystemPanel'
import { LoginGate } from './components/LoginGate'

const AGENT_ICONS = {
  'agent-0': Terminal,
  'agent-1': Search,
  'agent-2': Paintbrush,
  'agent-3': Code2,
  'agent-4': ShieldCheck,
}

function AgentCard({ agent }) {
  const Icon = AGENT_ICONS[agent.agent_id] || Activity
  const isActive = agent.state !== 'idle'

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="agent-card"
    >
      <div className="agent-head">
        <div className="avatar-container">
          <div className="avatar">
            <Icon size={20} strokeWidth={2.5} />
          </div>
          <div className={`status-dot ${isActive ? 'active' : ''}`} />
        </div>
        <div>
          <div className="agent-name">{agent.display_name}</div>
          <div className="agent-role">{agent.role}</div>
        </div>
      </div>
      <div className="state-pill">{agent.state}</div>
      <p className="muted" style={{ marginTop: '12px', lineHeight: '1.4' }}>
        {agent.personality}
      </p>
    </motion.div>
  )
}

function AgentNode({ agent, index }) {
  const Icon = AGENT_ICONS[agent.agent_id] || Activity
  const isActive = agent.state !== 'idle'
  
  // Posiciones predefinidas para el mapa de oficina gigante (Sample.png)
  const positions = [
    { top: '45%', left: '42%' },
    { top: '65%', left: '55%' },
    { top: '40%', left: '60%' },
    { top: '75%', left: '35%' },
    { top: '25%', left: '65%' },
  ]
  const pos = positions[index] || { top: '50%', left: '50%' }

  return (
    <motion.div 
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className="agent-node"
      style={{ ...pos, zIndex: Math.round(parseFloat(pos.top)) }}
    >
      <div className="avatar-container" style={{ margin: '0 auto 8px', width: 'fit-content' }}>
        <div className={`avatar ${isActive ? 'active-glow' : ''}`} style={{ width: 44, height: 44 }}>
          <Icon size={20} />
        </div>
        <div className={`status-dot ${isActive ? 'active' : ''}`} />
      </div>
      <div className="agent-name" style={{ fontSize: '13px', lineHeight: 1.2, marginBottom: '2px' }}>{agent.display_name}</div>
      <div className="agent-role" style={{ fontSize: '10px', opacity: 0.8 }}>{agent.role}</div>
      <div className="state-pill" style={{ fontSize: '10px', padding: '4px 8px', marginTop: '8px' }}>
        {agent.state}
      </div>
    </motion.div>
  )
}

export default function App() {
  const [entered, setEntered] = useState(true)
  const snapshot = useSnapshot()
  const { activeMission, agents = [], tasks = [], stream = { events: [], notifications: [] } } = snapshot

  if (!entered) {
    return <LoginGate onLogin={() => setEntered(true)} />
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Layers className="text-indigo-400" size={24} />
          <div className="brand">VIRTUAL AGENCY</div>
        </div>
        <div className="badge">
          <Zap size={12} fill="currentColor" style={{ marginRight: 6 }} />
          Runtime Active
        </div>
      </header>

      <main className="layout">
        <section className="panel left-stack">
          <h2 className="section-title">
            <Activity size={14} /> Team Operatives
          </h2>
          <div className="scroll-area" style={{ overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
            <AnimatePresence mode="popLayout">
              {agents.map((agent) => (
                <AgentCard key={agent.agent_id} agent={agent} />
              ))}
            </AnimatePresence>
          </div>
        </section>

        <section className="panel room">
          <div className="room-world">
            <div className="isometric-grid" />
            <div className="stage">
              {agents.map((agent, i) => (
                <AgentNode key={agent.agent_id} agent={agent} index={i} />
              ))}
            </div>
          </div>
        </section>

        <aside className="panel right-stack">
          <div className="mission-box">
            <h2 className="section-title">
              <Target size={14} /> Mission Objective
            </h2>
            <div className="agent-name" style={{ fontSize: '1.1rem', marginBottom: '8px' }}>
              {activeMission?.title || 'System Idle'}
            </div>
            <p className="muted" style={{ fontSize: '0.85rem', marginBottom: '12px' }}>
              {activeMission?.goal || 'Awaiting mission deployment...'}
            </p>
            <div className={`badge ${activeMission ? '' : 'muted'}`} style={{ background: 'rgba(255,255,255,0.05)', color: '#fff' }}>
              Status: {activeMission?.status || 'Standby'}
            </div>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <h2 className="section-title">
              <Terminal size={14} /> Operations Feed
            </h2>
            <div className="event-feed">
              {stream.events.slice().reverse().map((event) => (
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={event.id} 
                  className={`event-item ${event.actor !== 'system' ? 'working' : ''}`}
                >
                  <span style={{ color: 'var(--muted)', fontWeight: 600 }}>[{event.actor || 'sys'}]</span> {event.summary}
                </motion.div>
              ))}
            </div>
          </div>

          <SystemPanel stream={stream} />
        </aside>
      </main>
    </div>
  )
}

