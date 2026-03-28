function prettyEventType(value) {
  return (value || 'event').replaceAll('_', ' ')
}

function formatTime(value) {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString()
}

export function TimelinePanel({ events = [] }) {
  return (
    <section className="panel panel-section">
      <div className="stack-head">
        <h2 className="section-title">Mission timeline</h2>
        <span className="section-count">{events.length}</span>
      </div>

      {events.length === 0 ? (
        <p className="muted">Sin eventos todavía.</p>
      ) : (
        <div className="timeline-list">
          {events.map((event) => (
            <div key={event.id} className="timeline-item">
              <div className="timeline-dot" />
              <div className="timeline-content">
                <div className="timeline-head">
                  <strong>{event.summary}</strong>
                  <span className="meta-chip">{formatTime(event.created_at)}</span>
                </div>
                <div className="muted">{prettyEventType(event.event_type)} · {event.actor || 'system'}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
