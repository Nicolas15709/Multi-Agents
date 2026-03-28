function formatTime(value) {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

export function MissionInspector({ mission, tasks = [], agents = [] }) {
  const assignedAgents = agents.filter((agent) => agent.active_mission_id === mission?.id || tasks.some((task) => task.agent_id === agent.agent_id))
  const runningTask = tasks.find((task) => task.status === 'running')
  const blockedTasks = tasks.filter((task) => task.status === 'blocked')

  return (
    <section className="panel panel-section">
      <div className="stack-head">
        <h2 className="section-title">Mission inspector</h2>
        <span className="section-count">{tasks.length}</span>
      </div>

      {!mission ? (
        <p className="muted">Sin misión activa para inspeccionar.</p>
      ) : (
        <>
          <div className="inspector-grid">
            <div className="inspector-card">
              <div className="stat-label">Mission ID</div>
              <div className="inspector-value">{mission.id}</div>
            </div>
            <div className="inspector-card">
              <div className="stat-label">Source</div>
              <div className="inspector-value">{mission.source || 'n/a'}</div>
            </div>
            <div className="inspector-card">
              <div className="stat-label">Created</div>
              <div className="inspector-value">{formatTime(mission.created_at)}</div>
            </div>
            <div className="inspector-card">
              <div className="stat-label">Updated</div>
              <div className="inspector-value">{formatTime(mission.updated_at)}</div>
            </div>
          </div>

          <div className="inspector-list">
            <div className="inspector-row">
              <span className="muted">Running now</span>
              <strong>{runningTask ? runningTask.title : 'No running task'}</strong>
            </div>
            <div className="inspector-row">
              <span className="muted">Assigned agents</span>
              <strong>{assignedAgents.length}</strong>
            </div>
            <div className="inspector-row">
              <span className="muted">Blocked tasks</span>
              <strong>{blockedTasks.length}</strong>
            </div>
            <div className="inspector-row">
              <span className="muted">24x7</span>
              <strong>{mission.allow_24x7 ? 'Enabled' : 'Disabled'}</strong>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
