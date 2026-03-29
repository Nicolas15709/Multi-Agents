import { Activity, Clock3, Blocks, ShieldAlert } from 'lucide-react'

function formatTime(value) {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export function MissionInspector({ mission, tasks = [], agents = [], meta = {} }) {
  const assignedAgents = agents.filter((agent) => agent.active_mission_id === mission?.id || tasks.some((task) => task.agent_id === agent.agent_id))
  const runningTask = tasks.find((task) => task.status === 'running')
  const blockedTasks = tasks.filter((task) => task.status === 'blocked')

  if (!mission) {
    return <p className="muted" style={{ fontSize: '11px', textAlign: 'center', margin: '20px 0' }}>Sin misión activa para inspeccionar.</p>
  }

  return (
    <div>
      <div className="inspector-grid">
        <div className="inspector-card">
          <div className="stat-label">ID / Hash</div>
          <div className="inspector-value" style={{ fontFamily: 'monospace', color: 'var(--accent-3)' }}>
            {mission.id.split('-')[0] || mission.id}
          </div>
        </div>
        <div className="inspector-card">
          <div className="stat-label">System Source</div>
          <div className="inspector-value">{mission.source || 'runtime'}</div>
        </div>
        <div className="inspector-card">
          <div className="stat-label"><Clock3 size={10} style={{ display: 'inline', marginRight: '4px' }} /> Created</div>
          <div className="inspector-value">{formatTime(mission.created_at)}</div>
        </div>
        <div className="inspector-card">
          <div className="stat-label"><Clock3 size={10} style={{ display: 'inline', marginRight: '4px' }} /> Updated</div>
          <div className="inspector-value">{formatTime(mission.updated_at)}</div>
        </div>
      </div>

      <div className="inspector-list">
        <div className="inspector-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Activity size={12} color="var(--accent)" /> <span className="muted">Running now</span></div>
          <strong style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'right' }}>
            {runningTask ? runningTask.title : meta?.runningTaskTitle || 'No running task'}
          </strong>
        </div>
        <div className="inspector-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Blocks size={12} color="var(--accent-2)" /> <span className="muted">Assigned agents</span></div>
          <strong>{assignedAgents.length} ops</strong>
        </div>
        <div className="inspector-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><ShieldAlert size={12} color="var(--warning)" /> <span className="muted">Blocked issues</span></div>
          <strong>{blockedTasks.length}</strong>
        </div>
        <div className="inspector-row">
          <span className="muted">24x7 Persistence</span>
          <span className="state-pill" style={{ background: mission.allow_24x7 ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.05)', color: mission.allow_24x7 ? 'var(--accent)' : 'var(--muted)' }}>
            {mission.allow_24x7 ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </div>
    </div>
  )
}
