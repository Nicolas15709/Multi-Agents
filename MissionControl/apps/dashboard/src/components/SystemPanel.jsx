export function SystemPanel({ stream, progress }) {
  const notifications = stream?.notifications || []
  return (
    <div className="panel-section">
      <div className="stack-head">
        <h2 className="section-title">System</h2>
        <span className="section-count">{progress?.percent ?? 0}%</span>
      </div>
      {progress?.mission ? (
        <div className="event-item">
          <strong>{progress.mission.title}</strong>
          <div className="muted">{progress.progress?.done || 0}/{progress.progress?.total || 0} tareas · running {progress.progress?.running || 0} · blocked {progress.progress?.blocked || 0}</div>
        </div>
      ) : null}
      {notifications.length === 0 ? (
        <p className="muted">Sin notificaciones recientes.</p>
      ) : (
        notifications.map((item) => (
          <div key={item.id} className="event-item">{item.summary}</div>
        ))
      )}
    </div>
  )
}
