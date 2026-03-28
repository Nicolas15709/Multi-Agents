export function TaskPanel({ tasks = [] }) {
  return (
    <div className="panel-section">
      <h2 className="section-title">Tasks</h2>
      {tasks.length === 0 ? (
        <p className="muted">No hay tareas todavía.</p>
      ) : (
        tasks.map((task) => (
          <div key={task.id} className="task-item">
            <div className="task-head">
              <strong>{task.title}</strong>
              <span className="state-pill">{task.status}</span>
            </div>
            <div className="muted">{task.agent_id} · prioridad {task.priority}</div>
          </div>
        ))
      )}
    </div>
  )
}
