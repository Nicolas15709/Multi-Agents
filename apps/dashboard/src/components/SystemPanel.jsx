export function SystemPanel({ stream }) {
  const notifications = stream?.notifications || []
  return (
    <div className="panel-section">
      <h2 className="section-title">System</h2>
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
